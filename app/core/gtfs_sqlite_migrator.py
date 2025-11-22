"""
gtfs_sqlite_migrator.py

Build or update a normalized SQLite GTFS DB from a GTFS zip or from in-memory `gtfs_manager.data`.

Features:
- Create schema (from `sql/schema_v2.sql`).
- Populate tables from `gtfs_manager.data` when available, otherwise from GTFS zip via `load_gtfs_from_zip`.
- Support ingesting supplemental pandas files (parquet/pkl/csv) for stop_times or rt snapshots.
- Deduplicate using UNIQUE constraints and `INSERT OR IGNORE` or `REPLACE` semantics.
- Atomic swap: build into a temp DB and move into place.

Usage:
  python -m app.core.gtfs_sqlite_migrator build <path_to_zip_or_dir> --out data/gtfs/gtfs.db --pd-dir data/pd_snaps

"""
import os
import sqlite3
import tempfile
import shutil
import argparse
from typing import Optional

import pandas as pd

from app.core.gtfs_manager import gtfs_manager


def _connect(path: str):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _apply_schema(conn: sqlite3.Connection, schema_path: str):
    with open(schema_path, "r", encoding="utf-8") as fh:
        sql = fh.read()
    conn.executescript(sql)


def _df_to_table(conn: sqlite3.Connection, df: pd.DataFrame, table: str, unique_cols: Optional[list] = None):
    if df is None or df.empty:
        return
    # sanitize column names to match DB
    cols = list(df.columns)
    placeholders = ",".join(["?" for _ in cols])
    insert_sql = f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
    cur = conn.cursor()
    cur.executemany(insert_sql, df.astype(object).where(pd.notnull(df), None).values.tolist())


def _load_from_manager(conn: sqlite3.Connection):
    data = gtfs_manager.data
    # feeds: insert a default feed row
    conn.execute("INSERT OR IGNORE INTO feeds (feed_name, loaded_at) VALUES (?, datetime('now'))", ("default",))
    cur = conn.execute("SELECT feed_id FROM feeds ORDER BY feed_id DESC LIMIT 1")
    feed_id = cur.fetchone()[0]

    # routes
    if data.get("routes") is not None and not data.get("routes").empty:
        df = data.get("routes").copy()
        if "route_id" in df.columns:
            df = df.rename(columns={c: c for c in df.columns})
            df["feed_id"] = feed_id
            _df_to_table(conn, df[[c for c in df.columns if c in ("route_id","feed_id","route_short_name","route_long_name","route_type","route_desc","route_color","route_text_color")]], "routes")

    # stops
    if data.get("stops") is not None and not data.get("stops").empty:
        df = data.get("stops").copy()
        _df_to_table(conn, df[[c for c in df.columns if c in ("stop_id","stop_name","stop_desc","stop_lat","stop_lon","zone_id","stop_url","location_type","parent_station","platform_code","wheelchair_boarding")]], "stops")

    # services (calendar)
    if data.get("calendar") is not None and not data.get("calendar").empty:
        df = data.get("calendar").copy()
        # normalize expected columns
        cols = ["service_id","start_date","end_date","monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
        present = [c for c in cols if c in df.columns]
        df = df[present].copy()
        df["feed_id"] = feed_id
        _df_to_table(conn, df[[c for c in df.columns if c in ("service_id","feed_id","start_date","end_date","monday","tuesday","wednesday","thursday","friday","saturday","sunday")]], "services")

    # calendar_dates -> service_exceptions
    if data.get("calendar_dates") is not None and not data.get("calendar_dates").empty:
        df = data.get("calendar_dates").copy()
        if all(c in df.columns for c in ("service_id","date","exception_type")):
            _df_to_table(conn, df[["service_id","date","exception_type"]], "service_exceptions")

    # trips
    if data.get("trips") is not None and not data.get("trips").empty:
        df = data.get("trips").copy()
        cols = [c for c in ["trip_id","route_id","service_id","trip_headsign","direction_id","block_id","shape_id","wheelchair_accessible","bikes_allowed"] if c in df.columns]
        _df_to_table(conn, df[cols], "trips")

    # stop_times
    if data.get("stop_times") is not None and not data.get("stop_times").empty:
        df = data.get("stop_times").copy()
        cols = [c for c in ["trip_id","stop_sequence","arrival_time","departure_time","stop_id","pickup_type","drop_off_type","timepoint"] if c in df.columns]
        _df_to_table(conn, df[cols], "stop_times")

    # compute service_day materialization: for each service_id, create rows service_date where active
    try:
        # load services from DB
        cur = conn.execute("SELECT service_id, start_date, end_date, monday, tuesday, wednesday, thursday, friday, saturday, sunday FROM services")
        services = cur.fetchall()
        for s in services:
            sid = s[0]
            start = s[1] or ""
            end = s[2] or ""
            # determine date range
            if not start or not end:
                continue
            try:
                from datetime import datetime, timedelta

                start_dt = datetime.strptime(start, "%Y%m%d")
                end_dt = datetime.strptime(end, "%Y%m%d")
                cur_dt = start_dt
                rows = []
                while cur_dt <= end_dt:
                    wd = cur_dt.weekday()  # 0 Monday
                    flag = int(s[3 + wd]) if s[3 + wd] is not None else 0
                    if flag == 1:
                        rows.append((sid, cur_dt.strftime("%Y%m%d"), 1))
                    cur_dt = cur_dt + timedelta(days=1)
                if rows:
                    conn.executemany("INSERT OR IGNORE INTO service_day (service_id, service_date, active) VALUES (?, ?, ?)", rows)
            except Exception:
                continue
    except Exception:
        pass


def _ingest_pd_dir(conn: sqlite3.Connection, pd_dir: str):
    if not os.path.isdir(pd_dir):
        return
    for fname in sorted(os.listdir(pd_dir)):
        path = os.path.join(pd_dir, fname)
        try:
            if fname.endswith(".parquet"):
                df = pd.read_parquet(path)
            elif fname.endswith(".pkl") or fname.endswith(".pickle"):
                df = pd.read_pickle(path)
            elif fname.endswith(".csv"):
                df = pd.read_csv(path)
            else:
                continue
        except Exception:
            continue
        # Heuristic: if DataFrame has stop_id and trip_id -> treat as stop_times snapshot
        if "trip_id" in df.columns and "stop_id" in df.columns:
            cols = [c for c in ["trip_id","stop_sequence","arrival_time","departure_time","stop_id","pickup_type","drop_off_type","timepoint"] if c in df.columns]
            _df_to_table(conn, df[cols], "stop_times")


def _ingest_snapshot_file(conn: sqlite3.Connection, path: str):
    """Ingest a single pandas snapshot (parquet/pkl/csv).

    If the snapshot contains `service_date` (YYYYMMDD or YYYY-MM-DD) and stop/trip fields,
    we materialize/update `schedules` for those dates. Otherwise fall back to inserting
    into `stop_times`/`trips` as appropriate.
    """
    fname = os.path.basename(path)
    try:
        if fname.endswith(".parquet"):
            df = pd.read_parquet(path)
        elif fname.endswith(".pkl") or fname.endswith(".pickle"):
            df = pd.read_pickle(path)
        elif fname.endswith(".csv"):
            df = pd.read_csv(path)
        else:
            return
    except Exception:
        return

    # Prefer snapshots that already include a service_date column -> write directly to schedules
    if "service_date" in df.columns and "trip_id" in df.columns and "stop_id" in df.columns:
        # normalize service_date to YYYY-MM-DD
        s = df.copy()
        def _norm(d):
            if pd.isna(d):
                return None
            ds = str(d)
            if '-' in ds:
                return ds
            if len(ds) == 8:
                return f"{ds[0:4]}-{ds[4:6]}-{ds[6:8]}"
            return ds

        s["service_date"] = s["service_date"].apply(_norm)
        # ensure necessary columns exist
        cols = [c for c in ["trip_id","service_date","stop_id","arrival_time","departure_time","stop_sequence","route_id","route_short_name"] if c in s.columns]

        # Insert or replace schedules (use REPLACE to update existing entries for same unique key)
        placeholders = ",".join(["?" for _ in cols])
        insert_sql = f"INSERT OR REPLACE INTO schedules ({','.join(cols)}) VALUES ({placeholders})"
        cur = conn.cursor()
        rows = s[cols].astype(object).where(pd.notnull(s[cols]), None).values.tolist()
        try:
            cur.executemany(insert_sql, rows)
            conn.commit()
        except Exception:
            conn.rollback()
        return

    # fallback: if it looks like stop_times/trips, insert into those tables
    if "trip_id" in df.columns and "stop_id" in df.columns:
        cols = [c for c in ["trip_id","stop_sequence","arrival_time","departure_time","stop_id","pickup_type","drop_off_type","timepoint"] if c in df.columns]
        _df_to_table(conn, df[cols], "stop_times")
        conn.commit()
        return

    if "trip_id" in df.columns and "route_id" in df.columns:
        cols = [c for c in ["trip_id","route_id","service_id","trip_headsign","direction_id","block_id","shape_id"] if c in df.columns]
        _df_to_table(conn, df[cols], "trips")
        conn.commit()
        return


def build_db_from_source(source_path: str, out_db: str, pd_dir: Optional[str] = None):
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    try:
        conn = _connect(tmp_path)
        try:
            schema_path = os.path.join(os.path.dirname(__file__), "sql", "schema_v2.sql")
            _apply_schema(conn, schema_path)
            conn.commit()
            # prefer using already-loaded manager data
            if gtfs_manager.data and any((not df.empty) for df in gtfs_manager.data.values()):
                _load_from_manager(conn)
            else:
                # try to use loader from ZIP
                from app.core.load_gtfs import load_gtfs_from_zip
                if os.path.isdir(source_path):
                    # no zip provided, try manager or pd_dir only
                    pass
                else:
                    try:
                        data = load_gtfs_from_zip(source_path)
                        # temporarily populate manager and reuse loader
                        old = gtfs_manager.data
                        gtfs_manager.data = data
                        try:
                            _load_from_manager(conn)
                        finally:
                            gtfs_manager.data = old
                    except Exception:
                        pass

            # ingest supplemental pd files if provided
            if pd_dir:
                _ingest_pd_dir(conn, pd_dir)

            # materialize schedules for a sliding window around today by default (-2, +7 days)
            try:
                from datetime import datetime, timedelta
                today = datetime.now().date()
                start = (today - timedelta(days=2)).strftime("%Y%m%d")
                end = (today + timedelta(days=7)).strftime("%Y%m%d")
                # For each date in range, insert schedules by joining stop_times->trips->routes for active services
                cur = conn.cursor()
                sd = datetime.strptime(start, "%Y%m%d").date()
                ed = datetime.strptime(end, "%Y%m%d").date()
                d = sd
                while d <= ed:
                    date_key = d.strftime("%Y%m%d")
                    iso_date = d.strftime("%Y-%m-%d")
                    # Insert schedules using SQL join; use INSERT OR REPLACE to update existing
                    try:
                        q = (
                            "INSERT OR REPLACE INTO schedules (trip_id, service_date, stop_id, arrival_time, departure_time, stop_sequence, route_id, route_short_name, feed_id) "
                            "SELECT st.trip_id, ?, st.stop_id, st.arrival_time, st.departure_time, st.stop_sequence, t.route_id, r.route_short_name, f.feed_id "
                            "FROM stop_times st "
                            "JOIN trips t ON st.trip_id = t.trip_id "
                            "LEFT JOIN routes r ON t.route_id = r.route_id "
                            "LEFT JOIN feeds f ON r.feed_id = f.feed_id "
                            "JOIN service_day sd ON sd.service_id = t.service_id AND sd.service_date = ? "
                        )
                        conn.execute(q, (iso_date, date_key))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                    d = d + timedelta(days=1)
            except Exception:
                pass

            conn.commit()
        finally:
            conn.close()

        # atomic move into place
        os.makedirs(os.path.dirname(out_db), exist_ok=True)
        # if out_db exists, backup
        if os.path.exists(out_db):
            bak = out_db + ".bak"
            try:
                os.replace(out_db, bak)
            except Exception:
                pass
        os.replace(tmp_path, out_db)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def ingest_files_into_db(paths: list, db_path: str):
    """Ingest a list of pandas snapshot files into an existing DB atomically.

    Strategy: build a temporary copy of the DB, apply ingestions there, then atomically replace the live DB.
    """
    if not paths:
        return
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)

    tmp_fd, tmp_db = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    try:
        shutil.copy2(db_path, tmp_db)
        conn = _connect(tmp_db)
        try:
            for p in paths:
                _ingest_snapshot_file(conn, p)
        finally:
            conn.close()

        # atomic replace
        bak = db_path + ".ingest.bak"
        try:
            os.replace(db_path, bak)
        except Exception:
            pass
        os.replace(tmp_db, db_path)
    finally:
        if os.path.exists(tmp_db):
            try:
                os.remove(tmp_db)
            except Exception:
                pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["build"], help="build the sqlite db")
    p.add_argument("source", nargs='?', help="path to GTFS zip file or directory (optional)")
    p.add_argument("--out", default=os.path.join("data", "gtfs", "gtfs.db"), help="output sqlite db path")
    p.add_argument("--pd-dir", default=None, help="directory with pandas snapshots (parquet/pkl/csv)")
    args = p.parse_args()

    if args.command == "build":
        build_db_from_source(args.source, args.out, pd_dir=args.pd_dir)

    # support ingesting snapshot files
    if args.command == "ingest":
        # source may be a file or a directory
        src = args.source
        files = []
        if src is None:
            print("No source provided for ingest")
            return
        if os.path.isdir(src):
            for fname in sorted(os.listdir(src)):
                if fname.endswith(('.parquet', '.pkl', '.pickle', '.csv')):
                    files.append(os.path.join(src, fname))
        elif os.path.isfile(src):
            files = [src]
        else:
            print(f"Source not found: {src}")
            return
        ingest_files_into_db(files, args.out)


if __name__ == "__main__":
    main()
