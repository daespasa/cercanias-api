from fastapi.testclient import TestClient
from app import app
from app.core.gtfs_manager import gtfs_manager

client = TestClient(app)


def setup_module(module):
    import pandas as pd

    gtfs_manager.data = {}
    gtfs_manager.data["routes"] = pd.DataFrame([
        {"route_id": "40T0001C1", "route_short_name": "C1", "route_long_name": "Linea C1", "route_type": 2},
    ])


def test_list_routes():
    r = client.get("/routes/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    assert any(r["route_id"] == "40T0001C1" for r in data)


def test_get_route_found():
    r = client.get("/routes/40T0001C1")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("data")["route_id"] == "40T0001C1"


def test_get_route_not_found():
    r = client.get("/routes/NOPE")
    assert r.status_code == 404
    body = r.json()
    assert body.get("title") is not None
