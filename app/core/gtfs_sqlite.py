import os
import sqlite3
from typing import List, Dict, Optional


class GTFSStore:
    """A thin SQLite-backed GTFS store wrapper.

    Usage:
      store = GTFSStore(path_to_db)
      store.get_routes()
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self):
        # Open connection with row factory for dict-like rows
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        return conn

    def get_routes(self, limit: int = 1000) -> List[Dict]:
        q = "SELECT route_id, route_short_name, route_long_name, route_type FROM routes LIMIT ?"
        conn = self._connect()
        try:
            cur = conn.execute(q, (limit,))
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()

    def get_route(self, route_id: str) -> Optional[Dict]:
        q = "SELECT * FROM routes WHERE route_id = ? LIMIT 1"
        conn = self._connect()
        try:
            cur = conn.execute(q, (route_id,))
            r = cur.fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def get_route_stops(self, route_id: str) -> List[Dict]:
        """Return stops for a route grouped by direction_id.

        Returns a list of dicts with keys: direction_id, stop_sequence, stop_id, stop_name, stop_lat, stop_lon.
        The result is ordered by direction_id and stop_sequence.
        """
        q = (
            "SELECT t.direction_id as direction_id, st.stop_sequence as stop_sequence, st.stop_id as stop_id, s.stop_name as stop_name, s.stop_lat as stop_lat, s.stop_lon as stop_lon "
            "FROM trips t JOIN stop_times st ON t.trip_id = st.trip_id LEFT JOIN stops s ON st.stop_id = s.stop_id "
            "WHERE t.route_id = ? "
            "ORDER BY t.direction_id, st.stop_sequence"
        )
        conn = self._connect()
        try:
            cur = conn.execute(q, (route_id,))
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()

    def get_stops(self, limit: int = 1000) -> List[Dict]:
        q = "SELECT stop_id, stop_name, stop_lat, stop_lon FROM stops LIMIT ?"
        conn = self._connect()
        try:
            cur = conn.execute(q, (limit,))
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def search_stops(self, name_query: str, limit: int = 100) -> List[Dict]:
        """Case-insensitive search on stop_name using LIKE.

        Returns rows with stop_id, stop_name, stop_lat, stop_lon.
        """
        q = "SELECT stop_id, stop_name, stop_lat, stop_lon FROM stops WHERE lower(stop_name) LIKE ? ORDER BY stop_name LIMIT ?"
        conn = self._connect()
        try:
            term = f"%{name_query.lower()}%"
            cur = conn.execute(q, (term, limit))
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def list_stop_names(self, limit: int = 1000) -> List[Dict]:
        """Return distinct stop_id and stop_name pairs ordered by stop_name."""
        q = "SELECT DISTINCT stop_id, stop_name FROM stops ORDER BY stop_name LIMIT ?"
        conn = self._connect()
        try:
            cur = conn.execute(q, (limit,))
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def get_stop(self, stop_id: str) -> Optional[Dict]:
        q = "SELECT * FROM stops WHERE stop_id = ? LIMIT 1"
        conn = self._connect()
        try:
            cur = conn.execute(q, (stop_id,))
            r = cur.fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    def get_schedule_by_stop_date(self, stop_id: str, date: str, limit: int = 200) -> List[Dict]:
        """Convenience method to query the materialized `schedules` table by stop and date.

        Accepts date in YYYY-MM-DD or YYYYMMDD.
        """
        conn = self._connect()
        try:
            cur = conn.cursor()
            # normalize date
            if '-' in date:
                date_iso = date
                date_key = date.replace('-', '')
            else:
                date_key = date
                date_iso = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"

            # if schedules exists, prefer it
            try:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schedules'")
                if cur.fetchone():
                    q = "SELECT trip_id, arrival_time, departure_time, stop_id, stop_sequence, route_id, route_short_name, service_date FROM schedules WHERE service_date = ? AND stop_id = ? ORDER BY route_id, stop_sequence LIMIT ?"
                    cur.execute(q, (date_iso, str(stop_id), limit))
                    return [dict(r) for r in cur.fetchall()]
            except Exception:
                pass

            # fallback to dynamic query
            return self.get_schedule(stop_id=stop_id, date=date, limit=limit)
        finally:
            conn.close()

    def get_schedule(self, stop_id: Optional[str] = None, route_id: Optional[str] = None, date: Optional[str] = None, limit: int = 200) -> List[Dict]:
        """Query schedule for stop and/or route on a date.

        date should be YYYY-MM-DD or YYYYMMDD. This method will try to use a `schedules`
        materialized table if present; otherwise it computes active service_ids via SQL
        and filters stop_times JOIN trips JOIN routes accordingly.
        """
        conn = self._connect()
        try:
            cur = conn.cursor()

            # normalize date input
            if date:
                if '-' in date:
                    date_iso = date
                    date_key = date.replace('-', '')
                else:
                    date_key = date
                    date_iso = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
            else:
                date_key = None
                date_iso = None

            # if schedules table exists, query it
            try:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schedules'")
                if cur.fetchone():
                    q = "SELECT trip_id, arrival_time, departure_time, stop_id, stop_sequence, route_id, route_short_name, service_date FROM schedules WHERE 1=1"
                    params = []
                    if date_iso:
                        q += " AND service_date = ?"
                        params.append(date_iso)
                    if stop_id:
                        q += " AND stop_id = ?"
                        params.append(str(stop_id))
                    if route_id:
                        q += " AND route_id = ?"
                        params.append(str(route_id))
                    q += " ORDER BY route_id, stop_sequence LIMIT ?"
                    params.append(limit)
                    cur.execute(q, tuple(params))
                    return [dict(r) for r in cur.fetchall()]
            except Exception:
                # fallthrough to dynamic query
                pass

            # dynamic: compute active service_ids
            active_sids = None
            if date_key:
                # services from calendar matching weekday and range
                # Construct union of calendar-based and calendar_dates additions, then remove exceptions
                sql_active = (
                    "WITH base AS ("
                    " SELECT service_id FROM calendar WHERE (start_date IS NULL OR start_date <= ?) AND (end_date IS NULL OR end_date >= ?) "
                    ") "
                    ", added AS (SELECT service_id FROM calendar_dates WHERE date = ? AND exception_type = 1)"
                    ", removed AS (SELECT service_id FROM calendar_dates WHERE date = ? AND exception_type = 2)"
                    " SELECT service_id FROM (SELECT service_id FROM base UNION ALL SELECT service_id FROM added) EXCEPT SELECT service_id FROM removed"
                )
                try:
                    cur.execute(sql_active, (date_key, date_key, date_key, date_key))
                    active_sids = [str(r[0]) for r in cur.fetchall()]
                except Exception:
                    active_sids = None

            # Build main query joining stop_times -> trips -> routes
            q = (
                "SELECT st.trip_id, st.arrival_time, st.departure_time, st.stop_id, st.stop_sequence, t.route_id, r.route_short_name "
                "FROM stop_times st "
                "JOIN trips t ON st.trip_id = t.trip_id "
                "LEFT JOIN routes r ON t.route_id = r.route_id "
                "WHERE 1=1 "
            )
            params = []
            if date_key and active_sids is not None:
                # use IN clause
                placeholders = ','.join('?' for _ in active_sids)
                q += f" AND t.service_id IN ({placeholders})"
                params.extend(active_sids)
            if stop_id:
                q += " AND st.stop_id = ?"
                params.append(str(stop_id))
            if route_id:
                q += " AND t.route_id = ?"
                params.append(str(route_id))
            q += " ORDER BY t.route_id, st.stop_sequence LIMIT ?"
            params.append(limit)

            cur.execute(q, tuple(params))
            rows = [dict(r) for r in cur.fetchall()]

            # annotate service_date when date provided
            if date_iso:
                for r in rows:
                    r['service_date'] = date_iso

            return rows
        finally:
            conn.close()
