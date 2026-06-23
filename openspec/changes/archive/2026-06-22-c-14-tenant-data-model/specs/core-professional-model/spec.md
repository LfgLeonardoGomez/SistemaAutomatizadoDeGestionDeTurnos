## ADDED Requirements

### Requirement: Profesional tiene columnas de autenticación
El sistema SHALL almacenar en `Profesional` las columnas `email` (único, nullable inicialmente), `password_hash` (nullable), `api_key` (único, nullable) e `is_active` (default TRUE).

#### Scenario: Seed crea profesional con email y password_hash
- **WHEN** la aplicación inicia sin registros en `Profesional`
- **THEN** el seed crea un `Profesional` con `email="admin@local.dev"` y `password_hash` con un hash bcrypt dummy

#### Scenario: Email único por profesional
- **WHEN** se intenta crear un segundo `Profesional` con el mismo `email`
- **THEN** la base de datos rechaza la inserción por violación de UNIQUE

#### Scenario: API key única por profesional
- **WHEN** se intenta crear un segundo `Profesional` con el mismo `api_key`
- **THEN** la base de datos rechaza la inserción por violación de UNIQUE

#### Scenario: Profesional inactivo
- **WHEN** se actualiza `is_active` a `FALSE` para un `Profesional` existente
- **THEN** el campo se actualiza correctamente

### Requirement: Profesional tiene tokens de integración
El sistema SHALL almacenar en `Profesional` las columnas `google_refresh_token` (TEXT, nullable), `telegram_bot_token` (VARCHAR(255), nullable) y `telegram_secret_token` (VARCHAR(255), nullable) para integraciones futuras.

#### Scenario: Google Calendar token persistido
- **WHEN** se actualiza `google_refresh_token` para un `Profesional`
- **THEN** el valor se persiste correctamente en la base de datos

#### Scenario: Telegram bot token persistido
- **WHEN** se actualiza `telegram_bot_token` para un `Profesional`
- **THEN** el valor se persiste correctamente en la base de datos

#### Scenario: Telegram secret token persistido
- **WHEN** se actualiza `telegram_secret_token` para un `Profesional`
- **THEN** el valor se persiste correctamente en la base de datos

### Requirement: Profesional tiene configuración de agenda por defecto
El sistema SHALL crear un registro `Profesional` con valores por defecto al iniciar la aplicación si no existe ninguno.

#### Scenario: Seed idempotente en arranque
- **WHEN** la aplicación inicia y no hay registros en `Profesional`
- **THEN** se crea un `Profesional` con nombre="Dr. Por Defecto", especialidad="Odontología general", duracion_turno=30, horario_inicio="08:00", horario_fin="18:00", dias_atencion=["Lunes","Martes","Miércoles","Jueves","Viernes"], email="admin@local.dev", password_hash="$2b$12$...", is_active=TRUE

#### Scenario: Seed no duplica registros
- **WHEN** la aplicación inicia y ya existe un `Profesional`
- **THEN** no se crea un segundo registro; el seed es idempotente

### Requirement: Profesional define duración de turnos
El sistema SHALL almacenar `duracion_turno` en minutos para el profesional.

#### Scenario: Duración por defecto
- **WHEN** se consulta el `Profesional` creado por seed
- **THEN** `duracion_turno` es 30 minutos

### Requirement: Profesional tiene horarios de atención
El sistema SHALL almacenar `horario_inicio`, `horario_fin` y `dias_atencion` para el profesional.

#### Scenario: Horarios configurados
- **WHEN** se consulta el `Profesional` creado por seed
- **THEN** `horario_inicio` es "08:00", `horario_fin` es "18:00" y `dias_atencion` incluye los días laborables

#### Scenario: Profesional tiene múltiples turnos
- **WHEN** un `Profesional` tiene 5 turnos asignados
- **THEN** la consulta `profesional.turnos` retorna los 5 turnos
