from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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

# Token is obtained out-of-band via the JSON login endpoints (/auth/login,
# /admin/auth/login) and sent on each request as `Authorization: Bearer <token>`.
# HTTPBearer extracts that token and makes Swagger render a single paste-token
# "Authorize" field instead of the (incorrect) OAuth2 password-flow form.
bearer_scheme = HTTPBearer(auto_error=True)


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
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Profesional:
    token = credentials.credentials
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


async def _flexible_lookup_por_api_key(
    db: AsyncSession, x_api_key: str
) -> Profesional | None:
    """Active-professional lookup by ``api_key``, scoped to the flexible dep.

    Same query shape as ``get_profesional_by_api_key`` (kept as a private
    duplicate on purpose — that dependency stays untouched so it remains a
    safe, independent rollback point for ``recordatorios.py``).
    """
    result = await db.execute(
        select(Profesional).where(
            Profesional.api_key == x_api_key,
            Profesional.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def _flexible_lookup_por_bearer_jwt(
    db: AsyncSession, authorization: str
) -> Profesional | None:
    """Active-professional lookup by a ``Bearer <jwt>`` header value.

    Returns ``None`` on any failure (malformed scheme, invalid/expired JWT,
    missing/non-numeric ``sub``, or no matching active professional) instead
    of raising — the caller decides the single shared 401 for the whole
    dependency, so no branch here leaks which step failed.
    """
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    try:
        payload = await run_in_threadpool(
            jwt.decode,
            token,
            Settings().secret_key,
            algorithms=[Settings().algorithm],
        )
        sub: str | None = payload.get("sub")
        if sub is None:
            return None
        profesional_id = int(sub)
    except (JWTError, ValueError):
        return None

    result = await db.execute(
        select(Profesional).where(
            Profesional.id == profesional_id,
            Profesional.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def get_current_profesional_flexible(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Profesional:
    """Resolve a ``Profesional`` from either ``X-API-Key`` or ``Authorization: Bearer``.

    Both headers are individually optional (``Header(default=None)``): declaring
    either as required (``auto_error``/no default) would raise a 401/422 before
    the OR-fallback below can run. Precedence is X-API-Key first (n8n's durable
    machine credential), then Bearer JWT (human/dashboard sessions). Any failure
    on either path — missing headers, invalid key, invalid/expired JWT, malformed
    bearer scheme, or an inactive professional — raises one shared, generic 401 so
    no scheme is leaked to the caller.
    """
    if x_api_key:
        profesional = await _flexible_lookup_por_api_key(db, x_api_key)
        if profesional is not None:
            return profesional

    if authorization:
        profesional = await _flexible_lookup_por_bearer_jwt(db, authorization)
        if profesional is not None:
            return profesional

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )


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
FlexibleProfesionalDep = Annotated[Profesional, Depends(get_current_profesional_flexible)]


async def require_super_admin(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuperAdmin:
    token = credentials.credentials
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
