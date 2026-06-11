## ADDED Requirements

### Requirement: Sistema permite reprogramar un turno confirmado
El sistema SHALL permitir reprogramar un turno en estado `CONFIRMADO`. La reprogramación SHALL gestionarse como cancelación del turno anterior seguida de una nueva reserva confirmada. El sistema SHALL validar que el nuevo slot esté disponible y que el paciente no tenga otro turno activo (RN-TU-01). El sistema SHALL eliminar el evento anterior de Google Calendar y SHALL crear un nuevo evento para el turno reprogramado.

#### Scenario: Reprogramación exitosa
- **WHEN** el usuario solicita reprogramar un turno confirmado a un nuevo slot disponible
- **THEN** el sistema SHALL cancelar el turno anterior (estado `CANCELADO`)
- **AND** el sistema SHALL eliminar el evento anterior de Google Calendar
- **AND** el sistema SHALL crear un nuevo turno en estado `CONFIRMADO`
- **AND** el sistema SHALL crear un nuevo evento en Google Calendar
- **AND** el sistema SHALL retornar el nuevo turno con HTTP 200

#### Scenario: Reprogramación de turno no encontrado
- **WHEN** el usuario solicita reprogramar un turno con un ID que no existe
- **THEN** el sistema SHALL retornar HTTP 404 Not Found

#### Scenario: Reprogramación de turno ya cancelado
- **WHEN** el usuario solicita reprogramar un turno que ya está en estado `CANCELADO`
- **THEN** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Reprogramación con slot no disponible
- **WHEN** el usuario solicita reprogramar a un slot que ya está ocupado
- **THEN** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict
- **AND** el sistema SHALL dejar el turno original en estado `CANCELADO` (el slot anterior queda liberado)

#### Scenario: Reprogramación con paciente que tiene otro turno activo
- **WHEN** el usuario solicita reprogramar pero el paciente adquiere otro turno activo en paralelo
- **THEN** el sistema SHALL detectar la violación de RN-TU-01 atómicamente
- **AND** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Reprogramación con fallo de creación de evento en Google Calendar
- **WHEN** el sistema crea el nuevo turno confirmado pero falla la creación del evento en Google Calendar
- **THEN** el sistema SHALL mantener el nuevo turno en estado `CONFIRMADO`
- **AND** el sistema SHALL registrar el error en logs
- **AND** el sistema SHALL retornar HTTP 200

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
