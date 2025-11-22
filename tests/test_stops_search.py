from fastapi.testclient import TestClient
from app import app
from app.core.gtfs_manager import gtfs_manager
import pandas as pd

client = None


def setup_module(module):
    # Ensure on-disk DB is removed so this test uses the manager fixture
    import os
    # remove possible sqlite DBs in known locations
    paths = [os.path.join("data", "gtfs.db"), os.path.join("data", "gtfs", "gtfs.db")]
    for p in paths:
        for suffix in ["", "-wal", "-shm"]:
            try:
                fp = p + suffix
                if os.path.exists(fp):
                    os.remove(fp)
            except Exception:
                pass
    

    # prevent the app from auto-loading any on-disk GTFS zip during lifespan
    from app.config import settings as _settings
    _settings.settings.GTFS_PATH = "__test_disabled__.zip"

    # create TestClient after clearing DB so lifespan won't build or use sqlite
    global client
    client = TestClient(app)

    # populate manager with deterministic test data
    gtfs_manager.data = {}
    gtfs_manager._service_cache = {}
    gtfs_manager._schedules_by_date = {}

    df_stops = pd.DataFrame([
        {"stop_id": 65000, "stop_name": "Estación", "stop_lat": 40.0, "stop_lon": -3.0},
        {"stop_id": 65001, "stop_name": "Estación", "stop_lat": 41.0, "stop_lon": -4.0},
        {"stop_id": 65002, "stop_name": "Parada de", "stop_lat": 42.0, "stop_lon": -5.0},
    ])
    df_stops["stop_id"] = df_stops["stop_id"].astype(int)
    gtfs_manager.data["stops"] = df_stops


def test_search_stops_matches_partial_name():
    r = client.get("/stops/search?q=estaci")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    # should match two entries containing 'Estación'
    assert any("Estación" in s.get("stop_name", "") for s in data)
    assert any(s.get("stop_id") == 65000 for s in data)


def test_list_names_returns_pairs():
    r = client.get("/stops/names?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    assert all("stop_id" in s and "stop_name" in s for s in data)
