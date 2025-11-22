from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi import Depends
from app.core.security import api_key_required

router = APIRouter(prefix="", tags=["UI"])  # public/simple dashboard route


@router.get("/dashboard", dependencies=[Depends(api_key_required)])
def dashboard():
    """Serve the static dashboard HTML."""
    return FileResponse("app/static/dashboard.html")
