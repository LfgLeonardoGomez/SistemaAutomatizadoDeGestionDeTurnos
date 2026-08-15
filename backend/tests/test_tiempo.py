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


class TestRelojDeProcesoEnLaSuite:
    """Impide que la suite vuelva a desfasarse del reloj de la aplicación.

    El bug que motiva esto no fue teórico: varios tests sembraban datos con
    ``date.today()`` —el reloj del proceso, UTC dentro del container— mientras el
    código bajo prueba resuelve "hoy" con ``hoy_local()``. Entre las 21:00 y
    medianoche en UTC-3 esos son días distintos, así que el test sembraba un día
    y el endpoint consultaba otro. **Los tests estaban mal tres horas por día**,
    lo que se lee como flakiness pero es perfectamente determinístico: la corrida
    de la tarde pasaba y la de la noche fallaba.

    Hay un segundo modo, más silencioso: para columnas naive-UTC como
    ``expiracion``, ``datetime.now()`` da el valor correcto **solo porque el
    container corre en UTC**. Corriendo la suite fuera del container, en una
    máquina en Argentina, esas comparaciones se corren tres horas.

    Esta guarda no arregla los usos que ya existen: los congela como línea de
    base declarada y hace fallar cualquiera NUEVO. Ver ``LINEA_DE_BASE``.
    """

    # Sitios que ya usaban el reloj del proceso cuando se escribió esta guarda.
    # NO es una lista de "está bien": es deuda con nombre y apellido. Al tocar
    # uno de estos archivos, la mejora es migrarlo a ``ahora_local`` /
    # ``hoy_local`` y bajar el número de acá.
    LINEA_DE_BASE = {
        "test_captura_router.py": 1,
        "test_captura_service.py": 1,
        "test_confirmacion_asistencia.py": 1,
        "test_lista_espera_service.py": 1,
        "test_notificacion_service.py": 1,  # DNI único, no depende del reloj
        "test_profesional_isolation.py": 1,
        "test_recordatorio_service.py": 8,
        "test_relations.py": 1,
        "test_reserva_temporal.py": 4,
        "test_scheduler_isolation.py": 1,
        "test_scheduler_job.py": 4,
        "test_tiempo.py": 2,  # este archivo prueba el helper: es su tema
        "test_turno_service.py": 4,
    }

    @staticmethod
    def _usos_por_archivo() -> dict:
        """Cuenta llamadas reales a ``date.today()`` / ``datetime.now()``.

        Se parsea con ``ast`` y no con grep: media docena de menciones viven en
        comentarios y docstrings que explican justamente este bug, y contarlas
        haría ruido en vez de señal.
        """
        import ast
        from pathlib import Path

        conteo: dict = {}
        for archivo in sorted(Path(__file__).resolve().parent.glob("test_*.py")):
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
            usos = 0
            for nodo in ast.walk(arbol):
                if not isinstance(nodo, ast.Call):
                    continue
                fn = nodo.func
                if not isinstance(fn, ast.Attribute) or not isinstance(fn.value, ast.Name):
                    continue
                if fn.value.id == "date" and fn.attr == "today":
                    usos += 1
                elif fn.value.id == "datetime" and fn.attr == "now":
                    usos += 1
            if usos:
                conteo[archivo.name] = usos
        return conteo

    def test_ningun_archivo_nuevo_usa_el_reloj_del_proceso(self):
        actual = self._usos_por_archivo()
        nuevos = sorted(set(actual) - set(self.LINEA_DE_BASE))
        assert not nuevos, (
            "Estos archivos de test usan el reloj del proceso "
            f"(date.today()/datetime.now()): {nuevos}. Usá ahora_local() / "
            "hoy_local() de app.tiempo, que es lo que usa el código bajo prueba. "
            "Con el reloj del proceso el test pasa de día y falla de noche."
        )

    def test_ningun_archivo_suma_usos_nuevos(self):
        actual = self._usos_por_archivo()
        crecieron = {
            nombre: (self.LINEA_DE_BASE[nombre], cantidad)
            for nombre, cantidad in actual.items()
            if nombre in self.LINEA_DE_BASE and cantidad > self.LINEA_DE_BASE[nombre]
        }
        assert not crecieron, (
            "Estos archivos sumaron usos del reloj del proceso "
            f"(base -> actual): {crecieron}. Usá ahora_local() / hoy_local()."
        )

    def test_la_linea_de_base_no_miente(self):
        """Si un archivo se arregla, la línea de base tiene que bajar con él.

        Sin esto la lista queda como folklore: nombres que ya no aplican y que
        nadie se anima a tocar porque no se sabe si siguen siendo ciertos.
        """
        actual = self._usos_por_archivo()
        obsoletos = {
            nombre: (esperados, actual.get(nombre, 0))
            for nombre, esperados in self.LINEA_DE_BASE.items()
            if actual.get(nombre, 0) < esperados
        }
        assert not obsoletos, (
            "Estos archivos tienen MENOS usos que la línea de base "
            f"(base -> actual): {obsoletos}. Bajá el número en LINEA_DE_BASE: "
            "la deuda se achicó y el registro tiene que reflejarlo."
        )
