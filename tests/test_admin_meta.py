from fastapi.testclient import TestClient
from app.core import gtfs_manager
import os
import json
import sys


def _fresh_app_import():
    # remove cached app modules to force re-evaluation with current env
    to_remove = [k for k in list(sys.modules.keys()) if k.startswith('app')]
    for k in to_remove:
        del sys.modules[k]
    from app import app
    return app


def test_admin_meta_no_meta_file(monkeypatch, tmp_path):
    # point GTFS_DATA_DIR to temp dir
    monkeypatch.setenv("GTFS_DATA_DIR", str(tmp_path))
    # import app after setting env so settings pick it up
    app = _fresh_app_import()
    client = TestClient(app)
    # ensure no meta file exists
    # reload app state by calling the endpoint
    r = client.get("/admin/gtfs/meta")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    data = payload["data"]
    assert "disk" in data and "manager" in data
    assert data["disk"] == {} or data["disk"] is None


def test_admin_meta_with_fake_meta(monkeypatch, tmp_path):
    monkeypatch.setenv("GTFS_DATA_DIR", str(tmp_path))
    # create a fake meta file next to expected zip BEFORE importing app
    zip_name = "fomento_transit.zip"
    zip_path = tmp_path / zip_name
    zip_path.write_bytes(b"fake")
    meta = {"etag": "W/\"abc\"", "last_downloaded_at": "2025-01-01T00:00:00Z", "status": "downloaded"}
    meta_path = str(zip_path) + ".meta"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    app = _fresh_app_import()
    client = TestClient(app)

    r = client.get("/admin/gtfs/meta")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    data = payload["data"]
    # disk meta keys might be strings as written
    assert data["disk"].get("etag") == meta["etag"]
    # manager meta may be empty
    assert isinstance(data["manager"], dict)
