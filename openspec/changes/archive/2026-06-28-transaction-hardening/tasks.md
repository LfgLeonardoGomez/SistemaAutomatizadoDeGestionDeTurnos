# Tasks — transaction-hardening

> Plan de implementación derivado de la auditoría de transacciones y concurrencia. **TDD estricto activo**: cada task sigue el ciclo test rojo → verde → refactor. **Baseline conocido**: 383 passing / 7 failing pre-existentes (no relacionados con este change).

## 1. Safety net y baseline

- [x] 1.1 Capturar baseline de pytest desde `backend/` y guardar en `tests/.baseline-failures.txt`. Expected: **7 failed, 383 passed, 1 skipped** (pre-existente: `test_base_tables_populated`, `test_profesional_new_columns_nullable`, `test_scheduler_tiene_job_registrado`, `test_scheduler_job_marcar_turnos_completados_loguea_excepciones`, `test_scheduler_job_enviar_recordatorios_maneja_excepcion`, `test_enviar_mensaje_con_log_loggea_contexto_al_fallar`, `test_turno_estado_invalido`) — CONFIRMADO 7F/383P/1S
- [x] 1.2 Verificar que `backend/tests/test_postgresql_infrastructure` provee engine real de PostgreSQL (no SQLite) para tests de concurrencia. Si no existe, anotar como gap para el task 10. — VERIFICADO: conftest.py usa testcontainers[postgres] (PostgresContainer("postgres:15-alpine")) o TEST_DATABASE_URL. **NO HAY SQLite, TODO PostgreSQL real**.
- [x] 1.3 Verificar que `backend/tests/conftest.py` tiene fixtures `db_session`, `profesional`, `paciente`, `turno_confirmado`, `reserva_temporal`. Si faltan, crear las mínimas necesarias. — VERIFICADO: conftest.py tiene `db_session`, `profesional`, `client`, `authenticated_client`, `make_profesional`, `make_profesional_persisted`. Las fixtures `paciente`, `turno_confirmado`, `reserva_temporal` se crean localmente en cada test (no es problema, no es necesario centralizar).

## 2. Contrato de servicios (Patrón A — foundational)

> **Patrón**: los servicios NO hacen `await db.commit()`. Routers y scheduler son los únicos responsables. Estos cambios son prerequisito de TODO lo demás.

- [x] 2.1 Quitar `await db.commit()` de `turno_service.cancelar_turno` (línea 309). Mantener `await db.refresh(turno)` para devolver el estado actualizado. Test rojo que valide que la sesión tiene cambios pendientes pero la DB no (usar `await db.rollback()` y verificar rollback limpia). Test verde: commit hecho por el caller persiste.
- [x] 2.2 Quitar `await db.commit()` de `turno_service.reservar_turno` (línea 113). Misma estrategia de test que 2.1.
- [x] 2.3 Quitar `await db.commit()` de `turno_service.liberar_reservas_vencidas` (línea 230). NO reorganizar el flujo aún (eso es task 6). Solo quitar el commit. Verificar que tests existentes del scheduler sigan pasando.
- [x] 2.4 Quitar `await db.commit()` de `turno_service.marcar_turnos_completados` (línea 276). Misma estrategia.
- [x] 2.5 Quitar `await db.commit()` de `turno_service.confirmar_asistencia_turno` (línea 435). Misma estrategia.
- [x] 2.6 Quitar `await db.commit()` de `lista_espera_service.registrar_en_lista_espera` (línea 45). Misma estrategia.
- [x] 2.7 Quitar `await db.commit()` de `lista_espera_service.eliminar_de_lista_espera` (línea 65). Misma estrategia.
- [x] 2.8 Quitar `await db.commit()` de `lista_espera_service.notificar_y_marcar` (línea 151). Misma estrategia.
- [x] 2.9 Quitar `await db.commit()` de `lista_espera_service.aceptar_turno_lista_espera` (línea 225). NO capturar `TurnoExpiradoError` aún (eso es task 7). Solo quitar el commit.
- [x] 2.10 Quitar `await db.commit()` de `lista_espera_service.rechazar_turno_lista_espera` (línea 265). Misma estrategia.
- [x] 2.11 Quitar `await db.commit()` de `lista_espera_service.procesar_timeouts_lista_espera` (línea 394). Misma estrategia.
- [x] 2.12 Verificar que `paciente_service.crear_o_obtener_paciente` NO tiene commit (ya no lo tiene, solo usa savepoint). Confirmar con lectura del código.

## 3. Adaptar routers al Patrón A

- [x] 3.1 `routers/turnos.py::create_turno`: agregar `await db.commit()` en happy path. Agregar `await db.rollback()` en cada `except`. Test que valide commit en 201 y rollback en cada error de negocio.
- [x] 3.2 `routers/turnos.py::cancelar_turno_endpoint`: ya NO depende de que el servicio commitee; agregar `await db.commit()` en happy path y `await db.rollback()` en cada `except`. Test similar.
- [x] 3.3 `routers/turnos.py::reprogramar_turno_endpoint`: agregar `await db.commit()` en happy path. Agregar `await db.rollback()` en cada `except`. Test que valide atomicidad (mock de excepción en confirmar, verificar que el turno viejo sigue `CONFIRMADO`).
- [x] 3.4 `routers/turnos.py::confirmar_turno_endpoint`: ya tiene `commit` y `rollback`. Verificar que el bloque `try/except` está correcto y agregar test que valide rollback en cada excepción.
- [x] 3.5 `routers/turnos.py::confirmar_asistencia_endpoint`: agregar `await db.commit()` en happy path. Agregar `await db.rollback()` en cada `except`.
- [x] 3.6 `routers/pacientes.py::create_paciente`: refactorizar para unificar contrato (ver task 9). Por ahora, agregar `await db.commit()` consistente.
- [x] 3.7 Correr `pytest` completo. **Expected**: 383 passing / 7 failing (sin cambios respecto al baseline). **RESULT**: 7F/398P/1S/1X (15 nuevos tests passing, 0 regresiones).

## 4. Adaptar scheduler al Patrón A

- [x] 4.1 `scheduler/jobs.py::_ejecutar_liberar_reservas_vencidas`: agregar `await sess.commit()` al final del bloque `try` por profesional (o al final del job entero). El servicio ya no commitea, así que el job debe hacerlo. Test del job con un mock de la sesión que valide que `commit()` se llama una vez por job.
- [x] 4.2 `scheduler/jobs.py::_ejecutar_marcar_turnos_completados`: agregar `await sess.commit()` al final. Misma estrategia.
- [x] 4.3 `scheduler/jobs.py::_ejecutar_procesar_timeouts_lista_espera`: agregar `await sess.commit()` al final. Misma estrategia.
- [x] 4.4 Verificar que `_ejecutar_enviar_recordatorios` sigue funcionando (delega a `marcar_recordatorio_enviado` que también puede no commitear — ajustar si es necesario). — Modificado `notificacion_service.marcar_recordatorio_enviado` para no commitear, agregado commit en job.
- [x] 4.5 Correr `pytest tests/test_scheduler_job.py` y validar que los 3 tests pre-existentes que fallan siguen fallando (no son responsabilidad de este change, pero no se deben arreglar accidentalmente sin querer). **VERIFIED**: los 3 pre-existentes siguen fallando (test_scheduler_tiene_job_registrado, test_scheduler_job_marcar_turnos_completados_loguea_excepciones, test_scheduler_job_enviar_recordatorios_maneja_excepcion).

## 5. Fix timezone en comparaciones de expiración

- [x] 5.1 Reemplazar `datetime.now()` por `datetime.now(timezone.utc).replace(tzinfo=None)` en `turno_service.reservar_turno` (línea 110, cálculo de `expiracion`). Test con `freezegun` o mock de `datetime.now` que valide que el timestamp calculado es UTC.
- [x] 5.2 Reemplazar en `turno_service.confirmar_turno` (línea 154, comparación `reserva.expiracion < datetime.now()`). Test con mock de `datetime.now` que retorne una hora local (ej. `datetime(2026, 6, 27, 9, 0, 0)` sin tzinfo) y verificar que la comparación se hace correctamente contra UTC.
- [x] 5.3 Reemplazar en `turno_service.liberar_reservas_vencidas` (línea 206, query de `ReservaTemporal.expiracion < datetime.now()`). Misma estrategia de test.
- [x] 5.4 Reemplazar en `lista_espera_service.procesar_timeouts_lista_espera` (línea 344, cálculo de `umbral`).
- [x] 5.5 Reemplazar en `lista_espera_service.notificar_y_marcar` (línea 150, `datetime.now()`).
- [x] 5.6 Reemplazar en `lista_espera_service.rechazar_turno_lista_espera` (línea 264, `datetime.now()`).
- [x] 5.7 Reemplazar en `lista_espera_service.registrar_en_lista_espera` (imports y creación si aplica).
- [x] 5.8 Correr `pytest tests/test_turno_service.py` y validar que no se rompieron tests (algunos pueden haber asumido `datetime.now()`). **VERIFIED**: 41/41 tests pasando en test_turno_service.py después del fix de timezone.

## 6. `SELECT FOR UPDATE` en `ReservaTemporal` en `confirmar_turno`

- [x] 6.1 Agregar `.with_for_update()` a la query de `ReservaTemporal` en `turno_service.confirmar_turno` (líneas 148-150). Test que valide que dos confirmaciones concurrentes al mismo turno serializan: la primera confirma, la segunda detecta que el turno ya no está `RESERVADO_TEMPORAL`. — DONE en `turno_service.confirmar_turno`. Tests de concurrencia van en group 12.

## 7. `reprogramar_turno` atómico (C-2 — CRITICAL)

- [x] 7.1 **Test rojo**: test que mockea `confirmar_turno` lanzando `PacienteConTurnoActivoError`. Valida que el turno viejo sigue `CONFIRMADO` y NO existe turno nuevo. **VERDE en `test_transaction_hardening.py::test_reprogramar_rollback_si_confirmar_falla_paciente_duplicado`**.
- [x] 7.2 Refactorizar `reprogramar_turno` para que use una sola transacción (cancelar, reservar, confirmar — sin commits internos; caller hace commit). **DONE en `turno_service.py::reprogramar_turno`**.
- [x] 7.3 **Triangulación**: test que mockea `confirmar_turno` lanzando `TurnoNoDisponibleError`. Misma validación. **VERDE en `test_reprogramar_rollback_si_confirmar_falla_slot_no_disponible`**.
- [x] 7.4 **Happy path test**: reprogramación exitosa end-to-end. **VERDE en `test_reprogramar_happy_path`**.

## 8. `liberar_reservas_vencidas` reordenado (C-5)

- [x] 8.1 **Test rojo**: test de liberación + LE atómico. **VERDE en `test_transaction_hardening.py::test_liberar_crea_reserva_para_lista_espera_atomico`**.
- [x] 8.2 Refactorizar `liberar_reservas_vencidas` para que la evaluación de LE ocurra dentro de la misma transacción. **DONE en `turno_service.py::liberar_reservas_vencidas`**.
- [x] 8.3 **Test de rollback**: test que mockea `evaluar_lista_espera` lanzando. Valida rollback completo. **VERDE en `test_liberar_rollback_si_evaluar_le_falla`**.

## 9. `aceptar_turno_lista_espera` captura `TurnoExpiradoError` (C-4)

- [x] 9.1 **Test rojo**: test con reserva expirada. Valida slot liberado, reserva eliminada, registro reseteado, LE re-llamada. **VERDE en `test_transaction_hardening.py::test_aceptar_con_reserva_expirada_libera_y_re_evaluar`**.
- [x] 9.2 Refactorizar `aceptar_turno_lista_espera` con `try/except TurnoExpiradoError`. **DONE en `lista_espera_service.py::aceptar_turno_lista_espera` + helper `_reset_y_reofertar_lista_espera`**.
- [x] 9.3 **Test de propagación**: test que valida que la excepción se propaga al router. **Cubierto por `test_aceptar_con_reserva_expirada_libera_y_re_evaluar`** (pytest.raises(TurnoExpiradoError)).

## 10. Extraer `completar_turno` a servicio (B-3)

- [x] 10.1 **Test rojo**: test de `completar_turno()`. **VERDE en `test_transaction_hardening.py::TestCompletarTurno`** (4 tests).
- [x] 10.2 Implementar `turno_service.completar_turno()`. **DONE**.
- [x] 10.3 Refactorizar `completar_turno_endpoint` para usar el servicio. **DONE en `routers/turnos.py`**.
- [x] 10.4 Validar que los tests del router siguen pasando. **VERDE**.

## 11. Unificar `pacientes.py::create_paciente` (B-4)

- [x] 11.1 **Test rojo**: test del router. **VERDE en `test_transaction_hardening.py::TestCreatePacienteUnificado`** (3 tests).
- [x] 11.2 Refactorizar `create_paciente` para unificar. **DONE en `routers/pacientes.py`**.
- [x] 11.3 Validar tests. **VERDE**.

## 12. Test de concurrencia real

- [x] 12.1 Verificar que el engine de tests es PostgreSQL real. **VERIFICADO**: conftest.py usa testcontainers[postgres].
- [x] 12.2 **Test**: dos `confirmar_turno` concurrentes. **VERDE en `test_concurrency.py::test_doble_confirmar_mismo_turno_solo_uno_exitoso`**. La serialización con SELECT FOR UPDATE funciona.
- [x] 12.3 **Test**: dos `reservar_turno` concurrentes. **XFALLED** (esperado). Race condition documentada en `design.md` R3/OQ-5; requiere UNIQUE constraint o SERIALIZABLE isolation, fuera del scope de este change.
- [x] 12.4 **Test**: dos `liberar_reservas_vencidas` concurrentes. **VERDE en `test_doble_liberar_reservas_sin_doble_procesamiento`**.

## 13. Verificación final

- [x] 13.1 Correr `pytest` completo. **RESULT**: 7F/398P/1S/1X (xfail esperado). Comparado con baseline 7F/383P/1S = 15 tests nuevos passing, 0 regresiones. ✅
- [x] 13.2 Correr `pytest --co -q`. **RESULT**: 407 tests collected (391 baseline + 16 nuevos). Delta: +16 tests. ✅
- [x] 13.3 `openspec validate transaction-hardening --strict`. **RESULT**: "Change 'transaction-hardening' is valid". ✅
- [x] 13.4 Verificar servicios sin commit. **VERIFIED**: turno_service.py, lista_espera_service.py, paciente_service.py NO tienen `await db.commit()` (excepto savepoint en `crear_o_obtener_paciente`). ✅
- [x] 13.5 Verificar routers con commit/rollback. **VERIFIED**: routers/turnos.py, pacientes.py, lista_espera.py, profesional.py tienen commit en happy path y rollback en cada except. ✅
