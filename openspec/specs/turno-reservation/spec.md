## ADDED Requirements

### Requirement: Sistema permite consultar disponibilidad de turnos
El sistema SHALL exponer un endpoint que devuelva los slots disponibles para una fecha dada, calculados como horarios posibles según configuración del profesional MINUS turnos en estado `CONFIRMADO` o `RESERVADO_TEMPORAL`.

#### Scenario: Consulta con slots disponibles
- **WHEN** el usuario solicita disponibilidad para una fecha con horarios libres
- **THEN** el sistema SHALL retornar la lista de slots disponibles con hora de inicio y fin

#### Scenario: Consulta sin slots disponibles
- **WHEN** el usuario solicita disponibilidad para una fecha donde todos los slots están ocupados
- **THEN** el sistema SHALL retornar una lista vacía
- **AND** el sistema SHALL responder con HTTP 200

## ADDED Requirements

### Requirement: Sistema permite reservar un turno temporalmente
El sistema SHALL permitir la creación de un turno en estado `RESERVADO_TEMPORAL` con una `ReservaTemporal` asociada que incluya fecha de expiración. La expiración SHALL ser calculada como `NOW() + RESERVA_TEMPORAL_MINUTOS` (default 2 minutos).

#### Scenario: Reserva temporal exitosa
- **WHEN** el paciente selecciona un slot disponible
- **THEN** el sistema SHALL crear un `Turno` en estado `RESERVADO_TEMPORAL`
- **AND** el sistema SHALL crear una `ReservaTemporal` con `expiracion` calculada
- **AND** el sistema SHALL retornar el turno creado con HTTP 201

#### Scenario: Reserva temporal bloqueada por turno activo del mismo paciente
- **WHEN** el paciente intenta reservar un slot pero ya tiene un turno en estado `RESERVADO_TEMPORAL` o `CONFIRMADO`
- **THEN** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Condición de carrera en reserva simultánea
- **WHEN** dos pacientes intentan reservar el mismo slot disponible exactamente al mismo tiempo
- **THEN** el sistema SHALL garantizar que solo uno de los dos obtenga la reserva
- **AND** el segundo SHALL recibir un error indicando que el slot ya no está disponible

## ADDED Requirements

### Requirement: Sistema permite confirmar un turno reservado
El sistema SHALL permitir confirmar un turno en estado `RESERVADO_TEMPORAL`. Al confirmar, el sistema SHALL validar que el paciente no tenga otro turno activo, SHALL registrar/identificar al paciente, SHALL pasar el turno a `CONFIRMADO`, SHALL eliminar la `ReservaTemporal` asociada y SHALL crear un evento en Google Calendar.

#### Scenario: Confirmación exitosa
- **WHEN** el paciente confirma un turno en `RESERVADO_TEMPORAL` proporcionando sus datos
- **THEN** el sistema SHALL validar que el paciente no tenga otro turno activo
- **AND** el sistema SHALL registrar o identificar al paciente
- **AND** el sistema SHALL actualizar el turno a estado `CONFIRMADO`
- **AND** el sistema SHALL eliminar la `ReservaTemporal` asociada
- **AND** el sistema SHALL crear un evento en Google Calendar
- **AND** el sistema SHALL retornar el turno confirmado con HTTP 200

#### Scenario: Confirmación de turno ya expirado
- **WHEN** el paciente intenta confirmar un turno cuya `ReservaTemporal` ya expiró
- **THEN** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Confirmación con doble turno activo del mismo paciente
- **WHEN** el paciente intenta confirmar un turno pero adquiere otro turno activo en paralelo
- **THEN** el sistema SHALL detectar la violación de RN-TU-01 atomically
- **AND** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Confirmación persiste event_id de Google Calendar
- **WHEN** se confirma un turno y `CalendarService.create_event()` retorna `"event_abc123"`
- **THEN** el sistema SHALL asignar `turno.google_event_id = "event_abc123"`
- **AND** el sistema SHALL hacer commit para persistir el valor en base de datos
- **AND** el sistema SHALL retornar el turno con `google_event_id` poblado

#### Scenario: Confirmación con fallo de Google Calendar no persiste event_id
- **WHEN** se confirma un turno y `CalendarService.create_event()` lanza una excepción
- **THEN** el turno SHALL quedar en estado `CONFIRMADO`
- **AND** `turno.google_event_id` SHALL ser `NULL`
- **AND** el sistema SHALL registrar el error en logs

## ADDED Requirements

### Requirement: Sistema libera reservas temporales vencidas automáticamente
El sistema SHALL ejecutar un job periódico que identifique las `ReservaTemporal` cuya `expiracion` sea menor a `NOW()`, actualice los `Turno` asociados a estado `DISPONIBLE` y elimine las `ReservaTemporal` vencidas.

#### Scenario: Expiración automática de reserva temporal
- **WHEN** el job de limpieza ejecuta y encuentra una `ReservaTemporal` vencida
- **THEN** el sistema SHALL actualizar el `Turno` asociado a estado `DISPONIBLE`
- **AND** el sistema SHALL eliminar la `ReservaTemporal`
- **AND** el sistema SHALL registrar la operación en logs

#### Scenario: No hay reservas vencidas
- **WHEN** el job de limpieza ejecuta y no encuentra reservas vencidas
- **THEN** el sistema SHALL no modificar ningún registro
- **AND** el sistema SHALL registrar que no hubo acciones

## MODIFIED Requirements

### Requirement: APScheduler initializes with FastAPI lifespan
The system SHALL initialize an `AsyncIOScheduler` instance during FastAPI application startup (lifespan context) and shut it down gracefully on application shutdown. The scheduler SHALL register a periodic job `liberar_reservas_vencidas` that ejecuta cada minuto para limpiar reservas temporales expiradas.

#### Scenario: Scheduler starts with application
- **WHEN** the FastAPI application starts
- **THEN** an `AsyncIOScheduler` instance SHALL be created and started without errors
- **AND** the scheduler SHALL be accessible via the application state or dependency injection mechanism
- **AND** the job `liberar_reservas_vencidas` SHALL be registered with trigger `interval` de 1 minuto

#### Scenario: Scheduler shuts down gracefully
- **WHEN** the FastAPI application receives a shutdown signal
- **THEN** the scheduler SHALL be shut down gracefully without raising unhandled exceptions
- **AND** any pending jobs SHALL be allowed to complete or timeout according to APScheduler default behavior

#### Scenario: Scheduler accepts job registration
- **WHEN** code registers a dummy job function with the scheduler after startup
- **THEN** the job SHALL be accepted without errors
- **AND** the job SHALL be listed in the scheduler's job store

#### Scenario: Job de limpieza ejecuta correctamente
- **WHEN** el job `liberar_reservas_vencidas` ejecuta
- **THEN** el sistema SHALL llamar a `turno_service.liberar_reservas_vencidas()`
- **AND** el sistema SHALL capturar y loguear cualquier excepción sin detener el scheduler
