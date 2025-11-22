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
                # Compute weekday for the date (0=Monday, 6=Sunday)
                import datetime
                try:
                    year = int(date_key[0:4])
                    month = int(date_key[4:6])
                    day = int(date_key[6:8])
                    dt = datetime.date(year, month, day)
                    weekday = dt.weekday()  # 0=Monday, 6=Sunday
                    
                    # Map weekday to GTFS calendar columns
                    weekday_cols = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    weekday_col = weekday_cols[weekday]
                    
                    # services from calendar matching weekday and range
                    sql_active = (
                        f"WITH base AS ("
                        f" SELECT service_id FROM calendar "
                        f" WHERE (start_date IS NULL OR start_date <= ?) "
                        f" AND (end_date IS NULL OR end_date >= ?) "
                        f" AND {weekday_col} = 1"
                        f") "
                        ", added AS (SELECT service_id FROM calendar_dates WHERE date = ? AND exception_type = 1)"
                        ", removed AS (SELECT service_id FROM calendar_dates WHERE date = ? AND exception_type = 2)"
                        " SELECT service_id FROM (SELECT service_id FROM base UNION ALL SELECT service_id FROM added) EXCEPT SELECT service_id FROM removed"
                    )
                    cur.execute(sql_active, (date_key, date_key, date_key, date_key))
                    active_sids = [str(r[0]) for r in cur.fetchall()]
                except Exception:
                    active_sids = None

            # Build main query joining stop_times -> trips -> routes
            q = (
                "SELECT st.trip_id, st.arrival_time, st.departure_time, st.stop_id, st.stop_sequence, t.route_id, r.route_short_name, t.trip_headsign "
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

    def get_upcoming_trains(self, stop_id: str, current_time: Optional[str] = None, limit: int = 10) -> Dict:
        """Get upcoming departures and arrivals for a stop.
        
        Args:
            stop_id: Stop ID to query
            current_time: Current time in HH:MM:SS format (defaults to now)
            limit: Maximum number of trains to return for each category
            
        Returns:
            Dict with:
            - stop_id, stop_name, current_time
            - departures: list of upcoming trains departing from this stop
            - arrivals: list of upcoming trains arriving at this stop
            Each train includes: trip_id, route info, headsign, scheduled time, minutes_until
        """
        import datetime
        
        conn = self._connect()
        try:
            cur = conn.cursor()
            
            # Get stop info
            cur.execute("SELECT stop_id, stop_name FROM stops WHERE stop_id = ? LIMIT 1", (stop_id,))
            stop_row = cur.fetchone()
            if not stop_row:
                return {
                    'stop_id': stop_id,
                    'stop_name': None,
                    'current_time': current_time or '00:00:00',
                    'departures': [],
                    'arrivals': []
                }
            
            stop_name = stop_row['stop_name']
            
            # Determine current time
            if not current_time:
                now = datetime.datetime.now()
                current_time = now.strftime('%H:%M:%S')
            
            # Parse current time to minutes since midnight for calculations
            time_parts = current_time.split(':')
            current_minutes = int(time_parts[0]) * 60 + int(time_parts[1])
            
            # Get active service IDs for today
            today = datetime.date.today()
            weekday = today.weekday()  # 0=Monday, 6=Sunday
            date_key = today.strftime('%Y%m%d')
            
            # Map weekday to GTFS column names
            weekday_cols = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            weekday_col = weekday_cols[weekday]
            
            # Get active services from calendar
            active_services_query = f"""
                SELECT DISTINCT service_id FROM calendar 
                WHERE {weekday_col} = 1 
                AND start_date <= ? 
                AND end_date >= ?
            """
            cur.execute(active_services_query, (date_key, date_key))
            active_services = [row['service_id'] for row in cur.fetchall()]
            
            if not active_services:
                return {
                    'stop_id': stop_id,
                    'stop_name': stop_name,
                    'current_time': current_time,
                    'departures': [],
                    'arrivals': []
                }
            
            placeholders = ','.join('?' for _ in active_services)
            
            # Query for DEPARTURES (trains leaving this stop)
            departures_query = f"""
                SELECT 
                    st.trip_id,
                    st.departure_time as scheduled_time,
                    st.stop_sequence,
                    t.trip_headsign,
                    r.route_id,
                    r.route_short_name,
                    r.route_long_name
                FROM stop_times st
                JOIN trips t ON st.trip_id = t.trip_id
                JOIN routes r ON t.route_id = r.route_id
                WHERE st.stop_id = ?
                AND t.service_id IN ({placeholders})
                AND st.departure_time >= ?
                ORDER BY st.departure_time
                LIMIT ?
            """
            
            params = [stop_id] + active_services + [current_time, limit]
            cur.execute(departures_query, params)
            departure_rows = cur.fetchall()
            
            # Query for ARRIVALS (trains arriving at this stop)
            arrivals_query = f"""
                SELECT 
                    st.trip_id,
                    st.arrival_time as scheduled_time,
                    st.stop_sequence,
                    t.trip_headsign,
                    r.route_id,
                    r.route_short_name,
                    r.route_long_name
                FROM stop_times st
                JOIN trips t ON st.trip_id = t.trip_id
                JOIN routes r ON t.route_id = r.route_id
                WHERE st.stop_id = ?
                AND t.service_id IN ({placeholders})
                AND st.arrival_time >= ?
                ORDER BY st.arrival_time
                LIMIT ?
            """
            
            cur.execute(arrivals_query, params)
            arrival_rows = cur.fetchall()
            
            # Helper function to calculate minutes until
            def calculate_minutes_until(scheduled_time_str: str) -> int:
                """Calculate minutes from current_time to scheduled_time."""
                parts = scheduled_time_str.split(':')
                scheduled_minutes = int(parts[0]) * 60 + int(parts[1])
                
                # Handle times past midnight (like 25:30:00 for 1:30 AM next day)
                if scheduled_minutes < current_minutes and scheduled_minutes < 180:  # likely next day
                    scheduled_minutes += 24 * 60
                
                return scheduled_minutes - current_minutes
            
            # Format departures
            departures = []
            for row in departure_rows:
                departures.append({
                    'trip_id': row['trip_id'],
                    'route_short_name': row['route_short_name'],
                    'route_long_name': row['route_long_name'],
                    'trip_headsign': row['trip_headsign'] or 'Sin destino',
                    'headsign': row['trip_headsign'] or 'Sin destino',
                    'direction_id': None,  # Not available in this dataset
                    'departure_time': row['scheduled_time'],
                    'scheduled_time': row['scheduled_time'],
                    'minutes_until': calculate_minutes_until(row['scheduled_time']),
                    'stop_sequence': row['stop_sequence']
                })
            
            # Format arrivals
            arrivals = []
            for row in arrival_rows:
                arrivals.append({
                    'trip_id': row['trip_id'],
                    'route_short_name': row['route_short_name'],
                    'route_long_name': row['route_long_name'],
                    'trip_headsign': row['trip_headsign'] or 'Sin origen',
                    'headsign': row['trip_headsign'] or 'Sin origen',
                    'direction_id': None,  # Not available in this dataset
                    'arrival_time': row['scheduled_time'],
                    'scheduled_time': row['scheduled_time'],
                    'minutes_until': calculate_minutes_until(row['scheduled_time']),
                    'stop_sequence': row['stop_sequence']
                })
            
            return {
                'stop_id': stop_id,
                'stop_name': stop_name,
                'current_time': current_time,
                'departures': departures,
                'arrivals': arrivals
            }
        finally:
            conn.close()
