## Context

La suite de tests del backend (FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Alembic) actualmente corre sobre SQLite in-memory. Esto fue un atajo inicial que se convirtió en regla dura del proyecto: **"NADA DE SQLITE, TODO CON POSTGRESQL"**. El uso de SQLite tiene consecuencias negativas:

1. **Falsos negativos**: Los tests no detectan comportamientos específicos de PostgreSQL (ENUMs, `SELECT FOR UPDATE`, `RETURNING`, locking real, constraints de integridad referencial con `ON DELETE`).
2. **Smell en migraciones**: Las migraciones de Alembic contienen lógica condicional `_is_sqlite()` solo para que los tests pasen, lo cual complica el código de migración y no refleja el entorno productivo.
3. **Bugs ocultos**: Múltiples tests tienen errores que SQLite no expone: valores de ENUM inválidos, race conditions simuladas secuencialmente, uso de `datetime.now()` sin timezone que en PostgreSQL genera comparaciones inválidas.

El change afecta 369 tests en 37 archivos. Es un change de infraestructura transversal que toca fixtures, configuración de pytest, migraciones Alembic y correcciones puntuales en tests.

## Goals / Non-Goals

**Goals:**
- Todos los tests ejecutan contra PostgreSQL real, nunca SQLite.
- Las migraciones de Alembic no contienen lógica condicional para SQLite.
- Los fixtures de pytest proveen aislamiento entre tests sin recrear la base de datos completa (lento).
- Los tests con bugs ocultos por SQLite son corregidos.
- El developer experience (DX) es razonable: tests corren local con Docker (testcontainers) o con una DB de test manual (env var).
- Se establece un baseline de tests pasando antes de comenzar la migración.

**Non-Goals:**
- No se modifican requerimientos de negocio ni comportamiento de la aplicación en producción.
- No se agrega multi-tenancy (es v2.0).
- No se optimiza la velocidad de la suite más allá de no recrear la DB entre tests.
- No se reescriben tests que ya funcionan correctamente (salvo que dependan del fixture `client` sin override de DB).

## Decisions

### D1: testcontainers como default, TEST_DATABASE_URL como fallback

**Decision**: Usar `testcontainers[postgres]` como mecanismo principal para levantar PostgreSQL en tests. Si la variable de entorno `TEST_DATABASE_URL` está definida, usar esa instancia en su lugar.

**Rationale**:
- testcontainers garantiza que cada developer y CI corre exactamente la misma versión de PostgreSQL, sin depender de instalaciones locales.
- `TEST_DATABASE_URL` permite a developers con PostgreSQL local evitar Docker si lo prefieren, mejorando velocidad de iteración local.
- El fallback es trivial: `postgresql+asyncpg://...` vía env var en lugar de contenedor.

**Alternativas consideradas**:
- *Servicio PostgreSQL dedicado siempre*: Requiere que cada developer tenga PG instalado. Fricción innecesaria para nuevos contribuyentes.
- *SQLite con pragmas*: Rechazado por regla dura del proyecto.

### D2: Alembic `upgrade head` para crear esquema, no `Base.metadata.create_all`

**Decision**: Los fixtures de tests aplican las migraciones reales vía `alembic upgrade head` (o el equivalente programático) para crear el esquema, en lugar de usar `Base.metadata.create_all()`.

**Rationale**:
- Esto valida que las migraciones funcionan en PostgreSQL limpio.
- Detecta migraciones rotas antes de que lleguen a producción.
- Elimina la duplicación de esquema entre modelos y migraciones.

**Trade-off**: Es más lento que `create_all`, pero solo ocurre una vez por sesión de pytest (session-scoped fixture), no por test.

### D3: Limpieza de tablas entre tests vía TRUNCATE CASCADE, no drop/create

**Decision**: Entre tests, truncar todas las tablas con `TRUNCATE ... CASCADE` y reiniciar secuencias, en lugar de hacer `drop_all` + `create_all` o recrear la DB.

**Rationale**:
- `TRUNCATE CASCADE` es rápido en PostgreSQL (milisegundos).
- Mantiene el esquema y conexiones intactos, evitando overhead de recrear el engine.
- Funciona correctamente con tablas que tienen FKs.

**Alternativas consideradas**:
- *Transacciones anidadas + rollback*: SQLAlchemy async con `begin_nested()` tiene limitaciones con PostgreSQL real (SAVEPOINTs) y no funciona bien cuando el código bajo test hace commits explícitos.
- *Recrear DB entre tests*: Demasiado lento para 369 tests.

### D4: Unificar fixture `client` y `api_client`

**Decision**: Eliminar el fixture `client` que arranca la app real sin overridear `get_db`. Renombrar/ajustar `api_client` (o crear un nuevo fixture `client`) que siempre overridee `get_db` con la sesión de test de PostgreSQL.

**Rationale**:
- El fixture `client` actual arranca el lifespan de la app, que intenta seedear conectándose a la DB real configurada en env. Si no hay PG corriendo, crashea en startup.
- Un solo fixture de TestClient con overrides reduce confusión.
- Los tests que usaban `client` se migran al fixture corregido.

### D5: NullPool en el engine de tests

**Decision**: El engine de tests usa `NullPool` (no mantiene conexiones persistentes en el pool).

**Rationale**:
- Evita que conexiones queden abiertas entre tests cuando se hace truncate.
- Simplifica el manejo de conexiones en async con pytest-asyncio.
- Trade-off mínimo: ligeramente más lento por crear conexiones, pero irrelevante en contexto de tests.

### D6: Eliminar lógica SQLite de migraciones sin migración reversa

**Decision**: Eliminar directamente los bloques `if _is_sqlite():` de las migraciones existentes, sin crear una nueva migración para ello.

**Rationale**:
- Las migraciones ya aplicadas en producción/staging usaron el branch PostgreSQL (no el SQLite). Eliminar código muerto no afecta el estado de la DB.
- Es un refactor de código, no un cambio de esquema.

## Risks / Trade-offs

- **[Risk] testcontainers requiere Docker running** → *Mitigation*: Fallback con `TEST_DATABASE_URL`. Documentar en README/AGENTS.md.
- **[Risk] TRUNCATE CASCADE puede ser lento si hay muchas tablas** → *Mitigation*: Actualmente hay ~10 tablas. Si escala a cientos, evaluar `DELETE` + `RESTART IDENTITY` o particionamiento de tests. No es problema hoy.
- **[Risk] Alembic upgrade head en session-scoped fixture puede fallar silenciosamente si una migración es async-incompatible** → *Mitigation*: El fixture correrá en CI desde el primer PR. Si falla, se detecta inmediatamente.
- **[Risk] Tests que asumían comportamiento específico de SQLite (autoincrement, tipos débiles) fallan en PostgreSQL** → *Mitigation*: Fase 3 del plan de tasks aborda explícitamente estos tests. Se esperan fallas y se fixean una por una.
- **[Risk] Datetime sin timezone en tests genera `can't compare offset-naive and offset-aware datetimes`** → *Mitigation*: Fix sistemático a `datetime.now(timezone.utc)` en Fase 3.

## Migration Plan

1. **Safety net**: Correr suite actual en SQLite, capturar baseline (cuántos tests pasan, cuántos fallan, tiempo).
2. **Fase 1**: Implementar fixtures PostgreSQL + testcontainers. Validar que un test simple pasa.
3. **Fase 2**: Migrar tests que usan SQLite explícito (`test_seed`, `test_migration`).
4. **Fase 3**: Fix tests con bugs ocultos por SQLite (race condition, ENUM inválido, datetime, etc.).
5. **Fase 4**: Limpiar migraciones de lógica SQLite.
6. **Fase 5**: Correr suite completa. Iterar hasta que todos pasen.
7. **Commit**: Conventional commits por fase (ej. `test: migrate conftest to postgresql`, `fix: remove sqlite logic from migrations`).

## Open Questions

- ¿Se prefiere que el fixture de testcontainers sea `session`-scoped o `module`-scoped? → **session** por performance, pero si hay fugas de estado entre tests, se evalúa `module`.
- ¿Qué versión de PostgreSQL usa testcontainers? → **15-alpine** (misma que producción, verificar en `docker-compose.yml` si existe).
