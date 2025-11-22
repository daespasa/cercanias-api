import os
from typing import Optional


def _bool_env(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes", "on")


class Settings:
    """Simple settings loader that reads from environment with sensible defaults.

    This avoids a hard dependency on pydantic-settings while keeping behavior
    predictable for tests and runtime.
    """

    def __init__(self) -> None:
        # Directory where GTFS files and related metadata will be stored
        self.GTFS_DATA_DIR: str = os.getenv("GTFS_DATA_DIR", "data/gtfs")
        # GTFS filename (relative to GTFS_DATA_DIR if GTFS_PATH is not absolute)
        self.GTFS_PATH: str = os.getenv("GTFS_PATH", "fomento_transit.zip")
        self.API_KEY: Optional[str] = os.getenv("API_KEY")

        # Logging
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_TO_CONSOLE: bool = _bool_env("LOG_TO_CONSOLE", True)
        self.LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
        self.LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s | %(levelname)s | %(name)s | %(message)s")

        # GTFS downloader and RT
        self.GTFS_ZIP_URL: str = os.getenv(
            "GTFS_ZIP_URL",
            "https://ssl.renfe.com/ftransit/Fichero_CER_FOMENTO/fomento_transit.zip",
        )
        self.AUTO_DOWNLOAD_GTFS: bool = _bool_env("AUTO_DOWNLOAD_GTFS", False)
        try:
            self.GTFS_DOWNLOAD_INTERVAL_HOURS: int = int(os.getenv("GTFS_DOWNLOAD_INTERVAL_HOURS", "24"))
        except Exception:
            self.GTFS_DOWNLOAD_INTERVAL_HOURS = 24

        self.RT_ALERTS_URL: str = os.getenv("RT_ALERTS_URL", "https://gtfsrt.renfe.com/alerts.pb")
        self.RT_VEHICLES_URL: str = os.getenv("RT_VEHICLES_URL", "https://gtfsrt.renfe.com/vehicle_positions.pb")
        self.RT_TRIP_UPDATES_URL: str = os.getenv("RT_TRIP_UPDATES_URL", "https://gtfsrt.renfe.com/trip_updates.pb")
        try:
            self.RT_POLL_INTERVAL: int = int(os.getenv("RT_POLL_INTERVAL", "30"))
        except Exception:
            self.RT_POLL_INTERVAL = 30
        try:
            self.RT_TIMEOUT: int = int(os.getenv("RT_TIMEOUT", "10"))
        except Exception:
            self.RT_TIMEOUT = 10
        try:
            self.RT_MAX_RETRIES: int = int(os.getenv("RT_MAX_RETRIES", "3"))
        except Exception:
            self.RT_MAX_RETRIES = 3


settings = Settings()
