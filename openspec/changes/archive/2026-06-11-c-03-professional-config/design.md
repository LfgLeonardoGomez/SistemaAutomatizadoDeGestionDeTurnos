## Context

Este change se ejecuta sobre el modelo `Profesional` ya creado en C-02 (`backend/app/models/profesional.py`). El modelo incluye `horario_inicio`, `horario_fin`, `dias_atencion` y `duracion_turno`. En C-02 se creó un registro seed con valores por defecto (08:00 a 18:00, lunes a viernes, 30 minutos). Este change expone esos campos a través de una API REST y agrega la lógica de cálculo de disponibilidad que será consumida por el bot de Telegram y los futuros endpoints de turnos.

## Goals / Non-Goals

**Goals:**
- Exponer endpoints REST para leer y actualizar la configuración del profesional.
- Implementar un servicio `availability_service.py` que, dada una fecha, calcule los slots libres.
- Respetar RN-TU-06: disponibilidad = horarios posibles según config MINUS turnos `CONFIRMADO` o `RESERVADO_TEMPORAL`.
- Filtrar días no laborables (días fuera de `dias_atencion`).
- Evitar solapamientos entre turnos existentes y slots propuestos.
- Proveer validaciones estrictas en los endpoints (`horario_inicio` < `horario_fin`, `duracion_turno` > 0, `dias_atencion` válidos).
- Cubrir con tests TDD: recálculo de slots al cambiar duración, filtrado por día no laborable, prevención de solapamientos, validación de horarios.

**Non-Goals:**
- No se agrega autenticación al panel del profesional en este change (v1.0 asume acceso restringido por red/URL).
- No se implementa la UI de Telegram en este change (es parte de C-04 y siguientes).
- No se modifica el modelo de datos (se reutiliza el existente de C-02).
- No se integra Google Calendar en este change.

## Decisions

1. **Single-profesional simplificado**
   - *Decision*: Asumir que existe un único registro en `Profesional` (id=1) y los endpoints operan sobre él sin recibir `profesional_id` en la URL.
   - *Rationale*: v1.0 es single-tenant. Agregar `{profesional_id}` a la URL sería over-engineering. Si en el futuro se necesita multi-profesional, se migra a `/profesionales/{id}/configuracion`.
   - *Alternativa considerada*: `GET /profesionales/{id}/configuracion` — descartada por complejidad innecesaria en v1.

2. **Router dedicado `profesional.py` bajo prefix `/profesional`**
   - *Decision*: Crear un router FastAPI separado en `backend/app/routers/profesional.py` en lugar de agregar endpoints al router de turnos.
   - *Rationale*: Separa responsabilidades (configuración vs. turnos), facilita testing y sigue la estructura de directorios propuesta en `08_arquitectura_propuesta.md`.

3. **Servicio `availability_service.py` como función pura + query de DB**
   - *Decision*: El servicio recibe `db: AsyncSession`, `fecha: date`, y opcionalmente un `profesional_id`. Realiza la query de turnos ocupados y calcula slots libres.
   - *Rationale*: Mantiene la lógica de negocio desacoplada del router y permite reutilizarla desde otros servicios (ej. turno_service en C-04).
   - *Alternativa considerada*: Query raw SQL para performance — descartada porque el volumen de turnos por día es bajo y SQLAlchemy ORM es suficiente.

4. **Schema de salida del cálculo de disponibilidad**
   - *Decision*: Retornar lista de `time` objects (o strings ISO) representando los `hora_inicio` de cada slot disponible.
   - *Rationale*: El bot de Telegram y los futuros endpoints de turnos solo necesitan saber qué horarios de inicio están libres. La `hora_fin` se calcula trivialmente (`hora_inicio + duracion_turno`).
   - *Alternativa considerada*: Retornar objetos completos `{hora_inicio, hora_fin}` — descartada porque es redundante y agrega payload innecesario.

5. **Transacción para actualización de configuración**
   - *Decision*: Usar `async with db.begin()` en el endpoint PUT para garantizar consistencia.
   - *Rationale*: Aunque es un solo registro, la transacción es gratuita y establece el patrón para futuros endpoints multi-tabla.

6. **Tests de integración con DB real en memoria**
   - *Decision*: Usar `asyncpg` + PostgreSQL de prueba (o sqlite async si no hay postgres disponible) para tests de `availability_service.py`.
   - *Rationale*: La lógica de disponibilidad depende de queries de base de datos; los tests unitarios con mocks no detectan race conditions ni errores de query. Dado que C-02 ya estableció el test setup con PostgreSQL, se reutiliza.

## Risks / Trade-offs

- **[Risk]** Asumir single-profesional puede generar deuda técnica si el dominio evoluciona a multi-profesional.
  → *Mitigación*: Documentar explícitamente en la KB y en el código (TODO/FIXME) que los endpoints son single-profesional.
- **[Risk]** Cambiar `duracion_turno` no recalcula turnos existentes automáticamente.
  → *Mitigación*: Es comportamiento esperado (la configuración afecta slots futuros, no turnos ya confirmados). Documentar en la API response o en la KB.
- **[Risk]** `dias_atencion` almacenado como VARCHAR o ARRAY puede complicar queries y validaciones.
  → *Mitigación*: Usar Pydantic para normalizar a lista de strings/ints antes de persistir; en la DB usar `ARRAY` de PostgreSQL si está disponible (C-02 ya lo definió). Si es VARCHAR, parsear en el modelo.
- **[Trade-off]** El cálculo de disponibilidad se hace en Python, no en SQL. Esto simplifica el código pero puede ser menos eficiente para agendas muy grandes.
  → *Aceptable*: una agenda de 8h a 18h con turnos de 30 min produce 20 slots por día; la diferencia de performance es irrelevante.

## Migration Plan

- No requiere migración de datos ni rollback. El modelo existe; solo se agregan endpoints y lógica.
- Deploy: levantar nuevo código, verificar que los endpoints respondan correctamente, validar con tests existentes.

## Open Questions

- ¿El formato de `dias_atencion` en el modelo es `ARRAY` de PostgreSQL o VARCHAR? → Confirmar en `backend/app/models/profesional.py` antes de implementar los schemas.
- ¿El seed de C-02 crea exactamente un `Profesional` con id=1? → Validar en el test de setup.
