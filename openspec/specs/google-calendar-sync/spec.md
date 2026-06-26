## ADDED Requirements

### Requirement: Servicio de sincronización con Google Calendar
El sistema DEBE proporcionar un servicio `calendar_service.py` que actúe como wrapper sobre Google Calendar API v3, permitiendo crear, actualizar y eliminar eventos de turnos.

#### Scenario: Crear evento de turno
- **WHEN** se invoca `create_event(turno)` con un objeto `Turno` válido
- **THEN** el servicio crea un evento en Google Calendar con título, descripción y horario correspondientes
- **AND** retorna el `event_id` generado por Google

#### Scenario: Actualizar evento de turno
- **WHEN** se invoca `update_event(turno)` con un `Turno` que ya tiene `google_event_id`
- **THEN** el servicio actualiza el evento existente en Google Calendar con los nuevos datos
- **AND** retorna el mismo `event_id`

#### Scenario: Eliminar evento de turno
- **WHEN** se invoca `delete_event(event_id)` con un `event_id` válido
- **THEN** el servicio elimina el evento correspondiente de Google Calendar
- **AND** retorna confirmación de éxito

### Requirement: Google Calendar authentication per professional
The system SHALL authenticate with Google Calendar API using each professional's stored `google_refresh_token` together with global OAuth client credentials.

#### Scenario: Authentication succeeds with refresh token
- GIVEN professional has `google_refresh_token` set
- WHEN the calendar service is built for that professional
- THEN it constructs valid OAuth credentials and can call Google Calendar API

#### Scenario: Missing refresh token fails fast
- GIVEN professional has no `google_refresh_token`
- WHEN the calendar service is built for that professional
- THEN it raises a configuration error

### Requirement: Reintentos con backoff exponencial
El sistema DEBE reintentar automáticamente las operaciones de Google Calendar ante errores transitorios, usando backoff exponencial con jitter configurable.

#### Scenario: Reintento ante error 5xx
- **WHEN** Google Calendar API responde con HTTP 500 o 503
- **THEN** el servicio reintenta la operación hasta `GOOGLE_CALENDAR_MAX_RETRIES` veces
- **AND** el delay entre reintentos crece exponencialmente desde `GOOGLE_CALENDAR_BASE_DELAY` hasta `GOOGLE_CALENDAR_MAX_DELAY`

#### Scenario: No reintentar ante error 4xx
- **WHEN** Google Calendar API responde con HTTP 400 o 404
- **THEN** el servicio NO reintenta la operación
- **AND** lanza la excepción correspondiente inmediatamente

#### Scenario: Configuración de reintentos vía environment
- **WHEN** las variables `GOOGLE_CALENDAR_MAX_RETRIES`, `GOOGLE_CALENDAR_BASE_DELAY`, `GOOGLE_CALENDAR_MAX_DELAY` están definidas
- **THEN** el servicio usa esos valores para configurar la política de reintentos
- **AND** si no están definidas, usa valores por defecto (`max_retries=3`, `base_delay=1.0`, `max_delay=10.0`)

### Requirement: Calendar target per professional
The system SHALL target the calendar identified by `profesional.google_calendar_id`, falling back to `"primary"` when the value is null or empty.

#### Scenario: Create event on configured calendar
- GIVEN professional with `google_calendar_id="clinic@example.com"`
- WHEN `create_event(turno)` is invoked
- THEN the event is inserted into `"clinic@example.com"`

#### Scenario: Create event with default calendar
- GIVEN professional with `google_calendar_id` unset
- WHEN `create_event(turno)` is invoked
- THEN the event is inserted into `"primary"`

#### Scenario: Update and delete use same calendar
- GIVEN an existing event on the professional's configured calendar
- WHEN `update_event(turno)` or `delete_event(event_id)` is invoked
- THEN the operation targets the same `calendarId` used for creation

### Requirement: Pydantic Settings for Google Calendar
The system SHALL declare only `google_client_id`, `google_client_secret`, `google_calendar_max_retries`, `google_calendar_base_delay`, and `google_calendar_max_delay` as Pydantic Settings fields for Google Calendar integration.

#### Scenario: Valid settings present
- WHEN the backend starts with Google OAuth client settings and retry settings
- THEN `Settings` exposes them as typed attributes
- AND startup succeeds without `GOOGLE_CALENDAR_CREDENTIALS` or `GOOGLE_CALENDAR_ID`

### Requirement: Idempotencia en creación de eventos
El sistema DEBE garantizar que `create_event` sea idempotente: si se invoca múltiples veces para el mismo `Turno`, no debe generar duplicados en Google Calendar.

#### Scenario: Creación idempotente
- **WHEN** `create_event(turno)` se invoca dos veces con el mismo `Turno`
- **THEN** la segunda invocación actualiza el evento existente en lugar de crear uno nuevo
- **AND** solo existe un evento en Google Calendar para ese turno
