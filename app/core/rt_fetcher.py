import asyncio
import logging
from typing import Optional

import aiohttp
from google.transit import gtfs_realtime_pb2

from app.config.settings import settings
from app.core.gtfs_manager import gtfs_manager

logger = logging.getLogger("cercanias.rt_fetcher")


class RTFetcher:
    def __init__(self):
        self._tasks = []
        self._stop = asyncio.Event()

    async def _fetch_loop(self, name: str, url: str, interval: int, parser):
        """Loop que consulta `url` cada `interval` segundos y pasa el contenido al `parser`."""
        backoff = 1
        while not self._stop.is_set():
            try:
                timeout = settings.RT_TIMEOUT
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=timeout) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            try:
                                feed = gtfs_realtime_pb2.FeedMessage()
                                feed.ParseFromString(data)
                                parser(feed)
                                backoff = 1
                            except Exception as e:
                                logger.exception(f"Failed to parse GTFS-RT {name}: {e}")
                        else:
                            logger.warning(f"RT {name} returned status {resp.status}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error fetching RT {name}: {e}")
                await asyncio.sleep(min(backoff, 60))
                backoff = backoff * 2
            # sleep until next poll (unless stopped)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        loop = loop or asyncio.get_event_loop()
        # create background tasks
        self._tasks.append(loop.create_task(self._fetch_loop("alerts", settings.RT_ALERTS_URL, settings.RT_POLL_INTERVAL, self._parse_alerts)))
        self._tasks.append(loop.create_task(self._fetch_loop("vehicles", settings.RT_VEHICLES_URL, settings.RT_POLL_INTERVAL, self._parse_vehicles)))
        self._tasks.append(loop.create_task(self._fetch_loop("trip_updates", settings.RT_TRIP_UPDATES_URL, settings.RT_POLL_INTERVAL, self._parse_trip_updates)))
        logger.info("RTFetcher started background tasks")

    async def stop(self):
        self._stop.set()
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("RTFetcher stopped")

    # parsers update gtfs_manager.rt_* structures
    def _parse_alerts(self, feed: gtfs_realtime_pb2.FeedMessage):
        alerts = []
        for e in feed.entity:
            if e.HasField("alert"):
                alerts.append(e.alert)
        gtfs_manager.rt_alerts = alerts
        logger.debug(f"Parsed {len(alerts)} alerts")

    def _parse_vehicles(self, feed: gtfs_realtime_pb2.FeedMessage):
        vehicles = []
        for e in feed.entity:
            if e.HasField("vehicle"):
                vehicles.append(e.vehicle)
        gtfs_manager.rt_vehicles = vehicles
        logger.debug(f"Parsed {len(vehicles)} vehicles")

    def _parse_trip_updates(self, feed: gtfs_realtime_pb2.FeedMessage):
        updates = []
        for e in feed.entity:
            if e.HasField("trip_update"):
                updates.append(e.trip_update)
        gtfs_manager.rt_trip_updates = updates
        logger.debug(f"Parsed {len(updates)} trip_updates")


rt_fetcher = RTFetcher()
