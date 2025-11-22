import os
import sqlite3
from typing import Dict

import pandas as pd


def build_sqlite_from_dict(tables: Dict[str, pd.DataFrame], db_tmp_path: str) -> None:
    """Build a SQLite DB file from a dict of DataFrames and write to db_tmp_path.

    This writes tables, creates basic indexes, and sets pragmas for better read performance.
    The caller should atomically replace the final DB file after this returns.
    """
    conn = sqlite3.connect(db_tmp_path)
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA temp_store=MEMORY;")
    except Exception:
        pass

    for name, df in tables.items():
        # normalize table name
        table_name = name
        try:
            # pandas will create the table; ensure column names are safe strings
            df.columns = [str(c) for c in df.columns]
            df.to_sql(table_name, conn, if_exists="replace", index=False)
        except Exception:
            # fallback: create empty table if df is empty
            try:
                cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (dummy INTEGER);")
            except Exception:
                pass

    # create a handful of helpful indexes if those tables exist
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS ix_stop_times_stop_id ON stop_times(stop_id);")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS ix_stop_times_trip_id ON stop_times(trip_id);")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS ix_trips_service_id ON trips(service_id);")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS ix_trips_route_id ON trips(route_id);")
    except Exception:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_service_id ON calendar(service_id);")
    except Exception:
        pass

    conn.commit()
    conn.close()


def build_sqlite_from_zip(zip_path: str, db_tmp_path: str):
    """Convenience: read GTFS ZIP via existing loader and build a SQLite DB tmp file."""
    from app.core.load_gtfs import load_gtfs_from_zip

    tables = load_gtfs_from_zip(zip_path)
    build_sqlite_from_dict(tables, db_tmp_path)
