## Why

El backend de **Tesis-N8N-turnos** tiene **issues críticos de transacciones y concurrencia** descubiertos en una auditoría posterior a v1.0. El más grave (C-2, severidad **CRITICAL**) es que `reprogramar_turno` ejecuta `cancelar_turno` + `reservar_turno` + `confirmar_turno` con `await db.commit()` adentro de cada uno, lo que produce **commits parciales irrecuperables** si la tercera operación falla: el turno original queda `CANCELADO` y el nuevo queda huérfano en `RESERVADO_TEMPORAL` sin posibilidad de rollback. Adicionalmente, hay issues **HIGH** de timezone (uso de `datetime.now()` sin `timezone.utc` en comparaciones de expiración) y de race conditions (falta de `SELECT FOR UPDATE` sobre `ReservaTemporal` en `confirmar_turno`). Se necesitan fixes **ahora** porque comprometen la integridad de datos en producción.

## What Changes

### Contrato de transacciones (Patrón A — fundamental)

- **Adoptar Patrón A** a nivel codebase: los **servicios NO hacen commit** (solo `add`, `delete`, `flush`), routers y scheduler son los únicos responsables de `commit()`/`rollback()`. Esto permite que operaciones compuestas como `reprogramar_turno` ejecuten atómicamente.
- **Quitar `await db.commit()`** de: `cancelar_turno`, `confirmar_turno`, `reservar_turno` (no tenía), `liberar_reservas_vencidas`, `notificar_y_marcar`, `registrar_en_lista_espera`, `eliminar_de_lista_espera`, `rechazar_turno_lista_espera`, `procesar_timeouts_lista_espera`.
- **Agregar `await db.commit()` / `await db.rollback()`** en los routers `turnos.py` y `pacientes.py` que corresponda, manteniendo el contrato de error en `try/except` ya existente.

### Atomicidad de `reprogramar_turno` (C-2 — CRITICAL)

- Refactorizar `reprogramar_turno` para que las tres operaciones (cancelar viejo, reservar nuevo, confirmar nuevo) ocurran dentro de **una sola transacción**. Si `confirmar_turno` falla, **rollback completo**: el turno viejo sigue `CONFIRMADO` y no se crea el nuevo.
- Eliminar el `await db.commit()` final que existía en el `reprogramar_turno` actual (el caller del router hará commit/rollback).

### Timezone y race conditions (C-3 — HIGH)

- Reemplazar `datetime.now()` por `datetime.now(timezone.utc)` en todas las comparaciones de expiración: `confirmar_turno` (verificación de `reserva.expiracion`), `liberar_reservas_vencidas` (query y comparación), `reservar_turno` (cálculo de expiración), `procesar_timeouts_lista_espera`, `notificar_y_marcar`, `rechazar_turno_lista_espera`, `registrar_en_lista_espera`.
- Agregar `with_for_update()` a la query de `ReservaTemporal` en `confirmar_turno` para serializar lecturas concurrentes durante la verificación de expiración.
- Persistir `ReservaTemporal.expiracion` con `tzinfo=UTC` explícitamente.

### Lista de espera: race en aceptación (C-4 — HIGH)

- En `aceptar_turno_lista_espera`, wrappear la llamada a `confirmar_turno` con manejo de `TurnoExpiradoError`. Si la reserva temporal ofrecida expiró, liberar el slot (`DISPONIBLE`), eliminar la `ReservaTemporal`, resetear el registro de lista de espera y re-llamar a `evaluar_lista_espera` para ofrecer al siguiente paciente.
- Quitar `await db.commit()` de `notificar_y_marcar` (delegar al caller).

### `liberar_reservas_vencidas`: reordenamiento (C-5 — MEDIUM)

- Reordenar el flujo: en una **sola transacción** por profesional, identificar reservas vencidas, marcar `DISPONIBLE`, eliminar `ReservaTemporal`, evaluar lista de espera (mismo turno), y **luego** hacer un solo commit. Eliminar el antipatrón de "commit → re-SELECT → evaluar lista de espera".

### Extracción de `completar_turno` a servicio (B-3 — MEDIUM)

- Mover la lógica de `completar_turno_endpoint` (router `turnos.py:143-169`) a una nueva función `turno_service.completar_turno()` que aplique el contrato Patrón A (sin commit, flush only). El router pasa a ser un wrapper delgado que llama al servicio y maneja HTTPException/rollback.

### Unificar contrato de commit en `pacientes.py` (B-4 — MEDIUM)

- Definir contrato único para `create_paciente`: el servicio `crear_o_obtener_paciente` mantiene su contrato actual (no commitea, usa savepoint); el router hace commit/rollback. Refactorizar para que **siempre** se llame al servicio (ya sea path de "existe" o "nuevo") sin duplicar la lógica de `select` en el router.

### Contrato `confirmar_turno_endpoint` (B-2 — HIGH)

- Mantener `confirmar_turno` sin `await db.commit()` (cambio en el servicio). El router `confirmar_turno_endpoint` sigue siendo el responsable de `commit` y `rollback` en su bloque `try/except` (que ya existe). El cambio principal es **documentar el contrato** y eliminar el commit interno que pueda existir accidentalmente.

## Capabilities

### New Capabilities

- `service-transaction-contract`: Define el contrato de transacciones para los servicios del backend: los servicios modifican la sesión (add/delete/flush) pero NO hacen commit; routers y scheduler son los únicos responsables de `commit()`/`rollback()`. Esto habilita composición atómica de operaciones (ej. `reprogramar_turno`) y elimina los commits parciales irrecuperables.

### Modified Capabilities

- `turno-reschedule`: Agregar requirement de **atomicidad** — la reprogramación debe ejecutarse en una sola transacción. Si la confirmación del nuevo turno falla, se debe hacer rollback completo (el turno original permanece `CONFIRMADO` y no se crea el nuevo turno). Scenario de rollback explícito.
- `turno-reservation`: Agregar requirement de **timezone UTC** — todas las comparaciones de `expiracion` deben usar `datetime.now(timezone.utc)`. Agregar requirement de **`SELECT FOR UPDATE` en `ReservaTemporal`** durante la confirmación para evitar race conditions entre SELECT y verificación de expiración.
- `turno-cancel`: Aclarar contract de commit — `cancelar_turno` no hace commit interno; el caller (router) es responsable. No cambiar el comportamiento observable (turno `CANCELADO`, evento Calendar eliminado, lista evaluada).
- `core-reserva-temporal-model`: Agregar requirement de que la comparación contra `expiracion` se haga con valores timezone-aware (UTC). Aclarar que el ORM debe persistir el datetime con tzinfo explícito.
- `turno-completado-transition`: Mover la lógica del endpoint `PUT /turnos/{id}/completar` desde el router al servicio `turno_service.completar_turno()` para cumplir con la separación router/servicio. No cambiar el comportamiento observable.

## Impact

### Archivos a modificar

**Servicios (cambiar contrato de commit y agregar funcionalidad):**
- `backend/app/services/turno_service.py` — quitar commits internos, refactorizar `reprogramar_turno` atómico, fix timezone, agregar `SELECT FOR UPDATE` en `ReservaTemporal`, agregar función `completar_turno()`.
- `backend/app/services/lista_espera_service.py` — quitar commits internos, capturar `TurnoExpiradoError` en `aceptar_turno_lista_espera`, reordenar flujo.
- `backend/app/services/paciente_service.py` — verificar/ajustar contrato (probablemente sin cambios mayores; ya no commitea, usa savepoint).

**Routers (agregar commits explícitos, refactorizar):**
- `backend/app/routers/turnos.py` — agregar `commit()`/`rollback()` donde corresponda; reemplazar lógica inline de `completar_turno_endpoint` con llamada a `turno_service.completar_turno()`.
- `backend/app/routers/pacientes.py` — refactorizar `create_paciente` para unificar contrato (siempre llamar al servicio, commit único en el router).

**Scheduler (verificar patrón):**
- `backend/app/scheduler/jobs.py` — verificar que los jobs que llaman a `liberar_reservas_vencidas`, `marcar_turnos_completados`, `procesar_timeouts_lista_espera` se adapten correctamente al Patrón A (probablemente requieren commit al final del job o ajustar el patrón de retorno de las funciones de servicio).

**Tests (cubrir gaps críticos):**
- `backend/tests/test_turno_service.py` — tests de atomicidad para `reprogramar_turno` (mock de fallo en confirmar), timezone para `confirmar_turno`, `SELECT FOR UPDATE` en `ReservaTemporal`.
- `backend/tests/test_lista_espera_service.py` — tests de `TurnoExpiradoError` capturado y reintento en `aceptar_turno_lista_espera`.
- `backend/tests/test_turno_router.py` — test de `completar_turno` movido a servicio.
- Tests de concurrencia REAL con `asyncio.gather` y dos sesiones distintas para validar `SELECT FOR UPDATE` y locks.
- Tests de integración que validen que **no hay commit parcial** (todos los cambios se aplican o ninguno).

### Breaking changes

**BREAKING** en el contrato interno de los servicios: cualquier código fuera de los routers/scheduler que llame directamente a estos servicios y dependa de que el commit ya esté hecho **debe ser actualizado**. En este codebase esto afecta a `reprogramar_turno` (auto-llamada) y a las llamadas internas entre servicios (`aceptar_turno_lista_espera` → `confirmar_turno`).

### Riesgos

- **Tests de 369 existentes** (383 passing / 7 failing pre-existentes): varios tests existentes pueden romperse porque asumían que el servicio commitea. Hay que adaptarlos al nuevo contrato. Los 7 failures pre-existentes NO son responsabilidad de este change (son de test fixtures/factories).
- **Concurrencia**: la fix de `SELECT FOR UPDATE` requiere DB transaccional (no aplica a SQLite in-memory sin PRAGMA). En el setup actual con PostgreSQL real (vía test-postgresql-infrastructure) debería funcionar, pero hay que verificar que los tests concurrentes usen el engine correcto.
- **TDD estricto activo**: cada fix va test rojo → verde → refactor, lo cual incrementará el número de tests significativamente.

### No-objetivos (explícitos)

- No cambiar el comportamiento observable de los endpoints HTTP (status codes, response bodies, mensajes de error).
- No cambiar la estructura de la base de datos (no es un change de schema).
- No agregar multi-tenancy ni aislamiento por `profesional_id` adicional.
- No tocar la integración con Google Calendar más allá de asegurar que sigue siendo best-effort y no afecta la transacción.
