## ADDED Requirements

### Requirement: Modelo de datos soporta aislamiento por profesional
El sistema SHALL modificar el schema de base de datos para que `Paciente` y `ListaDeEspera` estén vinculados obligatoriamente a un `Profesional`, y `Profesional` SHALL incluir columnas de autenticación e integración para uso futuro.

#### Scenario: Paciente vinculado a profesional
- **WHEN** se crea un `Paciente`
- **THEN** el campo `profesional_id` es obligatorio y referencia a `Profesional.id`

#### Scenario: DNI único por profesional
- **WHEN** se intenta crear dos `Paciente` con el mismo DNI pero distintos `profesional_id`
- **THEN** ambos registros se persisten exitosamente

#### Scenario: DNI duplicado dentro del mismo profesional bloqueado
- **WHEN** se intenta crear dos `Paciente` con el mismo DNI y el mismo `profesional_id`
- **THEN** la base de datos rechaza la inserción por violación de `UNIQUE(profesional_id, dni)`

#### Scenario: ListaDeEspera vinculada a profesional
- **WHEN** se crea un registro en `ListaDeEspera`
- **THEN** el campo `profesional_id` es obligatorio y referencia a `Profesional.id`

#### Scenario: Profesional tiene columnas de autenticación
- **WHEN** se consulta un `Profesional` existente
- **THEN** los campos `email`, `password_hash`, `api_key`, `is_active`, `google_refresh_token`, `telegram_bot_token` y `telegram_secret_token` están disponibles en el schema

#### Scenario: Seed crea profesional con valores por defecto para nuevas columnas
- **WHEN** la aplicación inicia sin registros en `Profesional`
- **THEN** el seed crea un `Profesional` con `email="admin@local.dev"`, `password_hash` con un hash bcrypt dummy, e `is_active=TRUE`

#### Scenario: Configuración incluye secretos para JWT
- **WHEN** se inicializan los `Settings`
- **THEN** `secret_key` y `algorithm` están definidos y disponibles para uso en C-15

#### Scenario: Fixture profesional disponible en tests
- **WHEN** se ejecuta cualquier test que requiera un profesional
- **THEN** el fixture `profesional` proporciona un `Profesional` persistido con todos los campos obligatorios poblados
