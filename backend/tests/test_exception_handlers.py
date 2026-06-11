import pytest
from fastapi import Request
from unittest.mock import MagicMock

from app.exceptions import (
    TurnoNoDisponibleError,
    TurnoExpiradoError,
    PacienteConTurnoActivoError,
    TurnoNoEncontradoError,
    TurnoYaCanceladoError,
)
from app.exception_handlers import (
    turno_no_disponible_handler,
    turno_expirado_handler,
    paciente_con_turno_activo_handler,
    turno_no_encontrado_handler,
    turno_ya_cancelado_handler,
)


def mock_request():
    return MagicMock(spec=Request)


class TestTurnoNoEncontradoHandler:
    def test_handler_returns_404(self):
        exc = TurnoNoEncontradoError()
        response = turno_no_encontrado_handler(mock_request(), exc)
        assert response.status_code == 404
        assert "no encontrado" in response.body.decode()


class TestTurnoYaCanceladoHandler:
    def test_handler_returns_409(self):
        exc = TurnoYaCanceladoError()
        response = turno_ya_cancelado_handler(mock_request(), exc)
        assert response.status_code == 409
        assert "cancelado" in response.body.decode()


class TestExistingHandlers:
    def test_turno_no_disponible_handler(self):
        exc = TurnoNoDisponibleError()
        response = turno_no_disponible_handler(mock_request(), exc)
        assert response.status_code == 409

    def test_turno_expirado_handler(self):
        exc = TurnoExpiradoError()
        response = turno_expirado_handler(mock_request(), exc)
        assert response.status_code == 409

    def test_paciente_con_turno_activo_handler(self):
        exc = PacienteConTurnoActivoError()
        response = paciente_con_turno_activo_handler(mock_request(), exc)
        assert response.status_code == 409
