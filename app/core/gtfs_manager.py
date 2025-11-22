from typing import Optional, List, Dict
import pandas as pd
import numpy as np


class GTFSManager:
    def __init__(self) -> None:
        self.data: Dict[str, pd.DataFrame] = {}
        # containers for GTFS-RT data
        self.rt_alerts = []
        self.rt_vehicles = []
        self.rt_trip_updates = []
        # metadata about the GTFS zip and last operations
        # Example keys: last_downloaded_at, etag, last_modified, file_size, file_hash, last_checked_at, last_reload_at, status
        self.metadata: Dict[str, str] = {}
        # cache of active service_ids keyed by YYYYMMDD date string
        self._service_cache: Dict[str, set] = {}
        # cache of prebuilt schedule DataFrames per date (YYYYMMDD)
        self._schedules_by_date: Dict[str, pd.DataFrame] = {}

    def load(self, zip_path: str) -> None:
        from app.core.load_gtfs import load_gtfs_from_zip

        import logging
        logger = logging.getLogger("cercanias")
        from time import perf_counter
        start = perf_counter()

        self.data = load_gtfs_from_zip(zip_path)

        # normalize expected tables
        for k in ["stops", "routes", "trips", "stop_times", "calendar", "agency"]:
            if k not in self.data:
                self.data[k] = pd.DataFrame()
        # calendar_dates may also exist
        if "calendar_dates" not in self.data:
            self.data["calendar_dates"] = pd.DataFrame()

        # normalize date columns if present
        if not self.data.get("calendar").empty:
            for col in ["start_date", "end_date"]:
                if col in self.data["calendar"].columns:
                    self.data["calendar"][col] = self.data["calendar"][col].astype(str)
        # record reload time
        try:
            from datetime import datetime, timezone

            self.metadata["last_reload_at"] = datetime.now(timezone.utc).isoformat()
            self.metadata.setdefault("status", "loaded")
            # clear any cached service date lookups when reloading data
            try:
                self._service_cache = {}
            except Exception:
                pass
            # clear schedule cache
            try:
                self._schedules_by_date = {}
            except Exception:
                pass
        except Exception:
            pass

        # precompute schedule for today (local system date) to speed up typical queries
        try:
            from datetime import datetime

            today = datetime.now().date()
            today_str = today.strftime("%Y%m%d")
            sched_df = self._build_schedule_for_date(today_str)
            if sched_df is not None:
                self._schedules_by_date[today_str] = sched_df
                try:
                    self.metadata["today_schedule_count"] = str(len(sched_df))
                except Exception:
                    pass
        except Exception:
            pass

        # log load summary
        try:
            end = perf_counter()
            elapsed_ms = (end - start) * 1000.0
            counts = {k: (len(v) if hasattr(v, "__len__") else 0) for k, v in self.data.items()}
            logger.info(
                f"GTFS loaded: routes={counts.get('routes',0)} stops={counts.get('stops',0)} trips={counts.get('trips',0)} stop_times={counts.get('stop_times',0)} calendar={counts.get('calendar',0)} calendar_dates={counts.get('calendar_dates',0)} agency={counts.get('agency',0)}; build_time={elapsed_ms:.1f}ms"
            )
        except Exception:
            pass

    def update_metadata(self, meta: Dict[str, str]) -> None:
        """Merge provided metadata into manager.metadata."""
        if not isinstance(meta, dict):
            return
        self.metadata.update({k: v for k, v in meta.items() if v is not None})

    def get_metadata(self) -> Dict[str, str]:
        """Return a shallow copy of known metadata."""
        return dict(self.metadata)

    def _service_active_on(self, service_id: str, date_str: str) -> bool:
        """Determina si el service_id está activo en la fecha YYYYMMDD.

        Usa `calendar` y `calendar_dates`.
        """
        if not date_str:
            return True
        # check calendar
        cal = self.data.get("calendar", pd.DataFrame())
        cd = self.data.get("calendar_dates", pd.DataFrame())
        active = False
        if not cal.empty and "service_id" in cal.columns:
            row = cal.loc[cal["service_id"] == service_id]
            if not row.empty:
                # parse weekday flags
                try:
                    r = row.iloc[0]
                    y = int(date_str[0:4])
                    m = int(date_str[4:6])
                    d = int(date_str[6:8])
                    from datetime import date

                    weekday = date(y, m, d).weekday()  # 0 = Monday
                    weekday_flag = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][weekday]
                    if weekday_flag in r.index and int(r[weekday_flag]) == 1:
                        # check date range
                        if ("start_date" in r.index and "end_date" in r.index) and r["start_date"] and r["end_date"]:
                            if r["start_date"] <= date_str <= r["end_date"]:
                                active = True
                        else:
                            active = True
                except Exception:
                    active = False
        # override with calendar_dates exceptions
        if not cd.empty and "service_id" in cd.columns and "date" in cd.columns:
            overrides = cd.loc[cd["service_id"] == service_id]
            if not overrides.empty:
                # exception_type: 1 add, 2 remove
                row = overrides.loc[overrides["date"] == date_str]
                if not row.empty:
                    et = int(row.iloc[0]["exception_type"]) if "exception_type" in row.columns else 0
                    if et == 1:
                        return True
                    if et == 2:
                        return False
        return active
    def _active_service_ids(self, date_str: str) -> set:
        """Compute a set of service_id values active on the given YYYYMMDD date_str.

        This inspects `calendar` and `calendar_dates` in a vectorized manner.
        """
        cal = self.data.get("calendar", pd.DataFrame())
        cd = self.data.get("calendar_dates", pd.DataFrame())
        active = set()
        if not cal.empty and "service_id" in cal.columns:
            # Determine weekday flag
            try:
                from datetime import datetime

                dt = datetime.strptime(date_str, "%Y%m%d")
                weekday_flag = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][dt.weekday()]
            except Exception:
                # try accepting YYYY-MM-DD
                try:
                    from datetime import datetime

                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    weekday_flag = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][dt.weekday()]
                    date_str = dt.strftime("%Y%m%d")
                except Exception:
                    weekday_flag = None

            if weekday_flag and weekday_flag in cal.columns:
                c = cal.copy()
                # Ensure date strings and flags are present
                for dcol in ("start_date", "end_date"):
                    if dcol not in c.columns:
                        c[dcol] = ""
                # normalize columns to strings
                c["start_date"] = c["start_date"].fillna("").astype(str)
                c["end_date"] = c["end_date"].fillna("").astype(str)
                # weekday flag as numeric
                try:
                    flag = c[weekday_flag].fillna(0).astype(int)
                except Exception:
                    # fallback if flags are stored as strings
                    flag = c[weekday_flag].fillna("0").astype(str).str.strip().replace("", "0").astype(int)

                mask_weekday = flag == 1
                mask_range = ((c["start_date"] == "") | (c["start_date"] <= date_str)) & ((c["end_date"] == "") | (c["end_date"] >= date_str))
                mask = mask_weekday & mask_range
                try:
                    sids = c.loc[mask, "service_id"].dropna().astype(str).tolist()
                    active.update(sids)
                except Exception:
                    pass
        # apply calendar_dates overrides
        if not cd.empty and "service_id" in cd.columns and "date" in cd.columns:
            try:
                cdd = cd.copy()
                cdd["date"] = cdd["date"].astype(str)
                matches = cdd.loc[cdd["date"] == date_str]
                if not matches.empty:
                    # exception_type: 1 add, 2 remove
                    for _, row in matches.iterrows():
                        sid = str(row.get("service_id"))
                        try:
                            et = int(row.get("exception_type", 0))
                        except Exception:
                            et = 0
                        if et == 1:
                            active.add(sid)
                        elif et == 2 and sid in active:
                            active.discard(sid)
            except Exception:
                pass
        return active

    def _build_schedule_for_date(self, date_str: str):
        """Build a merged schedule DataFrame for the given date (YYYYMMDD).

        The returned DataFrame contains stop_times merged with trips and route_short_name
        where the trip's service_id is active on the given date. Adds a `service_date`
        column in `YYYY-MM-DD` format to each row to link the schedule to the date.
        """
        if not date_str:
            return None
        st = self.data.get("stop_times", pd.DataFrame())
        trips = self.data.get("trips", pd.DataFrame())
        routes = self.data.get("routes", pd.DataFrame())
        if st.empty or trips.empty:
            return pd.DataFrame()

        # determine active service ids set
        active_sids = self._service_cache.get(date_str)
        if active_sids is None:
            active_sids = self._active_service_ids(date_str)
            self._service_cache[date_str] = active_sids

        if not active_sids:
            # no active services
            return pd.DataFrame()

        # filter trips by active service ids
        try:
            # trips['service_id'] may be numeric or string; compare as str
            trips_local = trips.copy()
            trips_local['service_id'] = trips_local['service_id'].astype(str)
            valid_trips = trips_local[trips_local['service_id'].isin(set(map(str, active_sids)))]
        except Exception:
            valid_trips = trips[trips['service_id'].isin(active_sids)] if 'service_id' in trips.columns else pd.DataFrame()

        if valid_trips.empty:
            return pd.DataFrame()

        # merge stop_times with valid trips
        try:
            merged = st.merge(valid_trips, on='trip_id', how='inner', suffixes=("", "_trip"))
        except Exception:
            # fallback: ensure trip_id exists
            if 'trip_id' not in st.columns or 'trip_id' not in trips.columns:
                return pd.DataFrame()
            merged = st.merge(valid_trips, on='trip_id', how='inner', suffixes=("", "_trip"))

        # attach route_short_name if available
        if not routes.empty and 'route_id' in routes.columns and 'route_id' in merged.columns:
            try:
                routes_subset = routes[[c for c in ['route_id', 'route_short_name'] if c in routes.columns]]
                merged = merged.merge(routes_subset, on='route_id', how='left')
            except Exception:
                pass

        # select sensible columns
        wanted = [c for c in ['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence', 'route_id', 'route_short_name'] if c in merged.columns]
        df_out = merged[wanted].copy()

        # sort and add service_date column in ISO format YYYY-MM-DD
        df_out = df_out.sort_values(by=[c for c in ['route_id', 'stop_sequence'] if c in df_out.columns])
        try:
            # accept YYYYMMDD input and convert
            if '-' in date_str:
                iso_date = date_str
            else:
                iso_date = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except Exception:
            iso_date = date_str
        df_out['service_date'] = iso_date
        return df_out

    def get_stops(self, limit: Optional[int] = None) -> List[Dict]:
        df = self.data.get("stops", pd.DataFrame())
        if df.empty:
            return []
        cols = [c for c in ["stop_id", "stop_name", "stop_lat", "stop_lon"] if c in df.columns]
        df2 = df[cols].copy()
        if limit:
            df2 = df2.head(limit)
        return df2.to_dict(orient="records")

    def get_stop(self, stop_id: str) -> Optional[Dict]:
        df = self.data.get("stops", pd.DataFrame())
        if df.empty or "stop_id" not in df.columns:
            return None

        # try numeric comparison if possible
        try:
            series_num = pd.to_numeric(df["stop_id"], errors="coerce")
            val_num = pd.to_numeric(stop_id, errors="coerce")
            if not np.isnan(val_num):
                row = df.loc[series_num == val_num]
            else:
                # fallback to string compare
                row = df.loc[df["stop_id"].astype(str).str.strip() == str(stop_id).strip()]
        except Exception:
            row = df.loc[df["stop_id"].astype(str).str.strip() == str(stop_id).strip()]
        if row.empty:
            return None
        result = row.iloc[0].to_dict()
        # ensure stop_id is int
        if "stop_id" in result:
            try:
                result["stop_id"] = int(result["stop_id"])
            except (ValueError, TypeError):
                pass
        return result
        return result

    def get_routes(self) -> List[Dict]:
        df = self.data.get("routes", pd.DataFrame())
        if df.empty:
            return []
        cols = [c for c in ["route_id", "route_short_name", "route_long_name", "route_type"] if c in df.columns]
        return df[cols].to_dict(orient="records")

    def get_route(self, route_id: str) -> Optional[Dict]:
        df = self.data.get("routes", pd.DataFrame())
        if df.empty or "route_id" not in df.columns:
            return None
        # try numeric comparison first
        try:
            series_num = pd.to_numeric(df["route_id"], errors="coerce")
            val_num = pd.to_numeric(route_id, errors="coerce")
            if not np.isnan(val_num):
                row = df.loc[series_num == val_num]
            else:
                row = df.loc[df["route_id"].astype(str).str.strip() == str(route_id).strip()]
        except Exception:
            row = df.loc[df["route_id"].astype(str).str.strip() == str(route_id).strip()]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def get_schedule(self, stop_id: Optional[str] = None, route_id: Optional[str] = None, date: Optional[str] = None, limit: int = 200) -> List[Dict]:
        """Devuelve horarios combinando stop_times -> trips -> routes.

        - stop_id: filtra por parada
        - route_id: filtra por ruta
        - date: sin implementar filtros por servicio en profundidad (requeriría calendar parsing)
        """
        stop_times = self.data.get("stop_times", pd.DataFrame())
        trips = self.data.get("trips", pd.DataFrame())
        routes = self.data.get("routes", pd.DataFrame())

        if stop_times.empty or trips.empty:
            return []

        # If a precomputed schedule for the date exists and no extra filters, use it
        df = stop_times.copy()
        date_str = None
        if date:
            date_str = date.replace("-", "")
            try:
                if date_str in self._schedules_by_date and (not stop_id and not route_id):
                    df = self._schedules_by_date[date_str].copy()
                else:
                    df = stop_times.copy()
            except Exception:
                df = stop_times.copy()
        # if date provided, filter trips by service_id using calendar/calendar_dates
        if date and "service_id" in trips.columns:
            # expect date in YYYY-MM-DD or YYYYMMDD
            date_str = date.replace("-", "")
            valid_trips = trips[trips["service_id"].apply(lambda sid: self._service_active_on(sid, date_str) if sid is not None else False)]
            df = df[df["trip_id"].isin(valid_trips["trip_id"]) ]
        if "trip_id" in df.columns and "trip_id" in trips.columns:
            df = df.merge(trips, on="trip_id", how="left", suffixes=("", "_trip"))
        if route_id and "route_id" in df.columns:
            df = df[df["route_id"] == route_id]
        if stop_id and "stop_id" in df.columns:
            # robust matching for numeric or string stop_id
            try:
                series_num = pd.to_numeric(df["stop_id"], errors="coerce")
                val_num = pd.to_numeric(stop_id, errors="coerce")
                if not np.isnan(val_num):
                    df = df[series_num == val_num]
                else:
                    df = df[df["stop_id"].astype(str).str.strip() == str(stop_id).strip()]
            except Exception:
                df = df[df["stop_id"].astype(str).str.strip() == str(stop_id).strip()]

        # attach route short name if available
        if not routes.empty and "route_id" in routes.columns and "route_id" in df.columns:
            df = df.merge(routes[[c for c in ["route_id", "route_short_name"] if c in routes.columns]], on="route_id", how="left")

        # select sensible columns
        wanted = [c for c in ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "route_id", "route_short_name"] if c in df.columns]
        df = df[wanted]
        df = df.sort_values(by=[c for c in ["route_id", "stop_sequence"] if c in df.columns])
        if limit:
            df = df.head(limit)

        # when a date was provided, annotate results with ISO service_date for clarity
        try:
            if date:
                if '-' in date:
                    iso_date = date
                else:
                    iso_date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
                df['service_date'] = iso_date
        except Exception:
            pass

        return df.to_dict(orient="records")

    # Real-time getters
    def get_rt_alerts(self):
        return self.rt_alerts or []

    def get_rt_vehicles(self, route_id: Optional[str] = None, trip_id: Optional[str] = None):
        vehicles = self.rt_vehicles or []
        if route_id:
            vehicles = [v for v in vehicles if getattr(v, "trip", None) and getattr(v.trip, "route_id", None) == route_id]
        if trip_id:
            vehicles = [v for v in vehicles if getattr(v, "trip", None) and getattr(v.trip, "trip_id", None) == trip_id]
        return vehicles

    def get_rt_trip_updates(self, trip_id: Optional[str] = None, route_id: Optional[str] = None):
        updates = self.rt_trip_updates or []
        if trip_id:
            updates = [u for u in updates if getattr(u.trip, "trip_id", None) == trip_id]
        if route_id:
            updates = [u for u in updates if getattr(u.trip, "route_id", None) == route_id]
        return updates


gtfs_manager = GTFSManager()
