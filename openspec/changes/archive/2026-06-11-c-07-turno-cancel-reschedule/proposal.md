## Why

El ciclo de vida de un turno no está completo sin las operaciones de cancelación y reprogramación. Actualmente el sistema permite reservar y confirmar turnos (C-06), pero los pacientes no pueden cancelar un turno confirmado ni moverlo a otro horario. Esto es bloqueante para la integración con Telegram (C-08) y para los recordatorios automáticos (C-10), que requieren que el usuario pueda gestionar su turno. Además, la cancelación es el disparador de la lista de espera (C-11), por lo que sin este change no se puede avanzar en el camino crítico.

## What Changes

- **Nuevo endpoint**: `PUT /turnos/{id}/cancelar` — cambia el estado del turno a `CANCELADO`, elimina el evento asociado de Google Calendar, libera el slot para otros pacientes.
- **Nuevo endpoint**: `PUT /turnos/{id}/reprogramar` — cancela el turno anterior (misma lógica de cancelación) + crea un nuevo turno en estado `CONFIRMADO` en el slot seleccionado + crea el nuevo evento en Google Calendar.
- **Extensión del servicio de turnos**: `cancelar_turno()` y `reprogramar_turno()` en `turno_service.py`, reutilizando `reservar_turno()` y `confirmar_turno()` de C-06 para la parte de reserva/confirmación en reprogramación.
- **Manejo de errores**: 404 para turno inexistente, 409 para turno ya cancelado, 409 para slot no disponible en reprogramación, manejo graceful de fallas en Google Calendar (loggear error, no revertir cambios en DB).
- **Tests**: TDD estricto — cancelación exitosa, reprogramación exitosa, edge cases, race conditions, calendar delete failure.
- **Placeholder para lista de espera**: tras cancelar, se libera el slot; el hook que notifica a la lista de espera se implementará en C-11.

## Capabilities

### New Capabilities
- `turno-cancel`: Cancelación de un turno confirmado con sincronización de Google Calendar y liberación de slot.
- `turno-reschedule`: Reprogramación de un turno confirmado como cancelación + nueva reserva confirmada, con sincronización de Google Calendar.

### Modified Capabilities
- (ninguno — los requisitos de `turno-reservation` no cambian; solo se reutiliza su lógica de reserva/confirmación)

## Impact

- **Backend**: `backend/app/routers/turnos.py`, `backend/app/services/turno_service.py`, `backend/app/schemas/turno.py` (nuevos schemas de request/response).
- **Tests**: `backend/tests/test_turno_service.py`, `backend/tests/test_turnos_router.py`.
- **Dependencias**: Requiere `calendar_service.py` (C-05) y `turno_service.py` / `turnos.py` (C-06).
- **Integraciones**: Google Calendar API (delete/create eventos).
- **Futuro**: Habilita C-11 (lista de espera) y C-10 (recordatorios con cancelar/reprogramar desde Telegram).
