# Baseline pre-change test-suite-postgresql

**Fecha**: 2026-06-27
**Comando**: `cd backend && pytest --tb=no -q`
**Backend con**: SQLite in-memory (`sqlite+aiosqlite:///:memory:`)

---

# Baseline pre-change fix-test-fixtures-email

**Fecha**: 2026-06-27
**Comando**: `cd backend && pytest --tb=no -q`
**Backend con**: PostgreSQL (testcontainers `postgres:15-alpine`)

## Resultados

```
86 failed, 294 passed, 1 skipped, 1 warning in 385.17s (0:06:25)
```

## Failures atribuibles a `null value in column "email"`

```
pytest --tb=line 2>&1 | grep -c 'null value in column "email"'
83
```

**~83 de 86 failures (~96%)** son por la constraint `NOT NULL` en `email` introducida en C-14. SQLite no enforced consistentemente el `NOT NULL` en algunos contextos (especialmente `String` sin `CHECK`), pero PostgreSQL sí. El change `fix-test-fixtures-email` ataca exactamente esta causa raíz.

## Failures NO atribuibles a email (~3 de 86)

Causas probables: datetime sin timezone, ENUM inválido, race conditions, etc. **FUERA DE SCOPE** de este change. Se documentarán en T-06 al comparar con post-change.

## Instancias de `Profesional(...)` en tests

```
grep -rn "Profesional(" backend/tests/ --include="*.py" | wc -l
86
```

- **23 archivos** contienen `Profesional(...)` (22 listados en `proposal.md` + `isolation/test_isolation.py` descubierto durante el grep).
- **85 instancias** a reemplazar (la #86 es el fixture `profesional` existente en `conftest.py`, que tiene email `"test@local.dev"` y se conserva sin cambios por compatibilidad con `test_auth_integration.py`).
- **Distribución**: `test_telegram_service.py` (18), `test_availability_service.py` (11), `test_profesional.py` (10), `test_turno.py` (7), `isolation/test_isolation.py` (7), `test_relations.py` (4), `test_calendar_service.py` (4), `test_notificacion_service.py` (3), `test_reserva_temporal.py` (3), `test_auth_integration.py` (2), `test_paciente.py` (2), `test_profesional_router.py` (2), `test_turno_service.py` (2), `test_lista_espera_api.py` (1), `test_lista_de_espera.py` (1), `test_lista_espera_service.py` (1), `test_lista_espera_integration.py` (1), `test_pacientes_router.py` (1), `test_profesional_isolation.py` (1), `test_scheduler_isolation.py` (1), `test_scheduler_timeout.py` (1), `test_scheduler_job.py` (1), `test_webhooks.py` (1).

## Estrategia de fix

- Factory `make_profesional(**overrides) -> Profesional` en `conftest.py` con defaults válidos para todos los campos `nullable=False` (uuid-based email por default, `password_hash=hash_password("test-password")`).
- Helper `make_profesional_persisted(db_session, **overrides) -> Profesional` que hace add+commit+refresh.
- Reemplazar las 85 instancias de `Profesional(...)` en los 23 archivos por invocaciones del factory.
- TDD: `backend/tests/test_conftest.py` con tests para el factory antes del barrido masivo.

## Resultados

```
87 failed, 293 passed, 1 skipped, 1 warning in 163.06s (0:02:43)
```

## Distribución de failures por archivo

| Archivo | Failures |
|---|---|
| test_telegram_service.py | 16 |
| test_lista_espera_service.py | 18 |
| test_availability_service.py | 11 |
| test_notificacion_service.py | 11 |
| test_scheduler_job.py | 7 |
| test_turno.py | 7 |
| test_reserva_temporal.py | 3 |
| test_lista_espera_integration.py | 3 |
| test_seed.py (TestSeedProfesional) | 2 |
| test_scheduler_timeout.py | 2 |
| test_profesional.py | 2 |
| test_turno_service.py | 1 |
| test_scheduler_isolation.py | 1 |
| test_migration.py | 1 |
| test_models.py | 1 |
| **TOTAL** | **87** |

## Categorías de failure esperadas

- **F-1/F-2/F-3**: Tests con SQLite explícito (test_seed, test_migration) — EN SCOPE
- **F-4/F-5**: Tests con `client` fixture sin override (test_scheduler, test_health) — EN SCOPE
- **F-6**: Datetime sin timezone (test_scheduler_job, test_scheduler_timeout) — EN SCOPE
- **F-7**: Race condition simulada (test_turno_service) — EN SCOPE
- **F-8**: ENUM inválido (test_calendar_service) — EN SCOPE
- **Otros**: Services, models, integraciones — FUERA DE SCOPE (revisar al final)
