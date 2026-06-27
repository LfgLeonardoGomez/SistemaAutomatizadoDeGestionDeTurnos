import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.scheduler.jobs import init_scheduler, shutdown_scheduler


class TestSchedulerSkeleton:
    """Tests for APScheduler skeleton integration.

    The conftest replaces the FastAPI app's lifespan with a no-op to keep
    APScheduler and the seed out of the test runtime. These tests therefore
    boot the scheduler on a dedicated ``FastAPI()`` instance (which never
    triggers the noop lifespan) and verify its lifecycle and job-registration
    contract.
    """

    @pytest.mark.asyncio
    async def test_scheduler_starts_and_is_accessible(self, monkeypatch):
        """Scenario: Scheduler starts when ``init_scheduler`` is called."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        app = FastAPI()
        init_scheduler(app)
        try:
            scheduler = app.state.scheduler
            assert scheduler is not None
            assert isinstance(scheduler, AsyncIOScheduler)
            assert scheduler.running is True
        finally:
            shutdown_scheduler(app)

    @pytest.mark.asyncio
    async def test_scheduler_shutdown_gracefully(self, monkeypatch):
        """Scenario: Scheduler shuts down gracefully."""
        import asyncio
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        app = FastAPI()
        init_scheduler(app)
        scheduler = app.state.scheduler
        assert scheduler.running is True
        shutdown_scheduler(app)
        # Allow event loop to process shutdown
        await asyncio.sleep(0.05)
        assert scheduler.running is False

    @pytest.mark.asyncio
    async def test_scheduler_accepts_job_registration(self, monkeypatch):
        """Scenario: Scheduler accepts job registration."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        app = FastAPI()
        init_scheduler(app)
        try:
            scheduler: AsyncIOScheduler = app.state.scheduler

            def new_dummy_job():
                pass

            job = scheduler.add_job(new_dummy_job, "interval", seconds=3600, id="new_dummy")
            assert job is not None
            jobs = scheduler.get_jobs()
            assert any(j.id == "new_dummy" for j in jobs)
        finally:
            shutdown_scheduler(app)
