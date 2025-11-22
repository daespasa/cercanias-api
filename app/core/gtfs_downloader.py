import asyncio
import logging
import os
import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import aiohttp

from app.config.settings import settings
from app.core.gtfs_manager import gtfs_manager

logger = logging.getLogger("cercanias.gtfs_downloader")


class GTFSDownloader:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        # compute destination and meta path; ensure data dir exists
        path = settings.GTFS_PATH
        if os.path.isabs(path):
            self._dest = path
            self._meta_path = f"{self._dest}.meta"
        else:
            data_dir = settings.GTFS_DATA_DIR or "data"
            try:
                os.makedirs(data_dir, exist_ok=True)
            except Exception:
                pass
            self._dest = os.path.join(data_dir, path)
            self._meta_path = f"{self._dest}.meta"

    def _read_meta(self) -> Dict[str, Any]:
        """Load metadata from disk. Accepts JSON format; falls back to legacy simple lines."""
        if not os.path.exists(self._meta_path):
            return {}
        try:
            with open(self._meta_path, "r", encoding="utf-8") as f:
                text = f.read()
                try:
                    data = json.loads(text)
                    return data if isinstance(data, dict) else {}
                except Exception:
                    # legacy parsing
                    out: Dict[str, str] = {}
                    for line in text.splitlines():
                        if line.startswith("ETag:"):
                            out["etag"] = line.split("ETag:", 1)[1].strip()
                        if line.startswith("Last-Modified:"):
                            out["last_modified"] = line.split("Last-Modified:", 1)[1].strip()
                    return out
        except Exception:
            logger.exception("Failed to read GTFS meta file")
            return {}

    def _write_meta(self, meta: Dict[str, Any]) -> None:
        try:
            with open(self._meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("Failed to write GTFS meta file")

    def get_metadata(self) -> Dict[str, Any]:
        return self._read_meta()

    async def _download_once(self) -> bool:
        """Download the GTFS zip if changed. Returns True if downloaded (and reloaded), False otherwise."""
        url = settings.GTFS_ZIP_URL
        dest = self._dest
        headers = {}
        # load previous metadata
        meta = self._read_meta()
        etag = meta.get("etag")
        lastmod = meta.get("last_modified")
        if etag:
            headers["If-None-Match"] = etag
        if lastmod:
            headers["If-Modified-Since"] = lastmod

        timeout = settings.RT_TIMEOUT
        # update checked timestamp
        meta["last_checked_at"] = datetime.now(timezone.utc).isoformat()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    if resp.status == 304:
                        logger.debug("GTFS not modified (304)")
                        meta["status"] = "not_modified"
                        self._write_meta(meta)
                        # propagate minimal meta
                        gtfs_manager.update_metadata({"last_checked_at": meta.get("last_checked_at"), "status": "not_modified"})
                        return False
                    if resp.status != 200:
                        logger.warning(f"GTFS download returned status {resp.status}")
                        meta["status"] = f"error_{resp.status}"
                        self._write_meta(meta)
                        return False
                    # check headers
                    new_etag = resp.headers.get("ETag")
                    new_lm = resp.headers.get("Last-Modified")
                    # write to temp file first
                    tmp = dest + ".tmp"
                    with open(tmp, "wb") as f:
                        while True:
                            chunk = await resp.content.read(1024 * 32)
                            if not chunk:
                                break
                            f.write(chunk)
                    # compute hash and size
                    try:
                        sha256 = hashlib.sha256()
                        size = 0
                        with open(tmp, "rb") as f:
                            for chunk in iter(lambda: f.read(1024 * 64), b""):
                                sha256.update(chunk)
                                size += len(chunk)
                        file_hash = sha256.hexdigest()
                    except Exception:
                        file_hash = None
                        size = None
                    # replace
                    os.replace(tmp, dest)
                    # update meta
                    meta.update({
                        "etag": new_etag,
                        "last_modified": new_lm,
                        "last_downloaded_at": datetime.now(timezone.utc).isoformat(),
                        "file_size": size,
                        "file_hash": file_hash,
                        "status": "downloaded",
                    })
                    self._write_meta(meta)

                    # reload GTFS in thread
                    try:
                        import asyncio as _asyncio

                        await _asyncio.to_thread(gtfs_manager.load, dest)
                    except AttributeError:
                        import concurrent.futures as _cf

                        loop = asyncio.get_event_loop()
                        with _cf.ThreadPoolExecutor() as ex:
                            await loop.run_in_executor(ex, gtfs_manager.load, dest)

                    # record reload time in meta and manager
                    meta["last_reload_at"] = datetime.now(timezone.utc).isoformat()
                    meta["status"] = "reloaded"
                    self._write_meta(meta)
                    try:
                        gtfs_manager.update_metadata(meta)
                    except Exception:
                        logger.exception("Failed to update manager metadata after reload")

                    logger.info("GTFS downloaded and reloaded from %s", url)
                    return True
        except Exception as e:
            logger.exception(f"Error downloading GTFS: {e}")
            meta["status"] = "error"
            meta.setdefault("error_message", str(e))
            self._write_meta(meta)
            return False

    async def _loop(self):
        interval = max(1, settings.GTFS_DOWNLOAD_INTERVAL_HOURS) * 3600
        # initial attempt on start
        try:
            await self._download_once()
        except Exception:
            logger.exception("Initial GTFS download failed")
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                # time to check
                await self._download_once()

    def start(self):
        if self._task and not self._task.done():
            return
        # ensure manager has any existing meta on start
        try:
            meta = self._read_meta()
            if meta:
                gtfs_manager.update_metadata(meta)
        except Exception:
            logger.exception("Failed to load existing GTFS meta into manager on start")

        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._loop())
        logger.info("GTFSDownloader started")

    async def stop(self):
        self._stop.set()
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        logger.info("GTFSDownloader stopped")


gtfs_downloader = GTFSDownloader()
