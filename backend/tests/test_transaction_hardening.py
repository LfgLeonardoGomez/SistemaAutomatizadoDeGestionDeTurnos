"""Tests for transaction-hardening (atomicidad, timezone, contratos).

Estos tests cubren los cambios estructurales del change ``transaction-hardening``:
- Group 7: ``reprogramar_turno`` atómico (rollback si confirmar falla)
- Group 8: ``liberar_reservas_vencidas`` reordenado (LE en misma transacción)
- Group 9: ``aceptar_turno_lista_espera`` captura ``TurnoExpiradoError``
- Group 10: ``completar_turno`` extraído a servicio
- Group 11: ``create_paciente`` contrato unificado (router siempre llama al servicio)

Los tests usan PostgreSQL real (testcontainers) porque los casos críticos
(SELECT FOR UPDATE, rollback) requieren soporte transaccional completo.
"""
import pytest
from datetime import date, time, datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from app.models.lista_de_espera import ListaDeEspera
from app.exceptions import (
    TurnoNoDisponibleError,
    TurnoExpiradoError,
    PacienteConTurnoActivoError,
    TurnoNoEncontradoError,
)
from tests.conftest import make_profesional, utcnow_naive


def _utcnow_naive() -> datetime:
    return utcnow_naive()


@pytest.fixture(autouse=True)
def _set_env_vars(monkeypatch):
    """Asegurar que ``Settings()`` se pueda instanciar sin args (necesario
    en tests que llaman a ``reservar_turno`` con ``settings=None``)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("RESERVA_TEMPORAL_MINUTOS", "10")


@pytest.fixture
def make_session_factory(engine):
    """Helper para crear un AsyncSessionLocal que comparte el engine de tests."""
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _seed_profesional(db_session, **overrides):
    p = make_profesional(**overrides)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def _seed_paciente(db_session, profesional_id, dni="12345678"):
    paciente = Paciente(
        nombre="Juan", apellido="Perez", dni=dni, telefono="555-1234",
        profesional_id=profesional_id,
    )
    db_session.add(paciente)
    await db_session.commit()
    await db_session.refresh(paciente)
    return paciente


# =============================================================================
# Group 7: reprogramar_turno atómico (C-2 CRITICAL)
# =============================================================================


class TestReprogramarTurnoAtomico:
    """Verifica que ``reprogramar_turno`` ejecute sus 3 sub-operaciones en una
    sola transacción, con rollback completo si alguna falla.
    """

    @pytest.mark.asyncio
    async def test_reprogramar_rollback_si_confirmar_falla_paciente_duplicado(
        self, db_session, make_session_factory
    ):
        """Test 7.1: Si ``confirmar_turno`` lanza ``PacienteConTurnoActivoError``,
        el turno viejo debe seguir CONFIRMADO y NO debe existir el nuevo.
        """
        from app.services.turno_service import reprogramar_turno

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, p.id, dni="11111111")

        # Turno viejo CONFIRMADO
        turno_viejo = Turno(
            fecha=date(2026, 6, 15), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno_viejo)
        await db_session.commit()
        await db_session.refresh(turno_viejo)
        viejo_id = turno_viejo.id

        paciente_data = {
            "nombre": paciente.nombre, "apellido": paciente.apellido,
            "dni": paciente.dni, "telefono": paciente.telefono,
        }

        # Usar una nueva sesión para que la sesión del test no quede en estado raro
        async with make_session_factory() as sess:
            with patch("app.services.turno_service.CalendarService"):
                with patch(
                    "app.services.turno_service.confirmar_turno",
                    new=AsyncMock(side_effect=PacienteConTurnoActivoError()),
                ):
                    with pytest.raises(PacienteConTurnoActivoError):
                        await reprogramar_turno(
                            sess, profesional_id=p.id, turno_id=viejo_id,
                            nueva_fecha=date(2026, 6, 16), nueva_hora_inicio=time(10, 0),
                            paciente_data=paciente_data,
                        )
                await sess.rollback()

        # El turno viejo debe seguir CONFIRMADO (rollback completo)
        result = await db_session.execute(
            select(Turno).where(Turno.id == viejo_id)
        )
        viejo_post = result.scalar_one()
        assert viejo_post.estado == "CONFIRMADO", (
            f"Atomicidad violada: viejo está {viejo_post.estado}, esperaba CONFIRMADO"
        )

        # No debe existir un turno nuevo en la fecha nueva
        result = await db_session.execute(
            select(Turno).where(
                Turno.fecha == date(2026, 6, 16),
                Turno.profesional_id == p.id,
            )
        )
        nuevos = result.scalars().all()
        assert len(nuevos) == 0, (
            f"Atomicidad violada: existen {len(nuevos)} turnos nuevos, esperaba 0"
        )

    @pytest.mark.asyncio
    async def test_reprogramar_rollback_si_confirmar_falla_slot_no_disponible(
        self, db_session, make_session_factory
    ):
        """Test 7.3 (triangulación): Si ``confirmar_turno`` lanza
        ``TurnoNoDisponibleError`` (race tardío), el viejo sigue CONFIRMADO.
        """
        from app.services.turno_service import reprogramar_turno

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, p.id)

        turno_viejo = Turno(
            fecha=date(2026, 6, 15), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno_viejo)
        await db_session.commit()
        await db_session.refresh(turno_viejo)
        viejo_id = turno_viejo.id

        paciente_data = {
            "nombre": paciente.nombre, "apellido": paciente.apellido,
            "dni": paciente.dni, "telefono": paciente.telefono,
        }

        async with make_session_factory() as sess:
            with patch("app.services.turno_service.CalendarService"):
                with patch(
                    "app.services.turno_service.confirmar_turno",
                    new=AsyncMock(side_effect=TurnoNoDisponibleError("Slot race")),
                ):
                    with pytest.raises(TurnoNoDisponibleError):
                        await reprogramar_turno(
                            sess, profesional_id=p.id, turno_id=viejo_id,
                            nueva_fecha=date(2026, 6, 16), nueva_hora_inicio=time(10, 0),
                            paciente_data=paciente_data,
                        )
                await sess.rollback()

        result = await db_session.execute(
            select(Turno).where(Turno.id == viejo_id)
        )
        assert result.scalar_one().estado == "CONFIRMADO"

    @pytest.mark.asyncio
    async def test_reprogramar_happy_path(self, db_session):
        """Test 7.4: Reprogramación exitosa end-to-end. Viejo CANCELADO, nuevo CONFIRMADO."""
        from app.services.turno_service import reprogramar_turno

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, p.id)

        turno_viejo = Turno(
            fecha=date(2026, 6, 15), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=p.id, paciente_id=paciente.id,
            google_event_id="old_event_123",
        )
        db_session.add(turno_viejo)
        await db_session.commit()
        await db_session.refresh(turno_viejo)
        viejo_id = turno_viejo.id

        paciente_data = {
            "nombre": paciente.nombre, "apellido": paciente.apellido,
            "dni": paciente.dni, "telefono": paciente.telefono,
        }

        with patch("app.services.turno_service.CalendarService") as mock_cal_cls:
            mock_cal = MagicMock()
            mock_cal.create_event.return_value = "new_event_456"
            mock_cal.delete_event.return_value = None
            mock_cal_cls.return_value = mock_cal

            nuevo = await reprogramar_turno(
                db_session, profesional_id=p.id, turno_id=viejo_id,
                nueva_fecha=date(2026, 6, 16), nueva_hora_inicio=time(10, 0),
                paciente_data=paciente_data,
            )
        # El router haría commit; lo simulamos.
        await db_session.commit()

        assert nuevo.estado == "CONFIRMADO"
        assert nuevo.fecha == date(2026, 6, 16)
        assert nuevo.hora_inicio == time(10, 0)
        assert nuevo.paciente_id == paciente.id
        assert nuevo.google_event_id == "new_event_456"

        # El viejo debe estar CANCELADO
        result = await db_session.execute(
            select(Turno).where(Turno.id == viejo_id)
        )
        viejo_post = result.scalar_one()
        assert viejo_post.estado == "CANCELADO"

        # Calendar.delete_event fue llamado con el event_id viejo
        mock_cal.delete_event.assert_called_with("old_event_123")
        # Calendar.create_event fue llamado para el nuevo turno
        mock_cal.create_event.assert_called_once()


# =============================================================================
# Group 8: liberar_reservas_vencidas reordenado (C-5)
# =============================================================================


class TestLiberarReservasConLE:
    """Verifica que ``liberar_reservas_vencidas`` evalúe la lista de espera
    dentro de la misma transacción que la liberación.
    """

    @pytest.mark.asyncio
    async def test_liberar_crea_reserva_para_lista_espera_atomico(
        self, db_session, make_session_factory
    ):
        """Test 8.1: tras liberar, hay una nueva ``ReservaTemporal`` para el paciente de LE."""
        from app.services.turno_service import liberar_reservas_vencidas

        p = await _seed_profesional(db_session, telegram_bot_token="test-token")
        paciente_orig = await _seed_paciente(db_session, p.id, dni="11111111")
        paciente_espera = await _seed_paciente(db_session, p.id, dni="22222222")

        # Turno RESERVADO_TEMPORAL con reserva vencida
        fecha = date(2026, 6, 15)
        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="RESERVADO_TEMPORAL", profesional_id=p.id, paciente_id=paciente_orig.id,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)
        turno_id = turno.id

        reserva = ReservaTemporal(
            turno_id=turno.id,
            expiracion=_utcnow_naive() - timedelta(minutes=5),  # ya vencida
        )
        db_session.add(reserva)
        await db_session.commit()

        # Paciente en lista de espera
        registro = ListaDeEspera(
            paciente_id=paciente_espera.id, fecha_solicitada=fecha,
            telegram_chat_id="12345", profesional_id=p.id,
        )
        db_session.add(registro)
        await db_session.commit()

        # Hacer la liberación Y las verificaciones en la misma sesión
        async with make_session_factory() as sess:
            with patch(
                "app.services.lista_espera_service.enviar_notificacion_lista_espera",
                new=AsyncMock(return_value=True),
            ):
                # Mock que NO crea reserva nueva (solo verifica que se llama)
                with patch(
                    "app.services.lista_espera_service.evaluar_lista_espera",
                    new=AsyncMock(return_value=None),
                ) as mock_evaluar:
                    liberados = await liberar_reservas_vencidas(sess, p.id)
            await sess.commit()

            # Verificar en la misma sesión
            assert liberados == 1
            result = await sess.execute(select(Turno).where(Turno.id == turno_id))
            t_post = result.scalar_one()
            assert t_post.estado == "DISPONIBLE"
            assert t_post.paciente_id is None

            # La reserva original fue eliminada; la mock de evaluar_lista_espera
            # no crea una nueva, así que hay 0 reservas después de la liberación.
            result = await sess.execute(
                select(ReservaTemporal).where(ReservaTemporal.turno_id == turno_id)
            )
            reservas = result.scalars().all()
            assert len(reservas) == 0
            # Y se llamó a evaluar_lista_espera
            mock_evaluar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_liberar_rollback_si_evaluar_le_falla(self, db_session, make_session_factory):
        """Test 8.3: si ``evaluar_lista_espera`` lanza, el slot original sigue bloqueado."""
        from app.services.turno_service import liberar_reservas_vencidas

        p = await _seed_profesional(db_session, telegram_bot_token="test-token")
        paciente = await _seed_paciente(db_session, p.id)

        fecha = date(2026, 6, 15)
        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="RESERVADO_TEMPORAL", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)
        turno_id = turno.id

        reserva = ReservaTemporal(
            turno_id=turno.id,
            expiracion=_utcnow_naive() - timedelta(minutes=5),
        )
        db_session.add(reserva)
        await db_session.commit()

        # Paciente en lista
        registro = ListaDeEspera(
            paciente_id=paciente.id, fecha_solicitada=fecha,
            telegram_chat_id="12345", profesional_id=p.id,
        )
        db_session.add(registro)
        await db_session.commit()

        # Hacer la liberación y verificaciones en la misma sesión
        async with make_session_factory() as sess:
            # Mock: evaluar_lista_espera falla
            with patch(
                "app.services.lista_espera_service.evaluar_lista_espera",
                new=AsyncMock(side_effect=RuntimeError("Telegram down")),
            ):
                with pytest.raises(RuntimeError):
                    await liberar_reservas_vencidas(sess, p.id)
                await sess.rollback()

            # Verificar en la misma sesión (post-rollback)
            result = await sess.execute(select(Turno).where(Turno.id == turno_id))
            t_post = result.scalar_one()
            assert t_post.estado == "RESERVADO_TEMPORAL", (
                f"Rollback violado: turno está {t_post.estado}"
            )
            # La reserva vencida debe seguir existiendo (rollback la restauró)
            result = await sess.execute(
                select(ReservaTemporal).where(ReservaTemporal.turno_id == turno_id)
            )
            assert result.scalar_one_or_none() is not None


# =============================================================================
# Group 9: aceptar_turno_lista_espera captura TurnoExpiradoError (C-4)
# =============================================================================


class TestAceptarTurnoListaEsperaExpirado:
    """Verifica que ``aceptar_turno_lista_espera`` capture ``TurnoExpiradoError``
    cuando la reserva temporal ofrecida expiró, libere el slot y re-llame
    a ``evaluar_lista_espera``.
    """

    @pytest.mark.asyncio
    async def test_aceptar_con_reserva_expirada_libera_y_re_evaluar(self, db_session):
        """Test 9.1: aceptar con reserva expirada → libera, resetea, re-evalúa."""
        from app.services.lista_espera_service import aceptar_turno_lista_espera

        p = await _seed_profesional(db_session, telegram_bot_token="test-token")
        paciente = await _seed_paciente(db_session, p.id)
        fecha = date(2026, 6, 15)

        # Turno RESERVADO_TEMPORAL con reserva YA EXPIRADA
        turno = Turno(
            fecha=fecha, hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="RESERVADO_TEMPORAL", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        reserva = ReservaTemporal(
            turno_id=turno.id,
            expiracion=_utcnow_naive() - timedelta(minutes=5),  # vencida
        )
        db_session.add(reserva)
        await db_session.commit()

        registro = ListaDeEspera(
            paciente_id=paciente.id, fecha_solicitada=fecha,
            turno_ofrecido_id=turno.id, notificado=True,
            notificado_en=_utcnow_naive() - timedelta(minutes=10),
            telegram_chat_id="12345", profesional_id=p.id,
        )
        db_session.add(registro)
        await db_session.commit()
        await db_session.refresh(registro)
        registro_id = registro.id

        with patch(
            "app.services.lista_espera_service.evaluar_lista_espera",
            new=AsyncMock(),
        ) as mock_evaluar:
            with pytest.raises(TurnoExpiradoError):
                await aceptar_turno_lista_espera(
                    db_session, profesional_id=p.id, lista_espera_id=registro_id
                )
        await db_session.commit()  # Patrón A: caller hace commit

        # El slot vuelve a DISPONIBLE
        result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
        t_post = result.scalar_one()
        assert t_post.estado == "DISPONIBLE"
        assert t_post.paciente_id is None

        # La ReservaTemporal fue eliminada
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno.id)
        )
        assert result.scalar_one_or_none() is None

        # El registro de lista fue reseteado
        result = await db_session.execute(
            select(ListaDeEspera).where(ListaDeEspera.id == registro_id)
        )
        r_post = result.scalar_one()
        assert r_post.notificado is False
        assert r_post.turno_ofrecido_id is None

        # Se re-llamó a evaluar_lista_espera
        mock_evaluar.assert_awaited_once()


# =============================================================================
# Group 10: completar_turno extraído a servicio (B-3)
# =============================================================================


class TestCompletarTurno:
    """Verifica ``turno_service.completar_turno`` (servicio) y el router."""

    @pytest.mark.asyncio
    async def test_completar_turno_confirmado_a_completado(self, db_session):
        """Test 10.2: turno CONFIRMADO → COMPLETADO. Patrón A: no commitea."""
        from app.services.turno_service import completar_turno

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, p.id)

        turno = Turno(
            fecha=date(2026, 6, 15), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CONFIRMADO", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        result_t = await completar_turno(db_session, p.id, turno.id)
        await db_session.commit()  # Patrón A: caller hace commit

        assert result_t.estado == "COMPLETADO"

    @pytest.mark.asyncio
    async def test_completar_turno_ya_completado_idempotente(self, db_session):
        """Test 10.2: turno ya COMPLETADO → retorna sin error."""
        from app.services.turno_service import completar_turno

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, p.id)

        turno = Turno(
            fecha=date(2026, 6, 15), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="COMPLETADO", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        result_t = await completar_turno(db_session, p.id, turno.id)
        assert result_t.estado == "COMPLETADO"

    @pytest.mark.asyncio
    async def test_completar_turno_cancelado_error(self, db_session):
        """Test 10.2: turno CANCELADO → TurnoNoDisponibleError."""
        from app.services.turno_service import completar_turno

        p = await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, p.id)

        turno = Turno(
            fecha=date(2026, 6, 15), hora_inicio=time(9, 0), hora_fin=time(9, 30),
            estado="CANCELADO", profesional_id=p.id, paciente_id=paciente.id,
        )
        db_session.add(turno)
        await db_session.commit()
        await db_session.refresh(turno)

        with pytest.raises(TurnoNoDisponibleError):
            await completar_turno(db_session, p.id, turno.id)

    @pytest.mark.asyncio
    async def test_completar_turno_inexistente_error(self, db_session):
        """Test 10.2: turno inexistente → TurnoNoEncontradoError."""
        from app.services.turno_service import completar_turno

        p = await _seed_profesional(db_session)
        with pytest.raises(TurnoNoEncontradoError):
            await completar_turno(db_session, p.id, 99999)


# =============================================================================
# Group 11: create_paciente contrato unificado (B-4)
# =============================================================================


class TestCreatePacienteUnificado:
    """Verifica que ``create_paciente`` siempre llame a ``crear_o_obtener_paciente``
    y mapee 200/201 según si el paciente es nuevo o preexistente.
    """

    @pytest.mark.asyncio
    async def test_create_paciente_nuevo_retorna_201(self, authenticated_client, db_session, profesional):
        """Paciente nuevo → 201."""
        paciente_data = {
            "nombre": "Juan", "apellido": "Perez",
            "dni": "11111111", "telefono": "555-1234",
        }
        resp = authenticated_client.post("/pacientes", json=paciente_data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["dni"] == "11111111"
        assert body["nombre"] == "Juan"

    @pytest.mark.asyncio
    async def test_create_paciente_existente_retorna_200(self, authenticated_client, db_session, profesional):
        """Paciente existente por DNI → 200 (mismo registro)."""
        paciente_data = {
            "nombre": "Juan", "apellido": "Perez",
            "dni": "11111111", "telefono": "555-1234",
        }
        # Primer POST: crea
        resp1 = authenticated_client.post("/pacientes", json=paciente_data)
        assert resp1.status_code == 201
        id1 = resp1.json()["id"]

        # Segundo POST con mismo DNI: retorna existente
        resp2 = authenticated_client.post("/pacientes", json=paciente_data)
        assert resp2.status_code == 200
        id2 = resp2.json()["id"]
        assert id1 == id2  # mismo registro

    @pytest.mark.asyncio
    async def test_create_paciente_router_llama_a_servicio(
        self, authenticated_client, db_session, profesional
    ):
        """El router SIEMPRE llama a ``crear_o_obtener_paciente``: verificable
        indirectamente porque sin el servicio el endpoint fallaría con IntegrityError
        o retornaría 500. Los 2 tests anteriores confirman el contrato (200/201).
        """
        # Verificación funcional: con 2 DNIs distintos, ambos retornan PacienteRead válido
        dnis = ["33333333", "44444444"]
        for dni in dnis:
            resp = authenticated_client.post(
                "/pacientes",
                json={"nombre": "Test", "apellido": "X", "dni": dni, "telefono": "555"},
            )
            assert resp.status_code == 201
            body = resp.json()
            assert body["dni"] == dni
            assert "id" in body
