## Why

Los endpoints REST del backend (turnos, pacientes, profesional, webhooks) están completos y funcionales desde C-06 a C-08, pero n8n necesita workflows importables para orquestar los flujos conversacionales de Telegram. Este change entrega los archivos JSON de workflow que conectan los triggers de Telegram con los endpoints de FastAPI y devuelven respuestas al usuario. Es la capa de integración que hace operativo el sistema end-to-end.

## What Changes

- Crear `n8n-workflows/flujo-reserva.json` — workflow para reserva de turnos con pasos de selección de fecha, hora, reserva temporal y confirmación.
- Crear `n8n-workflows/flujo-cancelacion.json` — workflow para cancelación de turnos vía API.
- Crear `n8n-workflows/flujo-recordatorio.json` — template/placeholder para envío de recordatorios (depende de C-10).
- Crear `n8n-workflows/flujo-lista-espera.json` — template/placeholder para gestión de lista de espera (depende de C-11).
- Crear `n8n-workflows/README.md` — guía de importación, variables de entorno requeridas (`N8N_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `FASTAPI_BASE_URL`) y pasos de configuración.
- **No se modifica código del backend** — este change es puramente de integración y documentación.

## Capabilities

### New Capabilities
- `n8n-workflow-reserva`: Workflow n8n para flujo conversacional de reserva de turnos (fechas → horarios → reserva → confirmación).
- `n8n-workflow-cancelacion`: Workflow n8n para cancelación de turnos por ID.
- `n8n-workflow-recordatorio`: Workflow n8n placeholder para envío automático de recordatorios (activará `scheduler-skeleton` en C-10).
- `n8n-workflow-lista-espera`: Workflow n8n placeholder para notificación y gestión de lista de espera (activará `core-lista-espera-model` en C-11).

### Modified Capabilities
<!-- Ninguna capability existente cambia sus requisitos; solo se añaden workflows de integración -->

## Impact

- **Directorio afectado**: `n8n-workflows/` (ya existe desde C-01, vacío).
- **APIs utilizadas**: `GET /turnos/disponibles`, `POST /turnos`, `PUT /turnos/{id}/confirmar`, `PUT /turnos/{id}/cancelar`, `PUT /turnos/{id}/reprogramar`, `POST /webhooks/telegram`, `POST /pacientes`.
- **Dependencias externas**: n8n (workflow engine) y Telegram Bot API (mensajería).
- **Riesgo**: Bajo. No hay cambios de código; los workflows son archivos JSON exportables e importables. El backend sigue siendo testeable de forma aislada.
