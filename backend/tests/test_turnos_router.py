import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi import status

from app.models.profesional import Profesional
from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from sqlalchemy import select, delete


async def _seed_profesional(db_session):
    p = Profesional(
        nombre="Dr. Test",
        especialidad="Odontología",
        duracion_turno=30,
        horario_inicio="08:00",
        horario_fin="18:00",
        dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


async def _seed_paciente(db_session, dni="12345678"):
    paciente = Paciente(
        nombre="Juan", apellido="Perez", dni=dni, telefono="555-1234"
    )
    db_session.add(paciente)
    await db_session.commit()
    await db_session.refresh(paciente)
    return paciente


class TestTurnosRouter:
    # -----------------------------------------------------------------------
    # GET /turnos/disponibles
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_get_turnos_disponibles(self, api_client, db_session):
        """Scenario: consulta slots disponibles para una fecha."""
        await _seed_profesional(db_session)
        response = api_client.get("/turnos/disponibles", params={"fecha": "2026-06-15"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 20
        assert data[0]["hora_inicio"] == "08:00"
        assert data[0]["disponible"] is True

    @pytest.mark.asyncio
    async def test_get_turnos_disponibles_fecha_invalida(self, api_client, db_session):
        """Scenario: fecha inválida → 422."""
        await _seed_profesional(db_session)
        response = api_client.get("/turnos/disponibles", params={"fecha": "not-a-date"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # -----------------------------------------------------------------------
    # POST /turnos
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_post_turnos_reserva_exitosa(self, api_client, db_session):
        """Scenario: reserva temporal exitosa → 201."""
        await _seed_profesional(db_session)
        response = api_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["estado"] == "RESERVADO_TEMPORAL"
        assert data["hora_inicio"] == "09:00:00"

    @pytest.mark.asyncio
    async def test_post_turnos_reserva_con_paciente_id(self, api_client, db_session):
        """Scenario: reserva con paciente_id ya existente."""
        await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, dni="87654321")

        response = api_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00", "paciente_id": paciente.id},
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["paciente_id"] == paciente.id

    @pytest.mark.asyncio
    async def test_post_turnos_doble_reserva(self, api_client, db_session):
        """Scenario: doble reserva del mismo paciente → 409."""
        await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, dni="11111111")

        # Primera reserva
        r1 = api_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00", "paciente_id": paciente.id},
        )
        assert r1.status_code == status.HTTP_201_CREATED

        # Segunda reserva debe fallar
        r2 = api_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "10:00", "paciente_id": paciente.id},
        )
        assert r2.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_post_turnos_slot_ocupado(self, api_client, db_session):
        """Scenario: reservar slot ya ocupado → 409."""
        await _seed_profesional(db_session)

        # Primera reserva sin paciente
        r1 = api_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        assert r1.status_code == status.HTTP_201_CREATED

        # Segunda reserva del mismo slot
        r2 = api_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        assert r2.status_code == status.HTTP_409_CONFLICT

    # -----------------------------------------------------------------------
    # PUT /turnos/{id}/confirmar
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_put_turnos_confirmar_exitoso(self, api_client, db_session):
        """Scenario: confirmar turno reservado temporal → 200."""
        await _seed_profesional(db_session)
        r1 = api_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service

            response = api_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "12345678",
                    "telefono": "555-1234",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["estado"] == "CONFIRMADO"
        assert data["paciente_id"] is not None

    @pytest.mark.asyncio
    async def test_put_turnos_confirmar_turno_no_existe(self, api_client, db_session):
        """Scenario: confirmar turno inexistente → 404."""
        response = api_client.put(
            "/turnos/99999/confirmar",
            json={
                "nombre": "Juan",
                "apellido": "Perez",
                "dni": "12345678",
                "telefono": "555-1234",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_put_turnos_confirmar_turno_expirado(self, api_client, db_session):
        """Scenario: confirmar turno expirado → 409."""
        await _seed_profesional(db_session)
        r1 = api_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        # Eliminar ReservaTemporal para simular expiración
        result = await db_session.execute(
            select(ReservaTemporal).where(ReservaTemporal.turno_id == turno_id)
        )
        reserva = result.scalar_one()
        await db_session.delete(reserva)
        await db_session.commit()

        response = api_client.put(
            f"/turnos/{turno_id}/confirmar",
            json={
                "nombre": "Juan",
                "apellido": "Perez",
                "dni": "12345678",
                "telefono": "555-1234",
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_put_turnos_confirmar_doble_turno(self, api_client, db_session):
        """Scenario: confirmar turno con paciente que ya tiene otro activo → 409."""
        await _seed_profesional(db_session)
        paciente = await _seed_paciente(db_session, dni="22222222")

        # Turno 1 confirmado
        r1 = api_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00", "paciente_id": paciente.id},
        )
        t1_id = r1.json()["id"]
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            api_client.put(
                f"/turnos/{t1_id}/confirmar",
                json={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "22222222",
                    "telefono": "555",
                },
            )

        # Turno 2 temporal
        r2 = api_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "10:00"},
        )
        t2_id = r2.json()["id"]

        response = api_client.put(
            f"/turnos/{t2_id}/confirmar",
            json={
                "nombre": "Juan",
                "apellido": "Perez",
                "dni": "22222222",
                "telefono": "555",
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT
