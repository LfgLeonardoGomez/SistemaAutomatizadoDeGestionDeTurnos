## MODIFIED Requirements

### Requirement: Endpoint manual para marcar turno como completado
El sistema SHALL exponer un endpoint `PUT /turnos/{id}/completar` que permita marcar un turno `CONFIRMADO` como `COMPLETADO`. El endpoint SHALL validar que el turno exista y esté en estado `CONFIRMADO`. **La lógica de validación y actualización SHALL residir en `turno_service.completar_turno()` y SHALL seguir el contrato de Patrón A (servicio sin commit, router con commit/rollback).** El router SHALL ser un wrapper delgado que llama al servicio, maneja `HTTPException` y ejecuta `await db.commit()`/`await db.rollback()`.

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

#### Scenario: Lógica de completar reside en servicio
- **WHEN** se invoca el endpoint `PUT /turnos/{id}/completar`
- **THEN** la lógica de SELECT FOR UPDATE, validación de estado, y mutación SHALL ejecutarse en `turno_service.completar_turno()`
- **AND** el router SHALL contener solo la llamada al servicio, manejo de excepciones y commit/rollback
- **AND** el servicio `completar_turno` SHALL NO ejecutar `await db.commit()`

## ADDED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
