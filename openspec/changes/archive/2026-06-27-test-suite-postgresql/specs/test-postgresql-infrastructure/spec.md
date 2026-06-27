## ADDED Requirements

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
