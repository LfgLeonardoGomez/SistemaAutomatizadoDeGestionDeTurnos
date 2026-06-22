## ADDED Requirements

### Requirement: Reprogramación lee google_event_id desde base de datos y persiste el nuevo
El sistema SHALL garantizar que `reprogramar_turno()` lea el `google_event_id` del turno anterior desde la columna persistente de base de datos (para eliminar el evento viejo de Google Calendar) y que el nuevo turno confirmado persista el nuevo `google_event_id` devuelto por `CalendarService.create_event()`.

#### Scenario: Reprogramación lee event_id viejo de DB
- **WHEN** se reprograma un turno que tiene `google_event_id = "event_old"` en base de datos
- **THEN** `cancelar_turno()` SHALL leer `"event_old"` de la columna persistente
- **AND** `CalendarService.delete_event()` SHALL ser invocado con `"event_old"`

#### Scenario: Reprogramación persiste event_id nuevo en DB
- **WHEN** la reprogramación crea un nuevo turno confirmado y `CalendarService.create_event()` retorna `"event_new"`
- **THEN** el nuevo turno SHALL tener `google_event_id = "event_new"` persistido en base de datos

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
