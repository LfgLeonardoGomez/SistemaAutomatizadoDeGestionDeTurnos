## Context

El proyecto **Tesis-N8N-turnos** tiene el ciclo de reserva de turnos completado en C-06: `turno-reservation` (137 tests, endpoints de disponibilidad, reserva temporal, confirmación, scheduler de expiración). El backend usa FastAPI + SQLAlchemy 2.0 async + PostgreSQL, con Google Calendar sincronizado via `CalendarService` (C-05). El modelo `Turno` tiene estados `DISPONIBLE`, `RESERVADO_TEMPORAL`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`.

Este change (C-07) cierra el ciclo básico de gestión de turnos agregando **cancelación** y **reprogramación**, requisitos bloqueantes para la integración con Telegram (C-08) y la lista de espera (C-11).

## Goals / Non-Goals

**Goals:**
- Permitir a un paciente cancelar un turno `CONFIRMADO` vía `PUT /turnos/{id}/cancelar`.
- Permitir a un paciente reprogramar un turno `CONFIRMADO` vía `PUT /turnos/{id}/reprogramar`.
- Sincronizar ambas operaciones con Google Calendar (eliminar evento anterior, crear nuevo si aplica).
- Mantener la consistencia de la base de datos como fuente de verdad (DB first, calendar second).
- Respetar RN-TU-01 (un turno activo por paciente) durante la reprogramación.
- Reutilizar al máximo la lógica de `turno_service.py` y `calendar_service.py` ya existentes.
- Entregar tests TDD estrictos que cubran happy path, edge cases y fallos de integración externa.

**Non-Goals:**
- No se implementa la notificación a lista de espera en este change (es C-11). Solo se libera el slot.
- No se agrega interfaz de usuario nueva (web o Telegram); solo endpoints REST.
- No se modifica el scheduler de expiración de reservas temporales (ya cubierto en C-06).
- No se implementa el cambio de estado a `COMPLETADO` (fuera de scope).

## Decisions

### 1. Cancelación como transacción DB + calendar async best-effort
- **Decisión**: La cancelación actualiza el estado del turno a `CANCELADO` y hace `COMMIT` inmediatamente. La eliminación del evento en Google Calendar se ejecuta **después** del commit, via `run_in_threadpool`, con try/except y logging. Si falla, no se revierte la cancelación.
- **Rationale**: RN-GL-01 establece que si un servicio externo falla, el sistema debe registrar el error y no perder datos. La base de datos es la fuente de verdad; el calendario es un espejo eventual.
- **Alternativa considerada**: Rollback automático si falla Google Calendar. **Rechazada**: dejaría un turno confirmado en DB cuando el usuario ya solicitó cancelar, generando confusión y posibles inasistencias.

### 2. Reprogramación = cancelación + nueva reserva confirmada (RN-TU-05)
- **Decisión**: `reprogramar_turno()` orquesta internamente: (a) cancelar el turno anterior (lógica compartida), (b) reservar un nuevo slot con `reservar_turno()` de C-06, (c) confirmar el nuevo turno con `confirmar_turno()` de C-06.
- **Rationale**: RN-TU-05 lo exige explícitamente. Mantiene trazabilidad: el turno original queda `CANCELADO`, el nuevo queda `CONFIRMADO`. Reutiliza código probado y evita duplicar validaciones (RN-TU-01, disponibilidad, calendar sync).
- **Alternativa considerada**: Actualizar in-place el turno existente (fecha/hora). **Rechazada**: pierde el historial del turno original y rompe el patrón de máquina de estados que usamos en el modelo.

### 3. Uso de `SELECT FOR UPDATE` en cancelación
- **Decisión**: Al cancelar, se bloquea la fila del turno con `select(Turno).where(Turno.id == id).with_for_update()` para evitar que otra operación (ej. confirmación desde otro hilo) modifique el estado concurrentemente.
- **Rationale**: Evita race conditions donde un turno podría pasar a `CONFIRMADO` mientras se cancela. Es consistente con el patrón ya usado en `reservar_turno` y `confirmar_turno`.

### 4. No usar `async def` para Google Calendar SDK
- **Decisión**: `CalendarService` mantiene sus métodos `def` (síncronos). Los servicios de turno los invocan con `run_in_threadpool`.
- **Rationale**: Es una regla dura del proyecto (AGENTS.md). El SDK de Google Calendar es bloqueante; ejecutarlo en el event loop async congelaría el servidor.

### 5. Graceful handling de calendar delete failure
- **Decisión**: Si `delete_event` falla (incluso tras retries), se loguea el error y se continúa. No se almacena estado de "pendiente de sincronización" ni se reintenta después.
- **Rationale**: Mantener la complejidad baja. Para v1, el logging + monitoreo manual es suficiente. Si se necesita reintentos deferred, es scope de un change futuro de operaciones/mantenimiento.

### 6. Nuevas excepciones de dominio
- **Decisión**: Se agregan `TurnoNoEncontradoError`, `TurnoYaCanceladoError` al módulo `exceptions.py` para diferenciar casos de error y mapear a códigos HTTP correctos (404 vs 409).
- **Rationale**: `TurnoNoDisponibleError` se usaba para múltiples casos (slot no disponible, turno no encontrado). Separar mejora la precisión de los handlers y los tests.

### 7. Schemas de request para reprogramación
- **Decisión**: `ReprogramarTurnoRequest` contiene `nueva_fecha` y `nueva_hora_inicio`, y opcionalmente `paciente_data` (solo si se quiere modificar datos del paciente; por defecto se reutiliza el paciente del turno anterior).
- **Rationale**: El flujo más común es que el mismo paciente se reprograme. Exigir `paciente_data` de nuevo sería fricción innecesaria. Si se omite, se reutiliza el `paciente_id` del turno cancelado.

## Risks / Trade-offs

- **[Risk]** El evento de Google Calendar queda huérfano si `delete_event` falla. → **Mitigación**: logging estructurado + alerta al profesional. No se puede hacer más sin un sistema de reintentos deferred.
- **[Risk]** Reprogramación como dos operaciones (cancel + reserva) tiene una ventana de concurrencia entre ambas. → **Mitigación**: todo ocurre dentro de una misma sesión/transacción de SQLAlchemy; si la reserva nueva falla, la cancelación del anterior ya se commiteó. Esto es aceptable porque RN-TU-05 dice que la reprogramación es cancelación seguida de nueva reserva; el usuario no quiere mantener el turno anterior si la reprogramación falla por slot no disponible, pero el slot anterior ya quedó libre (lo cual es correcto). Si la nueva reserva falla, el usuario puede intentar otro slot.
- **[Risk]** Tests de Google Calendar dependen de mocks; un cambio en la API del SDK puede romper la integración sin que los tests lo detecten. → **Mitigación**: tests de integración manual con cuenta de servicio real en staging.
- **[Trade-off]** No se implementa "undo" de cancelación. Si el usuario cancela por error, debe reservar de nuevo. Esto simplifica el modelo y es consistente con la mayoría de sistemas de turnos.
