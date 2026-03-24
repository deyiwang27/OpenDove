from __future__ import annotations

import logging
from collections.abc import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class OpenDoveScheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()

    @property
    def running(self) -> bool:
        return self._scheduler.running

    def add_interval_job(self, func: Callable[[], object], minutes: int, job_id: str) -> None:
        self._scheduler.add_job(
            func,
            IntervalTrigger(minutes=minutes),
            id=job_id,
            replace_existing=True,
        )

    def add_seconds_job(self, func: Callable[[], object], seconds: int, job_id: str) -> None:
        self._scheduler.add_job(
            func,
            IntervalTrigger(seconds=seconds),
            id=job_id,
            replace_existing=True,
        )

    def add_daily_job(self, func: Callable[[], object], hour: int, job_id: str) -> None:
        self._scheduler.add_job(
            func,
            CronTrigger(hour=hour, minute=0),
            id=job_id,
            replace_existing=True,
        )

    def clear_jobs(self) -> None:
        self._scheduler.remove_all_jobs()

    def start(self) -> None:
        if self._scheduler.running:
            return

        self._scheduler.start()
        logger.info("OpenDoveScheduler started")

    def shutdown(self) -> None:
        if not self._scheduler.running:
            return

        self._scheduler.shutdown(wait=False)
        logger.info("OpenDoveScheduler shut down")
