"""Tests for the local-time helpers.

The database stores two different kinds of time and they must not be mixed:

- ``turno.fecha`` / ``turno.hora_inicio`` are ``Date`` / ``Time`` — the
  appointment as a human agreed to it, in the professional's local terms.
- ``creado_en`` / ``reserva_temporal.expiracion`` are naive UTC.

Anything compared against the first kind must use these helpers. Using
``date.today()`` reads the *container's* clock, which runs in UTC, so between
21:00 and midnight local it already returns tomorrow — and every window
computed from it is a day short.
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.tiempo import ahora_local, hoy_local, a_local


TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")


@pytest.fixture(autouse=True)
def _settings_env(monkeypatch):
    """``Settings`` requires ``secret_key``; these are pure unit tests that
    never build the app, so it is supplied here rather than pulling in the
    whole ``client`` fixture."""
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")


class TestAhoraLocal:
    def test_devuelve_naive(self):
        """Comparisons are against naive columns; an aware datetime would
        raise ``can't compare offset-naive and offset-aware``."""
        assert ahora_local().tzinfo is None

    def test_coincide_con_la_hora_argentina(self):
        esperado = datetime.now(timezone.utc).astimezone(TZ_AR).replace(tzinfo=None)
        delta = abs((ahora_local() - esperado).total_seconds())
        assert delta < 5


class TestHoyLocal:
    def test_coincide_con_la_fecha_argentina(self):
        esperado = datetime.now(timezone.utc).astimezone(TZ_AR).date()
        assert hoy_local() == esperado


class TestALocal:
    """``a_local`` is the pure function the boundary cases are pinned on —
    it takes an explicit instant, so the assertions do not depend on when
    the suite happens to run."""

    def test_22h_argentina_sigue_siendo_el_dia_anterior(self):
        """01:00 UTC is 22:00 of the PREVIOUS day in Argentina.

        This is the exact bug: ``date.today()`` in the container returned
        the 12th while a patient booking at 22:00 on the 11th expected the
        11th, so a reminder window of '1 day + 12h' collapsed to '12h'.
        """
        instante = datetime(2026, 8, 12, 1, 0, tzinfo=timezone.utc)
        assert a_local(instante).date() == date(2026, 8, 11)
        assert a_local(instante).hour == 22

    def test_mediodia_utc_es_el_mismo_dia(self):
        instante = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        assert a_local(instante).date() == date(2026, 8, 12)
        assert a_local(instante).hour == 9

    def test_medianoche_utc_es_el_dia_anterior(self):
        instante = datetime(2026, 8, 12, 0, 0, tzinfo=timezone.utc)
        assert a_local(instante).date() == date(2026, 8, 11)
        assert a_local(instante).hour == 21

    def test_tres_de_la_manana_utc_ya_es_el_mismo_dia(self):
        """03:00 UTC is midnight local — the first instant of the new local
        day. Anything at or after this is the same date in both clocks."""
        instante = datetime(2026, 8, 12, 3, 0, tzinfo=timezone.utc)
        assert a_local(instante).date() == date(2026, 8, 12)
        assert a_local(instante).hour == 0

    def test_devuelve_naive(self):
        instante = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
        assert a_local(instante).tzinfo is None

    def test_instante_naive_se_interpreta_como_utc(self):
        """The columns this is compared against are naive UTC, so a naive
        input must not be read as local — that would shift it twice."""
        naive_utc = datetime(2026, 8, 12, 1, 0)
        assert a_local(naive_utc).date() == date(2026, 8, 11)


class TestZonaConfigurable:
    def test_respeta_la_zona_de_settings(self, monkeypatch):
        """The zone is configuration, not a constant: a professional outside
        Argentina must not inherit Buenos Aires."""
        import app.tiempo as tiempo

        monkeypatch.setattr(tiempo, "_get_zona", lambda: ZoneInfo("UTC"))
        instante = datetime(2026, 8, 12, 1, 0, tzinfo=timezone.utc)
        assert tiempo.a_local(instante).date() == date(2026, 8, 12)
        assert tiempo.a_local(instante).hour == 1


class TestCallSitesUsanHoraLocal:
    """Los call sites que comparan contra ``turno.fecha`` deben usar el
    helper, no el reloj del proceso.

    Estos tests fuerzan la fecha local en vez de leerla: en una máquina
    argentina ``date.today()`` y ``hoy_local()`` coinciden, así que el bug
    era invisible localmente y solo aparecía dentro del contenedor, que
    corre en UTC.
    """

    def test_calcular_horas_antes_usa_la_fecha_local(self, monkeypatch):
        import app.services.recordatorio_service as rs

        # 22:00 del 11 en Argentina == 01:00 UTC del 12. Con date.today()
        # el turno del 12 quedaba a "0 días" (12h de ventana); con la fecha
        # local queda a 1 día (36h), que es lo que el paciente espera.
        monkeypatch.setattr(rs, "hoy_local", lambda: date(2026, 8, 11))
        assert rs._calcular_horas_antes(date(2026, 8, 12)) == 36

    def test_calcular_horas_antes_mismo_dia(self, monkeypatch):
        import app.services.recordatorio_service as rs

        monkeypatch.setattr(rs, "hoy_local", lambda: date(2026, 8, 12))
        assert rs._calcular_horas_antes(date(2026, 8, 12)) == 12

    def test_calcular_horas_antes_fecha_pasada_es_cero(self, monkeypatch):
        import app.services.recordatorio_service as rs

        monkeypatch.setattr(rs, "hoy_local", lambda: date(2026, 8, 12))
        assert rs._calcular_horas_antes(date(2026, 8, 10)) == 0

    def test_notificacion_service_usa_ahora_local(self):
        """Guarda contra una regresión por copy-paste: si alguien reintroduce
        ``datetime.now()`` acá, la ventana vuelve a correrse 3 horas."""
        import inspect

        import app.services.notificacion_service as ns

        fuente = inspect.getsource(ns.obtener_turnos_para_recordar)
        assert "ahora_local()" in fuente
        assert "datetime.now()" not in fuente
