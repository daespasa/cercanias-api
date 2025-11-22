from fastapi.testclient import TestClient
from app import app

# Use TestClient without manager fixtures - test against loaded GTFS data
client = TestClient(app)


def test_search_stops_matches_partial_name():
    # Search for "Zaragoza" which exists in the fomento_transit data
    r = client.get("/stops/search?q=zaragoza")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    # should find stops with Zaragoza in the name
    assert any("Zaragoza" in s.get("stop_name", "") for s in data)


def test_list_names_returns_pairs():
    r = client.get("/stops/names?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("stop_id" in s and "stop_name" in s for s in data)
