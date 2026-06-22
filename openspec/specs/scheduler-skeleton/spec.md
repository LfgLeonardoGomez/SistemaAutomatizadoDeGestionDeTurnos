## MODIFIED Requirements

### Requirement: APScheduler initializes with FastAPI lifespan
The system SHALL initialize an `AsyncIOScheduler` instance during FastAPI application startup (lifespan context) and shut it down gracefully on application shutdown. The scheduler SHALL register a periodic job `liberar_reservas_vencidas` that executes cada minuto para limpiar reservas temporales expiradas.

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

#### Scenario: Job de limpieza no falla si no hay reservas vencidas
- **WHEN** el job `liberar_reservas_vencidas` ejecuta y no hay reservas vencidas
- **THEN** el sistema SHALL no lanzar excepciones
- **AND** el sistema SHALL continuar operando normalmente

### Requirement: Scheduler registra job para marcar turnos como completados
El sistema SHALL registrar un job periódico `marcar_turnos_completados` en el `AsyncIOScheduler` durante el startup de FastAPI. El job SHALL ejecutar `turno_service.marcar_turnos_completados()` con un trigger `interval` configurable (default 5 minutos). El job SHALL capturar y loguear excepciones sin detener el scheduler.

#### Scenario: Scheduler registra job de completado al iniciar
- **WHEN** la aplicación FastAPI inicia
- **THEN** el scheduler SHALL tener el job `marcar_turnos_completados` registrado
- **AND** el intervalo SHALL ser de 5 minutos por defecto

#### Scenario: Job de completado ejecuta sin errores
- **WHEN** el job `marcar_turnos_completados` ejecuta
- **THEN** el sistema SHALL llamar a `turno_service.marcar_turnos_completados()`
- **AND** el sistema SHALL capturar y loguear cualquier excepción sin detener el scheduler
