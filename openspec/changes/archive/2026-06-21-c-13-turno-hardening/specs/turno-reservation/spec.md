## ADDED Requirements

### Requirement: Confirmación de turno persiste google_event_id en base de datos
El sistema SHALL modificar `confirmar_turno()` para que, tras crear el evento en Google Calendar, persista el `event_id` retornado en la columna `google_event_id` del modelo `Turno` en base de datos.

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

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
