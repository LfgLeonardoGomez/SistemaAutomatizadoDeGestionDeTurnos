"""Tests para los schemas Pydantic del change C-23 (turno destinatario multicanal).

C-23 TAREA 4: ReservaTurnoRequest y ConfirmarTurnoRequest ganan un campo
opcional ``telegram_chat_id`` (retrocompatibilidad con contratos REST que
no lo envíen). El schema ``TurnoDestinatarioRead`` modela la respuesta de
un destinatario persistido (id, canal, destinatario).

Decisión confirmada (OQ-2): destinatario INTERNO, no se expone en
TurnoResponse. Por eso TurnoDestinatarioRead es independiente y solo se
usa cuando se necesita explícitamente (no se agrega a TurnoResponse).
"""
import pytest
from datetime import date, time
from pydantic import ValidationError

from app.schemas.turno import (
    ReservaTurnoRequest,
    ConfirmarTurnoRequest,
    TurnoDestinatarioRead,
)


class TestReservaTurnoRequestC23:
    """Tests C-23 TAREA 4.1/4.3: telegram_chat_id opcional y retrocompatible."""

    def test_reserva_request_acepta_telegram_chat_id(self):
        """TAREA 4.1 RED → GREEN: ReservaTurnoRequest acepta telegram_chat_id."""
        req = ReservaTurnoRequest(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            paciente_id=None,
            telegram_chat_id="555001",
        )
        assert req.telegram_chat_id == "555001"

    def test_reserva_request_sin_telegram_chat_id_es_valido(self):
        """TAREA 4.3 TRIANGULATE: requests sin telegram_chat_id siguen validando.

        El campo es retrocompatible: los clientes existentes (incluido n8n
        que aún no fue actualizado) pueden seguir enviando requests sin el
        campo, y el backend las acepta.
        """
        req = ReservaTurnoRequest(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            paciente_id=1,
        )
        assert req.telegram_chat_id is None

    def test_reserva_request_telegram_chat_id_none_explicito(self):
        """TAREA 4.3: ``telegram_chat_id: null`` también es válido (no breaking)."""
        req = ReservaTurnoRequest(
            fecha=date(2026, 6, 15),
            hora_inicio=time(9, 0),
            paciente_id=None,
            telegram_chat_id=None,
        )
        assert req.telegram_chat_id is None


class TestConfirmarTurnoRequestC23:
    """Tests C-23 TAREA 4.1/4.3: telegram_chat_id opcional en confirmación."""

    def test_confirmar_request_acepta_telegram_chat_id(self):
        """TAREA 4.1: ConfirmarTurnoRequest acepta telegram_chat_id (email ya existía)."""
        req = ConfirmarTurnoRequest(
            nombre="Juan",
            apellido="Pérez",
            dni="12345678",
            telefono="+54 9 11 1234-5678",
            email="juan@example.com",
            telegram_chat_id="555002",
        )
        assert req.telegram_chat_id == "555002"
        # email sigue funcionando como antes
        assert req.email == "juan@example.com"

    def test_confirmar_request_sin_telegram_chat_id_es_valido(self):
        """TAREA 4.3: requests sin telegram_chat_id siguen validando."""
        req = ConfirmarTurnoRequest(
            nombre="Juan",
            apellido="Pérez",
            dni="12345678",
            telefono="+54 9 11 1234-5678",
            email=None,
        )
        assert req.telegram_chat_id is None
        assert req.email is None

    def test_confirmar_request_telegram_chat_id_none_explicito(self):
        """TAREA 4.3: ``telegram_chat_id: null`` también es válido."""
        req = ConfirmarTurnoRequest(
            nombre="Juan",
            apellido="Pérez",
            dni="12345678",
            telefono="+54 9 11 1234-5678",
            telegram_chat_id=None,
        )
        assert req.telegram_chat_id is None


class TestTurnoDestinatarioRead:
    """Tests C-23 TAREA 4.2: schema TurnoDestinatarioRead."""

    def test_desde_modelo_orm(self):
        """TAREA 4.2: TurnoDestinatarioRead se construye desde un objeto ORM
        con atributos id/canal/destinatario (``from_attributes=True``)."""

        class FakeDestinatario:
            id = 42
            canal = "TELEGRAM"
            destinatario = "555001"

        read = TurnoDestinatarioRead.model_validate(FakeDestinatario())
        assert read.id == 42
        assert read.canal == "TELEGRAM"
        assert read.destinatario == "555001"

    def test_desde_dict(self):
        """TAREA 4.2: TurnoDestinatarioRead se construye desde un dict."""
        read = TurnoDestinatarioRead(
            id=1, canal="EMAIL", destinatario="user@example.com"
        )
        assert read.id == 1
        assert read.canal == "EMAIL"
        assert read.destinatario == "user@example.com"

    def test_canal_invalido_rechazado(self):
        """TAREA 4.2: el schema valida que el canal sea uno de los permitidos
        (TELEGRAM o EMAIL) — no es un string libre."""
        with pytest.raises(ValidationError) as exc:
            TurnoDestinatarioRead(id=1, canal="SMS", destinatario="x")
        # El mensaje de error menciona el campo canal
        assert "canal" in str(exc.value).lower()
