import logging
import logging.handlers
from typing import Optional
from app.config.settings import settings


def setup_logging():
    """Configura el sistema de logging según `settings`.

    - `LOG_LEVEL`: nivel de logging
    - `LOG_TO_CONSOLE`: activar handler de consola
    - `LOG_FILE`: si se proporciona, habilita RotatingFileHandler
    - `LOG_FORMAT`: formato de mensajes
    """
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    # Avoid duplicate handlers if called multiple times
    if root.handlers:
        return

    root.setLevel(level)
    formatter = logging.Formatter(settings.LOG_FORMAT)

    if settings.LOG_TO_CONSOLE:
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(formatter)
        root.addHandler(console)

    if settings.LOG_FILE:
        file_handler = logging.handlers.RotatingFileHandler(
            settings.LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # library log level adjustments (example)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
