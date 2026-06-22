## ADDED Requirements

### Requirement: Cancelación lee google_event_id desde columna persistente
El sistema SHALL modificar `cancelar_turno()` para leer `google_event_id` directamente desde la columna persistente del modelo `Turno` en lugar de usar `getattr` con valor por defecto. Si `google_event_id` es `NULL`, el sistema SHALL omitir la llamada a `CalendarService.delete_event()`.

#### Scenario: Cancelación lee event_id desde columna persistente
- **WHEN** se cancela un turno con `google_event_id = "event_123"` en base de datos
- **THEN** el sistema SHALL leer `turno.google_event_id` y obtener `"event_123"`
- **AND** el sistema SHALL invocar `CalendarService.delete_event("event_123")`

#### Scenario: Cancelación de turno sin google_event_id
- **WHEN** se cancela un turno con `google_event_id = NULL`
- **THEN** el sistema SHALL no invocar `CalendarService.delete_event()`
- **AND** el turno SHALL ser actualizado a `CANCELADO` normalmente

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
