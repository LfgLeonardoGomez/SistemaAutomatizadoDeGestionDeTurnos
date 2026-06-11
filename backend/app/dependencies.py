from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings

_engine = None
_async_session = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = Settings()
        _engine = create_async_engine(settings.database_url, echo=False, future=True)
    return _engine


def _get_sessionmaker():
    global _async_session
    if _async_session is None:
        _async_session = sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session


def _reset_engine_and_sessionmaker() -> None:
    """Reset cached engine and sessionmaker (useful for tests)."""
    global _engine, _async_session
    _engine = None
    _async_session = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = _get_sessionmaker()()
    try:
        yield session
    finally:
        await session.close()


def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
