## 1. Setup y Configuración

- [ ] 1.1 Agregar `TELEGRAM_WEBHOOK_SECRET` a `backend/app/config.py` (opcional, Pydantic Settings)
- [ ] 1.2 Verificar que `python-telegram-bot` está en `requirements.txt` y tiene versión async-compatible
- [ ] 1.3 Crear `backend/app/schemas/telegram.py` con schemas Pydantic para payloads de Telegram (opcional, para typing)
- [ ] 1.4 Crear `backend/app/services/telegram_service.py` (esqueleto con imports y docstrings)
- [ ] 1.5 Crear `backend/app/routers/webhooks.py` (esqueleto con router FastAPI)

## 2. Webhook Reception

- [ ] 2.1 Implementar `POST /webhooks/telegram` en `webhooks.py` con validación de `X-Telegram-Bot-Api-Secret-Token`
- [ ] 2.2 Parsear payload como `Update` de `python-telegram-bot` (o dict) y devolver HTTP 200 inmediatamente
- [ ] 2.3 Devolver HTTP 403 para secret token inválido, HTTP 400 para payload malformado
- [ ] 2.4 Incluir router en `backend/app/main.py`
- [ ] 2.5 Test: `test_telegram_webhook.py` — validación de secret token válido, inválido, payload malformado, respuesta 200 inmediata

## 3. Conversational Router y State Management

- [ ] 3.1 Implementar diccionario de estado en memoria en `telegram_service.py` (`_conversation_states: dict[int, dict]`)
- [ ] 3.2 Implementar locks por `chat_id` (`defaultdict(asyncio.Lock)`) para evitar race conditions
- [ ] 3.3 Implementar tabla de enrutamiento: texto → acción (`/start`, "Quiero un turno", "Cancelar", "Reprogramar")
- [ ] 3.4 Implementar parseo de `callback_data` (`fecha:YYYY-MM-DD`, `hora:HH:MM`, `confirmar_datos`, `cancelar_accion`, `reminder:*`)
- [ ] 3.5 Implementar máquina de estados: `idle` → `esperando_fecha` → `esperando_hora` → `esperando_datos` → `esperando_confirmacion` → `idle`
- [ ] 3.6 Test: `test_telegram_conversation.py` — routing table, state transitions, reset on cancel, unrecognized message

## 4. Telegram Service Integration (Business Actions)

- [ ] 4.1 Implementar `procesar_mensaje(update)` en `telegram_service.py` que parsea y enruta
- [ ] 4.2 Implementar `mostrar_disponibilidad(fecha)` — llama `availability_service.calcular_disponibilidad` y `turno_service.consultar_disponibilidad`, devuelve texto + teclado
- [ ] 4.3 Implementar `accion_reservar_temporal(chat_id, fecha, hora)` — llama `turno_service.reservar_turno`, guarda `turno_temporal_id` en estado
- [ ] 4.4 Implementar `accion_confirmar_turno(chat_id, datos_paciente)` — llama `paciente_service.crear_o_obtener_paciente` + `turno_service.confirmar_turno`, limpia estado
- [ ] 4.5 Implementar `accion_cancelar_turno(chat_id)` — enruta a lógica de C-07 (o placeholder si C-07 no está listo)
- [ ] 4.6 Implementar `accion_reprogramar_turno(chat_id)` — enruta a lógica de C-07 (o placeholder)
- [ ] 4.7 Implementar `notificar_expiracion(chat_id, turno_id)` — formatea mensaje de liberación (placeholder para C-10)
- [ ] 4.8 Test: `test_telegram_service.py` — mocks de `turno_service`, `paciente_service`, flujo completo, manejo de errores

## 5. Message Formatting and Inline Keyboards

- [ ] 5.1 Implementar helper `format_fechas_keyboard(fechas)` en `telegram_service.py` (devuelve `InlineKeyboardMarkup` con `callback_data`)
- [ ] 5.2 Implementar helper `format_horas_keyboard(horas)` en `telegram_service.py`
- [ ] 5.3 Implementar helper `format_confirmacion_keyboard()` con "Confirmar" / "Cancelar"
- [ ] 5.4 Implementar `escape_markdown_v2(text)` helper o usar `telegram.helpers.escape_markdown`
- [ ] 5.5 Implementar `split_message(text)` helper que parte mensajes > 4096 chars
- [ ] 5.6 Test: formateo de Markdown, construcción de teclados, splitting de mensajes largos

## 6. Bot Instance and Message Sending

- [ ] 6.1 Instanciar `Bot` en `telegram_service.py` con `TELEGRAM_BOT_TOKEN` (desde `config.py`)
- [ ] 6.2 Implementar `enviar_mensaje(chat_id, text, reply_markup=None)` usando `run_in_threadpool` o `def` para no bloquear loop
- [ ] 6.3 Implementar `responder_callback_query(callback_query_id)` para quitar el "reloj" de cargando en Telegram
- [ ] 6.4 Test: mock de `Bot.send_message`, verificar que `run_in_threadpool` se usa correctamente

## 7. Integration and End-to-End Tests

- [ ] 7.1 Test E2E: flujo completo "Quiero un turno" → disponibilidad → selección fecha → selección hora → reserva temporal → datos paciente → confirmación
- [ ] 7.2 Test E2E: botones inline — callback query parsing y respuesta correcta
- [ ] 7.3 Test E2E: cancelar en medio del flujo limpia estado y libera reserva temporal
- [ ] 7.4 Test E2E: error path — turno no disponible durante reserva, mensaje amigable
- [ ] 7.5 Test E2E: mensaje no reconocido responde con menú de ayuda

## 8. Documentation and Final Polish

- [ ] 8.1 Actualizar `CHANGES.md` marcando `[x]` en C-08
- [ ] 8.2 Documentar en `knowledge-base/` (o comentario en código) que el estado conversacional es in-memory y roadmap para v2
- [ ] 8.3 Verificar que todos los tests nuevos pasan (`pytest backend/app/tests/test_telegram_*.py`)
- [ ] 8.4 Verificar que los 137 tests existentes siguen pasando (regresión)
- [ ] 8.5 Revisar type hints en todas las funciones públicas de `telegram_service.py` y `webhooks.py`
- [ ] 8.6 Revisar que ningún endpoint quedó sin `response_model` o return type
