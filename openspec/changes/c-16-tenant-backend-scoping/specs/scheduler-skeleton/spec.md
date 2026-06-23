## MODIFIED Requirements

### Requirement: APScheduler initializes with FastAPI lifespan
The system SHALL initialize an `AsyncIOScheduler` instance during FastAPI application startup (lifespan context) and shut it down gracefully on application shutdown. El scheduler SHALL registrar jobs periódicos que operen sobre todos los profesionales activos iterando por `profesional_id`.

#### Scenario: Scheduler starts with application
- **WHEN** the FastAPI application starts
- **THEN** an `AsyncIOScheduler` instance SHALL be created and started without errors
- **AND** the scheduler SHALL ser accesible vía application state

#### Scenario: Scheduler shuts down gracefully
- **WHEN** the FastAPI application receives a shutdown signal
- **THEN** the scheduler SHALL be shut down gracefully without raising unhandled exceptions

### Requirement: Job de liberar reservas vencidas scopado por profesional
El sistema SHALL ejecutar un job periódico `liberar_reservas_vencidas` que identifique las `ReservaTemporal` vencidas y libere los turnos asociados. El job SHALL iterar por todos los profesionales activos y filtrar las reservas por `profesional_id`.

#### Scenario: Job libera reservas de múltiples profesionales
- **WHEN** el job `liberar_reservas_vencidas` ejecuta
- **THEN** el sistema SHALL obtener la lista de profesionales activos
- **AND** para cada profesional SHALL llamar a `turno_service.liberar_reservas_vencidas(db, profesional_id)`
- **AND** SHALL capturar y loguear cualquier excepción por profesional sin detener el scheduler

### Requirement: Scheduler registra job para marcar turnos como completados
El sistema SHALL registrar un job periódico `marcar_turnos_completados` en el `AsyncIOScheduler`. El job SHALL ejecutar `turno_service.marcar_turnos_completados()` filtrado por `profesional_id` para cada profesional activo.

#### Scenario: Job marca turnos completados por profesional
- **WHEN** el job `marcar_turnos_completados` ejecuta
- **THEN** el sistema SHALL obtener la lista de profesionales activos
- **AND** para cada profesional SHALL llamar a `turno_service.marcar_turnos_completados(db, profesional_id)`
- **AND** SHALL capturar y loguear cualquier excepción sin detener el scheduler

### Requirement: Scheduler registra job de recordatorios scopado por profesional
El sistema SHALL registrar un job periódico `enviar_recordatorios` que envíe recordatorios de turnos confirmados próximos. El job SHALL iterar por profesionales activos y filtrar turnos por `profesional_id`.

#### Scenario: Job envía recordatorios por profesional
- **WHEN** el job `enviar_recordatorios` ejecuta
- **THEN** el sistema SHALL obtener la lista de profesionales activos
- **AND** para cada profesional SHALL obtener los turnos para recordar filtrados por `profesional_id`
- **AND** SHALL enviar los recordatorios usando el `telegram_bot_token` del profesional

### Requirement: Scheduler registra job de timeouts de lista de espera
El sistema SHALL registrar un job periódico `procesar_timeouts_lista_espera` que procese los timeouts de lista de espera. El job SHALL operar sobre todos los profesionales activos filtrando por `profesional_id`.

#### Scenario: Job procesa timeouts por profesional
- **WHEN** el job `procesar_timeouts_lista_espera` ejecuta
- **THEN** el sistema SHALL obtener la lista de profesionales activos
- **AND** para cada profesional SHALL procesar los timeouts de lista de espera filtrados por `profesional_id`
