from fastapi.testclient import TestClient
from app.core import gtfs_manager
import os


def test_stops_empty_by_default():
    from app import app
    client = TestClient(app)
    r = client.get("/stops/?limit=5")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert isinstance(payload["data"], list)


def test_routes_empty_by_default():
    from app import app
    client = TestClient(app)
    r = client.get("/routes/")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert isinstance(payload["data"], list)


def test_schedule_filters_and_limit(monkeypatch, tmp_path):
    # create client first so app startup does not later overwrite our test data
    from app import app
    client = TestClient(app)
    # create minimal stop_times and trips and routes in manager
    gtfs_manager.data = {}
    from pandas import DataFrame

    gtfs_manager.data["stop_times"] = DataFrame([
        {"trip_id": "t1", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_id": "S1", "stop_sequence": 1},
        {"trip_id": "t2", "arrival_time": "09:00:00", "departure_time": "09:00:00", "stop_id": "S1", "stop_sequence": 1},
    ])
    gtfs_manager.data["trips"] = DataFrame([
        {"trip_id": "t1", "service_id": "svc1", "route_id": "40T0001C1"},
        {"trip_id": "t2", "service_id": "svc2", "route_id": "40T0001C1"},
    ])
    gtfs_manager.data["routes"] = DataFrame([
        {"route_id": "40T0001C1", "route_short_name": "C1"}
    ])

    # no calendar/calendar_dates set -> date filtering should not remove results
    # call manager directly to avoid ASGI lifecycle side-effects
    from app.core.gtfs_manager import GTFSManager
    gm = GTFSManager()
    # populate the instance directly
    gm.data = gtfs_manager.data
    res = gm.get_schedule(stop_id="S1", limit=1)
    assert isinstance(res, list)
    assert len(res) == 1


def test_realtime_empty_lists():
    from app import app
    client = TestClient(app)
    r = client.get("/realtime/alerts")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    r = client.get("/realtime/vehicles")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    r = client.get("/realtime/trip_updates")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
