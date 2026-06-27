## Why

La suite de tests actual usa SQLite in-memory (`sqlite+aiosqlite:///:memory:`), lo cual viola la regla dura del proyecto: **"NADA DE SQLITE, TODO CON POSTGRESQL"**. Esto hace que los tests no detecten comportamientos específicos de PostgreSQL (ENUMs, locking, RETURNING, transacciones reales) y fuerza a las migraciones de Alembic a incluir lógica condicional `_is_sqlite()` que no debería existir. Además, múltiples tests tienen bugs ocultos precisamente porque SQLite no los expone (valores de ENUM inválidos, race conditions simuladas, datetimes sin timezone). Migrar a PostgreSQL real es necesario para que la suite de 369 tests sea confiable y la base de código mantenga integridad.

## What Changes

- **BREAKING**: Eliminar el engine SQLite in-memory de `backend/tests/conftest.py` y reemplazarlo por PostgreSQL real vía testcontainers (default) o `TEST_DATABASE_URL` (fallback local).
- **BREAKING**: Eliminar toda la lógica condicional `_is_sqlite()` de las migraciones de Alembic (`f3c8a2b91c4e` y otras).
- Reescribir fixtures `engine`, `db_session` y `client`/`api_client` para usar PostgreSQL con `NullPool` y limpieza de tablas entre tests (truncate, no recrear DB).
- Fix `test_seed.py` para que no instancie `Settings` con URL SQLite explícita.
- Fix `test_scheduler.py` y `test_health.py` para usar el fixture corregido que overridea `get_db` y no arranque la app real sin DB.
- Fix `test_scheduler_job.py`, `test_scheduler_timeout.py` y similares: usar `datetime.now(timezone.utc)` consistentemente.
- Fix `test_turno_service.py`: renombrar o reimplementar el test de race condition para que use concurrencia real (`asyncio.gather` con dos sesiones distintas).
- Fix `test_calendar_service.py`: corregir `turno.estado="RESERVADO"` (no existe en el ENUM) a `"CONFIRMADO"`.
- Fix `test_migration.py`: eliminar assert hardcodeado de revision ID obsoleto; usar `len(heads) == 1`.
- Agregar `testcontainers[postgres]` a dependencias de desarrollo.
- Agregar `TEST_DATABASE_URL` opcional a `.env.example`.

## Capabilities

### New Capabilities
- `test-postgresql-infrastructure`: Infraestructura de testing con PostgreSQL real (fixtures, testcontainers, limpieza de tablas entre tests, lifecycle de la DB de test).

### Modified Capabilities
<!-- No hay cambios a nivel de requerimientos de negocio. Este change es puramente de infraestructura de testing y corrección de tests existentes. -->
- *(ninguno)*

## Impact

- **Tests**: 37 archivos de test, 369 tests. Todos pasan a ejecutarse contra PostgreSQL.
- **Migraciones**: `backend/alembic/versions/f3c8a2b91c4e_add_profesional_id_and_auth_columns.py` y cualquier otra migración con lógica SQLite.
- **Dependencias**: `backend/requirements.txt` o `requirements-dev.txt` agrega `testcontainers[postgres]`.
- **Configuración**: `backend/.env.example` agrega variable `TEST_DATABASE_URL`.
- **CI/Local**: Requiere Docker running para testcontainers (default), o PostgreSQL local configurado vía env var.
