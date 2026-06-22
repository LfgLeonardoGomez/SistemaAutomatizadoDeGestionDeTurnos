## Purpose

TBD

## ADDED Requirements

### Requirement: Modelo Turno almacena google_event_id persistente
El sistema SHALL agregar una columna `google_event_id` al modelo `Turno` de tipo `VARCHAR(255)`, nullable. La columna SHALL almacenar el identificador del evento en Google Calendar asociado al turno. El sistema SHALL crear una migración Alembic que agregue la columna sin bloquear la tabla.

#### Scenario: Migración agrega columna google_event_id
- **WHEN** se ejecuta la migración Alembic
- **THEN** la tabla `turno` SHALL tener la columna `google_event_id`
- **AND** la columna SHALL ser nullable
- **AND** los registros existentes SHALL tener valor `NULL`

#### Scenario: Turno confirmado persiste google_event_id
- **WHEN** se confirma un turno y `CalendarService.create_event()` retorna `"event_123"`
- **THEN** el turno en base de datos SHALL tener `google_event_id = "event_123"`

#### Scenario: Turno cancelado lee google_event_id desde DB
- **WHEN** se cancela un turno que tiene `google_event_id = "event_456"` en base de datos
- **THEN** `CalendarService.delete_event()` SHALL ser invocado con `"event_456"`

#### Scenario: Reprogramación elimina evento viejo y persiste evento nuevo
- **WHEN** se reprograma un turno con `google_event_id = "event_old"`
- **THEN** `CalendarService.delete_event()` SHALL ser invocado con `"event_old"`
- **AND** el nuevo turno confirmado SHALL persistir el nuevo `google_event_id` devuelto por `create_event()`

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
