import pytest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi import status

from app.models.profesional import Profesional
from app.models.paciente import Paciente
from app.models.turno import Turno
from app.models.reserva_temporal import ReservaTemporal
from sqlalchemy import select, delete


async def _seed_paciente(db_session, profesional_id: int, dni="12345678"):
    paciente = Paciente(
        nombre="Juan", apellido="Perez", dni=dni, telefono="555-1234",
        profesional_id=profesional_id,
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
    async def test_get_turnos_disponibles(self, authenticated_client, db_session, profesional):
        """Scenario: consulta slots disponibles para una fecha."""
        response = authenticated_client.get("/turnos/disponibles", params={"fecha": "2026-06-15"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 20
        assert data[0]["hora_inicio"] == "08:00"
        assert data[0]["disponible"] is True

    @pytest.mark.asyncio
    async def test_get_turnos_disponibles_fecha_invalida(self, authenticated_client, db_session, profesional):
        """Scenario: fecha inválida → 422."""
        response = authenticated_client.get("/turnos/disponibles", params={"fecha": "not-a-date"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # -----------------------------------------------------------------------
    # POST /turnos
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_post_turnos_reserva_exitosa(self, authenticated_client, db_session, profesional):
        """Scenario: reserva temporal exitosa → 201."""
        response = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["estado"] == "RESERVADO_TEMPORAL"
        assert data["hora_inicio"] == "09:00:00"

    @pytest.mark.asyncio
    async def test_post_turnos_reserva_con_paciente_id(self, authenticated_client, db_session, profesional):
        """Scenario: reserva con paciente_id ya existente."""
        paciente = await _seed_paciente(db_session, profesional.id, dni="87654321")

        response = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00", "paciente_id": paciente.id},
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["paciente_id"] == paciente.id

    @pytest.mark.asyncio
    async def test_post_turnos_doble_reserva(self, authenticated_client, db_session, profesional):
        """Scenario: doble reserva del mismo paciente → 409."""
        paciente = await _seed_paciente(db_session, profesional.id, dni="11111111")

        # Primera reserva
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00", "paciente_id": paciente.id},
        )
        assert r1.status_code == status.HTTP_201_CREATED

        # Segunda reserva debe fallar
        r2 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "10:00", "paciente_id": paciente.id},
        )
        assert r2.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_post_turnos_slot_ocupado(self, authenticated_client, db_session, profesional):
        """Scenario: reservar slot ya ocupado → 409."""
        # Primera reserva sin paciente
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        assert r1.status_code == status.HTTP_201_CREATED

        # Segunda reserva del mismo slot
        r2 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        assert r2.status_code == status.HTTP_409_CONFLICT

    # -----------------------------------------------------------------------
    # PUT /turnos/{id}/confirmar
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_put_turnos_confirmar_exitoso(self, authenticated_client, db_session, profesional):
        """Scenario: confirmar turno reservado temporal → 200."""
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service

            response = authenticated_client.put(
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
    async def test_put_turnos_confirmar_turno_no_existe(self, authenticated_client, db_session, profesional):
        """Scenario: confirmar turno inexistente → 404."""
        response = authenticated_client.put(
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
    async def test_put_turnos_confirmar_turno_expirado(self, authenticated_client, db_session, profesional):
        """Scenario: confirmar turno expirado → 409."""
        r1 = authenticated_client.post(
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

        response = authenticated_client.put(
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
    async def test_put_turnos_confirmar_doble_turno(self, authenticated_client, db_session, profesional):
        """Scenario: confirmar turno con paciente que ya tiene otro activo → 409."""
        paciente = await _seed_paciente(db_session, profesional.id, dni="22222222")

        # Turno 1 confirmado
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00", "paciente_id": paciente.id},
        )
        t1_id = r1.json()["id"]
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{t1_id}/confirmar",
                json={
                    "nombre": "Juan",
                    "apellido": "Perez",
                    "dni": "22222222",
                    "telefono": "555",
                },
            )

        # Turno 2 temporal
        r2 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "10:00"},
        )
        t2_id = r2.json()["id"]

        response = authenticated_client.put(
            f"/turnos/{t2_id}/confirmar",
            json={
                "nombre": "Juan",
                "apellido": "Perez",
                "dni": "22222222",
                "telefono": "555",
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    # -----------------------------------------------------------------------
    # PUT /turnos/{id}/cancelar
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_put_turnos_cancelar_exitoso(self, authenticated_client, db_session, profesional):
        """Scenario: cancelar turno confirmado → 200, estado CANCELADO."""
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        # Confirmar turno
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        # Cancelar turno
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_calendar_cls.return_value = mock_service
            response = authenticated_client.put(f"/turnos/{turno_id}/cancelar")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["estado"] == "CANCELADO"
        assert data["id"] == turno_id

    @pytest.mark.asyncio
    async def test_put_turnos_cancelar_no_existe(self, authenticated_client, db_session, profesional):
        """Scenario: cancelar turno inexistente → 404."""
        response = authenticated_client.put("/turnos/99999/cancelar")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_put_turnos_cancelar_ya_cancelado(self, authenticated_client, db_session, profesional):
        """Scenario: cancelar turno ya cancelado → 409."""
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        # Primera cancelación
        authenticated_client.put(f"/turnos/{turno_id}/cancelar")

        # Segunda cancelación
        response = authenticated_client.put(f"/turnos/{turno_id}/cancelar")
        assert response.status_code == status.HTTP_409_CONFLICT

    # -----------------------------------------------------------------------
    # PUT /turnos/{id}/reprogramar
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_put_turnos_reprogramar_exitoso(self, authenticated_client, db_session, profesional):
        """Scenario: reprogramar turno confirmado → 200, nuevo CONFIRMADO."""
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_old"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_new"
            mock_calendar_cls.return_value = mock_service
            response = authenticated_client.put(
                f"/turnos/{turno_id}/reprogramar",
                json={"nueva_fecha": "2026-06-16", "nueva_hora_inicio": "10:00"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["estado"] == "CONFIRMADO"
        assert data["fecha"] == "2026-06-16"
        assert data["hora_inicio"] == "10:00:00"

    @pytest.mark.asyncio
    async def test_put_turnos_reprogramar_no_existe(self, authenticated_client, db_session, profesional):
        """Scenario: reprogramar turno inexistente → 404."""
        response = authenticated_client.put(
            "/turnos/99999/reprogramar",
            json={"nueva_fecha": "2026-06-16", "nueva_hora_inicio": "10:00"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_put_turnos_reprogramar_slot_no_disponible(self, authenticated_client, db_session, profesional):
        """Scenario: reprogramar a slot ocupado → 409."""
        # Ocupar slot 10:00
        r_ocupado = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "10:00"},
        )
        t_ocupado_id = r_ocupado.json()["id"]
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_ocupado"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{t_ocupado_id}/confirmar",
                json={"nombre": "Ana", "apellido": "Garcia", "dni": "87654321", "telefono": "555-9999"},
            )

        # Crear turno a reprogramar
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_old"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        response = authenticated_client.put(
            f"/turnos/{turno_id}/reprogramar",
            json={"nueva_fecha": "2026-06-15", "nueva_hora_inicio": "10:00"},
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_put_turnos_reprogramar_paciente_activo(self, authenticated_client, db_session, profesional):
        """Scenario: reprogramar con paciente que tiene otro turno activo → 409."""
        paciente = await _seed_paciente(db_session, profesional.id, dni="11111111")

        # Turno 1 confirmado del paciente
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00", "paciente_id": paciente.id},
        )
        t1_id = r1.json()["id"]
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_t1"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{t1_id}/confirmar",
                json={"nombre": paciente.nombre, "apellido": paciente.apellido, "dni": paciente.dni, "telefono": paciente.telefono},
            )

        # Turno 2 de otro paciente
        r2 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "10:00"},
        )
        t2_id = r2.json()["id"]
        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_t2"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{t2_id}/confirmar",
                json={"nombre": "Ana", "apellido": "Garcia", "dni": "22222222", "telefono": "555-9999"},
            )

        # Reprogramar t2 con datos del paciente que ya tiene t1 activo
        response = authenticated_client.put(
            f"/turnos/{t2_id}/reprogramar",
            json={
                "nueva_fecha": "2026-06-15",
                "nueva_hora_inicio": "11:00",
                "paciente_data": {
                    "nombre": paciente.nombre,
                    "apellido": paciente.apellido,
                    "dni": paciente.dni,
                    "telefono": paciente.telefono,
                },
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_put_turnos_reprogramar_con_paciente_data(self, authenticated_client, db_session, profesional):
        """Scenario: reprogramar pasando paciente_data explícito → 200."""
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_old"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_new"
            mock_calendar_cls.return_value = mock_service
            response = authenticated_client.put(
                f"/turnos/{turno_id}/reprogramar",
                json={
                    "nueva_fecha": "2026-06-16",
                    "nueva_hora_inicio": "10:00",
                    "paciente_data": {
                        "nombre": "Juan",
                        "apellido": "Perez",
                        "dni": "12345678",
                        "telefono": "555-1234",
                    },
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["estado"] == "CONFIRMADO"
        assert data["fecha"] == "2026-06-16"

    # -----------------------------------------------------------------------
    # PUT /turnos/{id}/completar
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_put_turnos_completar_exitoso(self, authenticated_client, db_session, profesional):
        """Scenario: completar turno CONFIRMADO → 200, estado COMPLETADO."""
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        response = authenticated_client.put(f"/turnos/{turno_id}/completar")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["estado"] == "COMPLETADO"

    @pytest.mark.asyncio
    async def test_put_turnos_completar_no_existe(self, authenticated_client, db_session, profesional):
        """Scenario: completar turno inexistente → 404."""
        response = authenticated_client.put("/turnos/99999/completar")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_put_turnos_completar_cancelado(self, authenticated_client, db_session, profesional):
        """Scenario: completar turno CANCELADO → 409."""
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        authenticated_client.put(f"/turnos/{turno_id}/cancelar")

        response = authenticated_client.put(f"/turnos/{turno_id}/completar")
        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_put_turnos_completar_ya_completado(self, authenticated_client, db_session, profesional):
        """Scenario: completar turno ya COMPLETADO → 200 idempotente."""
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        # Primera vez
        r1 = authenticated_client.put(f"/turnos/{turno_id}/completar")
        assert r1.status_code == status.HTTP_200_OK

        # Segunda vez (idempotente)
        r2 = authenticated_client.put(f"/turnos/{turno_id}/completar")
        assert r2.status_code == status.HTTP_200_OK
        assert r2.json()["estado"] == "COMPLETADO"

    # -----------------------------------------------------------------------
    # PUT /turnos/{id}/confirmar-asistencia
    # -----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_put_turnos_confirmar_asistencia_exitoso(self, authenticated_client, db_session, profesional):
        """Scenario: confirmar asistencia de turno CONFIRMADO → 200."""
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        response = authenticated_client.put(f"/turnos/{turno_id}/confirmar-asistencia")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["estado"] == "CONFIRMADO"

    @pytest.mark.asyncio
    async def test_put_turnos_confirmar_asistencia_cancelado(self, authenticated_client, db_session, profesional):
        """Scenario: confirmar asistencia de turno CANCELADO → 409."""
        r1 = authenticated_client.post(
            "/turnos",
            json={"fecha": "2026-06-15", "hora_inicio": "09:00"},
        )
        turno_id = r1.json()["id"]

        with patch("app.services.turno_service.CalendarService") as mock_calendar_cls:
            mock_service = MagicMock()
            mock_service.create_event.return_value = "event_123"
            mock_calendar_cls.return_value = mock_service
            authenticated_client.put(
                f"/turnos/{turno_id}/confirmar",
                json={"nombre": "Juan", "apellido": "Perez", "dni": "12345678", "telefono": "555-1234"},
            )

        authenticated_client.put(f"/turnos/{turno_id}/cancelar")

        response = authenticated_client.put(f"/turnos/{turno_id}/confirmar-asistencia")
        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_put_turnos_confirmar_asistencia_no_existe(self, authenticated_client, db_session, profesional):
        """Scenario: confirmar asistencia de turno inexistente → 404."""
        response = authenticated_client.put("/turnos/99999/confirmar-asistencia")
        assert response.status_code == status.HTTP_404_NOT_FOUND
