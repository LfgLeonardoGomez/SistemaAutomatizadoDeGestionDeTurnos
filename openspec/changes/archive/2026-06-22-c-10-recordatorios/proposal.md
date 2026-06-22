## Why

El sistema necesita reducir la tasa de inasistencias recordando a los pacientes sus turnos confirmados con antelación. Actualmente no existe mecanismo automático de recordatorio; el profesional debe contactar manualmente a cada paciente. Automatizar esto mejora la experiencia del usuario y la ocupación de la agenda.

## What Changes

- **Nuevo campo `recordatorio_enviado`** en modelo `Turno` (boolean, default `False`) + migración Alembic.
- **Nuevo job de scheduler** `enviar_recordatorios` que corre periódicamente (configurable vía `RECORDATORIO_JOB_INTERVAL_MINUTOS`) y consulta turnos `CONFIRMADO` cuya fecha/hora esté dentro de la ventana de recordatorio (configurable vía `RECORDATORIO_HORAS_ANTES`).
- **Nuevo servicio `notificacion_service.py`**: encapsula el envío de recordatorios vía Telegram, incluyendo mensaje con fecha, hora y botones inline (Confirmar asistencia, Cancelar, Reprogramar).
- **Integración con Telegram**: mensaje MarkdownV2 con `InlineKeyboardMarkup`; callback data enruta a los handlers existentes de cancelación/reprogramación o a un nuevo endpoint de confirmación de asistencia.
- **Actualización de `scheduler/jobs.py`**: registra el nuevo job con `AsyncIOScheduler`.
- **Tests unitarios e integración**: cobertura del job, query de ventana 24h, envío mock Telegram, manejo de reintentos.

## Capabilities

### New Capabilities
- `recordatorio-automatico`: Envío automático de recordatorios 24h antes de un turno confirmado vía Telegram, con opciones de confirmación, cancelación y reprogramación inline.

### Modified Capabilities
- *(ninguna — este change no modifica specs existentes, solo agrega capacidad nueva)*

## Impact

- **Base de datos**: nueva columna `recordatorio_enviado` en tabla `turnos`.
- **Backend / Scheduler**: nuevo job periódico y servicio de notificación.
- **Backend / Telegram**: nueva plantilla de mensaje + callback handlers para acciones desde recordatorio.
- **Configuración**: nuevas variables de entorno `RECORDATORIO_HORAS_ANTES`, `RECORDATORIO_JOB_INTERVAL_MINUTOS`.
- **Dependencias**: requiere `C-13` (`turno-hardening`) ya implementado (estados `CONFIRMADO`/`COMPLETADO`, `google_event_id`).
