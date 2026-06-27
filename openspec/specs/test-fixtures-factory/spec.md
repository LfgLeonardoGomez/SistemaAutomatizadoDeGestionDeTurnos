# test-fixtures-factory Specification

## Purpose
TBD - created by archiving change fix-test-fixtures-email. Update Purpose after archive.
## Requirements
### Requirement: Factory `make_profesional` con defaults válidos
El sistema de tests SHALL proveer un factory `make_profesional(**overrides) -> Profesional` en `backend/tests/conftest.py` que genere instancias del modelo `Profesional` con defaults válidos para todos los campos requeridos, de modo que cualquier test pueda obtener una instancia insertable en PostgreSQL sin necesidad de setear manualmente los campos `nullable=False`.

#### Scenario: Default email es único por invocación
- **WHEN** un test invoca `make_profesional()` dos veces en la misma sesión
- **THEN** las dos instancias resultantes tienen emails distintos
- **AND** ambos emails respetan la constraint `unique=True` del modelo

#### Scenario: Default email es válido para `NOT NULL` constraint
- **GIVEN** un test invoca `make_profesional()` sin override
- **WHEN** la instancia se persiste (`db_session.add(...)` + `commit()`)
- **THEN** PostgreSQL NO rechaza el commit con `null value in column "email" violates not-null constraint`

#### Scenario: Default password_hash es un bcrypt válido
- **GIVEN** un test invoca `make_profesional()` sin override
- **WHEN** se lee el campo `password_hash` de la instancia
- **THEN** el valor es un string que comienza con `$2b$` (formato bcrypt)
- **AND** `verify_password(plaintext, hash)` retorna `True` para el plaintext usado por el factory

#### Scenario: Override de cualquier campo es soportado
- **WHEN** un test invoca `make_profesional(email="custom@x.com", nombre="Dr. X")`
- **THEN** la instancia retornada tiene `email == "custom@x.com"` y `nombre == "Dr. X"`
- **AND** los demás campos usan los defaults

#### Scenario: Defaults para todos los campos `nullable=False`
- **WHEN** un test invoca `make_profesional()` sin override
- **THEN** la instancia tiene valores no-None para: `nombre`, `especialidad`, `duracion_turno`, `horario_inicio`, `horario_fin`, `dias_atencion`, `email`, `is_active`, `google_calendar_id`

#### Scenario: Campos opcionales son `None` por default
- **WHEN** un test invoca `make_profesional()` sin override
- **THEN** los campos `api_key`, `google_refresh_token`, `telegram_bot_token`, `telegram_secret_token` son `None`

### Requirement: Helper `make_profesional_persisted` retorna instancia con `id`
El sistema de tests SHALL proveer un helper asincrónico `make_profesional_persisted(db_session, **overrides) -> Profesional` que crea una instancia con `make_profesional`, la persiste en la DB, hace `commit` y `refresh`, y retorna la instancia con `id` asignado.

#### Scenario: Instancia persistida tiene `id` válido
- **GIVEN** un test invoca `await make_profesional_persisted(db_session)`
- **WHEN** se lee el campo `id` de la instancia retornada
- **THEN** `id` es un entero positivo (no `None`)

#### Scenario: Instancia persistida está queryable después
- **GIVEN** un test que llama `await make_profesional_persisted(db_session, email="x@y.z")`
- **WHEN** el test ejecuta `SELECT * FROM profesional WHERE email = 'x@y.z'`
- **THEN** la query retorna exactamente una fila

#### Scenario: Override funciona en el helper persistido
- **WHEN** un test invoca `await make_profesional_persisted(db_session, email="custom@x.com", duracion_turno=60)`
- **THEN** la instancia retornada tiene `email == "custom@x.com"` y `duracion_turno == 60`

### Requirement: Tests del factory validan el comportamiento
El sistema de tests SHALL incluir un archivo `backend/tests/test_conftest.py` con tests que validen el comportamiento de `make_profesional` y `make_profesional_persisted` antes de aplicarlos masivamente al resto de la suite.

#### Scenario: Test de email único
- **WHEN** se ejecuta el test `test_make_profesional_emails_son_unicos`
- **THEN** dos invocaciones consecutivas de `make_profesional()` producen emails distintos

#### Scenario: Test de persistencia exitosa
- **WHEN** se ejecuta el test `test_make_profesional_persisted_asigna_id`
- **THEN** `await make_profesional_persisted(db_session)` retorna una instancia con `id` no-None y queryable desde `db_session`

#### Scenario: Test de override
- **WHEN** se ejecuta el test `test_make_profesional_override`
- **THEN** `make_profesional(email="x@y.z", duracion_turno=60)` retorna instancia con los valores overridden y el resto de defaults

#### Scenario: Test de defaults completos
- **WHEN** se ejecuta el test `test_make_profesional_defaults_completos`
- **THEN** la instancia retornada tiene todos los campos `nullable=False` con valores no-None

### Requirement: Aplicación masiva del factory en tests existentes
El sistema de tests SHALL usar `make_profesional` o `make_profesional_persisted` en reemplazo de las instanciaciones directas de `Profesional(...)` en todos los archivos de test que actualmente fallan por falta de `email`.

#### Scenario: Reemplazo en archivos de test de modelos
- **WHEN** se aplica el factory a `test_profesional.py`, `test_turno.py`, `test_reserva_temporal.py`, `test_models.py`
- **THEN** ninguna instancia de `Profesional(...)` en estos archivos queda sin setear `email`
- **AND** la suite corre sin errores `null value in column "email"`

#### Scenario: Reemplazo en archivos de test de servicios
- **WHEN** se aplica el factory a `test_availability_service.py`, `test_turno_service.py`, `test_lista_espera_service.py`, `test_lista_espera_integration.py`, `test_notificacion_service.py`, `test_telegram_service.py`
- **THEN** ninguna instancia de `Profesional(...)` en estos archivos queda sin setear `email`

#### Scenario: Reemplazo en archivos de test de scheduler
- **WHEN** se aplica el factory a `test_scheduler_job.py`, `test_scheduler_timeout.py`, `test_scheduler_isolation.py`
- **THEN** ninguna instancia de `Profesional(...)` en estos archivos queda sin setear `email`

#### Scenario: Preservación del fixture `profesional` para tests de auth
- **WHEN** se aplica el factory al resto de la suite
- **THEN** el fixture `profesional` en `conftest.py` (que usa `email="test@local.dev"`, `password="changeme"`) se conserva sin cambios
- **AND** los tests de `test_auth_integration.py` que dependen de estos valores siguen pasando

