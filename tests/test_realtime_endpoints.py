from fastapi.testclient import TestClient
from google.transit import gtfs_realtime_pb2
from app import app
from app.core.gtfs_manager import gtfs_manager

client = TestClient(app)


def setup_module(module):
    # prepare in-memory RT data
    vp = gtfs_realtime_pb2.VehiclePosition()
    vp.trip.trip_id = "T100"
    vp.trip.route_id = "40T0001C1"
    vp.position.latitude = 40.1
    vp.position.longitude = -3.1
    vp.current_status = gtfs_realtime_pb2.VehiclePosition.IN_TRANSIT_TO

    tu = gtfs_realtime_pb2.TripUpdate()
    tu.trip.trip_id = "T100"
    tu.trip.route_id = "40T0001C1"

    alert = gtfs_realtime_pb2.Alert()
    alert.header_text.translation.add().text = "Test alert"

    gtfs_manager.rt_vehicles = [vp]
    gtfs_manager.rt_trip_updates = [tu]
    gtfs_manager.rt_alerts = [alert]


def test_get_alerts():
    r = client.get("/realtime/alerts")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert isinstance(body.get("data"), list)


def test_get_vehicles():
    r = client.get("/realtime/vehicles?route_id=40T0001C1")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert len(data) >= 1
    assert data[0].get("route_id") == "40T0001C1"


def test_get_trip_updates():
    r = client.get("/realtime/trip_updates?trip_id=T100")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert len(data) >= 1
    assert data[0].get("trip_id") == "T100"
