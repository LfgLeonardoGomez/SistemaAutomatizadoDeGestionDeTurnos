from passlib.context import CryptContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profesional import Profesional


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_profesional(session: AsyncSession) -> None:
    """Seed a default Profesional if none exists."""
    result = await session.execute(select(func.count()).select_from(Profesional))
    count = result.scalar_one()
    if count == 0:
        profesional = Profesional(
            nombre="Dr. Por Defecto",
            especialidad="Odontología general",
            duracion_turno=30,
            horario_inicio="08:00",
            horario_fin="18:00",
            dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            email="admin@local.dev",
            password_hash=pwd_context.hash("changeme"),
            is_active=True,
        )
        session.add(profesional)
