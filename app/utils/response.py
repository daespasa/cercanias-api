from typing import Any, Dict, Optional


def success_response(data: Any, meta: Optional[Dict] = None) -> Dict:
    """Formato estándar de respuesta para éxitos.

    Estructura:
    {
      "status": "ok",
      "data": ...,
      "meta": { ... }  # optional
    }
    """
    payload = {"status": "ok", "data": data}
    if meta is not None:
        payload["meta"] = meta
    return payload


def error_response(title: str, status: int, detail: Optional[str] = None, type_: str = "about:blank") -> Dict:
    """Formato estándar de respuesta para errores (Problem Details-like).

    Estructura:
    {
      "type": "about:blank",
      "title": "...",
      "status": 400,
      "detail": "..."
    }
    """
    payload = {"type": type_, "title": title, "status": status, "detail": detail}
    return payload
