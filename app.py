from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from app.utils.response import error_response
from app.routers import stops, routes, schedule
from app.routers import realtime
from app.services import gtfs_service
from app.core.security import api_key_required
from app.core.logging_config import setup_logging
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncio
from app.config.settings import settings


# inicializar logging lo antes posible
setup_logging()
logger = logging.getLogger("cercanias")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan handler: carga GTFS antes de servir y limpia recursos al cerrar."""
    # carga GTFS en un thread para no bloquear el event loop
    try:
        # ensure data dir exists so services and downloader can write
        try:
            import os

            os.makedirs(settings.GTFS_DATA_DIR, exist_ok=True)
        except Exception:
            pass

        await asyncio.to_thread(gtfs_service.load_if_present)
    except AttributeError:
        # fallback si asyncio.to_thread no está disponible
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as ex:
            await asyncio.get_event_loop().run_in_executor(ex, gtfs_service.load_if_present)
    # start realtime fetcher background tasks
    try:
        from app.core.rt_fetcher import rt_fetcher

        rt_fetcher.start()
        app.state._rt_fetcher = rt_fetcher
    except Exception as e:
        logger.exception(f"Failed to start realtime fetcher: {e}")
    # start GTFS downloader if enabled
    try:
        from app.core.gtfs_downloader import gtfs_downloader

        if settings.AUTO_DOWNLOAD_GTFS:
            gtfs_downloader.start()
            app.state._gtfs_downloader = gtfs_downloader
            # expose persisted metadata on startup so restarts know last download/check info
            try:
                meta = gtfs_downloader.get_metadata()
                if meta:
                    # update manager and store on app.state for easy access
                    try:
                        from app.core.gtfs_manager import gtfs_manager

                        gtfs_manager.update_metadata(meta)
                    except Exception:
                        logger.exception("Failed to update gtfs_manager with persisted meta")
                    app.state.gtfs_meta = meta
                    logger.info("Loaded GTFS metadata from disk: %s", {k: meta.get(k) for k in ["last_downloaded_at", "last_reload_at", "etag", "last_modified", "status"]})
            except Exception:
                logger.exception("Failed to read GTFS downloader metadata on startup")
    except Exception as e:
        logger.exception(f"Failed to start GTFS downloader: {e}")
    yield
    # shutdown: stop realtime fetcher if running
    rt = getattr(app.state, "_rt_fetcher", None)
    if rt:
        try:
            await rt.stop()
        except Exception:
            logger.exception("Error while stopping RT fetcher")


# crear la app con lifespan
app = FastAPI(
    title="Cercanías API",
    description="API moderna para consultar datos GTFS de Renfe Cercanías",
    version="1.0.0",
    lifespan=lifespan,
)

# aplicar dependencia de API key a todos los routers al registrarlos
app.include_router(stops.router, dependencies=[Depends(api_key_required)])
app.include_router(routes.router, dependencies=[Depends(api_key_required)])
app.include_router(schedule.router, dependencies=[Depends(api_key_required)])
app.include_router(realtime.router, dependencies=[Depends(api_key_required)])
from app.routers import admin as admin_router
app.include_router(admin_router.router, dependencies=[Depends(api_key_required)])


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware simple para registrar peticiones entrantes y respuestas.

    Registra: method, path, remote, status_code, elapsed_ms
    """
    import time

    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.1f}ms)")
    return response



@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    payload = error_response(title=str(exc.detail), status=exc.status_code, detail=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log exception if available
    try:
        import traceback

        tb = traceback.format_exc()
        logger.exception(tb)
    except Exception:
        tb = None
    payload = error_response(title="Internal Server Error", status=500, detail=str(exc))
    return JSONResponse(status_code=500, content=payload)
