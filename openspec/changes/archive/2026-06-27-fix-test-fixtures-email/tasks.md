# Tasks: `fix-test-fixtures-email`

> **TDD Estricto activo**: cada task sigue el ciclo **RED → GREEN → TRIANGULATE → REFACTOR**.
> **Regla dura**: no avanzar al siguiente task sin marcar el actual como `[x]`.
> **Safety net primero**: T-00 captura baseline antes de tocar nada.

## 0. Safety Net

- [x] 0.1 Correr `cd backend && pytest --tb=no -q 2>&1 | tail -30` y capturar baseline: total tests, fallidos, pasados, tiempo.
- [x] 0.2 Filtrar la salida para contar cuántos fallan con `null value in column "email" violates not-null constraint` específicamente.
- [x] 0.3 Documentar el baseline en `backend/tests/BASELINE.md` (crear nueva sección "Pre fix-test-fixtures-email").
- [x] 0.4 NO fixes pre-existing failures por otras causas (datetime, ENUM, race condition) — esos están fuera de scope de este change.

> **Esperado**: ~87 failed / ~293 passed, de los cuales ~60 fallan por `null value in column "email"`.

## 1. TDD: Factory `make_profesional` y helper persistido

- [x] 1.1 **RED**: Crear `backend/tests/test_conftest.py` con `test_make_profesional_defaults_completos`: invoca `make_profesional()`, asserta todos los campos `nullable=False` no-None. **Debe fallar** porque el factory no existe.
- [x] 1.2 **GREEN**: Implementar `make_profesional(**overrides) -> Profesional` en `backend/tests/conftest.py` con los defaults definidos en design.md D5. Importar `uuid` y `hash_password`. El test de 1.1 pasa.
- [x] 1.3 **TRIANGULATE**: Agregar `test_make_profesional_emails_son_unicos` — dos invocaciones generan emails distintos. **Pasa** con el impl de 1.2.
- [x] 1.4 **TRIANGULATE**: Agregar `test_make_profesional_override` — `make_profesional(email="x@y.z", nombre="Dr. X")` retorna instancia con esos valores. **Pasa** con el impl de 1.2.
- [x] 1.5 **TRIANGULATE**: Agregar `test_make_profesional_persisted_asigna_id` — `await make_profesional_persisted(db_session)` retorna instancia con `id` positivo. Implementar `make_profesional_persisted` (GREEN).
- [x] 1.6 **TRIANGULATE**: Agregar `test_make_profesional_persisted_es_queryable` — instancia persistida aparece en `SELECT * FROM profesional WHERE email = ...`. **Pasa** con el impl de 1.5.
- [x] 1.7 **TRIANGULATE**: Agregar `test_make_profesional_persisted_override` — override funciona en el helper persistido. **Pasa** con el impl de 1.5.
- [x] 1.8 **REFACTOR**: revisar el factory para type hints completos, docstring claro, y consistencia de estilo con el resto de `conftest.py`.

> **Validación T-01**: `cd backend && pytest tests/test_conftest.py -v` debe pasar todos los tests.

## 2. Reemplazo de `Profesional(...)` en tests de modelos

> Aplicar `make_profesional()` o `make_profesional_persisted(db_session, ...)` según el patrón del test (si necesita `id`, usar persistido).

- [x] 2.1 `backend/tests/test_profesional.py` (10 instancias) — reemplazar cada `Profesional(...)`. Si el test asume un email específico, pasarlo como override.
- [x] 2.2 `backend/tests/test_turno.py` (7 instancias) — reemplazar, preservando los emails literales donde el test los usa.
- [x] 2.3 `backend/tests/test_reserva_temporal.py` (3 instancias) — reemplazar.
- [x] 2.4 `backend/tests/test_relations.py` (4 instancias) — reemplazar.
- [x] 2.5 `backend/tests/test_paciente.py` (2 instancias) — el `Profesional` se usa para asociar al `Paciente`; reemplazar.
- [x] 2.6 `backend/tests/test_models.py` — si tiene `Profesional(...)` directo, reemplazar (probablemente no, ya que testea `Base`).

> **Validación T-02**: `cd backend && pytest tests/test_profesional.py tests/test_turno.py tests/test_reserva_temporal.py tests/test_relations.py tests/test_paciente.py -v` no debe tener errores `null value in column "email"`.

## 3. Reemplazo de `Profesional(...)` en tests de servicios

- [x] 3.1 `backend/tests/test_availability_service.py` (11 instancias) — todos los tests usan `db_session` y agregan el profesional; usar `make_profesional()` + `db_session.add` + commit manual, o `make_profesional_persisted(db_session)` si no hay lógica intermedia.
- [x] 3.2 `backend/tests/test_turno_service.py` (2 instancias) — reemplazar.
- [x] 3.3 `backend/tests/test_lista_espera_service.py` (1 helper `_seed_profesional`) — modificar el helper para usar el factory. Como el helper se llama múltiples veces en la misma sesión, el UUID del factory garantiza unicidad.
- [x] 3.4 `backend/tests/test_lista_espera_integration.py` (1 helper) — modificar el helper análogo.
- [x] 3.5 `backend/tests/test_lista_de_espera.py` (1 instancia) — reemplazar.
- [x] 3.6 `backend/tests/test_lista_espera_api.py` (1 instancia) — reemplazar.
- [x] 3.7 `backend/tests/test_notificacion_service.py` (3 instancias / 2 helpers) — modificar helpers `_seed_profesional` y el inline con `profesional_b`.
- [x] 3.8 `backend/tests/test_telegram_service.py` (18 instancias) — el más grande. Reemplazar todas. Tests que asumen `telegram_bot_token` específico: pasar como override.
- [x] 3.9 `backend/tests/test_calendar_service.py` (4 instancias) — reemplazar.

> **Validación T-03**: `cd backend && pytest tests/test_availability_service.py tests/test_turno_service.py tests/test_lista_espera_service.py tests/test_lista_espera_integration.py tests/test_lista_de_espera.py tests/test_lista_espera_api.py tests/test_notificacion_service.py tests/test_telegram_service.py tests/test_calendar_service.py -v` no debe tener errores `null value in column "email"`.

## 4. Reemplazo de `Profesional(...)` en tests de scheduler, auth, isolation, routers

- [x] 4.1 `backend/tests/test_scheduler_job.py` (1 instancia) — reemplazar.
- [x] 4.2 `backend/tests/test_scheduler_timeout.py` (1 instancia) — reemplazar.
- [x] 4.3 `backend/tests/test_scheduler_isolation.py` (1 instancia) — reemplazar (test de aislamiento entre profesionales: el factory con UUID es ideal).
- [x] 4.4 `backend/tests/test_auth_integration.py` (2 instancias) — si las instancias se usan para tests que no requieren login, reemplazar. Si usan `email` + `password` para login, dejar como están o usar el fixture `profesional` existente.
- [x] 4.5 `backend/tests/test_profesional_isolation.py` (1 instancia) — reemplazar.
- [x] 4.6 `backend/tests/test_profesional_router.py` (2 instancias) — reemplazar.
- [x] 4.7 `backend/tests/test_pacientes_router.py` (1 instancia) — reemplazar.
- [x] 4.8 `backend/tests/test_webhooks.py` (1 instancia) — reemplazar.

> **Validación T-04**: `cd backend && pytest tests/test_scheduler_job.py tests/test_scheduler_timeout.py tests/test_scheduler_isolation.py tests/test_auth_integration.py tests/test_profesional_isolation.py tests/test_profesional_router.py tests/test_pacientes_router.py tests/test_webhooks.py -v` no debe tener errores `null value in column "email"`.

## 5. Verificación de barrido completo

- [x] 5.1 `grep -rn "Profesional(" backend/tests/ --include="*.py" | grep -v "make_profesional" | grep -v "from app.models" | grep -v ": Profesional"` — debe retornar **0 líneas** (sin contar el fixture `profesional` en conftest.py, las definiciones del factory, ni las anotaciones de tipo).
- [x] 5.2 Documentar el conteo: cuántas instancias se reemplazaron, en cuántos archivos.
- [x] 5.3 Verificar manualmente 3-5 tests muestreados para confirmar que el factory está bien usado (no se rompió lógica accidentalmente).

## 6. Verificación de suite completa

- [x] 6.1 Correr `cd backend && pytest --tb=no -q 2>&1 | tail -30` y capturar nueva métrica.
- [x] 6.2 Comparar con baseline de T-00: cuántos tests pasaron de fallar a pasar.
- [x] 6.3 Filtrar errores `null value in column "email"`: **deben ser 0**.
- [x] 6.4 Si hay tests que fallan por otras causas (no email), evaluar:
  - Si la causa ya existía en el baseline → fuera de scope, documentar.
  - Si la causa fue introducida por este change → fixear antes de cerrar.
- [x] 6.5 Medir tiempo total: ¿la suite es más rápida, igual, o más lenta? Documentar delta.
- [x] 6.6 Iterar sobre 6.4 hasta que no haya regresiones atribuibles a este change.

## 7. Documentación y archival

- [x] 7.1 Actualizar `backend/tests/BASELINE.md` con sección "Post fix-test-fixtures-email": métricas, delta, archivos tocados.
- [x] 7.2 Verificar que `openspec/changes/fix-test-fixtures-email/` tiene los 4 artifacts: `proposal.md`, `design.md`, `specs/test-fixtures-factory/spec.md`, `specs/test-postgresql-infrastructure/spec.md`, `tasks.md`.
- [x] 7.3 Listo para `openspec-archive-change` (correr `/opsx-archive` o el skill equivalente en la próxima sesión).
- [x] 7.4 Reportar en CHANGES.md o herramienta equivalente que `fix-test-fixtures-email` está listo para archivar.

---

## Resumen de tasks

| Grupo | Tasks | Descripción |
|-------|-------|-------------|
| 0. Safety Net | 4 | Capturar baseline pre-cambio |
| 1. TDD Factory | 8 | Tests del factory con TDD estricto (rojo → verde → triangulación → refactor) |
| 2. Modelos | 6 | Reemplazo en tests de modelos |
| 3. Servicios | 9 | Reemplazo en tests de servicios (el más grande: telegram con 18 instancias) |
| 4. Scheduler/Auth/Routers | 8 | Reemplazo en tests misceláneos |
| 5. Barrido | 3 | Verificación con grep + muestreo manual |
| 6. Verificación | 6 | Suite completa + comparación baseline |
| 7. Docs | 4 | Documentación y archival |
| **TOTAL** | **48 tasks** | |

## Convenciones

- **Override de email**: si un test necesita un email específico (ej. para login), usar `make_profesional(email="specific@test.local", ...)`.
- **Override de campos opcionales**: si un test necesita `telegram_bot_token`, pasar como `make_profesional(telegram_bot_token="x", ...)`.
- **Patrón con `db_session.flush()`** (sin commit): usar `make_profesional()` + `db_session.add(p)` + `db_session.flush()` manual (no usar `make_profesional_persisted`).
- **Patrón con commit y `id`**: usar `make_profesional_persisted(db_session, ...)`.
- **NO modificar** el fixture `profesional` existente en `conftest.py` (preservar para tests de auth).
- **NO modificar** `app/models/profesional.py` ni `app/seed.py` ni `app/services/auth_service.py`.
