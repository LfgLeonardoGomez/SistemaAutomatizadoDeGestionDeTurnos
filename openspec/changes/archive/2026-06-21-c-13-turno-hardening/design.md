## Context

El núcleo de turnos fue implementado en C-06 (reserva/confirmación), C-07 (cancelación/reprogramación) y C-08 (bot Telegram). Sin embargo, quedaron tres deudas técnicas que impiden construir C-10 (recordatorios), C-11 (lista de espera) y C-12 (panel profesional) sobre una base estable:

1. **`google_event_id` no persiste**: `CalendarService.create_event()` retorna un `event_id`, pero el modelo `Turno` no tiene columna para almacenarlo. Hoy se usa `getattr(turno, "google_event_id", None)` en `cancelar_turno()` y los tests lo setean dinámicamente (`confirmado.google_event_id = "event_old"`). Al reiniciar el servidor, ese atributo desaparece y la sincronización con Google Calendar se rompe (no se pueden eliminar eventos antiguos).
2. **Estado `COMPLETADO` sin transiciones**: El ENUM `turno_estado_enum` incluye `COMPLETADO`, pero no existe lógica que pase un turno a ese estado. Esto rompe RN-TU-02 (historial del paciente) y las métricas del profesional (tasa de completados vs cancelados).
3. **Reprogramación en Telegram es placeholder**: `accion_reprogramar_turno()` en `telegram_service.py` devuelve "próximamente". El backend REST ya soporta reprogramación (`PUT /turnos/{id}/reprogramar`), pero el bot no ofrece el flujo conversacional.

Este change es de tipo **hardening**: no agrega funcionalidad de usuario nueva, sino que completa y corrige el núcleo existente para que las features subsiguientes se construyan sobre roca, no sobre arena movediza.

## Goals / Non-Goals

**Goals:**
- Agregar columna `google_event_id` al modelo `Turno` y migrar la base de datos.
- Persistir el `event_id` devuelto por Google Calendar al confirmar un turno.
- Leer `google_event_id` desde la columna persistente en cancelación y reprogramación.
- Implementar transición a estado `COMPLETADO` mediante (a) endpoint manual del profesional y (b) job automático del scheduler.
- Implementar el flujo conversacional completo de reprogramación en Telegram.
- Cubrir cada sub-tarea con tests TDD (test rojo → verde → refactor).

**Non-Goals:**
- No se modifica la lógica de reserva temporal ni expiración (C-06 está estable).
- No se modifica `CalendarService` (C-05 está estable); solo se consume su retorno.
- No se implementa lista de espera (C-11).
- No se implementan recordatorios (C-10).
- No se agrega panel web del profesional (solo Telegram).

## Decisions

### 1. Agregar `google_event_id` como columna `VARCHAR(255), nullable=True` en `Turno`
- **Rationale**: Es el mínimo cambio de schema necesario. `google_event_id` es un string opaco de Google Calendar (ej. `abc123def456`). 255 chars es suficiente y alineado con convenciones SQLAlchemy.
- **Alternativa considerada**: Tabla separada `TurnoCalendarEvent` con FK 1:1. **Rechazada**: over-engineering para v1. La relación es estrictamente 1:1 y el evento es propiedad del turno.
- **Índice**: Se agrega `Index("ix_turno_google_event_id", "google_event_id")` para lookups rápidos si en el futuro se necesita buscar por event_id.

### 2. Modificar `confirmar_turno()` para persistir `event_id`
- **Rationale**: `CalendarService.create_event(turno)` retorna el `event_id`. Hoy ese retorno se descarta. La decisión es asignarlo a `turno.google_event_id` antes del refresh y commit.
- **Cambio específico**: después de `await run_in_threadpool(calendar.create_event, turno)`, capturar el retorno y asignarlo a `turno.google_event_id`. Como la sesión ya hizo commit, se necesita un `await db.commit()` adicional o hacer el calendar call antes del commit final. Decidimos: calendar call va **después** del commit de confirmación (igual que hoy), pero ahora se hace `turno.google_event_id = event_id` + `await db.commit()` en el bloque try.
- **Alternativa considerada**: Hacer calendar call dentro de la transacción. **Rechazada**: el SDK de Google es bloqueante y podría mantener la transacción abierta demasiado tiempo.

### 3. Modificar `cancelar_turno()` para leer desde columna persistente
- **Rationale**: Hoy usa `getattr(turno, "google_event_id", None)` que funciona solo si el objeto está en memoria con el atributo seteado. Con la columna persistente, basta con `turno.google_event_id` (SQLAlchemy lo lee de DB si no está en el identity map).
- **Cambio específico**: reemplazar `getattr(turno, "google_event_id", None)` por `turno.google_event_id`. El resto del flujo (best-effort delete, logging) no cambia.

### 4. Modificar `reprogramar_turno()` para propagar `google_event_id`
- **Rationale**: La reprogramación cancela el turno viejo (que necesita `google_event_id` para eliminar el evento de calendar) y crea uno nuevo (que necesita persistir el nuevo `event_id`).
- **Cambio específico**: `cancelar_turno()` ya leerá `google_event_id` de DB. `confirmar_turno()` ya persistirá el nuevo `event_id`. No se requieren cambios adicionales en `reprogramar_turno()` más allá de asegurar que el turno viejo se refresca antes de cancelar (ya lo hace con `await db.refresh(turno)` implícito en el flow).

### 5. Scheduler job `marcar_turnos_completados` con trigger `interval` configurable
- **Rationale**: Los turnos `CONFIRMADO` cuya fecha/hora de fin ya pasaron deben transicionar a `COMPLETADO`. Esto es necesario para métricas y para que el historial del paciente sea preciso.
- **Frecuencia**: cada 5 minutos (configurable vía `COMPLETADO_JOB_INTERVAL_MINUTOS`, default 5). Menos frecuente que el job de limpieza de reservas (1 minuto) porque la transición a completado no es time-sensitive.
- **Query**: `SELECT ... FROM turno WHERE estado = 'CONFIRMADO' AND (fecha + hora_fin) < NOW()` — en PostgreSQL se puede usar `timestamp(fecha, hora_fin)`. Se ejecuta con `SELECT FOR UPDATE` para evitar race conditions.
- **Alternativa considerada**: Trigger en PostgreSQL. **Rechazada**: agrega lógica de negocio en la capa de datos, dificulta testing y debugging.

### 6. Endpoint `PUT /turnos/{id}/completar` para transición manual
- **Rationale**: El profesional puede querer marcar un turno como completado antes de que pase su hora de fin (ej. paciente atendido y se va antes). Es un endpoint simple que valida que el turno esté `CONFIRMADO` y lo pasa a `COMPLETADO`.
- **Autorización**: v1 no tiene RBAC completo. El endpoint es público (como los demás endpoints de turnos). En C-12 se puede agregar autenticación del profesional.

### 7. Flujo de reprogramación en Telegram como wizard de 3 pasos
- **Rationale**: El usuario solicita "Reprogramar" → el bot debe mostrar fechas disponibles → el usuario selecciona fecha → el bot muestra horarios → el usuario selecciona hora → el bot llama a `reprogramar_turno()` → confirma al usuario.
- **Estado conversacional**: se reutiliza el mecanismo existente (`_conversation_states`). Nuevos estados:
  - `reprogramando_esperando_fecha`: usuario pidió reprogramar, mostrar fechas.
  - `reprogramando_esperando_hora`: usuario seleccionó fecha, mostrar horarios.
  - `reprogramando_confirmar`: usuario seleccionó hora, ejecutar reprogramación.
- **Identificación del turno**: el bot debe identificar el turno `CONFIRMADO` del paciente vinculado al `chat_id`. Para v1, se asume que el paciente tiene un solo turno activo (RN-TU-01), por lo que se puede buscar por `paciente.telefono` o `chat_id`. Dado que no hay tabla de vinculación Telegram-paciente en v1, usaremos el estado conversacional para guardar el `turno_id` que se quiere reprogramar (obtenido previamente, por ejemplo, desde un recordatorio o desde una consulta de "mis turnos").
- **Simplificación para v1**: el flujo de reprogramación desde Telegram asume que el `turno_id` ya está en el estado conversacional (por ejemplo, el usuario llegó desde un mensaje de recordatorio con callback `reprogramar:<turno_id>`). Si el usuario escribe "reprogramar" sin contexto, el bot le pide que seleccione su turno activo (si tiene más de uno, aunque RN-TU-01 lo impide).

### 8. Tests TDD estrictos para cada sub-tarea
- **Rationale**: Es una regla dura del proyecto. Cada sub-tarea implica: test rojo → implementación → test verde → refactor.
- **Sub-tareas con tests**:
  1. Migración de `google_event_id`: test de modelo que verifica que la columna existe y acepta valores.
  2. Persistencia en confirmación: test que mockea `CalendarService.create_event` retornando un ID y verifica que queda en DB.
  3. Lectura en cancelación: test que crea un turno con `google_event_id` en DB y verifica que `cancelar_turno()` lo lee correctamente.
  4. Transición a COMPLETADO: tests del scheduler job y del endpoint manual.
  5. Reprogramación Telegram: tests del router conversacional con estados.

## Risks / Trade-offs

- **[Risk]** La migración Alembic agrega una columna nullable a una tabla con datos existentes. PostgreSQL lo hace sin bloqueo en la mayoría de los casos, pero en tablas muy grandes podría requerir `ALTER TABLE ... ADD COLUMN ... DEFAULT NULL;` de forma explícita. → **Mitigación**: la tabla `turno` tiene pocos registros en v1. La migración es trivial.
- **[Risk]** Si el servidor se reinicia entre la confirmación del turno y la persistencia de `google_event_id`, el turno quedará `CONFIRMADO` sin `google_event_id`. → **Mitigación**: el `event_id` se persiste inmediatamente después de crear el evento en el mismo bloque try/except. La ventana de riesgo es de milisegundos. En el peor caso, el evento de calendar queda huérfano; se puede limpiar manualmente o con un job futuro.
- **[Risk]** El job de `COMPLETADO` puede correr mientras un profesional intenta cancelar el mismo turno. → **Mitigación**: `SELECT FOR UPDATE` en ambas operaciones garantiza serialización a nivel de fila.
- **[Risk]** El flujo de reprogramación en Telegram es más complejo que los flujos existentes (reserva/cancelación) y puede introducir bugs de estado. → **Mitigación**: tests exhaustivos del router conversacional con estados limpios y sucios, y manejo de timeout/reset.
- **[Trade-off]** No se implementa "mis turnos" en Telegram como prerequisite de reprogramación. El flujo asume que el `turno_id` llega desde un recordatorio o mensaje interactivo. Si el usuario escribe "reprogramar" sin contexto, el bot busca su turno activo (RN-TU-01 garantiza que hay como máximo uno). Esto es suficiente para v1.

## Migration Plan

1. **Migración de base de datos**: Ejecutar `alembic upgrade head` para agregar `google_event_id`. Los turnos existentes quedan con `NULL` (se perderá la referencia a eventos de calendar previos, pero es aceptable para v1).
2. **Despliegue del backend**: Incluye el nuevo endpoint y los cambios en servicios.
3. **Verificación del scheduler**: En los logs de startup deben aparecer dos jobs registrados: `liberar_reservas_vencidas` y `marcar_turnos_completados`.
4. **Rollback**: Revertir el commit + `alembic downgrade`. Los turnos `COMPLETADO` revertirían a su estado anterior si el downgrade lo soporta; alternativamente, dejar la columna `google_event_id` como nullable sin usar.

## Open Questions

- Ninguna para este change. Las preguntas abiertas de `10_preguntas_abiertas.md` ya están resueltas: `RESERVA_TEMPORAL_MINUTOS` es env var, panel profesional es vía Telegram.
