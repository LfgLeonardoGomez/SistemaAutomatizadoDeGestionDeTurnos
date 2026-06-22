## Why

El núcleo de turnos quedó con tres deudas técnicas críticas tras C-06, C-07 y C-08 que impiden construir features posteriores (C-10 recordatorios, C-11 lista-espera, C-12 professional-dashboard) sobre una base sólida:

1. **`google_event_id` no persiste**: el modelo `Turno` no tiene columna `google_event_id`. Hoy se usa como atributo dinámico (`getattr`) y se pierde al reiniciar el servidor, rompiendo la sincronización con Google Calendar.
2. **Estado `COMPLETADO` existe pero nadie transiciona**: el ENUM en DB lo incluye, pero no hay scheduler job ni endpoint que marque turnos pasados como completados. Esto rompe el historial del paciente (RN-TU-02) y las métricas del profesional.
3. **Reprogramación en Telegram es un placeholder**: `accion_reprogramar_turno` devuelve "próximamente". El backend REST ya soporta reprogramación (`PUT /turnos/{id}/reprogramar` en C-07), pero el bot no ofrece el flujo conversacional.

Sin resolver estas tres deudas, C-10 no puede identificar eventos de calendar para recordatorios, C-11 no puede reasignar turnos liberados de forma confiable, y C-12 no puede mostrar métricas correctas.

## What Changes

- **Nueva columna `google_event_id`** en modelo `Turno` (SQLAlchemy) + migración Alembic.
- **Actualizar `confirmar_turno()`** para persistir el `event_id` devuelto por `CalendarService.create_event()` en el modelo.
- **Actualizar `cancelar_turno()`** para leer `google_event_id` desde la columna persistente en lugar de `getattr`.
- **Actualizar `reprogramar_turno()`** para propagar el `google_event_id` del turno viejo al eliminar y persistir el nuevo.
- **Nuevo endpoint `PUT /turnos/{id}/completar`** para que el profesional marque manualmente un turno como `COMPLETADO`.
- **Nuevo scheduler job `marcar_turnos_completados`** que ejecuta periódicamente y pasa a `COMPLETADO` los turnos `CONFIRMADO` cuya `fecha + hora_fin < NOW()`.
- **Flujo conversacional de reprogramación en Telegram**: el bot debe permitir seleccionar nueva fecha/hora y llamar a `reprogramar_turno()` del backend, reutilizando la lógica de disponibilidad y confirmación existente.
- **Tests TDD** para cada sub-tarea: migración, persistencia de `google_event_id`, transición a `COMPLETADO`, y flujo de reprogramación en Telegram.

## Capabilities

### New Capabilities
- `turno-google-event-persistence`: Persistencia de `google_event_id` en el modelo `Turno` con migración Alembic, integración en confirmación/cancelación/reprogramación.
- `turno-completado-transition`: Transición automática (scheduler) y manual (endpoint) de turnos `CONFIRMADO` a `COMPLETADO`.
- `telegram-turno-reschedule-flow`: Flujo conversacional completo en Telegram para reprogramar un turno confirmado.

### Modified Capabilities
- `turno-reservation`: Modificar `confirmar_turno()` para persistir `google_event_id` devuelto por Google Calendar.
- `turno-reschedule`: Modificar `reprogramar_turno()` para leer `google_event_id` desde DB y propagar correctamente.
- `turno-cancel`: Modificar `cancelar_turno()` para leer `google_event_id` desde la columna persistente en lugar de `getattr`.
- `scheduler-skeleton`: Agregar job periódico `marcar_turnos_completados`.

## Impact

- **Backend FastAPI**: `backend/app/models/turno.py`, `backend/app/schemas/turno.py`, `backend/app/services/turno_service.py`, `backend/app/routers/turnos.py`, `backend/app/scheduler/jobs.py`.
- **Base de datos**: Nueva migración Alembic para columna `google_event_id`; índice opcional en `(google_event_id)`.
- **Google Calendar**: `CalendarService.create_event()` ya retorna `event_id`; ahora se persiste en vez de descartarse.
- **Telegram bot**: `backend/app/services/telegram_service.py` — nuevo estado conversacional `reprogramando` y acciones `accion_reprogramar_turno`, `accion_seleccionar_nueva_fecha`, `accion_seleccionar_nueva_hora`.
- **Tests**: `backend/tests/test_turno_service.py`, `backend/tests/test_telegram_conversation.py`, `backend/tests/test_scheduler_jobs.py`.
- **Dependencias**: C-06 (turno-reservation), C-07 (turno-cancel-reschedule), C-08 (telegram-bot-webhook).
- **Prerrequisito de**: C-10 (recordatorios), C-11 (lista-espera), C-12 (professional-telegram-dashboard).
