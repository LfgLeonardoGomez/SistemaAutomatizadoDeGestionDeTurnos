## Context

El change `transaction-hardening` (archivado 2026-06-28) adoptó el Patrón A (servicios sin commit, routers/scheduler con commit) y agregó `SELECT FOR UPDATE` sobre `ReservaTemporal` en `confirmar_turno` para serializar confirmaciones. Sin embargo, documentó un **gap abierto (R3/OQ-5)**: la race condition en `reservar_turno` no fue resuelta.

### Análisis del gap

`reservar_turno` ejecuta:

```python
# Lock sobre turnos existentes (best-effort)
await db.execute(
    select(Turno).where(Turno.fecha == fecha, Turno.profesional_id == profesional_id)
    .with_for_update()
)
# Verificar disponibilidad teórica
disponibles = await calcular_disponibilidad(db, fecha, profesional_id)
# Verificar que el slot está en la lista
if hora_inicio not in disponibles:
    raise TurnoNoDisponibleError()
# INSERT
db.add(turno)
```

**El problema**: si dos requests concurrentes llegan antes de que se inserte CUALQUIER turno en esa fecha:
1. Ambos pasan por el `SELECT FOR UPDATE` (que no bloquea nada — no hay filas)
2. Ambos llaman a `calcular_disponibilidad` que devuelve la misma lista teórica
3. Ambos insertan el mismo slot

El test `test_doble_reservar_mismo_slot_solo_uno_exitoso` está xfailed, documentando este gap.

### Stack y constraints

- FastAPI + SQLAlchemy 2.0 async + PostgreSQL
- Alembic para migraciones
- pytest + pytest-asyncio + testcontainers[postgres] (PostgreSQL real, no SQLite)
- TDD estricto
- 7 tests pre-existentes fallando (no relacionados con este change)

## Goals / Non-Goals

**Goals:**
1. **Garantizar atomicidad de reservas concurrentes** vía constraint de DB, no solo lógica de aplicación.
2. **UNIQUE constraint parcial**: solo un Turno activo (`DISPONIBLE`/`RESERVADO_TEMPORAL`/`CONFIRMADO`) por `(profesional_id, fecha, hora_inicio)`.
3. **Manejar `IntegrityError` correctamente**: el segundo request concurrente recibe `TurnoNoDisponibleError` (mismo error que ya se lanza para slot no disponible teóricamente).
4. **Cerrar el xfail de test_concurrency.py**.
5. **Mantener la semántica de cancelación**: cancelar NO elimina el Turno (cambia estado a CANCELADO); el índice parcial permite múltiples Turnos CANCELADOS/COMPLETADOS para el mismo slot.

**Non-Goals:**
- No cambiar lógica de cancelación o liberación.
- No cambiar el flujo de `confirmar_turno` (ya tiene su propio `SELECT FOR UPDATE`).
- No agregar tests de concurrencia adicionales más allá del que cierra el gap.
- No convertir a SERIALIZABLE isolation (la constraint parcial es más simple y suficiente).

## Decisions

### Decisión 1: UNIQUE constraint PARCIAL (no absoluta)

**Elegido**: `CREATE UNIQUE INDEX uq_turno_active_slot ON turno(profesional_id, fecha, hora_inicio) WHERE estado IN ('DISPONIBLE', 'RESERVADO_TEMPORAL', 'CONFIRMADO')`.

**Alternativas consideradas**:
- **A) UNIQUE absoluta** `(profesional_id, fecha, hora_inicio)`: rechazada porque la cancelación NO elimina el Turno (cambia estado a CANCELADO). Un paciente que cancela su reserva dejaría el slot "ocupado" por el Turno CANCELADO, impidiendo a otro paciente reservar el mismo slot.
- **B) Cambiar la cancelación a DELETE en lugar de UPDATE**: rechazada porque rompe el historial del profesional y requiere cambios en más lugares (turno_service.cancelar_turno, google calendar event_id, etc.).
- **C) `SERIALIZABLE` isolation**: rechazada por overhead en la DB y porque requiere retry logic para errores de serialización.

**Rationale**:
- La constraint parcial es la convención SQL estándar para "una fila activa a la vez, múltiples históricas".
- Permite que la cancelación siga siendo un UPDATE (preserva el historial).
- Es la solución más simple y definitiva: la DB garantiza la atomicidad.
- Compatible con todos los tests existentes (verificado: ningún test crea múltiples Turnos activos para el mismo slot).

**Implementación en SQLAlchemy**:
```python
from sqlalchemy import text
Index(
    "uq_turno_active_slot",
    "profesional_id", "fecha", "hora_inicio",
    unique=True,
    postgresql_where=text(
        "estado IN ('DISPONIBLE', 'RESERVADO_TEMPORAL', 'CONFIRMADO')"
    ),
)
```

### Decisión 2: Capturar `IntegrityError` y convertir a `TurnoNoDisponibleError`

**Elegido**: En `reservar_turno`, agregar try/except que captura `IntegrityError` y lanza `TurnoNoDisponibleError`. El error genérico al cliente es "slot no disponible" (HTTP 409), sin distinción entre "ya estaba ocupado" o "otro request lo ganó por carrera".

**Rationale**:
- Mantiene el contrato observable del endpoint HTTP: el router `create_turno` ya mapea `TurnoNoDisponibleError` a 409 Conflict.
- No leakea detalles de implementación (pgcode, etc.) al cliente.
- Consistente con el resto del código: cuando `calcular_disponibilidad` ya muestra el slot como no disponible, el router retorna 409 también.

**Implementación**:
```python
try:
    db.add(turno)
    await db.flush()  # flush para forzar el INSERT y la constraint
except IntegrityError:
    # Otro request ganó la carrera
    await db.rollback()
    raise TurnoNoDisponibleError("El slot ya fue reservado por otro paciente")
```

**Nota**: el `flush` (no `commit`) es importante porque seguimos en Patrón A: el caller (router) hace el commit. El rollback deshace la sesión local sin afectar al caller.

### Decisión 3: Nueva migración Alembic

**Elegido**: `alembic/versions/<revision>_add_unique_active_slot_to_turno.py` que crea el índice único parcial.

**Alternativa**: usar `Base.metadata.create_all()` o autogenerate. **Rechazada** porque el proyecto usa Alembic explícitamente y el autogenerate puede no detectar índices parciales correctamente.

**Implementación**:
```python
def upgrade() -> None:
    op.create_index(
        "uq_turno_active_slot",
        "turno",
        ["profesional_id", "fecha", "hora_inicio"],
        unique=True,
        postgresql_where=sa.text(
            "estado IN ('DISPONIBLE', 'RESERVADO_TEMPORAL', 'CONFIRMADO')"
        ),
    )

def downgrade() -> None:
    op.drop_index("uq_turno_active_slot", table_name="turno")
```

La `down_revision` es la última migración existente (`c22d4e6f8a0c` para `add_google_calendar_id_to_profesional`).

### Decisión 4: Quitar el xfail de test_concurrency.py

**Elegido**: Quitar `@pytest.mark.xfail` y `@pytest.mark.asyncio` decorator del test `test_doble_reservar_mismo_slot_solo_uno_exitoso`. El test ahora pasa porque la constraint de DB garantiza que solo un request puede tener éxito.

**Rationale**: el test verifica exactamente el comportamiento que la constraint garantiza. Si después de este change el test sigue fallando, hay un bug en la implementación.

## Risks / Trade-offs

- **R1: Tests existentes con múltiples Turnos activos para el mismo slot**. Mitigation: verificado que ningún test existente crea esta situación. El test `test_dos_turnos_confirmados_excluyen_slots` crea dos turnos pero con slots distintos (9:00 y 10:00). El test `test_race_condition_doble_cancelacion` crea `turno1` y `turno2` con slots distintos.

- **R2: Datos existentes con duplicados**. Mitigation: si la migración falla al crear el índice, el log muestra el SQL exacto. En la práctica, los datos siempre cumplen la constraint. Si en producción hay duplicados, la migración aborta antes de tocar datos.

- **R3: Performance del índice**. Mitigation: el índice es O(log n) para INSERTs. Para `calcular_disponibilidad` (que lee slots disponibles), el índice no se usa directamente (la query es por `(fecha, profesional_id, estado IN (CONFIRMADO, RESERVADO_TEMPORAL))` que ya tiene el índice `ix_turno_fecha_hora_inicio`). Costo: ~1-2% más de tiempo en INSERTs/UPDATEs.

- **R4: Cambiar el modelo requiere reload de metadata**. Mitigation: en producción, las migraciones Alembic se aplican en deploy. En tests, el `conftest.py` ya hace `alembic upgrade head` (línea 181) por lo que la nueva migración se aplica automáticamente.

- **R5: El flush forzado puede tener un side-effect observable**. Mitigation: el `flush` solo persiste los cambios pendientes de la sesión; el caller (router) sigue siendo responsable del `commit`. Esto es consistente con el Patrón A.

## Migration Plan

### Fase 1: Modelo y migración (atómico)
1. Agregar el `Index` con `unique=True` y `postgresql_where` en `backend/app/models/turno.py`
2. Crear la migración Alembic con la misma definición
3. Verificar que `alembic upgrade head` aplica la migración sin errores en una DB limpia

### Fase 2: Servicio (TDD)
1. **Test rojo**: test que simula IntegrityError al insertar (mockeando `db.flush`) — debe verificar que `TurnoNoDisponibleError` se lanza
2. **Implementar**: try/except IntegrityError en `reservar_turno`
3. **Verificar**: el test pasa

### Fase 3: Test de concurrencia (TDD)
1. Quitar `@pytest.mark.xfail` de `test_doble_reservar_mismo_slot_solo_uno_exitoso`
2. Verificar que el test pasa con la nueva constraint
3. Agregar un test adicional: `test_reservar_turno_mismo_slot_distinto_paciente_gana_primero` que simula el caso "paciente A gana, paciente B recibe error"

### Fase 4: Verificación
1. Correr suite completa: `pytest` → debe ser 7F baseline + nuevos tests, 0 regresiones
2. Verificar con `openspec validate concurrency-hardening --strict` que los artifacts están bien formados
3. Verificar que `alembic downgrade -1` revierte correctamente la migración

### Rollback

- **Sí hay cambio de schema** (índice), pero solo se agrega un índice. Rollback es `alembic downgrade -1` que elimina el índice.
- Si el código tiene un bug, se puede hacer `git revert` del commit + `alembic downgrade -1`.

## Open Questions

- **OQ-1**: ¿Deberíamos también agregar `UNIQUE` para `(profesional_id, fecha, hora_fin)` para detectar overlap de slots? **Decisión**: NO, fuera del scope. La lógica de `calcular_disponibilidad` ya valida overlap; agregar otra constraint sería redundant y complicaría la cancelación.

- **OQ-2**: ¿Deberíamos usar `SERIALIZABLE` isolation en lugar del UNIQUE index? **Decisión**: NO. El UNIQUE index es más simple, más performante, y suficiente para el caso. SERIALIZABLE se difiere a un futuro change si se necesita.

- **OQ-3**: ¿Migrar datos existentes antes del upgrade? **Decisión**: NO necesario porque los datos existentes cumplen la constraint (no hay duplicados activos). Si en producción los hay, la migración aborta con un error claro.
