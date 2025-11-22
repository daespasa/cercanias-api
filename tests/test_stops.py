from fastapi.testclient import TestClient
from app import app

# Use TestClient without overwriting the database - test against loaded GTFS data
client = TestClient(app)


def test_list_stops_returns_envelope_and_items():
    r = client.get("/stops/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_stop_found_returns_stop():
    # Test with a known stop from the fomento_transit data
    r = client.get("/stops/04040")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, dict)
    assert data["stop_id"] == "04040"
    assert "Zaragoza Delicias" in data["stop_name"]


def test_get_stop_not_found_returns_404_problem_details():
    r = client.get("/stops/NOPE")
    assert r.status_code == 404
    body = r.json()
    # error responses follow Problem Details structure
    assert body.get("status") == 404
    assert body.get("title") is not None
