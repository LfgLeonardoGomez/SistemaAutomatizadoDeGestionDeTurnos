## Context

El proyecto ya cuenta con modelos `Turno`, `Paciente`, `ListaDeEspera` (C-02), reserva temporal con expiración (C-06), cancelación/reprogramación (C-07), y persistencia de `google_event_id` con transición a `COMPLETADO` (C-13). Sin embargo, cuando un turno se cancela o una reserva temporal expira, el slot liberado no se ofrece automáticamente a pacientes en espera. Este change cierra esa brecha.

## Goals / Non-Goals

**Goals:**
- Registrar y dar de baja pacientes en lista de espera vía endpoints REST.
- Evaluar automáticamente la lista de espera cuando se libera un slot (cancelación o expiración).
- Notificar al primer paciente en cola FIFO vía Telegram con botones Aceptar / Rechazar.
- Confirmar o rechazar la oferta de turno atómicamente, con manejo de timeout.
- Prevenir condiciones de carrera en la asignación FIFO usando transacciones de base de datos.

**Non-Goals:**
- Notificación push fuera de Telegram (no hay SMS/email en el stack actual).
- Panel web para administrar la lista de espera (el profesional opera vía Telegram o n8n).
- Reordenamiento manual de la cola FIFO.
- Notificación masiva a todos los pacientes en lista de espera (solo se notifica de a uno).

## Decisions

### 1. FIFO atómico con `SELECT FOR UPDATE` sobre `ListaDeEspera`
**Rationale:** Múltiples slots pueden liberarse concurrentemente (dos cancelaciones simultáneas, o una cancelación y una expiración). Si dos hilos leen el mismo primer paciente, generarían doble notificación o conflicto de asignación. Bloquear las filas relevantes de `ListaDeEspera` para una fecha dada con `with_for_update()` serializa el acceso y garantiza que solo un hilo notifique al siguiente paciente.

**Alternatives considered:**
- Advisory locks de PostgreSQL (`pg_advisory_lock`) → más complejo, requiere gestión de lock IDs.
- Columna `procesando` booleana → introduce race condition en el update inicial.

### 2. Timeout de lista de espera vía `AsyncIOScheduler` + job dedicado
**Rationale:** Reutilizamos `APScheduler` ya integrado en el proyecto (C-01). Un job periódico (intervalo configurable, default 1 minuto) escanea registros donde `notificado=TRUE` y `notificado_en < NOW() - LISTA_ESPERA_MINUTOS`. Si venció, marca `notificado=FALSE`, limpia `turno_ofrecido_id` y `notificado_en`, y re-evalúa la cola para ofrecer el mismo slot al siguiente paciente.

**Alternatives considered:**
- `asyncio.sleep` por paciente → no persiste ante reinicio del proceso, y acumula tareas en memoria.
- Celery/RabbitMQ → fuera del stack acordado.

### 3. Hook post-cancelación sincrónico dentro de la transacción del turno
**Rationale:** `cancelar_turno` ya hace `COMMIT` antes de eliminar el evento de Google Calendar (best-effort). El hook de lista de espera se ejecuta **después** del `COMMIT` de cancelación pero antes de retornar al caller, para evitar que un fallo en Telegram revierta la cancelación (la DB es fuente de verdad). La llamada a `evaluar_lista_espera()` se hace en la misma función `cancelar_turno` después del commit.

**Alternatives considered:**
- Eventos/mensajes asíncronos → requiere infraestructura adicional; overkill para v1.
- Trigger de base de datos → lógica de negocio en DB, difícil de testear y mantener.

### 4. Extender `ListaDeEspera` con `turno_ofrecido_id` y `notificado_en`
**Rationale:** Necesitamos saber (a) qué turno liberado se le ofreció al paciente para poder confirmarlo sin recalcular disponibilidad, y (b) cuándo se envió la notificación para calcular el timeout. Usar columnas en la tabla existente mantiene la atomicidad de las operaciones sin tablas auxiliares.

**Alternatives considered:**
- Tabla `NotificacionListaEspera` separada → más joins, más complejidad, no justificada para v1.

### 5. Botones inline con `callback_data` estructurado
**Rationale:** Se reutiliza el patrón existente en `telegram_service.py` (`tipo:valor`). Para lista de espera usamos `lista_espera:aceptar:<turno_id>` y `lista_espera:rechazar:<turno_id>`. Esto permite al router conversacional enrutar a `accion_aceptar_lista_espera` / `accion_rechazar_lista_espera`.

## Risks / Trade-offs

- **[Risk]** Paciente acepta pero el turno ya fue tomado por otro proceso (race condition).  
  → **Mitigation:** La confirmación desde lista de espera reutiliza `confirmar_turno` que ya bloquea la fila del turno con `SELECT FOR UPDATE` y valida estado. Si ya no está `DISPONIBLE`, se rechaza la operación y se pasa al siguiente.

- **[Risk]** Falla de envío de Telegram al notificar.  
  → **Mitigation:** Se loguea el error (RN-GL-01). El registro de `ListaDeEspera` queda con `notificado=FALSE` (no se actualiza si el envío falla), por lo que el próximo job de liberación de slots o la próxima cancelación reintentará con el mismo paciente.

- **[Risk]** Job de timeout se solapa con una interacción del usuario.  
  → **Mitigation:** El job de timeout también usa `SELECT FOR UPDATE` sobre la fila de `ListaDeEspera`. Si el usuario está en medio de aceptar, la transacción del usuario bloqueará la fila primero (o viceversa), y el perdedor reintentará en el próximo ciclo.

- **[Risk]** Múltiples pacientes en lista de espera para distintas fechas; un slot liberado no coincide con la `fecha_solicitada` de nadie.  
  → **Mitigation:** El query FIFO filtra por `fecha_solicitada = fecha_del_slot_liberado`. Si no hay match, el turno queda `DISPONIBLE` para reserva manual.

- **[Trade-off]** El timeout es global (`LISTA_ESPERA_MINUTOS`) y no configurable por paciente. Esto simplifica la lógica pero no cubre casos especiales.

## Migration Plan

1. Alembic migration: agregar `turno_ofrecido_id` (FK nullable) e `notificado_en` (timestamp nullable) a `lista_de_espera`.
2. Deploy del backend con nuevos endpoints y servicios.
3. Reinicio del scheduler para registrar el nuevo job de timeout.
4. Rollback: revertir migration, restaurar versión anterior del backend.

## Open Questions

- ¿`LISTA_ESPERA_MINUTOS` default = 5 minutos? (TBD antes de implementar; configurable vía `Settings`).
- ¿Se permite que un paciente esté en lista de espera y tenga un turno activo simultáneamente? Por ahora **sí**, dado que la lista de espera es para una fecha específica y el paciente podría querer "mejorar" su turno actual.
- ¿Se notifica también al liberar por expiración de reserva temporal? **Sí**, para maximizar ocupación, aunque el turno queda en `DISPONIBLE` (sin paciente) y puede ofrecerse.
