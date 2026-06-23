import pytest
from datetime import date, time, datetime, timedelta
from sqlalchemy import select

from app.scheduler.jobs import _liberar_reservas_vencidas_job
from app.models.profesional import Profesional
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from app.services.turno_service import reservar_turno
from app.config import Settings


async def _seed_profesional(db_session, nombre):
    p = Profesional(
        nombre=nombre,
        especialidad="Odontología",
        duracion_turno=30,
        horario_inicio="08:00",
        horario_fin="18:00",
        dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        is_active=True,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


class TestSchedulerIsolation:
    @pytest.mark.asyncio
    async def test_job_procesa_todos_los_profesionales(self, db_session, monkeypatch):
        """Scenario: dos profesionales activos con reservas vencidas → job libera ambas independientemente."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("GOOGLE_CALENDAR_CREDENTIALS", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")
        monkeypatch.setenv("SECRET_KEY", "test-secret")

        settings = Settings()

        p1 = await _seed_profesional(db_session, "Dr. A")
        p2 = await _seed_profesional(db_session, "Dr. B")

        fecha = date(2026, 6, 15)

        turno1 = await reservar_turno(
            db_session, profesional_id=p1.id, fecha=fecha, hora_inicio=time(9, 0), paciente_id=None, settings=settings
        )
        turno2 = await reservar_turno(
            db_session, profesional_id=p2.id, fecha=fecha, hora_inicio=time(10, 0), paciente_id=None, settings=settings
        )

        # Forzar expiración
        for turno in [turno1, turno2]:
            result = await db_session.execute(
                select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
            )
            reserva = result.scalar_one()
            reserva.expiracion = datetime.now() - timedelta(minutes=1)
        await db_session.commit()

        await _liberar_reservas_vencidas_job(session=db_session)

        for turno in [turno1, turno2]:
            result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
            t = result.scalar_one()
            assert t.estado == "DISPONIBLE"
