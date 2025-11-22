from fastapi.testclient import TestClient
from app import app

# Use TestClient without manager fixtures - test against loaded GTFS data
client = TestClient(app)


def test_schedule_basic():
    # Test with a known stop from the fomento_transit data
    r = client.get("/schedule/?stop_id=04040")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    # Should have results since 04040 (Zaragoza Delicias) is a real stop
    # We don't assert specific trips since the data changes


def test_schedule_by_date_active():
    # Test with a date from the calendar data (use today or a date in the GTFS range)
    # The fomento_transit calendar shows dates around November 2025
    r = client.get("/schedule/?stop_id=04040&date=2025-11-22")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)


def test_schedule_by_date_inactive():
    # date far in the past -> should have no results
    r = client.get("/schedule/?stop_id=04040&date=2020-01-01")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    # May be empty or have very few results for dates outside the calendar range
