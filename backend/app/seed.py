from passlib.context import CryptContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.profesional import Profesional
from app.models.super_admin import SuperAdmin


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_profesional(session: AsyncSession, settings: Settings) -> None:
    """Seed a default Profesional if none exists."""
    result = await session.execute(select(func.count()).select_from(Profesional))
    count = result.scalar_one()
    if count == 0:
        password = settings.seed_default_password or ""
        profesional = Profesional(
            nombre="Dr. Por Defecto",
            especialidad="Odontología general",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            email="admin@local.dev",
            password_hash=pwd_context.hash(password) if password else "",
            is_active=True,
        )
        session.add(profesional)


async def seed_super_admin(session: AsyncSession, settings: Settings) -> None:
    """Seed a SuperAdmin from env vars if the table is empty. Idempotent."""
    if not settings.super_admin_email or not settings.super_admin_password_hash:
        return
    result = await session.execute(select(func.count()).select_from(SuperAdmin))
    count = result.scalar_one()
    if count == 0:
        admin = SuperAdmin(
            email=settings.super_admin_email,
            password_hash=settings.super_admin_password_hash,
        )
        session.add(admin)
