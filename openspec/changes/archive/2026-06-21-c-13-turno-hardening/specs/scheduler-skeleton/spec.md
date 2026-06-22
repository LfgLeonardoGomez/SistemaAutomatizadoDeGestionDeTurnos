## ADDED Requirements

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

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
