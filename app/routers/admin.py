from fastapi import APIRouter, Depends
from app.core.gtfs_manager import gtfs_manager
from app.core.security import api_key_required
from app.utils.response import success_response

router = APIRouter(prefix="/admin", tags=["admin"])  # protected by API key dependency when included


@router.get("/gtfs/meta", summary="GTFS metadata", description="Devuelve metadata persistida y en memoria sobre el feed GTFS.")
def get_gtfs_meta():
    """Returns metadata about the GTFS feed (disk meta + manager metadata).

    - `etag`, `last_modified`, `last_downloaded_at`, `file_hash`, `file_size`, `last_reload_at`, `status`, etc.
    """
    disk_meta = {}
    try:
        # try to read meta from downloader if available
        from app.core.gtfs_downloader import gtfs_downloader

        disk_meta = gtfs_downloader.get_metadata() or {}
    except Exception:
        disk_meta = {}

    manager_meta = {}
    try:
        manager_meta = gtfs_manager.get_metadata() or {}
    except Exception:
        manager_meta = {}

    payload = {"disk": disk_meta, "manager": manager_meta}
    return success_response(payload)
