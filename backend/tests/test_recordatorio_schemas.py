"""Tests de los schemas Pydantic del módulo de recordatorios (C-24).

Cubre ``RecordatorioError`` y ``RecordatorioRunResponse`` —
contrato de la respuesta de ``POST /api/v1/recordatorios/run``.
"""
import pytest
from datetime import date

from app.schemas.recordatorio import (
    RecordatorioError,
    RecordatorioRunResponse,
)


class TestRecordatorioError:
    def test_crear_con_campos_obligatorios(self):
        err = RecordatorioError(
            profesional_id=1,
            turno_id=42,
            mensaje="envío falló",
        )
        assert err.profesional_id == 1
        assert err.turno_id == 42
        assert err.mensaje == "envío falló"

    def test_turno_id_es_opcional(self):
        err = RecordatorioError(
            profesional_id=1,
            turno_id=None,
            mensaje="error general del profesional",
        )
        assert err.profesional_id == 1
        assert err.turno_id is None
        assert err.mensaje == "error general del profesional"

    def test_mensaje_puede_ser_largo_y_con_contexto(self):
        msg = "Telegram API timeout tras 3 reintentos (turno 42, prof 1)"
        err = RecordatorioError(profesional_id=1, turno_id=42, mensaje=msg)
        assert err.mensaje == msg

    def test_serialization_a_dict(self):
        err = RecordatorioError(profesional_id=2, turno_id=10, mensaje="boom")
        data = err.model_dump()
        assert data == {
            "profesional_id": 2,
            "turno_id": 10,
            "mensaje": "boom",
        }


class TestRecordatorioRunResponse:
    def test_crear_response_basico_sin_errores(self):
        resp = RecordatorioRunResponse(
            fecha=date(2026, 7, 3),
            total_candidatos=5,
            total_enviados=5,
            total_fallidos=0,
            errores=[],
        )
        assert resp.fecha == date(2026, 7, 3)
        assert resp.total_candidatos == 5
        assert resp.total_enviados == 5
        assert resp.total_fallidos == 0
        assert resp.errores == []

    def test_response_con_errores(self):
        errores = [
            RecordatorioError(profesional_id=1, turno_id=10, mensaje="timeout"),
            RecordatorioError(profesional_id=2, turno_id=None, mensaje="bot_token_missing"),
        ]
        resp = RecordatorioRunResponse(
            fecha=date(2026, 7, 3),
            total_candidatos=3,
            total_enviados=1,
            total_fallidos=2,
            errores=errores,
        )
        assert resp.total_candidatos == 3
        assert resp.total_enviados == 1
        assert resp.total_fallidos == 2
        assert len(resp.errores) == 2
        assert resp.errores[0].turno_id == 10
        assert resp.errores[1].turno_id is None

    def test_response_todos_los_contadores_en_cero(self):
        resp = RecordatorioRunResponse(
            fecha=date(2026, 7, 3),
            total_candidatos=0,
            total_enviados=0,
            total_fallidos=0,
            errores=[],
        )
        assert resp.total_candidatos == 0
        assert resp.total_enviados == 0
        assert resp.total_fallidos == 0
        assert resp.errores == []

    def test_serialization_json_con_formato_fecha_iso(self):
        resp = RecordatorioRunResponse(
            fecha=date(2026, 7, 3),
            total_candidatos=0,
            total_enviados=0,
            total_fallidos=0,
            errores=[],
        )
        data = resp.model_dump()
        assert data["fecha"] == date(2026, 7, 3)
        assert isinstance(data["errores"], list)
