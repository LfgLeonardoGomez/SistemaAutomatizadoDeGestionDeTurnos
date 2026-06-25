from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.models.profesional import Profesional
from app.models.super_admin import SuperAdmin

_engine = None
_async_session = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)
admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/auth/login", auto_error=True)


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


async def get_current_profesional(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Profesional:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = await run_in_threadpool(
            jwt.decode,
            token,
            Settings().secret_key,
            algorithms=[Settings().algorithm],
        )
        sub: str | None = payload.get("sub")
        if sub is None:
            raise credentials_exception
        profesional_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(
        select(Profesional).where(
            Profesional.id == profesional_id,
            Profesional.is_active == True,
        )
    )
    profesional = result.scalar_one_or_none()
    if profesional is None:
        raise credentials_exception
    return profesional


async def get_profesional_by_api_key(
    api_key: Annotated[str, Header(alias="X-API-Key")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Profesional:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API Key inválida",
    )
    result = await db.execute(
        select(Profesional).where(
            Profesional.api_key == api_key,
            Profesional.is_active == True,
        )
    )
    profesional = result.scalar_one_or_none()
    if profesional is None:
        raise credentials_exception
    return profesional


async def get_profesional_by_telegram_secret_token(
    secret_token: Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None,
    db: AsyncSession = Depends(get_db),
) -> Profesional:
    if not secret_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing secret token",
        )
    result = await db.execute(
        select(Profesional).where(
            Profesional.telegram_secret_token == secret_token,
            Profesional.is_active == True,
        )
    )
    profesional = result.scalar_one_or_none()
    if profesional is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret token",
        )
    return profesional


SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
CurrentProfesionalDep = Annotated[Profesional, Depends(get_current_profesional)]


async def require_super_admin(
    token: Annotated[str, Depends(admin_oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuperAdmin:
    settings = Settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = await run_in_threadpool(
            jwt.decode,
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        sub: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        if sub is None:
            raise credentials_exception
        if role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado",
            )
        admin_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(
        select(SuperAdmin).where(SuperAdmin.id == admin_id)
    )
    admin = result.scalar_one_or_none()
    if admin is None:
        raise credentials_exception
    return admin


CurrentSuperAdminDep = Annotated[SuperAdmin, Depends(require_super_admin)]


async def require_https(
    x_forwarded_proto: Annotated[str | None, Header(alias="X-Forwarded-Proto")] = None,
) -> None:
    """Reject plain-HTTP requests when running in production."""
    settings = Settings()
    if settings.env == "production":
        proto = x_forwarded_proto or "http"
        if proto.lower() != "https":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HTTPS required",
            )
