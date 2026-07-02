## Purpose

El sistema permite a los pacientes consultar disponibilidad, reservar turnos temporalmente, confirmarlos y liberarlos automáticamente al expirar.
## Requirements
### Requirement: Sistema permite consultar disponibilidad de turnos
El sistema SHALL exponer un endpoint que devuelva los slots disponibles para una fecha dada, calculados como horarios posibles según configuración del profesional MINUS turnos en estado `CONFIRMADO` o `RESERVADO_TEMPORAL`.

#### Scenario: Consulta con slots disponibles
- **WHEN** el usuario solicita disponibilidad para una fecha con horarios libres
- **THEN** el sistema SHALL retornar la lista de slots disponibles con hora de inicio y fin

#### Scenario: Consulta sin slots disponibles
- **WHEN** el usuario solicita disponibilidad para una fecha donde todos los slots están ocupados
- **THEN** el sistema SHALL retornar una lista vacía
- **AND** el sistema SHALL responder con HTTP 200

### Requirement: Sistema permite reservar un turno temporalmente
El sistema SHALL permitir la creación de un turno en estado `RESERVADO_TEMPORAL` con una `ReservaTemporal` asociada que incluya fecha de expiración. La expiración SHALL ser calculada como `NOW_UTC() + RESERVA_TEMPORAL_MINUTOS` (default 10 minutos). El timestamp de expiración SHALL ser timezone-aware en UTC al momento de calcularse y SHALL persistirse como naive UTC (`datetime.now(timezone.utc).replace(tzinfo=None)`) para mantener compatibilidad con la columna `TIMESTAMP WITHOUT TIME ZONE` de PostgreSQL.

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

### Requirement: Sistema permite confirmar un turno reservado
El sistema SHALL permitir confirmar un turno en estado `RESERVADO_TEMPORAL`. Al confirmar, el sistema SHALL validar que el paciente no tenga otro turno activo, SHALL registrar/identificar al paciente, SHALL pasar el turno a `CONFIRMADO`, SHALL eliminar la `ReservaTemporal` asociada y SHALL crear un evento en Google Calendar. **El sistema SHALL obtener la `ReservaTemporal` con `SELECT FOR UPDATE` para serializar lecturas concurrentes durante la verificación de expiración, y SHALL comparar `reserva.expiracion` contra `datetime.now(timezone.utc).replace(tzinfo=None)` para garantizar consistencia temporal independientemente del timezone del servidor.**

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
- **THEN** el sistema SHALL rechazar la operación de negocio (`TurnoExpiradoError`)
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Confirmación de turno con comparación timezone-aware
- **WHEN** el servidor está configurado con un timezone distinto a UTC (ej. `America/Argentina/Buenos_Aires`)
- **AND** una `ReservaTemporal` tiene `expiracion = 2026-06-27 12:00:00` (naive UTC)
- **AND** la hora actual UTC es `2026-06-27 12:00:30`
- **THEN** el sistema SHALL detectar la expiración correctamente usando `datetime.now(timezone.utc).replace(tzinfo=None)`
- **AND** SHALL lanzar `TurnoExpiradoError`

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

#### Scenario: Confirmación con SELECT FOR UPDATE sobre ReservaTemporal
- **WHEN** dos requests concurrentes intentan confirmar el mismo `turno_id` simultáneamente
- **THEN** el segundo SHALL esperar a que el primero libere el lock sobre `ReservaTemporal`
- **AND** SHALL ver el estado actualizado (reserva eliminada si el primero confirmó, o turno ya no en `RESERVADO_TEMPORAL`)

### Requirement: Sistema libera reservas temporales vencidas automáticamente
El sistema SHALL ejecutar un job periódico que identifique las `ReservaTemporal` cuya `expiracion` sea menor a `NOW_UTC()`, actualice los `Turno` asociados a estado `DISPONIBLE` y elimine las `ReservaTemporal` vencidas. **El job SHALL ejecutar todas las liberaciones de un profesional en una sola transacción, y SHALL evaluar la lista de espera para cada slot liberado dentro de la misma transacción antes de hacer el commit final.**

#### Scenario: Expiración automática de reserva temporal
- **WHEN** el job de limpieza ejecuta y encuentra una `ReservaTemporal` vencida
- **THEN** el sistema SHALL actualizar el `Turno` asociado a estado `DISPONIBLE`
- **AND** el sistema SHALL eliminar la `ReservaTemporal`
- **AND** el sistema SHALL registrar la operación en logs

#### Scenario: No hay reservas vencidas
- **WHEN** el job de limpieza ejecuta y no encuentra reservas vencidas
- **THEN** el sistema SHALL no modificar ningún registro
- **AND** el sistema SHALL registrar que no hubo acciones

#### Scenario: Liberación con evaluación de lista de espera atómica
- **WHEN** el job libera una reserva vencida y existe un paciente en lista de espera para esa fecha
- **THEN** el sistema SHALL evaluar la lista de espera dentro de la misma transacción
- **AND** SHALL crear una nueva `ReservaTemporal` para el paciente notificado
- **AND** SHALL commitear todo el bloque (liberación + nueva reserva) en una sola operación atómica
- **AND** si la notificación a Telegram falla, SHALL hacer rollback completo (la reserva original queda en su estado, sin liberar)

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

#### Scenario: Job de limpieza ejecuta correctamente
- **WHEN** el job `liberar_reservas_vencidas` ejecuta
- **THEN** el sistema SHALL llamar a `turno_service.liberar_reservas_vencidas()`
- **AND** el sistema SHALL capturar y loguear cualquier excepción sin detener el scheduler

### Requirement: La reserva registra el destinatario de origen
El sistema SHALL aceptar de forma opcional un `telegram_chat_id` al reservar un turno. Cuando se provea, el sistema SHALL registrar un `turno_destinatario` con `canal="TELEGRAM"` y `destinatario=telegram_chat_id` para el turno recién creado, dentro de la misma transacción de la reserva (Patrón A: sin commit propio). Cuando no se provea, el sistema SHALL crear el turno sin destinatario y SHALL diferir el registro del destinatario a la confirmación.

#### Scenario: Reserva desde Telegram fija el destinatario
- **WHEN** el paciente reserva un slot desde el chat de Telegram `"555001"`
- **THEN** el sistema SHALL crear el `Turno` en estado `RESERVADO_TEMPORAL`
- **AND** el sistema SHALL registrar un destinatario `TELEGRAM` con valor `"555001"` para ese turno

#### Scenario: Reserva sin chat_id no crea destinatario
- **WHEN** se reserva un turno sin proporcionar `telegram_chat_id`
- **THEN** el sistema SHALL crear el `Turno` sin destinatarios
- **AND** el registro del destinatario SHALL quedar pendiente para la confirmación

### Requirement: La confirmación registra o actualiza los destinatarios del turno
El sistema SHALL aceptar en la confirmación un `telegram_chat_id` opcional y un `email` opcional, además de los datos del beneficiario (nombre, apellido, DNI, teléfono). El sistema SHALL resolver al beneficiario por DNI reutilizando `crear_o_obtener_paciente`, y SHALL registrar o actualizar (upsert por `UNIQUE(turno_id, canal)`) los `turno_destinatario` correspondientes: un destinatario `TELEGRAM` si se provee `telegram_chat_id`, y un destinatario `EMAIL` si se provee `email`. La operación SHALL ejecutarse dentro de la transacción de la confirmación (Patrón A).

#### Scenario: Confirmación con Telegram fija el destinatario Telegram
- **WHEN** se confirma un turno proporcionando `telegram_chat_id="555002"` y datos del beneficiario
- **THEN** el sistema SHALL identificar/crear al beneficiario por DNI
- **AND** el turno confirmado SHALL tener un destinatario `TELEGRAM` con valor `"555002"`

#### Scenario: Confirmación con email modela el canal EMAIL
- **WHEN** se confirma un turno proporcionando `email="abuela@example.com"`
- **THEN** el turno confirmado SHALL tener un destinatario `EMAIL` con valor `"abuela@example.com"`
- **AND** el sistema SHALL persistir el destinatario aunque el envío por email no esté implementado

#### Scenario: Confirmación con ambos canales
- **WHEN** se confirma un turno proporcionando `telegram_chat_id` y `email`
- **THEN** el turno SHALL tener dos destinatarios, uno `TELEGRAM` y uno `EMAIL`

#### Scenario: Confirmación no sobrescribe el destinatario de otro turno del mismo paciente
- **WHEN** el paciente con DNI `X` ya tiene el turno 1 con destinatario `TELEGRAM="A"`
- **AND** se confirma un turno 2 del mismo DNI `X` con `telegram_chat_id="B"`
- **THEN** el turno 2 SHALL tener destinatario `TELEGRAM="B"`
- **AND** el turno 1 SHALL conservar su destinatario `TELEGRAM="A"` sin cambios

