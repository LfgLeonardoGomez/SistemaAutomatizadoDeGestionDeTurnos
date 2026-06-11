## ADDED Requirements

### Requirement: Sistema permite cancelar un turno confirmado
El sistema SHALL permitir cancelar un turno en estado `CONFIRMADO`. Al cancelar, el sistema SHALL actualizar el turno a estado `CANCELADO`, SHALL eliminar el evento correspondiente de Google Calendar (best-effort), y SHALL liberar el slot para otros pacientes.

#### Scenario: Cancelación exitosa de turno confirmado
- **WHEN** el usuario solicita cancelar un turno en estado `CONFIRMADO`
- **THEN** el sistema SHALL actualizar el turno a estado `CANCELADO`
- **AND** el sistema SHALL eliminar el evento de Google Calendar
- **AND** el sistema SHALL retornar el turno actualizado con HTTP 200

#### Scenario: Cancelación de turno no encontrado
- **WHEN** el usuario solicita cancelar un turno con un ID que no existe
- **THEN** el sistema SHALL retornar HTTP 404 Not Found

#### Scenario: Cancelación de turno ya cancelado
- **WHEN** el usuario solicita cancelar un turno que ya está en estado `CANCELADO`
- **THEN** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Cancelación con fallo de Google Calendar
- **WHEN** el usuario cancela un turno confirmado y la eliminación del evento en Google Calendar falla
- **THEN** el sistema SHALL mantener el turno en estado `CANCELADO`
- **AND** el sistema SHALL registrar el error en logs
- **AND** el sistema SHALL retornar HTTP 200

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
