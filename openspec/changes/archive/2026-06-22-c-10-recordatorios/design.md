## Context

El backend ya cuenta con:
- **APScheduler** (`AsyncIOScheduler`) inicializado en `scheduler/jobs.py` con dos jobs: `liberar_reservas_vencidas` (cada 1 min) y `marcar_turnos_completados` (cada 5 min).
- **Servicio Telegram** (`telegram_service.py`) con helpers para enviar mensajes (`enviar_mensaje`), teclados inline (`InlineKeyboardMarkup`) y parsing de callbacks (`_parse_callback_data`).
- **Modelo `Turno`** con estados `CONFIRMADO`, `CANCELADO`, `COMPLETADO`, etc., y columna `google_event_id` persistida desde `C-13`.
- **Configuración centralizada** en `app/config.py` con `Pydantic Settings` (ej. `reserva_temporal_minutos`, `completado_job_interval_minutos`).

Falta el mecanismo de recordatorio automático que cumpla **RN-RE-01** y **RN-RE-02**.

## Goals / Non-Goals

**Goals:**
1. Detectar turnos `CONFIRMADO` cuya fecha/hora de inicio esté dentro de la ventana configurada (`RECORDATORIO_HORAS_ANTES`) y aún no hayan recibido recordatorio.
2. Enviar un mensaje de Telegram al paciente con fecha, hora y botones inline para **Confirmar asistencia**, **Cancelar** o **Reprogramar**.
3. Marcar el turno como `recordatorio_enviado = True` para evitar duplicados.
4. Permitir que el paciente interactúe directamente desde el mensaje de recordatorio sin necesidad de comandos adicionales.
5. Configurar el job y la ventana de recordatorio exclusivamente por variables de entorno (Pydantic Settings).

**Non-Goals:**
- Recordatorios por canales alternativos (email, WhatsApp, SMS).
- Recordatorios múltiples (solo uno por turno).
- Lógica de lista de espera (pertenece a `C-11`).
- Modificación del flujo de reserva original (`C-06`).
- Panel de administración de recordatorios para el profesional.

## Decisions

1. **Bandera `recordatorio_enviado` en `Turno`**
   - *Razón*: evita crear una tabla adicional y un JOIN innecesario en cada ejecución del scheduler. El campo es un booleano simple, eficiente para filtrar.
   - *Alternativa considerada*: tabla `RecordatorioEnvio` con historial de envíos. Rechazada porque no hay requisito de auditoría de envíos en v1.

2. **Query del scheduler con rango de tiempo**
   - *Razón*: el job debe encontrar turnos donde `fecha/hora_inicio` caiga entre `NOW()` y `NOW() + RECORDATORIO_HORAS_ANTES`. Esto garantiza que no se envíen recordatorios demasiado temprano ni demasiado tarde.
   - *Implementación*: `SELECT ... WHERE estado = 'CONFIRMADO' AND recordatorio_enviado = FALSE AND (fecha, hora_inicio) BETWEEN now AND future`.

3. **Reutilización de `telegram_service.py` y callbacks existentes**
   - *Razón*: minimiza duplicación de código y mantiene consistencia en el formato de mensajes (MarkdownV2, `escape_markdown`, splitting > 4096 chars).
   - *Detalle*: los botones del recordatorio usarán `callback_data` con prefijo `reminder:<accion>:<turno_id>`, que ya tiene un handler placeholder en `telegram_service.py` (líneas 433-449). Se completará ese handler para enrutar a `cancelar_turno`, `reprogramar_turno` o un nuevo endpoint de confirmación de asistencia.

4. **Job con `AsyncIOScheduler` y `run_in_threadpool` para Telegram**
   - *Razón*: `python-telegram-bot` es sincrónico en sus métodos de envío. Siguiendo la regla dura del proyecto, nunca se bloquea el event loop; se delega a `run_in_threadpool`.
   - *Alternativa considerada*: usar `Bot.send_message` directamente en async. Rechazada porque la librería subyacente realiza requests bloqueantes.

5. **Servicio dedicado `notificacion_service.py`**
   - *Razón*: separa la lógica de "qué turnos recordar" (query) de "cómo enviar el mensaje" (formato + botones). Facilita testing unitario y permite reutilizar el servicio si en el futuro se agregan otros canales.

6. **Nuevo endpoint `PUT /turnos/{id}/confirmar-asistencia`**
   - *Razón*: "Confirmar asistencia" desde un recordatorio no es lo mismo que "confirmar turno" (que pasa de `RESERVADO_TEMPORAL` a `CONFIRMADO`). Es una acción idempotente que marca que el paciente recibió el recordatorio y confirma que asistirá, sin cambiar el estado del turno (sigue `CONFIRMADO`).
   - *Alternativa considerada*: no tener endpoint y solo registrar en logs. Rechazada porque `RN-RE-02` exige que el paciente pueda "confirmar asistencia" directamente desde el mensaje.

## Risks / Trade-offs

| Risk | Mitigación |
|------|------------|
| **Paciente sin `chat_id` de Telegram** | La query del scheduler JOIN con `Paciente` y filtra `chat_id IS NOT NULL`. Si es NULL, el turno se marca igual como `recordatorio_enviado = True` para no reintentar indefinidamente, y se loguea un warning. |
| **Falla de Telegram API** | Se captura excepción, se loguea error y **NO** se marca `recordatorio_enviado = True`. El job reintentará en la próxima ejecución. |
| **Duplicados por race condition** | El scheduler usa `SELECT FOR UPDATE` sobre los turnos candidatos dentro de la transacción del job, evitando que otra instancia del job (o deploy concurrente) envíe el mismo recordatorio. |
| **Zona horaria** | Todos los campos `fecha`/`hora_inicio` se almacenan en la zona horaria local del servidor (asumida Argentina). El job usa `datetime.now()` local. Se documenta que `RECORDATORIO_HORAS_ANTES` opera en horas locales. |
| **Mensaje > 4096 caracteres** | El mensaje de recordatorio es corto por diseño (~300 chars). Si en el futuro crece, se reutiliza `split_message` de `telegram_service.py`. |

## Migration Plan

1. Ejecutar migración Alembic para agregar `recordatorio_enviado` a `turnos`.
2. Reiniciar el backend para que `init_scheduler` registre el nuevo job.
3. Verificar logs del scheduler en la próxima ejecución del job (`INFO` de turnos encontrados y enviados).
4. Rollback: eliminar la columna vía migración down + reinicio del backend (el job desaparece al no estar registrado).

## Open Questions

- ¿Se requiere un log de "recordatorio enviado" para auditoría futura? (No para v1; se puede agregar en `C-12` si el profesional lo solicita.)
- ¿Cuál es el intervalo óptimo del job? Por defecto 60 minutos (1 hora) para no saturar logs, configurable.
