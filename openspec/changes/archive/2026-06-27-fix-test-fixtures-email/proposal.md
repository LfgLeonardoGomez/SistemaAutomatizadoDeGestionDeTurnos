# Proposal: `fix-test-fixtures-email`

## Status
`proposal` — awaiting `design` and `specs` artifacts.

## Why

Aproximadamente **60 de los 87 tests que fallan en PostgreSQL** lo hacen por una única causa raíz: tests que instancian `Profesional(...)` sin setear el campo `email`. El modelo tiene `email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)` desde C-14 (`tenant-data-model`), regla de negocio correcta. SQLite no respetaba consistentemente el `NOT NULL` en algunos contextos (especialmente al usar `String` sin `CHECK`), por lo que los tests pasaban silenciosamente; PostgreSQL falla con `null value in column "email" violates not-null constraint` al hacer `commit`.

El change anterior `test-suite-postgresql` (archivado el 2026-06-27) confirmó este patrón como la **causa raíz #1** de los failures restantes. Modificar cada test individualmente (76+ instancias de `Profesional(...)` en 22 archivos) sería churn alto, propenso a regresiones, y repetiría el mismo `email="..."` literal en todas partes. Un factory DRY en `conftest.py` resuelve la causa estructural con un solo punto de cambio.

## What Changes

- **Agregar** factory `make_profesional(**overrides) -> Profesional` en `backend/tests/conftest.py` con defaults válidos para todos los campos requeridos.
  - Default `email`: string único por invocación (UUID-based) para respetar la constraint `unique=True`.
  - Default `password_hash`: `hash_password("test-password")` reutilizando el helper ya importado.
  - Demás defaults razonables: `nombre="Dr. Test"`, `duracion_turno=30`, `horario_inicio="08:00"`, `horario_fin="18:00"`, `dias_atencion=[...]`, `is_active=True`, `google_calendar_id="primary"`.
- **Agregar** helper `make_profesional_persisted(db_session, **overrides) -> Profesional` (variante que hace `add`+`commit`+`refresh` y devuelve la instancia persistida con `id` asignado).
- **Reemplazar** todas las instancias de `Profesional(...)` en los 22 archivos de test listados en "Impact", utilizando `make_profesional(**overrides)` o `make_profesional_persisted(db_session, **overrides)`. Cuando un test necesite un email específico (ej. login con credenciales), pasar `email=` explícito.
- **Agregar** tests para el factory mismo en `backend/tests/test_conftest.py` (TDD rojo → verde → refactor) que verifiquen: default email único, override funciona, instancia persistida tiene `id` asignado.
- **NO modificar** el modelo `app/models/profesional.py` (la constraint `nullable=False` es correcta y regla de negocio).
- **NO modificar** `app/seed.py` (ya setea email correctamente).

## Capabilities

### New Capabilities
- `test-fixtures-factory`: Helpers/factories de pytest (`make_profesional`, `make_profesional_persisted`) para crear instancias válidas de `Profesional` en tests, con defaults que respetan todas las constraints del modelo y soportan overrides por test.

### Modified Capabilities
- `test-postgresql-infrastructure`: agregar el requisito de que `backend/tests/conftest.py` provea factories de `Profesional` con defaults válidos (especialmente `email` único) para evitar el patrón "test crea `Profesional()` con `email=None` y falla en PostgreSQL". Este es un delta spec sobre la capability existente.

## Impact

### Tests a modificar (estimación)

| Archivo | Instancias | Naturaleza |
|---------|-----------|------------|
| `test_profesional.py` | 10 | Modelo profesional |
| `test_availability_service.py` | 11 | Slot/turno logic |
| `test_turno.py` | 7 | Turno model |
| `test_turno_service.py` | 2 | Turno service |
| `test_lista_espera_service.py` | 1 (helper `_seed_profesional`) | Lista espera |
| `test_lista_espera_integration.py` | 1 (helper) | E2E lista espera |
| `test_lista_de_espera.py` | 1 | Lista espera |
| `test_lista_espera_api.py` | 1 | Lista espera API |
| `test_notificacion_service.py` | 3 | Notificaciones |
| `test_telegram_service.py` | 18 | Telegram |
| `test_scheduler_job.py` | 1 | Scheduler |
| `test_scheduler_timeout.py` | 1 | Timeouts |
| `test_scheduler_isolation.py` | 1 | Isolation |
| `test_reserva_temporal.py` | 3 | Reserva temporal |
| `test_models.py` | 0 (no tiene Profesional directo, ver nota) | Base models |
| `test_profesional_isolation.py` | 1 | Isolation |
| `test_profesional_router.py` | 2 | Router |
| `test_paciente.py` | 2 | Paciente model |
| `test_pacientes_router.py` | 1 | Pacientes router |
| `test_auth_integration.py` | 2 | Auth integration |
| `test_calendar_service.py` | 4 | Calendar service |
| `test_relations.py` | 4 | Relations |
| `test_webhooks.py` | 1 | Webhooks |
| `conftest.py` | 1 (fixture `profesional` existente) | Conftest |

> **Nota**: `test_models.py` no tiene `Profesional(...)` directo pero `test_conftest.py` se agrega como archivo nuevo. Total estimado: **76 instancias en 22 archivos** + nuevo archivo de test del factory.

### Archivos a crear
- `backend/tests/test_conftest.py` — tests del factory `make_profesional` y `make_profesional_persisted` (TDD).

### Archivos a modificar
- `backend/tests/conftest.py` — agregar factories `make_profesional` y `make_profesional_persisted`; opcionalmente ajustar el fixture `profesional` para que use el factory internamente.
- 22 archivos de test listados arriba — reemplazar `Profesional(...)` por invocaciones del factory.

### Archivos a NO modificar
- `backend/app/models/profesional.py` — la columna `email` con `nullable=False` es correcta.
- `backend/app/seed.py` — ya setea email.
- `backend/app/services/auth_service.py` — `hash_password` ya existe y se reusa.

### Riesgos
- **Bajo**: el factory no introduce comportamiento nuevo, solo encapsula defaults. Riesgo principal es regresión en algún test que dependa de un valor literal que el factory cambia.
- **Mitigation**: comparar baseline de tests pasando antes/después; cualquier regresión se fixa en el mismo change.

## Approach and Key Decisions

1. **Factory, no fixture parametrizada**: `make_profesional(**overrides)` retorna la instancia sin persistir; el caller decide cuándo commitear. Esto da control fino (algunos tests usan `flush()` sin commit, otros `commit()`, otros quieren `refresh()` para tener `id`).
2. **UUID para default email**: `f"test-{uuid.uuid4().hex[:8]}@test.local"` garantiza unicidad incluso si el factory se llama múltiples veces en el mismo test (ej. tests de aislamiento entre profesionales). Es la diferencia crítica vs el fixture `profesional` actual que usa `"test@local.dev"` hardcoded.
3. **Helper persistido separado**: `make_profesional_persisted(db_session, **overrides)` reduce boilerplate en tests que solo quieren "un profesional en la DB para asociarle turnos/pacientes". Internamente hace `add`+`commit`+`refresh`.
4. **Override `email=` soportado**: tests que necesitan login (ej. `test_auth_integration.py` con `profesional.email`) usan el fixture `profesional` existente, que se conserva. Tests que crean Profesionales ad-hoc usan el factory con UUID.
5. **TDD estricto en el factory**: test rojo (factory no existe, falla al instanciar) → test verde (factory existe, defaults válidos) → tests de triangulación (override email, múltiples instancias no colisionan) → refactor.

## Non-Goals

- No se cambia la regla de negocio `email NOT NULL` en el modelo.
- No se introduce un patrón genérico de factory para otros modelos (Paciente, Turno) — solo `Profesional` que es el problema actual.
- No se modifica `seed.py` ni el fixture `profesional` (se conserva por compatibilidad con tests de auth que dependen de `profesional.email == "test@local.dev"` y `password == "changeme"`).
- No se reescriben tests que ya pasan.

## Success Criteria

- [ ] Existen `make_profesional()` y `make_profesional_persisted()` en `backend/tests/conftest.py` con type hints completos.
- [ ] `backend/tests/test_conftest.py` valida: default email único, override funciona, instancia persistida tiene `id`.
- [ ] Las 76+ instancias de `Profesional(...)` en 22 archivos de test están reemplazadas por invocaciones del factory.
- [ ] La suite de tests completa corre contra PostgreSQL sin los ~60 errores `null value in column "email" violates not-null constraint`.
- [ ] No se introducen nuevas regresiones: los tests que pasaban antes siguen pasando.

## Suggested Task Breakdown

1. **T-01 Safety net** — capturar baseline de tests fallando (cuántos son por falta de email) y documentarlo.
2. **T-02 TDD: test del factory `make_profesional`** — escribir `test_conftest.py` con tests rojos, implementar factory, verde, triangulación.
3. **T-03 Refactor del fixture `profesional`** — opcionalmente hacer que el fixture use el factory internamente (consolidación DRY).
4. **T-04 Reemplazar `Profesional(...)` en archivos de test** — iterar sobre los 22 archivos. Tarea sistemática con `grep` como guía. Marcar cada archivo tocado.
5. **T-05 Verificación de suite completa** — correr pytest, comparar contra baseline, iterar hasta que los ~60 errores de email desaparezcan.
6. **T-06 Documentación y archival** — actualizar `backend/tests/BASELINE.md` con resultados antes/después.

## Dependencies

- `test-suite-postgresql` (archivado el 2026-06-27) — estableció la infraestructura PostgreSQL sobre la que aplicamos este change.

## Next Recommended Phase

`sdd-spec` (escribir `specs/test-fixtures-factory/spec.md` y `specs/test-postgresql-infrastructure/spec.md` con delta).
