"""Scheduler skeleton — business jobs will be added in C-06 and C-10."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI


def init_scheduler(app: FastAPI) -> None:
    scheduler = AsyncIOScheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    # Dummy job to verify scheduler accepts registrations
    @scheduler.scheduled_job("interval", id="dummy_job", seconds=3600)
    def dummy_job() -> None:
        pass


def shutdown_scheduler(app: FastAPI) -> None:
    scheduler: AsyncIOScheduler | None = getattr(app.state, "scheduler", None)
    if scheduler:
        scheduler.shutdown(wait=False)
