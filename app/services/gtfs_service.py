import os
from typing import List, Optional
from app.core.gtfs_manager import gtfs_manager
from app.core.gtfs_sqlite import GTFSStore
from app.config.settings import settings


def _zip_path() -> str:
    """Return the full path to the GTFS zip file, creating data dir if needed."""
    path = settings.GTFS_PATH
    # if GTFS_PATH is absolute, use it directly
    if os.path.isabs(path):
        return path
    dirpath = settings.GTFS_DATA_DIR or "data"
    return os.path.join(dirpath, path)


def load_if_present():
    """Intenta cargar GTFS desde directorio o ZIP si existe.
    
    Si AUTO_DOWNLOAD_GTFS está habilitado, no hace nada ya que el downloader
    se encarga de descargar, extraer y construir la BD automáticamente.
    
    Prioridad: directorio fomento_transit -> ZIP
    Devuelve True si se cargó, False si no existe.
    """
    import logging

    logger = logging.getLogger("cercanias")
    
    # If auto-download is enabled, let the downloader handle everything
    if settings.AUTO_DOWNLOAD_GTFS:
        logger.info("AUTO_DOWNLOAD_GTFS is enabled, skipping manual load (downloader will handle it)")
        return True
    
    # Check for uncompressed directory first
    gtfs_dir = os.path.join(settings.GTFS_DATA_DIR or "data/gtfs", "fomento_transit")
    db_dir = settings.GTFS_DATA_DIR or "data/gtfs"
    db_tmp = os.path.join(db_dir, "gtfs.db.tmp")
    db_final = os.path.join(db_dir, "gtfs.db")
    
    if os.path.isdir(gtfs_dir):
        try:
            # Load from directory into sqlite directly
            from app.core.gtfs_sqlite_loader import build_sqlite_from_directory
            os.makedirs(db_dir, exist_ok=True)
            build_sqlite_from_directory(gtfs_dir, db_tmp)
            os.replace(db_tmp, db_final)
            logger.info(f"GTFS loaded from directory {gtfs_dir} into SQLite DB {db_final}")
            return True
        except Exception as e:
            logger.exception(f"Failed to load GTFS from directory {gtfs_dir}: {e}")
            return False
    
    # Fallback to ZIP loading
    zip_path = _zip_path()
    try:
        os.makedirs(os.path.dirname(zip_path) or ".", exist_ok=True)
    except Exception:
        pass
    if os.path.exists(zip_path):
        try:
            gtfs_manager.load(zip_path)
            logger.info(f"GTFS loaded from {zip_path}")
            # attempt to build a sqlite DB alongside the zip for faster queries
            try:
                from app.core.gtfs_sqlite_loader import build_sqlite_from_zip
                try:
                    build_sqlite_from_zip(zip_path, db_tmp)
                    os.replace(db_tmp, db_final)
                    logger.info(f"GTFS sqlite DB built at {db_final}")
                except Exception:
                    logger.debug("Failed to build sqlite DB for GTFS", exc_info=True)
            except Exception:
                pass
            return True
        except Exception as e:
            logger.exception(f"Failed to load GTFS from {zip_path}: {e}")
            return False
    else:
        logger.warning(f"GTFS not found at {gtfs_dir} or {zip_path}; no data loaded")
        return False



def get_stops(limit: Optional[int] = None):
    # Prefer sqlite store if available (do not use pre-injected manager for reads)
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_stops(limit=limit or 1000)
        except Exception:
            pass
    # fallback to manager only if sqlite not present
    return gtfs_manager.get_stops(limit=limit)


def search_stops(name_query: str, limit: int = 100):
    """Search for stops by name (case-insensitive). Returns list of stop dicts."""
    # Prefer sqlite store for searches
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.search_stops(name_query=name_query, limit=limit)
        except Exception:
            pass
    # fallback to manager only if sqlite not present
    try:
        return gtfs_manager.search_stops(name_query=name_query, limit=limit)
    except Exception:
        return []


def list_stop_names(limit: int = 1000):
    """Return a list of available stops (stop_id, stop_name)."""
    # Prefer sqlite store for listing stop names
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.list_stop_names(limit=limit)
        except Exception:
            pass
    # fallback to manager
    try:
        stops = gtfs_manager.get_stops(limit=limit)
        return [{"stop_id": s.get("stop_id"), "stop_name": s.get("stop_name")} for s in stops]
    except Exception:
        return []


def get_stop(stop_id: str):
    # Prefer sqlite store for single stop lookup
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_stop(stop_id)
        except Exception:
            pass
    return gtfs_manager.get_stop(stop_id)


def get_routes():
    # Prefer sqlite for routes
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_routes()
        except Exception:
            pass
    return gtfs_manager.get_routes()


def get_route(route_id: str):
    # Prefer sqlite for route metadata
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_route(route_id)
        except Exception:
            pass
    return gtfs_manager.get_route(route_id)


def get_route_stops(route_id: str):
    """Return ordered stops for a route. Prefer manager when populated, otherwise sqlite."""
    # Prefer sqlite store for route stops (avoid slow in-memory joins when DB present)
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_route_stops(route_id)
        except Exception:
            pass
    # fallback: try to build from manager stop_times/trips
    try:
        if hasattr(gtfs_manager, 'data'):
            trips = gtfs_manager.data.get('trips')
            stop_times = gtfs_manager.data.get('stop_times')
            stops = gtfs_manager.data.get('stops')
            if trips is not None and stop_times is not None:
                # join in pandas if available
                try:
                    merged = stop_times.merge(trips[['trip_id','direction_id','route_id']], on='trip_id')
                    merged = merged[merged['route_id'] == route_id]
                    merged = merged.sort_values(['direction_id','stop_sequence'])
                    out = []
                    for _, row in merged.iterrows():
                        sid = row['stop_id']
                        srow = None
                        if stops is not None:
                            try:
                                srow = stops[stops['stop_id'] == sid].to_dict('records')[0]
                            except Exception:
                                srow = None
                        out.append({
                            'direction_id': int(row.get('direction_id') if row.get('direction_id') is not None else 0),
                            'stop_sequence': int(row.get('stop_sequence') if row.get('stop_sequence') is not None else 0),
                            'stop_id': sid,
                            'stop_name': srow.get('stop_name') if srow else None,
                            'stop_lat': srow.get('stop_lat') if srow else None,
                            'stop_lon': srow.get('stop_lon') if srow else None,
                        })
                    return out
                except Exception:
                    pass
    except Exception:
        pass
    return []


def get_schedule(stop_id: Optional[str] = None, route_id: Optional[str] = None, date: Optional[str] = None, limit: int = 200) -> List[dict]:
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_schedule(stop_id=stop_id, route_id=route_id, date=date, limit=limit)
        except Exception:
            pass
    return gtfs_manager.get_schedule(stop_id=stop_id, route_id=route_id, date=date, limit=limit)


def get_upcoming_trains(stop_id: str, current_time: Optional[str] = None, limit: int = 10):
    """Get upcoming departures and arrivals for a stop with minutes until departure/arrival."""
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        store = GTFSStore(db_path)
        return store.get_upcoming_trains(stop_id=stop_id, current_time=current_time, limit=limit)
    # No fallback to manager for this specialized query
    return {
        'stop_id': stop_id,
        'stop_name': None,
        'current_time': current_time or '00:00:00',
        'departures': [],
        'arrivals': []
    }
