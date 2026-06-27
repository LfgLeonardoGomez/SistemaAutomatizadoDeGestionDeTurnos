# Design: `fix-test-fixtures-email`

## Context

La suite de tests del backend (369 tests, 37 archivos, FastAPI + SQLAlchemy 2.0 async + PostgreSQL + pytest + pytest-asyncio) fue migrada a PostgreSQL real en el change `test-suite-postgresql` (archivado 2026-06-27). La migración expuso una clase masiva de bugs latentes: tests que instanciaban `Profesional(...)` sin setear el campo `email`, aprovechando que SQLite no enforced consistentemente el `NOT NULL` constraint. Con PostgreSQL, esos tests fallan al `commit()` con `null value in column "email" violates not-null constraint`.

El modelo `Profesional` (`backend/app/models/profesional.py:25-27`) define:

```python
email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
```

La constraint es correcta: es parte de la regla de negocio de autenticación y unicidad introducida en C-14. El problema es del lado de los tests, no del modelo.

Hay **76+ instancias de `Profesional(...)` en 22 archivos de test** que no setean `email`. Modificarlas una por una introduce churn alto, riesgo de regresión por inconsistencias (algunos tests usan el mismo email literal, otros olvidan algún campo), y no resuelve el problema estructuralmente: el próximo campo requerido en el modelo (v2.0 podría agregar `tenant_id`, `timezone`, etc.) volvería a requerir un barrido similar.

**Solución propuesta**: un factory `make_profesional(**overrides) -> Profesional` en `conftest.py` con defaults válidos para todos los campos requeridos. Los tests invocan `make_profesional()` o `make_profesional(email="x@y.z")` y obtienen una instancia lista para commit. Es DRY, mantenible, y reduce el churn a un solo punto de cambio.

## Goals / Non-Goals

**Goals:**
- Proveer un factory `make_profesional(**overrides)` en `backend/tests/conftest.py` que genere instancias válidas de `Profesional` por default.
- Proveer un helper `make_profesional_persisted(db_session, **overrides)` que retorne una instancia persistida con `id` asignado.
- El default de `email` debe ser único por invocación (vía `uuid.uuid4().hex[:8]`) para respetar la constraint `unique=True` del modelo.
- El default de `password_hash` debe ser un hash bcrypt válido (reusar `hash_password("test-password")`).
- Reemplazar las 76+ instancias de `Profesional(...)` en los 22 archivos de test por invocaciones del factory.
- Validar con TDD: tests del factory en `backend/tests/test_conftest.py` antes de usarlo masivamente.
- Reducir los ~60 tests que fallan por falta de `email` en PostgreSQL.

**Non-Goals:**
- No se cambia el modelo `Profesional` ni la constraint `email NOT NULL`.
- No se introduce un patrón genérico de factory para otros modelos (Paciente, Turno, etc.) — solo `Profesional`.
- No se modifica el fixture `profesional` existente más allá de opcionalmente delegar al factory.
- No se reescriben tests que ya pasan.

## Decisions

### D1: Factory function, no fixture parametrizada

**Decision**: Implementar `make_profesional(**overrides) -> Profesional` como función Python regular (no fixture de pytest), y un helper `make_profesional_persisted(db_session, **overrides) -> Profesional` que sí recibe la sesión.

**Rationale**:
- Un factory función es invocable dentro de un test (`prof = make_profesional(email="x")`) sin necesidad de parametrizar fixtures por override.
- Tests que necesitan múltiples Profesionales con emails distintos (ej. tests de aislamiento entre profesionales) pueden llamar el factory varias veces con overrides, garantizando unicidad.
- Tests que necesitan la instancia sin persistir (para asociarle turnos antes de commit) usan `make_profesional()` y manejan el `db_session.add(...)` ellos mismos, replicando patrones ya establecidos en el código.
- Tests que solo quieren "un profesional en la DB" usan `make_profesional_persisted(db_session)` y obtienen el `id` listo.

**Alternativas consideradas**:
- *Fixture parametrizada*: pytest-asyncio permite `@pytest.fixture(params=[...])`, pero parametrizar por email único requiere generar los params en runtime, lo cual es incómodo y rompe el patrón "fixture = setup, no test data".
- *Builder pattern*: overkill para 7-8 campos. El factory con `**overrides` es suficiente.
- *Factory Boy*: librería externa. No está en el stack actual y agrega dependencia para un solo uso.

### D2: UUID-based default email, no `pytest fixture` unique counter

**Decision**: `email` default = `f"test-{uuid.uuid4().hex[:8]}@test.local"`.

**Rationale**:
- Garantiza unicidad sin estado global (no requiere fixture de pytest que mantenga un counter).
- Funciona correctamente con paralelización (`pytest -n auto`) porque cada proceso genera sus propios UUIDs.
- El sufijo `8 hex chars` da 4.3 mil millones de combinaciones — más que suficiente para una suite de ~400 tests.
- El dominio `@test.local` es RFC 6761 (reservado para testing), evitando falsos positivos en sistemas de email scanning.

**Alternativas consideradas**:
- *Counter global* (`f"test-{next(counter)}@test.local"`): funciona pero requiere setup de módulo y no paraleliza bien.
- *Timestamp* (`f"test-{int(time.time()*1000)}@test.local"`): colisiona si dos tests corren en el mismo milisegundo.
- *Email literal fijo* (`"test@local.dev"`): es lo que hace el fixture `profesional` actual; falla con `unique=True` si se crea más de uno en la misma sesión (lo cual pasa en tests de aislamiento).

### D3: Helper persistido separado, no combinación

**Decision**: Dos funciones distintas, no una sola con flag `persist=True`.

```python
def make_profesional(**overrides) -> Profesional:
    """Retorna instancia NO persistida."""
    ...

async def make_profesional_persisted(db_session, **overrides) -> Profesional:
    """Retorna instancia persistida con id asignado."""
    p = make_profesional(**overrides)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p
```

**Rationale**:
- API explícita por nombre. Un test que ve `make_profesional_persisted(db_session)` sabe que la instancia está en la DB.
- Sin overhead para tests que solo quieren el objeto en memoria.
- Type hints claros: `make_profesional` no requiere `AsyncSession`, `make_profesional_persisted` sí.

### D4: Reusar `hash_password` del servicio de auth, no crear helper propio

**Decision**: `password_hash` default = `hash_password("test-password")`, importando desde `app.services.auth_service` (mismo módulo que ya usa el fixture `profesional`).

**Rationale**:
- Cero código nuevo: `hash_password` ya existe y ya está importado en `conftest.py`.
- Garantiza que el hash es un bcrypt válido (tests de login que verifiquen `verify_password` siguen funcionando).
- El plaintext `"test-password"` solo se usa en tests; no es un secret de producción.

### D5: Defaults "razonables para tests", no exhaustivos

**Decision**: Los defaults cubren todos los campos `nullable=False` y los más usados, pero NO todos los campos opcionales. Si un test necesita un campo opcional (ej. `telegram_bot_token`, `google_refresh_token`), lo pasa vía `**overrides`.

**Rationale**:
- Mantiene el factory simple y legible.
- No se intenta adivinar valores "razonables" para campos opcionales que el test no usa.
- El patrón `make_profesional(telegram_bot_token="x", telegram_secret_token="y")` es explícito y descubrible.

**Defaults concretos**:
| Campo | Default |
|-------|---------|
| `nombre` | `"Dr. Test"` |
| `especialidad` | `"Odontología general"` |
| `duracion_turno` | `30` |
| `horario_inicio` | `"08:00"` |
| `horario_fin` | `"18:00"` |
| `dias_atencion` | `["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]` |
| `email` | `f"test-{uuid.uuid4().hex[:8]}@test.local"` |
| `password_hash` | `hash_password("test-password")` |
| `is_active` | `True` |
| `google_calendar_id` | `"primary"` |
| Opcionales (`api_key`, `google_refresh_token`, `telegram_bot_token`, `telegram_secret_token`) | `None` (default del modelo) |

### D6: Fixture `profesional` existente se conserva sin cambios

**Decision**: NO se modifica el fixture `profesional` de `conftest.py` (que usa `email="test@local.dev"`, `password="changeme"`).

**Rationale**:
- Tests de auth (`test_auth_integration.py`) dependen de `profesional.email == "test@local.dev"` y `password == "changeme"` para el flujo de login.
- El fixture sigue siendo válido en su rol de "un profesional listo para login".
- Si en el futuro se quiere consolidar, se puede refactorizar para que el fixture use el factory internamente, pero ese no es el objetivo de este change.

### D7: TDD estricto para el factory

**Decision**: Antes de aplicar masivamente el factory a 76+ sitios, escribir tests en `backend/tests/test_conftest.py` que verifiquen:

1. **Happy path**: `make_profesional()` retorna instancia con todos los defaults correctos.
2. **Email único**: dos invocaciones de `make_profesional()` generan emails distintos.
3. **Override funciona**: `make_profesional(email="x@y.z")` setea el email exacto.
4. **Persisted helper**: `make_profesional_persisted(db_session)` retorna instancia con `id` asignado.
5. **Constraint respetada**: la instancia es insertable en PostgreSQL sin error.

**Rationale**:
- El factory mismo es código de test; no aplicar TDD a código de test es laxo. Pero la consistencia importa: si el factory tiene un bug, los 76+ sitios que lo usan se rompen.
- Triangular con 2+ casos (default + override) cumple el flujo TDD del proyecto.

## Risks / Trade-offs

- **[Risk] Email UUID es legible pero feo** (`test-a1b2c3d4@test.local`) → *Mitigation*: usar dominio `.test.local` (RFC 6761) hace evidente que es un email de test. Si un test falla y aparece en logs, no se confunde con un email real.
- **[Risk] Tests de aislamiento entre profesionales que asumen email hardcoded** → *Mitigation*: hacer `grep` de emails literales (`"@local.dev"`, `"@test.com"`) en los tests afectados y ajustar manualmente. Documentar en T-04.
- **[Risk] Inconsistencia si solo se reemplaza parcialmente** (ej. 50 de 76 sitios) → *Mitigation*: la T-04 hace el barrido completo con `grep "Profesional("` como guía. Marcar cada archivo tocado.
- **[Risk] Tests que asumen `email=NULL` o `email=""` para casos negativos** (ej. test de constraint `NOT NULL`) → *Mitigation*: estos tests deben usar `make_profesional(email="")` o setear `email=None` vía override explícito. El factory no fuerza email, solo provee default.
- **[Risk] El factory crece si el modelo suma campos requeridos en v2.0** → *Mitigation*: el factory vive en `conftest.py`; agregar un default es una línea. Trade-off aceptable: ahora pagamos 1 línea por cada campo nuevo vs antes pagábamos 76+ sitios por cada campo nuevo.
- **[Trade-off] Tests ligeramente más lentos** (cada `make_profesional()` genera un UUID, irrelevante) → *Acceptable*: el overhead es del orden de microsegundos.
- **[Trade-off] `make_profesional_persisted` hace commit implícito** → *Documentado en nombre y type hint*: el caller sabe que se hace commit. Si necesita `flush()` sin commit, usa `make_profesional()` y maneja el ciclo de vida manualmente.

## Migration Plan

1. **Safety net**: Correr la suite actual contra PostgreSQL, capturar baseline. Confirmar que ~60 tests fallan por error `null value in column "email"`. Documentar en `backend/tests/BASELINE.md` (ya está documentado en baseline anterior; actualizar con corrida fresca).
2. **TDD fase 1 — test del factory**: escribir `test_conftest.py` con los 5 escenarios en estado rojo. Implementar `make_profesional` y `make_profesional_persisted` en `conftest.py`. Verde. Refactor.
3. **TDD fase 2 — aplicación masiva**: iterar sobre los 22 archivos de test. Reemplazar cada `Profesional(...)` por `make_profesional(...)` o `make_profesional_persisted(db_session, ...)`. Si un test asume un email específico, pasarlo como override.
4. **Validación**: correr la suite completa. Esperado: ~60 tests menos fallando. Si quedan tests fallando por otras causas (no email), evaluar si están en scope.
5. **Documentación**: actualizar `backend/tests/BASELINE.md` con los resultados pre/post.
6. **Rollback**: si el factory tiene un bug crítico, `git revert` del commit. Los tests vuelven a fallar por email, pero no queda código roto. El factory se reintroduce cuando se arregle.

## Open Questions

- ¿El fixture `profesional` debería delegar al factory? → Decidido D6: no en este change, para minimizar churn y mantener compatibilidad con tests de auth. Se puede hacer en un refactor posterior.
- ¿Se necesita un factory para `Paciente` también? → Decidido: no en este change. Si surgen bugs similares con `Paciente` (constraint nuevos en v2.0), se hace un change análogo.
- ¿El factory debería ser un fixture de pytest con scope `function` en vez de función libre? → Decidido D1: función libre. Más explícito, no requiere import especial, no tiene side effects de fixture lifecycle.
- ¿`make_profesional_persisted` debería aceptar `flush_only: bool` para tests que no quieren commit? → Decidido: no. Si un test necesita `flush()` sin commit, usa `make_profesional()` directamente y maneja el ciclo. Mantiene la API simple.
