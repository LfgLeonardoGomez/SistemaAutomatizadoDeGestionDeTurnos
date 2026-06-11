# Propuesta: Telegram Bot Webhook y Router Conversacional

## Why

El sistema necesita una interfaz conversacional para que los pacientes puedan reservar, cancelar y reprogramar turnos odontológicos de forma autónoma. La única interfaz de usuario en v1.0 es el bot de Telegram (KB-08). Sin un webhook propio y un router conversacional, el backend no puede recibir ni procesar mensajes de los pacientes, bloqueando completamente las historias de usuario US-001, US-003, US-004 y US-006. Este change cierra el gap de integración entre Telegram Bot API y la lógica de negocio ya implementada en C-01..C-06.

## What Changes

- **Nuevo endpoint** `POST /webhooks/telegram` — recibe updates de Telegram Bot API, valida `TELEGRAM_BOT_TOKEN` y secret token `X-Telegram-Bot-Api-Secret-Token`.
- **Conversational Router** — parsea texto y botones inline (`callback_query`), enruta a acciones de negocio según el estado de la conversación.
- **Acciones básicas implementadas**:
  1. "Quiero un turno" / `/start` → consulta disponibilidad y presenta fechas.
  2. Selección de fecha → consulta horarios disponibles.
  3. Selección de horario → reserva temporal (`POST /turnos` vía `turno_service`).
  4. Solicitud de datos del paciente → pide nombre, apellido, DNI.
  5. Confirmación de datos → confirma turno (`PUT /turnos/{id}/confirmar`).
  6. "Cancelar" / "Reprogramar" → enruta a lógica de C-07 (gestión de ciclo de turnos).
  7. Recordatorios (placeholder para C-10) — manejo de botones inline en mensajes de recordatorio.
- **Message Formatting** — Markdown válido, `InlineKeyboardMarkup` para selección interactiva, splitting de mensajes si superan 4096 caracteres.
- **Service Layer** — `telegram_service.py` con `procesar_mensaje`, `mostrar_disponibilidad`, `confirmar_reserva`, `notificar_expiracion`.
- **Tests** — validación de webhook, routing table, mocks de Telegram, flujo completo E2E, manejo de errores, botones inline.
- **State management v1** — diccionario en memoria para estados de conversación (documentado como mejora futura).

## Capabilities

### New Capabilities
- `telegram-webhook-reception`: Recepción y validación de updates de Telegram Bot API en el endpoint dedicado.
- `telegram-conversation-router`: Parsing de mensajes y callback queries, enrutamiento a acciones de negocio, gestión de estado conversacional.
- `telegram-message-formatting`: Formato de mensajes con Markdown válido, construcción de InlineKeyboardMarkup, splitting de mensajes largos.
- `telegram-service-integration`: Capa de servicio `telegram_service.py` que orquesta llamadas a `turno_service`, `paciente_service` y `availability_service` para completar flujos conversacionales.

### Modified Capabilities
<!-- No se modifican requisitos de specs existentes; el bot es un nuevo consumidor de los endpoints y servicios ya definidos. -->
- *(ninguno)*

## Impact

- **Nuevos archivos**: `backend/app/routers/webhooks.py`, `backend/app/services/telegram_service.py`, `backend/app/schemas/telegram.py`, `backend/app/tests/test_telegram_webhook.py`, `backend/app/tests/test_telegram_service.py`, `backend/app/tests/test_telegram_conversation.py`.
- **Modificados**: `backend/app/main.py` (incluir router de webhooks), `backend/app/config.py` (ya tiene `TELEGRAM_BOT_TOKEN`; posible agregar `TELEGRAM_WEBHOOK_SECRET`).
- **Dependencias**: `python-telegram-bot` ya está en `requirements.txt`.
- **Consumidores de servicios existentes**: `telegram_service.py` reutiliza `turno_service.py`, `paciente_service.py`, `availability_service.py`.
- **Sistema externo**: Telegram Bot API (webhook configurado apuntando a `POST /webhooks/telegram`).
- **No breaking changes** en APIs REST existentes.
