from fastapi import Header, HTTPException, status, Depends
from app.config.settings import settings


def api_key_required(x_api_key: str | None = Header(None)):
    """Dependencia que valida el header `X-API-Key` si `settings.API_KEY` está configurada.

    Si `settings.API_KEY` es None permite todas las peticiones (modo desarrollo).
    """
    if settings.API_KEY is None:
        return True
    if x_api_key is None or x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")
    return True
