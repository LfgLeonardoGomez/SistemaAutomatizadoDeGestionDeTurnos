import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.scheduler.jobs import init_scheduler, shutdown_scheduler


class TestSchedulerSkeleton:
    """Tests for APScheduler skeleton integration."""

    def test_scheduler_starts_and_is_accessible(self, client):
        """Scenario: Scheduler starts with application."""
        from app.main import app
        scheduler = getattr(app.state, "scheduler", None)
        assert scheduler is not None
        assert isinstance(scheduler, AsyncIOScheduler)
        assert scheduler.running is True

    @pytest.mark.asyncio
    async def test_scheduler_shutdown_gracefully(self, monkeypatch):
        """Scenario: Scheduler shuts down gracefully."""
        import asyncio
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")

        from fastapi import FastAPI
        from app.scheduler.jobs import init_scheduler, shutdown_scheduler

        app = FastAPI()
        init_scheduler(app)
        scheduler = app.state.scheduler
        assert scheduler.running is True
        shutdown_scheduler(app)
        # Allow event loop to process shutdown
        await asyncio.sleep(0.05)
        assert scheduler.running is False

    def test_scheduler_accepts_job_registration(self, client):
        """Scenario: Scheduler accepts job registration."""
        from app.main import app
        scheduler: AsyncIOScheduler = app.state.scheduler

        def new_dummy_job():
            pass

        job = scheduler.add_job(new_dummy_job, "interval", seconds=3600, id="new_dummy")
        assert job is not None
        jobs = scheduler.get_jobs()
        assert any(j.id == "new_dummy" for j in jobs)
