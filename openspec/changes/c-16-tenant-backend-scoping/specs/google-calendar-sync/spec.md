## MODIFIED Requirements

### Requirement: Servicio de sincronización con Google Calendar
El sistema SHALL proporcionar un servicio `calendar_service.py` que actúe como wrapper sobre Google Calendar API v3 **por profesional**, permitiendo crear, actualizar y eliminar eventos de turnos en el calendario del profesional correspondiente.

#### Scenario: Crear evento de turno para profesional
- **WHEN** se invoca `create_event(turno)` con un objeto `Turno` válido y el profesional asociado tiene `google_refresh_token`
- **THEN** el servicio crea un evento en Google Calendar del profesional con título, descripción y horario correspondientes
- **AND** retorna el `event_id` generado por Google

#### Scenario: Crear evento sin refresh_token
- **WHEN** se invoca `create_event(turno)` y el profesional no tiene `google_refresh_token`
- **THEN** el servicio lanza ValueError indicando que el profesional no tiene token configurado
- **AND** el turno en base de datos permanece CONFIRMADO sin `google_event_id`

#### Scenario: Actualizar evento de turno
- **WHEN** se invoca `update_event(turno)` con un `Turno` que ya tiene `google_event_id` y el profesional tiene `google_refresh_token`
- **THEN** el servicio actualiza el evento existente en Google Calendar del profesional con los nuevos datos
- **AND** retorna el mismo `event_id`

#### Scenario: Eliminar evento de turno
- **WHEN** se invoca `delete_event(event_id)` con un `event_id` válido y el profesional tiene `google_refresh_token`
- **THEN** el servicio elimina el evento correspondiente de Google Calendar del profesional

### Requirement: Autenticación OAuth 2.0 por profesional
El sistema SHALL autenticarse con Google Calendar API usando credenciales OAuth 2.0 del profesional, cargando el `refresh_token` desde `profesional.google_refresh_token` y usando `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` de las variables de entorno para obtener access tokens.

#### Scenario: Autenticación exitosa por profesional
- **WHEN** el profesional tiene un `google_refresh_token` válido
- **THEN** el servicio construye un objeto `Credentials` de `google-auth` usando el refresh token
- **AND** puede realizar llamadas autorizadas a Google Calendar API en nombre del profesional

#### Scenario: Profesional sin refresh_token
- **WHEN** el profesional no tiene `google_refresh_token` configurado
- **THEN** el servicio no puede construir el cliente de Calendar
- **AND** las operaciones de Calendar para ese profesional se omiten con log warning

### Requirement: Reintentos con backoff exponencial
El sistema SHALL reintentar automáticamente las operaciones de Google Calendar ante errores transitorios, usando backoff exponencial con jitter configurable. El comportamiento de reintentos es global y no cambia por profesional.

#### Scenario: Reintento ante error 5xx
- **WHEN** Google Calendar API responde con HTTP 500 o 503 para un profesional
- **THEN** el servicio reintenta la operación hasta `GOOGLE_CALENDAR_MAX_RETRIES` veces
- **AND** el delay entre reintentos crece exponencialmente

#### Scenario: No reintentar ante error 4xx
- **WHEN** Google Calendar API responde con HTTP 400 o 404
- **THEN** el servicio NO reintenta la operación
- **AND** lanza la excepción correspondiente inmediatamente

### Requirement: Idempotencia en creación de eventos
El sistema SHALL garantizar que `create_event` sea idempotente: si se invoca múltiples veces para el mismo `Turno`, no debe generar duplicados en Google Calendar del profesional.

#### Scenario: Creación idempotente
- **WHEN** `create_event(turno)` se invoca dos veces con el mismo `Turno` del mismo profesional
- **THEN** la segunda invocación actualiza el evento existente en lugar de crear uno nuevo
- **AND** solo existe un evento en Google Calendar del profesional para ese turno
