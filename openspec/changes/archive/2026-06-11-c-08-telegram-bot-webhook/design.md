# Diseño: Telegram Bot Webhook y Router Conversacional

## Context

El backend FastAPI ya cuenta con los servicios de negocio (C-01..C-06): `turno_service`, `paciente_service`, `availability_service`, modelos SQLAlchemy, schemas Pydantic y endpoints REST expuestos. La interfaz de usuario v1.0 es exclusivamente el bot de Telegram (KB-08). Hasta ahora no existe un punto de entrada para recibir mensajes de Telegram. Este change implementa el webhook y la capa conversacional que cierra el circuito entre el paciente y la lógica de negocio.

**Stack relevante**: FastAPI + Pydantic, `python-telegram-bot` v20+ (asyncio-compatible), PostgreSQL, APScheduler. El bot opera en modo webhook: Telegram envía updates HTTP al backend, nunca en modo polling.

**Restricciones del proyecto** (AGENTS.md):
- Nunca usar `async def` para código bloqueante (librerías sync como Google Calendar SDK). Telegram SDK v20+ es nativamente async, pero sus HTTP calls a la API de Telegram internamente usan `httpx` async. Sin embargo, en este change la recepción del webhook es entrada HTTP; la respuesta al usuario (envío de mensajes) sí puede usar `python-telegram-bot` con su `Application` async, pero para evitar bloquear el event loop con llamadas HTTP a Telegram, se usará `run_in_threadpool` o `def` para el envío de mensajes si la librería expone sync helpers, o se usará `async` nativo de `python-telegram-bot` si se configura un `Application` standalone sin polling. Dado que el webhook ya lo recibe FastAPI, no necesitamos `Application.run_polling()`; usamos `Bot` directamente con `run_in_threadpool` para evitar dependencias de loop internas.

## Goals / Non-Goals

**Goals:**
- Proveer un endpoint `POST /webhooks/telegram` que valide autenticidad de los updates y los procese.
- Implementar un router conversacional que enrute mensajes de texto y callback queries a acciones de negocio.
- Mantener estado de conversación en memoria para v1 (suficiente para un único profesional y carga moderada).
- Formatear mensajes con Markdown válido y botones inline (`InlineKeyboardMarkup`).
- Reutilizar servicios existentes (`turno_service`, `paciente_service`, `availability_service`) sin duplicar lógica de negocio.
- Implementar tests que cubran: validación de webhook, routing, flujo E2E, errores, botones inline.

**Non-Goals:**
- Persistencia de estado conversacional en base de datos (v1 usa dict en memoria; se documenta como roadmap v2).
- Implementación de recordatorios automáticos (US-006) — este change solo prepara el handler de botones inline; el scheduler dispara en C-10.
- Panel de profesional vía Telegram — fuera de scope de este change; se aborda en C-09 o C-11.
- Soporte para múltiples idiomas.
- Webhook de n8n como proxy; el endpoint recibe directamente de Telegram o de n8n indistintamente.

## Decisions

### 1. Usar `python-telegram-bot` `Bot` + `run_in_threadpool` para envío de mensajes
- **Rationale**: `python-telegram-bot` v20+ es async, pero su `Application` está diseñado para polling/webhook propio. Como FastAPI ya recibe el webhook, no necesitamos `Application`. Se instanciará `Bot` con el token y se usará `run_in_threadpool` para enviar mensajes si la API subyacente no está integrada con el loop de FastAPI. Esto respeta la regla dura: "NUNCA usar async def para código bloqueante".
- **Alternativa considerada**: Usar `httpx` directamente para llamar a Telegram Bot API. Rechazada: perderíamos helpers de `python-telegram-bot` para `InlineKeyboardMarkup`, `ParseMode`, escaping de Markdown, etc.
- **Alternativa considerada**: Usar `Application` con `webhook_url` propio. Rechazada: generaría conflicto con FastAPI como receptor; `Application` intentaría levantar su propio servidor HTTP.

### 2. Estado conversacional en memoria (`dict` por `chat_id`)
- **Rationale**: v1.0 es un único profesional, carga moderada, un solo proceso FastAPI. Un `dict` global protegido por `asyncio.Lock` es suficiente y evita complejidad de schema/migraciones.
- **Estructura del estado**:
  ```python
  {
      chat_id: {
          "estado": "esperando_fecha" | "esperando_hora" | "esperando_datos" | "esperando_confirmacion" | "idle",
          "turno_temporal_id": int | None,
          "datos_paciente": {"nombre": str, "apellido": str, "dni": str} | None,
          "fecha_seleccionada": str | None,
      }
  }
  ```
- **Alternativa considerada**: Tabla `conversacion_estado` en PostgreSQL. Rechazada: over-engineering para v1; el AGENTS.md dice "evitar over-engineering; Clean/Hexagonal es preferido pero pragmático para v1".

### 3. Router como tabla de enrutamiento (texto + callback_data) + state machine
- **Rationale**: Desacopla el parsing de la acción. Facilita testing unitario del router sin depender de la lógica de servicios.
- **Tabla de enrutamiento**:
  - Texto: `"Quiero un turno"`, `/start` → `accion_mostrar_fechas`
  - Texto: `"Cancelar"` → `accion_cancelar_turno`
  - Texto: `"Reprogramar"` → `accion_reprogramar_turno`
  - Callback: `fecha:YYYY-MM-DD` → `accion_mostrar_horas`
  - Callback: `hora:HH:MM` → `accion_reservar_temporal`
  - Callback: `confirmar_datos` → `accion_confirmar_turno`
  - Callback: `cancelar_accion` → `accion_reset_estado`
- **Fallback**: cualquier texto no reconocido en estado `idle` responde con menú de ayuda.

### 4. `callback_data` como strings estructurados (`tipo:valor`) con delimiter simple
- **Rationale**: JSON en `callback_data` tiene límite de 64 bytes en Telegram; strings estructurados son más compactos y parseables. El patrón `fecha:2026-06-15` o `hora:09:00` es legible y seguro.
- **Alternativa considerada**: JSON encoded. Rechazada: riesgo de superar 64 bytes con datos adicionales.

### 5. `telegram_service.py` como orquestador; no HTTP interno
- **Rationale**: `telegram_service.py` llama directamente a métodos de `turno_service.py`, `paciente_service.py`, etc. No usa `TestClient` ni HTTP hacia sí mismo. Esto evita overhead de serialización HTTP y es más fácil de testear con mocks.
- **Alternativa considerada**: Usar `TestClient` para llamar endpoints REST internamente. Rechazada: AGENTS.md dice "NUNCA mezclar operaciones HTTP en la misma función"; aquí aplica a nivel arquitectónico: las capas de servicio se invocan directamente.

### 6. Markdown V2 como modo de parseo por defecto
- **Rationale**: Markdown V2 de Telegram es más estricto pero más potente (links, bold, italic). Se valida con `telegram.helpers.escape_markdown` para evitar mensajes rechazados por la API.
- **Alternativa considerada**: HTML. Rechazada: Markdown es más legible en el código y requiere menos escaping.

### 7. Validación de webhook con `X-Telegram-Bot-Api-Secret-Token`
- **Rationale**: Telegram soporta enviar un secret token en el header `X-Telegram-Bot-Api-Secret-Token` al configurar el webhook. Se valida contra un env var `TELEGRAM_WEBHOOK_SECRET` (opcional pero recomendado). Si no está configurado, se valida que el payload sea parseable como `Update` de `python-telegram-bot` como mínimo.
- **Alternativa considerada**: Validar HMAC con el token del bot. Rechazada: Telegram no firma los payloads con HMAC; el secret token es el mecanismo oficial.

## Risks / Trade-offs

- **[Riesgo] Pérdida de estado en reinicio del servidor** → *Mitigación*: aceptado para v1. Documentado en design.md como mejora futura. Los pacientes pueden reiniciar el flujo con `/start`.
- **[Riesgo] Race condition en reserva temporal** → *Mitigación*: `turno_service.reservar_turno` ya usa transacciones de base de datos (`SELECT FOR UPDATE` o equivalente en SQLAlchemy). El router no duplica esa lógica; delega al servicio.
- **[Riesgo] Mensaje de Telegram no entregado tras acción de negocio exitosa** → *Mitigación*: la lógica de negocio se ejecuta antes del envío del mensaje de confirmación. Si el envío falla, el turno ya quedó reservado/confirmado en DB. Se loguea el error; se puede implementar reintento en C-10.
- **[Riesgo] `python-telegram-bot` internamente maneja su propio loop de eventos** → *Mitigación*: no se usa `Application.start()`. Se usa `Bot` como cliente HTTP pasivo con `run_in_threadpool`, o se configura `Application` sin `start()` usando `bot = Bot(token)` directamente.
- **[Riesgo] Límite de 64 bytes en `callback_data`** → *Mitigación*: `callback_data` usa strings estructurados compactos. Fecha (`10`) + hora (`5`) + delimiter (`1`) = ~16 bytes. Margen amplio.
- **[Riesgo] `asyncio.Lock` en dict de estado puede serializar requests de chats diferentes** → *Mitigación*: usar `lock` por `chat_id` (dict de locks) o usar `asyncio.Lock` global si la carga es baja. Se opta por `defaultdict(asyncio.Lock)` por chat_id para paralelismo.

## Migration Plan

1. **Configuración**: agregar `TELEGRAM_WEBHOOK_SECRET` a `.env` y `config.py` (opcional pero recomendado).
2. **Despliegue**: levantar el backend con el nuevo router incluido.
3. **Configurar webhook de Telegram**: `POST https://api.telegram.org/bot<TOKEN>/setWebhook` con `url=<BASE_URL>/webhooks/telegram` y `secret_token=<TELEGRAM_WEBHOOK_SECRET>`.
4. **Verificación**: enviar `/start` al bot; debe responder con fechas disponibles.
5. **Rollback**: eliminar webhook de Telegram (`deleteWebhook`) y revertir código a versión anterior. No hay migraciones de DB.

## Open Questions

1. **¿Debe el bot soportar múltiples profesionales en v1?** → Respuesta: no. v1 asume un único profesional. El routing de profesional se puede agregar en C-11 o v2.
2. **¿El secret token de webhook es obligatorio o opcional?** → Respuesta: opcional para development, obligatorio para production. `config.py` debe manejarlo como `Optional[str]`.
3. **¿Dónde se configura la URL del webhook de Telegram?** → Respuesta: fuera del código (script de setup, Terraform, o n8n). No se hardcodea.
