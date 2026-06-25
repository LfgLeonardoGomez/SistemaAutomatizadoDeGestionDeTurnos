from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paciente import Paciente
from app.models.profesional import Profesional
from app.models.super_admin import SuperAdmin
from app.models.turno import Turno
from app.schemas.super_admin import GlobalMetricsResponse
from app.services.auth_service import verify_password


async def authenticate_super_admin(
    db: AsyncSession, email: str, password: str
) -> SuperAdmin | None:
    result = await db.execute(
        select(SuperAdmin).where(SuperAdmin.email == email)
    )
    admin = result.scalar_one_or_none()
    if admin is None:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


async def list_profesionales(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Profesional]:
    result = await db.execute(
        select(Profesional).offset(skip).limit(limit).order_by(Profesional.id)
    )
    return list(result.scalars().all())


async def get_profesional(
    db: AsyncSession, profesional_id: int
) -> Profesional | None:
    result = await db.execute(
        select(Profesional).where(Profesional.id == profesional_id)
    )
    return result.scalar_one_or_none()


async def activate_profesional(
    db: AsyncSession, profesional_id: int
) -> Profesional | None:
    profesional = await get_profesional(db, profesional_id)
    if profesional is None:
        return None
    profesional.is_active = True
    await db.commit()
    await db.refresh(profesional)
    return profesional


async def deactivate_profesional(
    db: AsyncSession, profesional_id: int
) -> Profesional | None:
    profesional = await get_profesional(db, profesional_id)
    if profesional is None:
        return None
    profesional.is_active = False
    await db.commit()
    await db.refresh(profesional)
    return profesional


async def compute_global_metrics(db: AsyncSession) -> GlobalMetricsResponse:
    now_utc = datetime.now(timezone.utc)
    today_utc = now_utc.date()
    thirty_days_ago = now_utc - timedelta(days=30)

    # Total profesionales
    total_profesionales = await db.scalar(select(func.count(Profesional.id))) or 0

    # Active / inactive profesionales
    profesionales_activos = (
        await db.scalar(
            select(func.count(Profesional.id)).where(Profesional.is_active == True)
        )
        or 0
    )
    profesionales_inactivos = total_profesionales - profesionales_activos

    # Total turnos
    total_turnos = await db.scalar(select(func.count(Turno.id))) or 0

    # Turnos hoy
    turnos_hoy = (
        await db.scalar(select(func.count(Turno.id)).where(Turno.fecha == today_utc))
        or 0
    )

    # Turnos in last 30 days
    total_turnos_30d = (
        await db.scalar(
            select(func.count(Turno.id)).where(Turno.creado_en >= thirty_days_ago)
        )
        or 0
    )

    # Confirmados / cancelados in last 30 days
    turnos_confirmados_30d = (
        await db.scalar(
            select(func.count(Turno.id)).where(
                Turno.estado == "CONFIRMADO",
                Turno.creado_en >= thirty_days_ago,
            )
        )
        or 0
    )
    turnos_cancelados_30d = (
        await db.scalar(
            select(func.count(Turno.id)).where(
                Turno.estado == "CANCELADO",
                Turno.creado_en >= thirty_days_ago,
            )
        )
        or 0
    )

    # Total pacientes
    total_pacientes = await db.scalar(select(func.count(Paciente.id))) or 0

    # Rates (0.0 when denominator is zero)
    tasa_confirmacion_30d = (
        turnos_confirmados_30d / total_turnos_30d if total_turnos_30d > 0 else 0.0
    )
    tasa_cancelacion_30d = (
        turnos_cancelados_30d / total_turnos_30d if total_turnos_30d > 0 else 0.0
    )

    return GlobalMetricsResponse(
        total_profesionales=total_profesionales,
        profesionales_activos=profesionales_activos,
        profesionales_inactivos=profesionales_inactivos,
        total_turnos=total_turnos,
        turnos_hoy=turnos_hoy,
        turnos_confirmados_30d=turnos_confirmados_30d,
        turnos_cancelados_30d=turnos_cancelados_30d,
        total_pacientes=total_pacientes,
        tasa_confirmacion_30d=tasa_confirmacion_30d,
        tasa_cancelacion_30d=tasa_cancelacion_30d,
    )
