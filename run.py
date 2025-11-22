"""Simple runner for the FastAPI app.

Usage:
  python run.py

Optional environment variables:
  HOST (default 0.0.0.0)
  PORT (default 8000)
  UVICORN_RELOAD (true/false)

This script ensures the configured `GTFS_DATA_DIR` exists before starting.
"""
import os
import sys

def main():
    # ensure project root is on PYTHONPATH when run from repo root
    cwd = os.path.dirname(__file__)
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # import settings and create data dir before app startup
    try:
        from app.config import settings

        data_dir = getattr(settings, "GTFS_DATA_DIR", None)
        if data_dir:
            try:
                os.makedirs(data_dir, exist_ok=True)
            except Exception:
                pass
    except Exception:
        # fallback: ignore if settings not importable
        data_dir = None

    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", "8000"))
    reload_env = os.getenv("UVICORN_RELOAD", "false").lower()
    reload_flag = reload_env in ("1", "true", "yes", "on")

    # run uvicorn programmatically; use module string so reload works
    try:
        import uvicorn

        uvicorn.run("app:app", host=host, port=port, reload=reload_flag)
    except Exception as e:
        print("Failed to start server:", e)
        raise


if __name__ == "__main__":
    main()
