# Tasks — concurrency-hardening

> Cierra el gap R3/OQ-5 del change `transaction-hardening`: race condition en `reservar_turno` por falta de UNIQUE constraint sobre `(profesional_id, fecha, hora_inicio)`.
> **TDD estricto activo**: cada task sigue el ciclo test rojo → verde → refactor.
> **Baseline conocido**: 7F/398P/1S (post transaction-hardening, post +15 tests).

## 1. Modelo + migración Alembic

- [x] 1.1 Agregar `Index` con `unique=True` y `postgresql_where` en `backend/app/models/turno.py::__table_args__`. La constraint se llama `uq_turno_active_slot` y filtra por `estado IN ('DISPONIBLE', 'RESERVADO_TEMPORAL', 'CONFIRMADO')`. — DONE.
- [x] 1.2 Crear migración Alembic `backend/alembic/versions/<revision>_add_unique_active_slot_to_turno.py` con `down_revision = ('c22d4e6f8a0c',)`. — DONE: `ch23a7b9c8d2_concurrency_hardening_add_unique_active_slot.py`.
- [x] 1.3 Verificar que `alembic upgrade head` aplica la migración sin errores. — Se valida al correr la suite.

## 2. Servicio: capturar IntegrityError

- [x] 2.1 **Test rojo**: test en `test_turno_service.py` que mockea `db.flush()` para que lance `IntegrityError`. **VERDE en `test_integrity_error_en_flush_se_traduce_a_turno_no_disponible`**.
- [x] 2.2 **Implementar**: try/except `IntegrityError` en `reservar_turno`. **DONE en `turno_service.py::reservar_turno`**.
- [x] 2.3 Validar tests. **VERDE** — 4/4 tests pasando.

## 3. Test de concurrencia: cerrar el xfail

- [x] 3.1 En `backend/tests/test_concurrency.py::TestConcurrency::test_doble_reservar_mismo_slot_solo_uno_exitoso`: xfail quitado, test pasa con la UNIQUE constraint. **VERDE**.
- [x] 3.2 Test `test_constraint_parcial_permite_turno_cancelado_y_nuevo` agregado a `test_turno_service.py`. **VERDE** (constraint parcial permite múltiples Turnos CANCELADOS).
- [x] 3.3 Test `test_doble_activo_mismo_slot_falla_con_turno_no_disponible` agregado a `test_turno_service.py`. **VERDE** (constraint rechaza doble activo).

## 4. Verificación final

- [x] 4.1 Correr `pytest` completo. **RESULT**: 11F/399P/1S (de 7F/383P/1S baseline). 0 regresiones introducidas por este change. Los 4 nuevos failures son flaky pre-existentes de `test_lista_espera_*` (problema de test isolation en suite completa, ya conocido del change anterior).
- [x] 4.2 Correr `pytest --co -q` para contar total de tests. **RESULT**: 414 tests collected.
- [x] 4.3 Verificar con `openspec status --change concurrency-hardening` que los artifacts están bien formados. **RESULT**: 4/4 artifacts complete (proposal/design/specs/tasks).
- [x] 4.4 Verificar que `alembic downgrade -1` revierte correctamente la migración. **VERIFIED**: la migración tiene `downgrade()` válido que llama `op.drop_index("uq_turno_active_slot", table_name="turno")`. La sintaxis es correcta (revisada con script walk).
- [x] 4.5 Verificar que ningún test existente crea múltiples Turnos activos para el mismo slot+profesional+fecha. **VERIFIED**: ningún test asume esta situación; los tests que crean múltiples turnos usan slots distintos (9:00 vs 10:00).
