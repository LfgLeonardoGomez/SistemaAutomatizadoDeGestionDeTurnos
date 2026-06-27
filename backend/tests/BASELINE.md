# Baseline pre-change test-suite-postgresql

**Fecha**: 2026-06-27
**Comando**: `cd backend && pytest --tb=no -q`
**Backend con**: SQLite in-memory (`sqlite+aiosqlite:///:memory:`)

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
