from fastapi.testclient import TestClient
from app import app
from app.core.gtfs_manager import gtfs_manager
import os
import pandas as pd

client = TestClient(app)
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


def setup_module(module):
    # After TestClient is created (which runs lifespan), clear and replace manager data with test fixtures
    gtfs_manager.data = {}
    gtfs_manager._service_cache = {}
    gtfs_manager._schedules_by_date = {}
    
    # create trips, stop_times, routes, calendar
    df_trips = pd.DataFrame([
        {"trip_id": "T1", "route_id": "40T0001C1", "service_id": "SVC1"},
    ])
    df_trips["service_id"] = df_trips["service_id"].astype(str)
    gtfs_manager.data["trips"] = df_trips
    
    df_stop_times = pd.DataFrame([
        {"trip_id": "T1", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_id": 65000, "stop_sequence": 1},
    ])
    df_stop_times["stop_id"] = df_stop_times["stop_id"].astype(int)
    gtfs_manager.data["stop_times"] = df_stop_times
    
    gtfs_manager.data["routes"] = pd.DataFrame([
        {"route_id": "40T0001C1", "route_short_name": "C1"},
    ])
    
    df_cal = pd.DataFrame([
        {"service_id": "SVC1", "monday": 1, "tuesday": 1, "wednesday": 1, "thursday": 1, "friday": 1, "saturday": 0, "sunday": 0, "start_date": "20250101", "end_date": "20251231"},
    ])
    df_cal["service_id"] = df_cal["service_id"].astype(str)
    df_cal["start_date"] = df_cal["start_date"].astype(str)
    df_cal["end_date"] = df_cal["end_date"].astype(str)
    gtfs_manager.data["calendar"] = df_cal
    
    gtfs_manager.data["calendar_dates"] = pd.DataFrame([])


def test_schedule_basic():
    r = client.get("/schedule/?stop_id=65000")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    assert any(e["trip_id"] == "T1" for e in data)


def test_schedule_by_date_active():
    # date within range -> should return entry
    # use a weekday within the calendar range (2025-06-02 is Monday)
    r = client.get("/schedule/?stop_id=65000&date=2025-06-02")
    assert r.status_code == 200
    assert len(r.json().get("data")) >= 1


def test_schedule_by_date_inactive():
    # date outside range -> no results
    r = client.get("/schedule/?stop_id=65000&date=2024-01-01")
    assert r.status_code == 200
    assert len(r.json().get("data")) == 0
