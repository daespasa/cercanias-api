from fastapi.testclient import TestClient
from app import app
from app.core.gtfs_manager import gtfs_manager
import os
import pandas as pd


def clean_gtfs_db():
    """Remove gtfs.db and related files to force service to use manager."""
    db_path = os.path.join("data", "gtfs.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
    # Also remove WAL/SHM files if they exist
    for suffix in ["-shm", "-wal"]:
        shm_path = db_path + suffix
        if os.path.exists(shm_path):
            try:
                os.remove(shm_path)
            except Exception:
                pass


client = TestClient(app)


def setup_module(module):
    # Clean gtfs.db so the service uses gtfs_manager directly
    clean_gtfs_db()
    
    # After TestClient is created (which runs lifespan), clear and replace manager data with test fixtures
    gtfs_manager.data = {}
    gtfs_manager._service_cache = {}
    gtfs_manager._schedules_by_date = {}
    
    df_stops = pd.DataFrame([
        {"stop_id": 65000, "stop_name": "Estación 65000", "stop_lat": 40.0, "stop_lon": -3.0},
        {"stop_id": 65001, "stop_name": "Estación 65001", "stop_lat": 41.0, "stop_lon": -4.0},
    ])
    # ensure stop_id is stored as int
    df_stops["stop_id"] = df_stops["stop_id"].astype(int)
    gtfs_manager.data["stops"] = df_stops


def test_list_stops():
    r = client.get("/stops/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    assert any(s["stop_id"] == 65000 for s in data)


def test_get_stop_found():
    r = client.get("/stops/65000")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("data")["stop_id"] == 65000


def test_get_stop_not_found():
    r = client.get("/stops/NOPE")
    assert r.status_code == 404
    body = r.json()
    assert body.get("status") == 404
    assert body.get("title") is not None
from fastapi.testclient import TestClient
from app import app
from app.core.gtfs_manager import gtfs_manager
import os
import pandas as pd


client = TestClient(app)


def setup_module(module):
    # After TestClient is created (which runs lifespan), clear and replace manager data with test fixtures
    gtfs_manager.data = {}
    def clean_gtfs_db():
        """Remove gtfs.db and related files to force service to use manager."""
        db_path = os.path.join("data", "gtfs.db")
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
        # Also remove WAL/SHM files if they exist
        for suffix in ["-shm", "-wal"]:
            shm_path = db_path + suffix
            if os.path.exists(shm_path):
                try:
                    os.remove(shm_path)
                except Exception:
                    pass


    client = TestClient(app)


    def setup_module(module):
        # Clean gtfs.db so the service uses gtfs_manager directly
        clean_gtfs_db()
    
        # After TestClient is created (which runs lifespan), clear and replace manager data with test fixtures
        gtfs_manager.data = {}
    gtfs_manager._service_cache = {}
    gtfs_manager._schedules_by_date = {}
    
    df_stops = pd.DataFrame([
        {"stop_id": 65000, "stop_name": "Estación 65000", "stop_lat": 40.0, "stop_lon": -3.0},
        {"stop_id": 65001, "stop_name": "Estación 65001", "stop_lat": 41.0, "stop_lon": -4.0},
    ])
    # ensure stop_id is stored as int
    df_stops["stop_id"] = df_stops["stop_id"].astype(int)
    gtfs_manager.data["stops"] = df_stops


def test_list_stops():
    r = client.get("/stops/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    assert any(s["stop_id"] == 65000 for s in data)


def test_get_stop_found():
    r = client.get("/stops/65000")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("data")["stop_id"] == 65000


def test_get_stop_not_found():
    r = client.get("/stops/NOPE")
    assert r.status_code == 404
    body = r.json()
    assert body.get("status") == 404
    assert body.get("title") is not None
