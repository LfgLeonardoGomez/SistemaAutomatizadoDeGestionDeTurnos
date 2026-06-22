## Why

El sistema necesita maximizar la ocupación de la agenda. Cuando un paciente cancela o una reserva temporal expira, el horario queda libre; sin una lista de espera automatizada, ese slot permanece vacío hasta que otro paciente lo reserve manualmente. Implementar una cola FIFO con notificación vía Telegram y tiempo de respuesta limitado reduce inasistencias y fricción operativa.

## What Changes

- **Nuevos endpoints REST** para registro y baja de lista de espera: `POST /lista-espera`, `DELETE /lista-espera/{id}`.
- **Hook post-cancelación** en `cancelar_turno` (y post-expiración en `liberar_reservas_vencidas`): al liberarse un slot, se dispara evaluación de la lista de espera.
- **Servicio de notificación FIFO** con atomicidad en base de datos (`SELECT FOR UPDATE` sobre `ListaDeEspera`) para evitar condiciones de carrera cuando múltiples slots se liberan concurrentemente.
- **Mensaje de Telegram** al primer paciente en cola con botones inline **Aceptar / Rechazar** y formato MarkdownV2.
- **Manejo de timeout** con `APScheduler` (`AsyncIOScheduler`): si el paciente no responde en `LISTA_ESPERA_MINUTOS`, se pasa automáticamente al siguiente en la cola.
- **Campos adicionales en `ListaDeEspera`** para trazabilidad: `turno_ofrecido_id` (FK nullable) y `notificado_en` (timestamp nullable).
- **Tests estrictos TDD**: orden FIFO, timeout, race condition en DB, aceptación/rechazo.

## Capabilities

### New Capabilities
- `lista-espera-registration`: API endpoints y servicio para registrar y eliminar pacientes de la lista de espera por fecha solicitada.
- `lista-espera-fifo-assignment`: Lógica atómica de consulta FIFO, notificación y asignación del turno liberado al primer paciente en cola.
- `lista-espera-telegram-notification`: Envío de mensaje Telegram con botones inline Aceptar/Rechazar, incluyendo escape MarkdownV2 y manejo de errores de envío.
- `lista-espera-timeout`: Job de APScheduler que detecta notificaciones vencidas y reasigna el turno al siguiente paciente en cola.

### Modified Capabilities
- `turno-cancel`: Se agrega requisito de evaluar la lista de espera inmediatamente después de una cancelación exitosa (antes de retornar HTTP 200).
- `core-lista-espera-model`: Se extiende el modelo con `turno_ofrecido_id` (FK a `Turno`, nullable) y `notificado_en` (timestamp nullable) para rastrear qué turno fue ofrecido y cuándo se envió la notificación.

## Impact

- `backend/app/api/lista_espera.py` — nuevos endpoints.
- `backend/app/services/lista_espera_service.py` — lógica de negocio FIFO.
- `backend/app/services/turno_service.py` — hook post-cancelación y post-expiración.
- `backend/app/services/telegram_service.py` — nuevos mensajes y botones para lista de espera.
- `backend/app/scheduler/jobs.py` — nuevo job de timeout.
- `backend/app/models/lista_de_espera.py` — migración para nuevos campos.
- Alembic migration para alterar `lista_de_espera`.
- Tests en `backend/tests/`.