## Why

El change `transaction-hardening` (archivado 2026-06-28) dejó un **issue abierto** documentado en su design.md como R3/OQ-5: la **race condition en `reservar_turno`**.

### El problema

`reservar_turno` hace `SELECT FOR UPDATE` sobre los turnos existentes para serializar reservas concurrentes. **Pero si no hay turnos pre-existentes para el slot, no hay nada que bloquear**: el lock no protege contra INSERTs concurrentes. El flujo es:

```python
# 1. SELECT FOR UPDATE sobre turnos existentes (no bloquea nada si no hay)
await db.execute(
    select(Turno).where(Turno.fecha == fecha, Turno.profesional_id == profesional_id)
    .with_for_update()
)
# 2. Verificar disponibilidad (lee la lista de slots teóricos)
disponibles = await calcular_disponibilidad(db, fecha, profesional_id)
# 3. INSERT del nuevo turno
db.add(turno)
```

Si dos requests llegan al mismo tiempo para el mismo slot:
1. Ambos pasan por el `SELECT FOR UPDATE` (que no bloquea nada porque no hay turnos)
2. Ambos calculan la misma disponibilidad
3. Ambos insertan el mismo `(profesional_id, fecha, hora_inicio)` → **DB tiene 2 turnos para el mismo slot**

El test `test_doble_reservar_mismo_slot_solo_uno_exitoso` está **xfailed** documentando este gap.

### Severidad

**HIGH**: compromete la integridad de la base de datos en producción. Si dos pacientes reservan el mismo slot concurrentemente, ambos creen tener la reserva, pero solo uno puede confirmarla. El otro verá un error confuso.

### Stack y constraints

- FastAPI + SQLAlchemy 2.0 async + PostgreSQL + pytest + pytest-asyncio
- TDD estricto activo
- 7 tests pre-existentes fallando (no relacionados con este change)
- Patrón A: los servicios NO hacen commit, routers/scheduler sí

## What Changes

### Constraint UNIQUE parcial sobre Turno

Agregar un **índice único parcial** en la tabla `turno`:

```sql
CREATE UNIQUE INDEX uq_turno_active_slot
ON turno(profesional_id, fecha, hora_inicio)
WHERE estado IN ('DISPONIBLE', 'RESERVADO_TEMPORAL', 'CONFIRMADO');
```

**¿Por qué parcial (no absoluto)?** Porque la cancelación actualmente NO elimina el Turno — solo cambia su estado a `CANCELADO`. Esto preserva el historial del profesional. Una constraint absoluta `(profesional_id, fecha, hora_inicio)` rompería el caso "paciente cancela → otro paciente reserva el mismo slot" (porque el Turno CANCELADO seguiría ocupando el índice). La constraint parcial permite múltiples Turnos CANCELADOS/COMPLETADOS para el mismo slot, pero solo **un Turno activo** a la vez.

### Captura de IntegrityError en `reservar_turno`

Cuando dos requests concurrentes intenten crear el mismo slot activo, el segundo recibe `IntegrityError` (pgcode `23505` — unique_violation). El servicio captura el error y lo traduce a `TurnoNoDisponibleError` (mismo error que ya lanza cuando el slot no está disponible teóricamente), preservando el contrato observable del endpoint.

### Nueva migración Alembic

`alembic/versions/<revision>_add_unique_active_slot_to_turno.py` que crea el índice único parcial.

### Eliminar el xfail

El test `test_doble_reservar_mismo_slot_solo_uno_exitoso` en `test_concurrency.py` ahora pasa: el segundo request recibe `TurnoNoDisponibleError` por la constraint de DB.

## Capabilities

### Modified Capabilities

- `turno-reservation`: El requirement `Sistema permite reservar un turno temporalmente` se fortalece. La scenario `Condición de carrera en reserva simultánea` ahora se cumple **garantizado por la base de datos** (UNIQUE constraint) además de por la lógica de aplicación. Se agrega scenario explícito de "captura de IntegrityError → TurnoNoDisponibleError".

## Impact

### Archivos a modificar

- `backend/app/models/turno.py` — agregar `Index` con `unique=True` y `postgresql_where` en `__table_args__`
- `backend/alembic/versions/<new>_add_unique_active_slot_to_turno.py` — nueva migración
- `backend/app/services/turno_service.py::reservar_turno` — capturar `IntegrityError` y convertir a `TurnoNoDisponibleError`
- `backend/tests/test_concurrency.py::test_doble_reservar_mismo_slot_solo_uno_exitoso` — quitar `@pytest.mark.xfail` y `@pytest.mark.asyncio`/etc.
- `backend/tests/test_turno_service.py` — nuevo test: `reservar_turno` con DB simulando IntegrityError retorna `TurnoNoDisponibleError`

### Schema change

- **Sí**: se agrega un índice único parcial a la tabla `turno`.
- **Alembic migration requerida**: la migración corre con `alembic upgrade head` y crea el índice.
- **Compatibilidad hacia atrás**: el índice parcial no afecta datos existentes (es solo un índice, no una columna nueva).
- **Performance**: el índice es O(log n) para INSERTs y UPDATEs. Para queries de disponibilidad (que leen muchos slots), el índice puede ayudar (lookup por prefijo).

### Breaking changes

**No** breaking changes en el contrato HTTP: el endpoint sigue retornando 409 Conflict con `TurnoNoDisponibleError` cuando el slot no está disponible. La diferencia es que ahora la detección es **garantizada** por la DB, no por la lógica de aplicación (que es best-effort).

### Riesgos

- **R1**: Si hay datos existentes con múltiples Turnos activos para el mismo slot (corrupción previa), la migración falla al crear el índice. **Mitigation**: antes de la migración, ejecutar un `SELECT` que cuente turnos activos duplicados; si > 0, loguear y abortar. En la práctica, los datos de test siempre cumplen la constraint.
- **R2**: La constraint parcial requiere PostgreSQL (no portable a SQLite). **Mitigation**: el proyecto ya es PostgreSQL-only en producción (testcontainers). SQLite no se usa.
- **R3**: El test `test_doble_reservar_mismo_slot_solo_uno_exitoso` puede ser flaky. **Mitigation**: usar `asyncio.gather` con reintentos; el test ya tiene la estructura para serialización con dos sesiones distintas.

### No-objetivos (explícitos)

- No cambiar la lógica de cancelación (sigue siendo UPDATE del estado, no DELETE).
- No cambiar el flujo de `confirmar_turno` (ya tiene su propia serialización con `SELECT FOR UPDATE` sobre `ReservaTemporal`).
- No cambiar el flujo de `liberar_reservas_vencidas` (ya reordenado en transaction-hardening).
- No agregar tests de concurrencia adicionales más allá del que está xfailed (este change resuelve ese gap y lo cierra).
- No convertir a SERIALIZABLE isolation (la constraint parcial es más simple y suficiente).
