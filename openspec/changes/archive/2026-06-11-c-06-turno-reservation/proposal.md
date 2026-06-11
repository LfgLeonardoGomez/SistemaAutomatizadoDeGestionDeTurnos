## Why

El sistema necesita un ciclo completo de reserva de turnos que permita a los pacientes consultar disponibilidad, bloquear temporalmente un horario y confirmar la reserva. Sin este change, los turnos permanecen como datos estáticos sin flujo de negocio real, bloqueando las funcionalidades centrales del sistema (US-001, US-002) y todas las integraciones posteriores (Google Calendar, Telegram, notificaciones).

## What Changes

- **Nuevo endpoint** `GET /turnos/disponibles` para consultar slots libres por fecha, reutilizando `availability_service` de C-03.
- **Nuevo endpoint** `POST /turnos` para crear una reserva temporal (`RESERVADO_TEMPORAL`) con expiración automática (`ReservaTemporal`).
- **Nuevo endpoint** `PUT /turnos/{id}/confirmar` para validar paciente, pasar a `CONFIRMADO`, eliminar `ReservaTemporal` y crear evento en Google Calendar.
- **Nuevo servicio** `turno_service.py` con lógica de negocio: `reservar_turno()`, `confirmar_turno()`, `liberar_reservas_vencidas()`.
- **Scheduler APScheduler** con job periódico que libera reservas temporales vencidas y devuelve turnos a `DISPONIBLE`.
- **Reglas de negocio aplicadas**: RN-TU-01 (único turno activo por paciente), RN-TU-03 (expiración automática), RN-TU-06 (disponibilidad = posibles - confirmados/temporales), RN-TU-07 (evento en Google Calendar al confirmar).
- **Tests** de reserva, expiración, doble reserva bloqueada, confirmación con calendar mock y condición de carrera.

## Capabilities

### New Capabilities
- `turno-reservation`: Ciclo completo de reserva de turnos — disponibilidad, reserva temporal, confirmación, expiración automática y liberación de slots.

### Modified Capabilities
- `scheduler-skeleton`: Agregar job periódico de limpieza de reservas temporales vencidas (`liberar_reservas_vencidas`).

## Impact

- **Backend FastAPI**: Nuevos endpoints, nuevo servicio, integración con scheduler.
- **Base de datos**: Lecturas con `SELECT FOR UPDATE` para evitar race conditions en reservas concurrentes.
- **Google Calendar**: Reutiliza `CalendarService` (C-05) para crear eventos al confirmar.
- **APScheduler**: Reutiliza `scheduler-skeleton` (C-02) agregando un job periódico.
- **Tests**: pytest obligatorio; TDD estricto.
- **Dependencias**: C-03 (availability), C-04 (paciente), C-05 (calendar).
