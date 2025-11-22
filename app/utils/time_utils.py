from typing import Optional


def parse_hhmmss_to_seconds(t: Optional[str]) -> Optional[int]:
    """Convierte 'HH:MM:SS' a segundos desde medianoche. Devuelve None si t es None o inválido."""
    if not t or not isinstance(t, str):
        return None
    parts = t.split(":")
    try:
        h, m, s = (int(p) for p in parts)
    except Exception:
        return None
    return h * 3600 + m * 60 + s


def seconds_to_hhmmss(sec: Optional[int]) -> Optional[str]:
    if sec is None:
        return None
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
