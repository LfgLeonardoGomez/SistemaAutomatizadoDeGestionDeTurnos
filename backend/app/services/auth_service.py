import secrets
from datetime import datetime, timezone, timedelta

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import Settings
from app.models.profesional import Profesional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(profesional_id: int, email: str, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {
        "sub": str(profesional_id),
        "email": email,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_super_admin_access_token(
    id: int, email: str, settings: Settings
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {
        "sub": str(id),
        "email": email,
        "role": "super_admin",
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


async def authenticate_profesional(
    db: AsyncSession, email: str, password: str
) -> Profesional | None:
    result = await db.execute(
        select(Profesional).where(
            Profesional.email == email,
            Profesional.is_active == True,
        )
    )
    profesional = result.scalar_one_or_none()
    if profesional is None:
        return None
    if not verify_password(password, profesional.password_hash):
        return None
    return profesional


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def generate_telegram_secret_token() -> str:
    return secrets.token_urlsafe(32)


async def set_profesional_api_key(
    db: AsyncSession, profesional: Profesional
) -> str:
    api_key = generate_api_key()
    profesional.api_key = api_key
    await db.commit()
    await db.refresh(profesional)
    return api_key
