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
    """Intenta cargar el ZIP GTFS si existe en `ZIP_PATH`.

    Devuelve True si se cargó, False si no existe el archivo.
    """
    import logging

    logger = logging.getLogger("cercanias")
    zip_path = _zip_path()
    # ensure directory exists for clarity (don't create the zip if missing)
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
                db_dir = settings.GTFS_DATA_DIR or "data"
                db_tmp = os.path.join(db_dir, "gtfs.db.tmp")
                db_final = os.path.join(db_dir, "gtfs.db")
                try:
                    build_sqlite_from_zip(zip_path, db_tmp)
                    # atomic replace
                    os.replace(db_tmp, db_final)
                    logger.info(f"GTFS sqlite DB built at {db_final}")
                except Exception:
                    # ignore loader errors; manager is already loaded
                    logger.debug("Failed to build sqlite DB for GTFS", exc_info=True)
            except Exception:
                pass
            return True
        except Exception as e:
            logger.exception(f"Failed to load GTFS from {zip_path}: {e}")
            return False
    else:
        logger.warning(f"GTFS zip not found at {zip_path}; manager left empty")
        return False



def get_stops(limit: Optional[int] = None):
    # If the in-memory manager already has stops loaded, prefer it (useful for tests).
    try:
        if gtfs_manager.data.get("stops") is not None and not gtfs_manager.data.get("stops").empty:
            return gtfs_manager.get_stops(limit=limit)
    except Exception:
        pass
    # Otherwise prefer sqlite store if available
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_stops(limit=limit or 1000)
        except Exception:
            pass
    return gtfs_manager.get_stops(limit=limit)


def get_stop(stop_id: str):
    # Prefer manager data if present (tests inject data there)
    try:
        if gtfs_manager.data.get("stops") is not None and not gtfs_manager.data.get("stops").empty:
            return gtfs_manager.get_stop(stop_id)
    except Exception:
        pass
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_stop(stop_id)
        except Exception:
            pass
    return gtfs_manager.get_stop(stop_id)


def get_routes():
    try:
        if gtfs_manager.data.get("routes") is not None and not gtfs_manager.data.get("routes").empty:
            return gtfs_manager.get_routes()
    except Exception:
        pass
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_routes()
        except Exception:
            pass
    return gtfs_manager.get_routes()


def get_route(route_id: str):
    try:
        if gtfs_manager.data.get("routes") is not None and not gtfs_manager.data.get("routes").empty:
            return gtfs_manager.get_route(route_id)
    except Exception:
        pass
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_route(route_id)
        except Exception:
            pass
    return gtfs_manager.get_route(route_id)


def get_schedule(stop_id: Optional[str] = None, route_id: Optional[str] = None, date: Optional[str] = None, limit: int = 200) -> List[dict]:
    # Prefer pre-injected manager data when present (tests)
    try:
        has_stop_times = gtfs_manager.data.get("stop_times") is not None and not gtfs_manager.data.get("stop_times").empty
        has_trips = gtfs_manager.data.get("trips") is not None and not gtfs_manager.data.get("trips").empty
        if has_stop_times and has_trips:
            return gtfs_manager.get_schedule(stop_id=stop_id, route_id=route_id, date=date, limit=limit)
    except Exception:
        pass
    db_path = os.path.join(settings.GTFS_DATA_DIR or "data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            store = GTFSStore(db_path)
            return store.get_schedule(stop_id=stop_id, route_id=route_id, date=date, limit=limit)
        except Exception:
            pass
    return gtfs_manager.get_schedule(stop_id=stop_id, route_id=route_id, date=date, limit=limit)
