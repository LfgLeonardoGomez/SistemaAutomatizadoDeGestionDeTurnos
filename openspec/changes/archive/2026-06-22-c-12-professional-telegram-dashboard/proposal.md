# Proposal: Professional Telegram Dashboard

## Why

El profesional odontológico necesita operar la agenda sin salir de Telegram. Hoy los pacientes reservan, cancelan y reprograman vía bot (C-08, C-13), pero el profesional no tiene visibilidad de sus turnos ni puede ajustar su configuración desde el mismo canal. Esta brecha fuerza al profesional a consultar la base de datos directamente o a depender de un panel web que no existe en v1.0. Además, la pregunta abierta IN-03 fue resuelta a favor de comandos de Telegram para reducir scope en v1.0.

## What Changes

- **Nuevos comandos de Telegram para el profesional**:
  - `/turnos_hoy` — lista de turnos `CONFIRMADO` del día actual con hora y paciente.
  - `/metricas` — resumen diario: cantidad de turnos, tasa de confirmación, tasa de cancelación/inasistencia.
  - `/configurar` — wizard conversacional paso a paso para modificar horarios de atención, duración del turno y días laborables.
- **Nuevos endpoints REST** (si no existen):
  - `GET /profesional/turnos-hoy` — retorna turnos confirmados del día con datos del paciente.
  - `GET /profesional/metricas` — retorna métricas calculadas sobre el conjunto de turnos.
- **Extensión del servicio `telegram_service.py`**:
  - Estados conversacionales para el wizard `/configurar` (paso a paso: horario inicio → horario fin → días → duración → confirmación).
  - Formateadores de mensajes para listado de turnos y métricas, respetando límite de 4096 caracteres de Telegram.
- **Tests**: TDD estricto (test rojo → verde → refactor) para endpoints, servicios y flujo conversacional.

## Capabilities

### New Capabilities
- `professional-telegram-dashboard`: Comandos de Telegram (`/turnos_hoy`, `/metricas`, `/configurar`) y sus handlers conversacionales para el actor Profesional.
- `professional-metrics-endpoint`: Endpoint REST `GET /profesional/metricas` con cálculo de tasas de confirmación, cancelación e inasistencia.
- `professional-turnos-hoy-endpoint`: Endpoint REST `GET /profesional/turnos-hoy` con join a Paciente y filtrado por estado `CONFIRMADO`.

### Modified Capabilities
- `configuration-management` (existente en `openspec/specs/configuration-management/spec.md`): se extiende el alcance para soportar modificación vía wizard de Telegram (no solo REST). El comportamiento de negocio — qué campos se editan y cómo se validan — no cambia; cambia el canal de interacción. Por tanto **no requiere delta de requerimientos**, solo implementación en `telegram_service.py`.
- `telegram-conversation-router` (existente): se agregan nuevas ramas de routing para comandos de profesional. Como el router ya maneja estados y callbacks, esto es implementación, no cambio de requerimiento de spec.

## Impact

- **Código**: `backend/app/routers/profesional.py` (nuevos endpoints), `backend/app/services/telegram_service.py` (nuevos handlers y estados), `backend/app/services/availability_service.py` (sin cambios; ya calcula slots), `backend/app/models/turno.py` (sin cambios; ya tiene estados necesarios).
- **Base de datos**: Sin migraciones nuevas. Reutiliza modelo `Profesional` (C-03) y `Turno` (C-02/C-13).
- **Dependencias**: Requiere C-03 (configuración del profesional) y C-13 (estado `COMPLETADO`, `google_event_id`, flujo reprogramación en Telegram).
- **Telegram**: Nuevos comandos a registrar en `@BotFather` si se desean menús de comando (`/turnos_hoy`, `/metricas`, `/configurar`).
- **API REST**: Endpoints públicos en v1.0 (sin auth formal, como el resto del sistema).
