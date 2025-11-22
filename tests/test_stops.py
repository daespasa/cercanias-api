from fastapi.testclient import TestClient
from app import app
from app.config.settings import settings
import os
import sqlite3


def _ensure_test_db():
    db_dir = settings.GTFS_DATA_DIR or os.path.join("data", "gtfs")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "gtfs.db")
    # recreate deterministic test DB
    for p in [db_path, db_path + "-wal", db_path + "-shm"]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stops (
            stop_id TEXT PRIMARY KEY,
            stop_name TEXT,
            stop_lat REAL,
            stop_lon REAL
        )
        """
    )
    cur.execute("DELETE FROM stops")
    cur.execute(
        "INSERT INTO stops (stop_id, stop_name, stop_lat, stop_lon) VALUES (?,?,?,?)",
        ("65000", "Estación 65000", 40.0, -3.0),
    )
    cur.execute(
        "INSERT INTO stops (stop_id, stop_name, stop_lat, stop_lon) VALUES (?,?,?,?)",
        ("65001", "Estación 65001", 41.0, -4.0),
    )
    conn.commit()
    conn.close()


# Ensure DB exists before creating TestClient so app startup sees it
_ensure_test_db()
client = TestClient(app)


def test_list_stops_returns_envelope_and_items():
    r = client.get("/stops/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, list)
    assert any(int(s.get("stop_id")) == 65000 for s in data)


def test_get_stop_found_returns_stop():
    r = client.get("/stops/65000")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    data = body.get("data")
    assert isinstance(data, dict)
    assert int(data["stop_id"]) == 65000


def test_get_stop_not_found_returns_404_problem_details():
    r = client.get("/stops/NOPE")
    assert r.status_code == 404
    body = r.json()
    # error responses follow Problem Details structure
    assert body.get("status") == 404
    assert body.get("title") is not None
