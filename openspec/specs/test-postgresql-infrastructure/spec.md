# test-postgresql-infrastructure Specification

## Purpose
TBD - created by archiving change test-suite-postgresql. Update Purpose after archive.
## Requirements
### Requirement: PostgreSQL real como único backend de tests
El sistema de tests SHALL ejecutar todos los tests contra una instancia de PostgreSQL real. El uso de SQLite in-memory está EXPRESAMENTE PROHIBIDO en cualquier fixture, test o migración.

#### Scenario: Engine de tests usa PostgreSQL
- **WHEN** pytest inicia la sesión de tests
- **THEN** el fixture `engine` crea un `AsyncEngine` apuntando a PostgreSQL (vía testcontainers o `TEST_DATABASE_URL`)
- **AND** el dialecto del engine NO es SQLite

#### Scenario: Migraciones no contienen lógica SQLite
- **WHEN** se inspeccionan las migraciones de Alembic en `backend/alembic/versions/`
- **THEN** ninguna migración contiene funciones o branches condicionales específicos de SQLite
- **AND** las migraciones aplican limpiamente en PostgreSQL con `alembic upgrade head`

### Requirement: Fixtures de base de datos con lifecycle aislado
El sistema de tests SHALL proveer fixtures `engine`, `db_session`, `client` y `api_client` que operen sobre PostgreSQL y garanticen aislamiento entre tests sin recrear la base de datos completa.

#### Scenario: Fixture engine es session-scoped y crea esquema vía Alembic
- **WHEN** pytest arranca
- **THEN** el fixture `engine` (session-scoped) levanta PostgreSQL si es necesario
- **AND** ejecuta `alembic upgrade head` para crear el esquema
- **AND** el esquema persiste durante toda la sesión de pytest

#### Scenario: Fixture db_session provee sesión async limpia por test
- **WHEN** cada test solicita `db_session`
- **THEN** se le provee una `AsyncSession` vinculada al engine de PostgreSQL
- **AND** al finalizar el test, todas las tablas son truncadas con `TRUNCATE ... CASCADE`
- **AND** las secuencias de auto-incremento se reinician

#### Scenario: Fixture client overridea get_db con la sesión de test
- **WHEN** un test usa el fixture `client` (TestClient)
- **THEN** la aplicación FastAPI tiene overrideado `get_db` para usar la sesión de test de PostgreSQL
- **AND** el lifespan de la app no intenta conectarse a la base de datos de producción/entorno
- **AND** el TestClient funciona sin requerir que `DATABASE_URL` apunte a una instancia real

### Requirement: Limpieza de tablas entre tests vía TRUNCATE
El sistema de tests SHALL limpiar el estado de la base de datos entre tests usando `TRUNCATE` en lugar de eliminar y recrear el esquema o la base de datos.

#### Scenario: Estado de tablas no persiste entre tests
- **GIVEN** un test A que inserta una fila en la tabla `turnos`
- **WHEN** el test A finaliza y comienza el test B
- **THEN** la tabla `turnos` está vacía al inicio del test B
- **AND** no hay filas residuales de ejecuciones anteriores

#### Scenario: TRUNCATE CASCADE maneja foreign keys
- **GIVEN** tablas con relaciones de clave foránea (ej. `reservas_temporales` → `turnos`)
- **WHEN** se ejecuta la limpieza entre tests
- **THEN** `TRUNCATE ... CASCADE` elimina datos de todas las tablas dependientes sin errores de constraint

### Requirement: Fallback a TEST_DATABASE_URL para desarrollo local
El sistema de tests SHALL soportar una variable de entorno `TEST_DATABASE_URL` como alternativa a testcontainers, permitiendo a developers usar una instancia PostgreSQL local.

#### Scenario: TEST_DATABASE_URL definida usa instancia local
- **GIVEN** que la variable de entorno `TEST_DATABASE_URL` está configurada con una URL `postgresql+asyncpg://...`
- **WHEN** pytest inicia
- **THEN** el fixture `engine` se conecta a la URL proporcionada en lugar de levantar un contenedor

#### Scenario: Sin TEST_DATABASE_URL se usa testcontainers
- **GIVEN** que `TEST_DATABASE_URL` no está definida
- **AND** Docker está disponible
- **WHEN** pytest inicia
- **THEN** testcontainers levanta un contenedor PostgreSQL efímero para la sesión de tests

### Requirement: Tests corregidos de bugs ocultos por SQLite
Los tests que tenían errores no detectados por SQLite SHALL ser corregidos para ejecutar correctamente en PostgreSQL.

#### Scenario: Datetime con timezone UTC consistente
- **WHEN** un test manipula campos de fecha/hora (ej. `ReservaTemporal.expiracion`)
- **THEN** usa `datetime.now(timezone.utc)` (offset-aware)
- **AND** no usa `datetime.now()` sin timezone (offset-naive)

#### Scenario: Valores ENUM válidos según el modelo
- **WHEN** un test asigna un valor al campo `estado` de `Turno`
- **THEN** el valor SHALL ser uno de los definidos en el ENUM: `DISPONIBLE`, `RESERVADO_TEMPORAL`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`

#### Scenario: Test de concurrencia usa paralelismo real
- **WHEN** un test valida comportamiento bajo concurrencia (ej. doble reserva del mismo slot)
- **THEN** ejecuta las operaciones concurrentemente usando `asyncio.gather` con sesiones/connections independientes
- **AND** no ejecuta las operaciones secuencialmente en la misma sesión

### Requirement: Factory de `Profesional` en conftest con defaults válidos
El sistema de tests SHALL proveer un factory `make_profesional(**overrides) -> Profesional` en `backend/tests/conftest.py` que genere instancias del modelo `Profesional` con defaults válidos para todos los campos requeridos por la schema de PostgreSQL (incluido `email: NOT NULL UNIQUE` introducido en C-14).

#### Scenario: Default email es único por invocación
- **WHEN** un test invoca `make_profesional()` dos veces en la misma sesión
- **THEN** las dos instancias resultantes tienen emails distintos (generados vía `uuid.uuid4().hex[:8]`)
- **AND** ambos emails pueden coexistir en la tabla `profesional` sin violar la constraint `UNIQUE`

#### Scenario: Instancia creada por el factory es insertable en PostgreSQL
- **GIVEN** un test invoca `make_profesional()` sin override
- **WHEN** la instancia se persiste con `db_session.add(p)` + `await db_session.commit()`
- **THEN** el commit NO falla con `null value in column "email" violates not-null constraint`
- **AND** la fila es visible con un `SELECT` posterior

#### Scenario: Helper `make_profesional_persisted` retorna instancia con `id`
- **GIVEN** un test invoca `await make_profesional_persisted(db_session)` 
- **WHEN** se lee el campo `id` de la instancia retornada
- **THEN** `id` es un entero positivo asignado por la secuencia de PostgreSQL

### Requirement: Aplicación del factory en archivos de test existentes
Los archivos de test que crean instancias de `Profesional` SHALL usar `make_profesional(**overrides)` o `make_profesional_persisted(db_session, **overrides)` en lugar de instanciar `Profesional(...)` directamente sin setear `email`, ya que SQLite no enforced consistentemente el `NOT NULL` constraint y esos tests fallan en PostgreSQL.

#### Scenario: Barrido completo de archivos de test
- **WHEN** se aplica el factory a los 22 archivos de test que contienen `Profesional(...)`
- **THEN** ningún archivo contiene una llamada a `Profesional(...)` sin setear `email`
- **AND** la suite completa de tests corre contra PostgreSQL sin errores `null value in column "email" violates not-null constraint` en la tabla `profesional`

#### Scenario: Excepción para el fixture `profesional` preexistente
- **WHEN** se aplica el factory al resto de la suite
- **THEN** el fixture `profesional` en `conftest.py` (que usa `email="test@local.dev"`, `password="changeme"`) se conserva sin cambios
- **AND** los tests de autenticación que dependen de estos valores específicos siguen pasando

