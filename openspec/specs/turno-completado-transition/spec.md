## Purpose

TBD

## ADDED Requirements

### Requirement: Scheduler transiciona turnos confirmados a completados automáticamente
El sistema SHALL ejecutar un job periódico `marcar_turnos_completados` que identifique los turnos en estado `CONFIRMADO` cuya fecha y hora de fin ya hayan pasado (`fecha + hora_fin < NOW()`), y los actualice a estado `COMPLETADO`. El job SHALL usar `SELECT FOR UPDATE` para evitar race conditions.

#### Scenario: Turno confirmado pasado se marca como completado
- **WHEN** el job `marcar_turnos_completados` ejecuta y encuentra un turno `CONFIRMADO` con `fecha=2026-06-15` y `hora_fin=10:00` cuando la hora actual es `10:05`
- **THEN** el sistema SHALL actualizar el turno a estado `COMPLETADO`
- **AND** el sistema SHALL registrar la cantidad de turnos actualizados en logs

#### Scenario: Turno confirmado futuro no se marca como completado
- **WHEN** el job ejecuta y encuentra un turno `CONFIRMADO` con `fecha=2026-06-15` y `hora_fin=12:00` cuando la hora actual es `10:00`
- **THEN** el sistema SHALL no modificar el estado del turno

#### Scenario: No hay turnos confirmados pasados
- **WHEN** el job ejecuta y no encuentra turnos candidatos
- **THEN** el sistema SHALL no modificar ningún registro
- **AND** el sistema SHALL registrar que no hubo acciones

#### Scenario: Job no falla ante excepción
- **WHEN** el job ejecuta y ocurre una excepción inesperada
- **THEN** el sistema SHALL capturar y loguear la excepción
- **AND** el scheduler SHALL continuar operando normalmente

### Requirement: Endpoint manual para marcar turno como completado
El sistema SHALL exponer un endpoint `PUT /turnos/{id}/completar` que permita marcar un turno `CONFIRMADO` como `COMPLETADO`. El endpoint SHALL validar que el turno exista y esté en estado `CONFIRMADO`.

#### Scenario: Completar turno confirmado exitosamente
- **WHEN** se invoca `PUT /turnos/{id}/completar` para un turno en estado `CONFIRMADO`
- **THEN** el sistema SHALL actualizar el turno a estado `COMPLETADO`
- **AND** el sistema SHALL retornar HTTP 200 con el turno actualizado

#### Scenario: Completar turno no encontrado
- **WHEN** se invoca `PUT /turnos/{id}/completar` para un ID inexistente
- **THEN** el sistema SHALL retornar HTTP 404 Not Found

#### Scenario: Completar turno ya cancelado
- **WHEN** se invoca `PUT /turnos/{id}/completar` para un turno en estado `CANCELADO`
- **THEN** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Completar turno ya completado
- **WHEN** se invoca `PUT /turnos/{id}/completar` para un turno ya en estado `COMPLETADO`
- **THEN** el sistema SHALL retornar HTTP 200 con el turno sin modificar
- **AND** el sistema SHALL registrar un warning de idempotencia

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
