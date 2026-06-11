## Context

Los changes C-01 a C-05 establecieron la base del sistema: modelos de datos, conectividad, configuración del profesional, gestión de pacientes e integración con Google Calendar. El sistema ahora necesita el ciclo de vida completo de un turno — desde la consulta de disponibilidad hasta la confirmación con evento en calendario — para que el flujo de negocio (US-001, US-002) funcione end-to-end. Este change es CRÍTICO porque todas las operaciones posteriores (reprogramación, cancelación, lista de espera, notificaciones) dependen de la reserva y confirmación como primitivas.

## Goals / Non-Goals

**Goals:**
- Permitir a un paciente (vía Telegram → FastAPI) consultar slots disponibles por fecha.
- Permitir reservar un slot temporalmente (`RESERVADO_TEMPORAL`) con expiración automática configurable.
- Permitir confirmar la reserva (`CONFIRMADO`), validando que el paciente no tenga otro turno activo.
- Al confirmar, crear evento en Google Calendar y eliminar la reserva temporal.
- Ejecutar un job periódico que libere reservas temporales vencidas y devuelva los turnos a `DISPONIBLE`.
- Proteger contra condiciones de carrera en reservas concurrentes usando transacciones de base de datos.
- Entregar tests que cubran reserva, expiración, doble reserva, confirmación y carrera.

**Non-Goals:**
- No se implementa reprogramación ni cancelación en este change (C-07, C-08).
- No se implementa lista de espera en este change (C-09).
- No se implementa notificaciones vía Telegram en este change (C-10).
- No se modifica la UI del bot más allá de los endpoints REST que el bot consumirá.

## Decisions

### 1. `turno_service.py` como única puerta de entrada al dominio de turnos
- **Rationale**: Todo el ciclo de reserva (reservar, confirmar, liberar) vive en un solo servicio. Esto evita que los endpoints contengan lógica de negocio y facilita testing unitario.
- **Alternativas consideradas**: Dividir en `reserva_service.py` y `confirmacion_service.py`. Rechazado porque la reserva y confirmación son parte del mismo flujo de estado y comparten reglas (RN-TU-01).

### 2. `SELECT FOR UPDATE` en la fila del turno a reservar
- **Rationale**: Dos pacientes pueden intentar reservar el mismo slot simultáneamente. Bloquear la fila del turno a nivel de base de datos garantiza atomicidad sin depender de locks de aplicación.
- **Alternativas consideradas**: Optimistic locking con `version`. Rechazado porque es más complejo para v1 y la contención de reservas es baja (un solo profesional, slots discretos).

### 3. `SELECT FOR UPDATE` + subquery para validar paciente sin turno activo
- **Rationale**: RN-TU-01 exige que un paciente no tenga más de un turno activo. Al confirmar, usamos una transacción que consulta con bloqueo las filas del paciente para evitar que dos confirmaciones simultáneas del mismo paciente pasen la validación.
- **Alternativas consideradas**: Unique constraint parcial en DB. Rechazado porque el paciente puede no estar identificado en el momento de la reserva temporal (solo en la confirmación), y porque el estado activo es un conjunto de estados (`RESERVADO_TEMPORAL`, `CONFIRMADO`).

### 4. APScheduler `AsyncIOScheduler` para la expiración
- **Rationale**: El backend ya usa `AsyncIOScheduler` (C-02). Agregar un job `interval` cada minuto que ejecute `liberar_reservas_vencidas()` es la solución más simple y robusta. El job usa `AsyncSession` para operaciones async de SQLAlchemy.
- **Alternativas consideradas**: Celery + Redis. Rechazado porque agrega infraestructura innecesaria para v1. `APScheduler` ya está en el stack.

### 5. `CalendarService.create_event()` envuelto con `run_in_threadpool`
- **Rationale**: `CalendarService` (C-05) usa el SDK de Google Calendar que es sincrónico. FastAPI ejecuta funciones `def` en el threadpool por defecto, pero si llamamos desde `async def` dentro del servicio, usamos `run_in_threadpool` explícitamente para no bloquear el event loop.
- **Alternativas consideradas**: Reescribir `CalendarService` como async. Rechazado porque el SDK de Google no soporta async nativamente y eso rompería C-05.

### 6. Transacción atómica para confirmación
- **Rationale**: La confirmación implica: actualizar `Turno` → eliminar `ReservaTemporal` → crear evento en Google Calendar. Si el calendar falla, el turno ya quedó `CONFIRMADO`. Decidimos que el turno pase a `CONFIRMADO` y el evento de calendar se reintente de forma asíncrona (o se registre el error y notifique al profesional). No se hace rollback de la confirmación por falla de calendar, porque el turno es la fuente de verdad del sistema.
- **Alternativas consideradas**: Rollback total si calendar falla. Rechazado porque perderíamos la confirmación del paciente y el slot podría ser tomado por otro. Es preferible un turno confirmado sin evento de calendar que un turno perdido.

### 7. `reservar_turno` devuelve `Turno` en `RESERVADO_TEMPORAL` + `ReservaTemporal`
- **Rationale**: El frontend (bot) necesita saber cuánto tiempo tiene para confirmar. El objeto `ReservaTemporal` incluye `expiracion`, calculado como `now() + RESERVA_TEMPORAL_MINUTOS`.
- **Alternativas consideradas**: Computar expiración en el endpoint. Rechazado porque la lógica de negocio debe vivir en el servicio.

## Risks / Trade-offs

- **[Race condition en confirmación]** → Mitigación: `SELECT FOR UPDATE` sobre turnos del paciente al confirmar.
- **[Falla de Google Calendar durante confirmación]** → Mitigación: no se hace rollback del turno. Se registra el error en logs estructurados y se expone un endpoint de reintento (fuera de scope de este change, pero se documenta en el código como TODO).
- **[Job de scheduler no se ejecuta si el proceso muere]** → Mitigación: en v1, si el backend se reinicia, el scheduler se reinicia también. Para producción, se recomienda múltiples réplicas con `RedisJobStore` (fuera de scope de v1).
- **[Doble reserva temporal del mismo paciente]** → Mitigación: la validación RN-TU-01 se aplica tanto en reserva temporal como en confirmación. Si el paciente ya tiene un turno activo, `reservar_turno` lanza excepción de negocio.
- **[Expiración de reserva temporal mientras el paciente confirma]** → Mitigación: la confirmación verifica que el turno esté en `RESERVADO_TEMPORAL` y que exista la `ReservaTemporal` asociada. Si ya expiró, la confirmación falla con error controlado.

## Migration Plan

No se requiere migración de datos. Los modelos `Turno` y `ReservaTemporal` ya existen (C-01). Este change agrega lógica de negocio sobre tablas existentes.

Despliegue:
1. Asegurar que la variable `RESERVA_TEMPORAL_MINUTOS` esté configurada (default 2).
2. Desplegar backend. El scheduler se inicializa automáticamente en el lifespan.
3. Verificar que el job de limpieza aparece en los logs de startup.

Rollback:
- Revertir el commit. Los endpoints nuevos dejan de existir. El scheduler no registra el job. Los datos existentes (`Turno` en `CONFIRMADO` o `RESERVADO_TEMPORAL`) permanecen válidos.

## Open Questions

- Ninguna para este change. Las preguntas abiertas de prioridad alta (IN-01, IN-03) de `10_preguntas_abiertas.md` ya están resueltas: `RESERVA_TEMPORAL_MINUTOS` se configura por env var (default 2 minutos) y el panel del profesional es vía Telegram (no web).
