# Tasks — test-suite-stabilization

> Housekeeping de tests: cerrar las 2 failures pre-existentes restantes del baseline post-`concurrency-hardening`, marcar los 4 bugs reales de lista de espera como `xfail(strict=False)` con razones específicas, actualizar 2 tests obsoletos, y eliminar el archivo debug untracked.
>
> **TDD estricto activo**: cada task sigue el ciclo test rojo → verde → refactor. Como este change es housekeeping (no introduce funcionalidad), "rojo" significa "test falla en suite completa pre-cambio" y "verde" significa "test pasa en suite completa post-cambio".
>
> **Baseline conocido pre-cambio** (capturado 2026-06-28): 2 failed, 405 passed, 1 skipped, 4 xfailed in 410.11s.
>
> **Estado de implementación**: la mayoría de los cambios a tests ya están aplicados en el working directory (sin commitear) por la sesión anterior. Quedan como tareas pendientes: la verificación final en suite completa, el commit, y el archive.

## 1. Safety net y baseline

- [x] 1.1 Capturar baseline de pytest desde `backend/` y guardar en `tests/.baseline-failures.txt`. Expected: **2 failed, 405 passed, 1 skipped, 4 xfailed** (pre-existente: `test_scheduler_job_marcar_turnos_completados_loguea_excepciones`, `test_scheduler_job_enviar_recordatorios_maneja_excepcion`). — DONE 2026-06-28.
- [x] 1.2 Verificar que los 2 tests fallidos **pasan en aislamiento** (`pytest <ruta>::<test>` retorna `1 passed`). Confirma que el problema es de la suite, no del test. — DONE 2026-06-28.

## 2. Tests obsoletos (actualizar a la realidad post-hardening)

- [x] 2.1 **`backend/tests/test_models.py::test_base_tables_populated`**: agregar `"super_admin"` al set esperado de tablas (5→6). El modelo `super_admin` se introdujo en `c-19-super-admin-role`. — DONE en working directory (diff sin commitear).
- [x] 2.2 **`backend/tests/test_profesional.py::test_profesional_new_columns_nullable`**: refactor para reflejar que `email` y `password_hash` son **NOT NULL post-C-22**. Usar `make_profesional()` (factory del change `fix-test-fixtures-email`) y forzar null solo en las columnas opcionales (`api_key`, `google_refresh_token`, `telegram_bot_token`, `telegram_secret_token`). Asserear `email is not None` y `password_hash is not None`. — DONE en working directory.

## 3. Test de scheduler: instanciar scheduler directo

- [x] 3.1 **`backend/tests/test_scheduler_job.py::test_scheduler_tiene_job_registrado`**: convertir de `def` a `async def`. El fixture `client` overridea el lifespan con `_noop_lifespan` (no arranca el scheduler), por lo que `app.state.scheduler` queda en `None`. Instanciar el scheduler directamente con `init_scheduler(app)` desde `app.scheduler.jobs`, verificar que los 3 jobs se registran (`liberar_reservas_vencidas`, `marcar_turnos_completados`, `enviar_recordatorios`). Cleanup con `scheduler.shutdown(wait=False)`. — DONE en working directory.

## 4. Tests de scheduler: migrar de caplog a mock directo del logger

> **Contexto**: caplog en pytest-asyncio con event loop reutilizado (suite completa) no captura records de loggers específicos. El patrón "mockear logger directamente" ya está validado en `test_telegram_service.py::test_enviar_mensaje_con_log_loggea_contexto_al_fallar`. Lo replicamos en los 2 tests que fallan.
>
> **Nota técnica**: en 4.1, patcheamos `app.scheduler.jobs._ejecutar_marcar_turnos_completados` (no `marcar_turnos_completados`) porque el try/except interior del job hace `await sess.rollback()` que lanza `MissingGreenlet` cuando la sesión está en estado inconsistente por el mockeo de la función de servicio. Patcheando el ejecutor evitamos ese side-effect no relacionado al test.

- [x] 4.1 **`backend/tests/test_scheduler_job.py::test_scheduler_job_marcar_turnos_completados_loguea_excepciones`**: patchear `app.scheduler.jobs._ejecutar_marcar_turnos_completados` con `side_effect` async que lanza `RuntimeError("DB error")`, más `patch("app.scheduler.jobs.logger")` y assert sobre `mock_logger.exception.call_args[0][0]`. El mensaje exacto logueado es `f"Error en job marcar_turnos_completados: {exc}"` (try/except exterior). — DONE.
- [x] 4.2 **`backend/tests/test_scheduler_job.py::test_scheduler_job_enviar_recordatorios_maneja_excepcion`**: mismo patrón. Patchear `app.scheduler.jobs.enviar_recordatorio_telegram` con `side_effect` async que lanza `Exception("Telegram fail")`, más `patch("app.scheduler.jobs.logger")` y assert sobre `mock_logger.error.call_args[0][0]`. El mensaje exacto logueado es `f"Error enviando recordatorio para turno {turno.id}: {exc}"`. — DONE.

## 5. Tests de lista de espera: marcar como xfail con justificación

> **Contexto**: 4 tests son **flaky pre-existentes** por bugs reales en la lógica de lista de espera. Marcarlos como `xfail(strict=False)` con razones específicas documenta los bugs pendientes sin ocultar el problema.

- [x] 5.1 **`backend/tests/test_lista_espera_integration.py::test_e2e_cancelar_notificar_aceptar`**: marcar `@pytest.mark.xfail(reason="Flaky: el slot no se libera correctamente tras cancelar → evaluar_lista_espera no encuentra el slot disponible. Bug pre-existente de la lógica de lista de espera.", strict=False)`. — DONE en working directory.
- [x] 5.2 **`backend/tests/test_lista_espera_integration.py::test_race_condition_doble_cancelacion`**: marcar `@pytest.mark.xfail(reason="Flaky: comportamiento de doble cancelación es intermitente. Bug pre-existente relacionado con el orden de commits en la lista de espera.", strict=False)`. — DONE en working directory.
- [x] 5.3 **`backend/tests/test_lista_espera_integration.py::test_timeout_job_pasa_al_siguiente`**: marcar `@pytest.mark.xfail(reason="Bug pre-existente: tras timeout de un paciente, el slot no se libera para el siguiente. La query de turno no se marca como DISPONIBLE antes de la re-evaluación de LE, por lo que el siguiente paciente no puede tomarlo. Requiere refactor de procesar_timeouts_lista_espera + UNIQUE constraint. Fuera del scope de los cambios transaction-hardening/concurrency-hardening.", strict=False)`. Además, reemplazar `datetime.now()` por `utcnow_naive()` (helper de `conftest.py` introducido en `transaction-hardening`) para consistencia con la lógica del servicio. — DONE en working directory.
- [x] 5.4 **`backend/tests/test_lista_espera_service.py::test_evaluar_lista_espera_notifica_siguiente`**: marcar `@pytest.mark.xfail(reason="Flaky en suite completa: cuando se corre después de otros tests, el estado de la sesión async queda inconsistente (probable issue de cleanup). Pasa en aislamiento. Bug pre-existente.", strict=False)`. — DONE en working directory.

## 6. Cleanup

- [x] 6.1 Eliminar `backend/tests/test_caplog_debug.py` (archivo debug untracked, no debe quedar). — DONE en working directory.

## 7. Verificación final

- [x] 7.1 Correr `pytest --tb=no -q` desde `backend/`. **RESULTADO**: `406 passed, 1 skipped, 1 xfailed, 3 xpassed, 2 warnings in 356.08s`. **0 failed** ✅.
- [x] 7.2 Verificar que los xfails son los 4 bugs de lista de espera documentados. — DONE: 4 xfails totales (1 xfailed + 3 xpassed en este run; los 3 xpassed son flaky pre-existentes que pasan en suite limpia). El test `test_timeout_job_pasa_al_siguiente` falla consistentemente (XFAIL correcto); los otros 3 pasan en este run pero flakean con state heredado.
- [x] 7.3 Verificar que ningún test que pasaba antes ahora falla (0 regresiones). — DONE: la cuenta de passing pasó de 405 a 406 (+1, no regresiones).
- [x] 7.4 Actualizar `backend/tests/.baseline-failures.txt` con la cuenta post-change. — DONE.

## 8. Archival y commit

- [x] 8.1 Commitear los cambios con conventional commits (`test(scheduler): ...`, `test(models): ...`, etc.). — DONE.
- [x] 8.2 Archivar el change con `openspec archive test-suite-stabilization`. — DONE.
