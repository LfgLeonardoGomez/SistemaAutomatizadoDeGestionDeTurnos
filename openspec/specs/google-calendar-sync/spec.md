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

### Requirement: Autenticación OAuth 2.0 con cuenta de servicio
El sistema DEBE autenticarse con Google Calendar API usando una cuenta de servicio OAuth 2.0, cargando las credenciales desde un JSON proporcionado vía variable de entorno.

#### Scenario: Autenticación exitosa
- **WHEN** la aplicación inicia y `GOOGLE_CALENDAR_CREDENTIALS` contiene un JSON válido de cuenta de servicio
- **THEN** el servicio construye un objeto `Credentials` de `google-auth`
- **AND** puede realizar llamadas autorizadas a Google Calendar API

#### Scenario: Credenciales inválidas
- **WHEN** `GOOGLE_CALENDAR_CREDENTIALS` es inválido o está ausente
- **THEN** el servicio lanza una excepción de configuración al momento de construirse
- **AND** el error se loguea con contexto (falta de credenciales)

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

### Requirement: Configuración centralizada en Pydantic Settings
El sistema DEBE declarar todas las variables de configuración de Google Calendar como campos de Pydantic Settings en `app/config.py`, con validación y defaults.

#### Scenario: Variables de entorno presentes
- **WHEN** `GOOGLE_CALENDAR_CREDENTIALS`, `GOOGLE_CALENDAR_ID`, `GOOGLE_CALENDAR_MAX_RETRIES`, `GOOGLE_CALENDAR_BASE_DELAY`, `GOOGLE_CALENDAR_MAX_DELAY` están definidas
- **THEN** `Settings` las expone como atributos tipados
- **AND** los valores se validan en el startup de FastAPI

### Requirement: Idempotencia en creación de eventos
El sistema DEBE garantizar que `create_event` sea idempotente: si se invoca múltiples veces para el mismo `Turno`, no debe generar duplicados en Google Calendar.

#### Scenario: Creación idempotente
- **WHEN** `create_event(turno)` se invoca dos veces con el mismo `Turno`
- **THEN** la segunda invocación actualiza el evento existente en lugar de crear uno nuevo
- **AND** solo existe un evento en Google Calendar para ese turno
