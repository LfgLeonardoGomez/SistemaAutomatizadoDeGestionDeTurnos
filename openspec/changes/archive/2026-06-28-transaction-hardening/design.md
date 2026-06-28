## Context

El backend de **Tesis-N8N-turnos** está en una versión estable v1.0/v2.0 (los 14 changes de C-01 a C-22 están archivados, 383/390 tests pasando, 7 fallas pre-existentes no relacionadas). Sin embargo, una auditoría de código reciente identificó **siete issues de transacciones y concurrencia** en los servicios centrales de turnos que comprometen la integridad de datos en producción:

### Issues identificados (severidad)

| ID  | Severidad | Ubicación | Síntoma |
|-----|-----------|-----------|---------|
| C-2 | **CRITICAL** | `turno_service.py:334-411` (`reprogramar_turno`) | Commits parciales irrecuperables: `cancelar_turno` + `reservar_turno` + `confirmar_turno` commitean independientemente; si la 3ª falla, DB queda inconsistente (viejo `CANCELADO`, nuevo `RESERVADO_TEMPORAL` huérfano) |
| B-2 | HIGH | `turnos.py:70-95` + `turno_service.py:118-193` (`confirmar_turno`) | El servicio modifica la sesión y el router hace commit, pero no hay contrato explícito ni manejo de "service fails mid-flight" |
| C-3 | HIGH | `turno_service.py:118-193` (`confirmar_turno`) | Comparación `reserva.expiracion < datetime.now()` con `datetime.now()` naive; race window entre SELECT de `ReservaTemporal` y verificación de expiración |
| C-4 | HIGH | `lista_espera_service.py:154-227` (`aceptar_turno_lista_espera`) | `TurnoExpiradoError` no se captura cuando la reserva temporal ofrecida expira entre notificación y aceptación |
| C-5 | MEDIUM | `turno_service.py:196-247` (`liberar_reservas_vencidas`) | Antipatrón: commit dentro del loop + re-SELECT post-commit para evaluar lista de espera |
| B-3 | MEDIUM | `turnos.py:143-169` (`completar_turno_endpoint`) | Lógica de negocio (SELECT FOR UPDATE, validación, modificación) inline en el router en lugar de un servicio |
| B-4 | MEDIUM | `pacientes.py:19-42` (`create_paciente`) | El router hace `select` directo y `commit` directo, duplicando lógica que también está en `crear_o_obtener_paciente` |

### Estado actual del contrato de transacciones

**Patrón mixto (problemático)**: cada servicio decide individualmente si hace commit. La mayoría de los servicios de `turno_service` hacen `await db.commit()` internamente, lo cual **rompe la composición**: si `reprogramar_turno` llama a tres sub-servicios, no puede agruparlos en una transacción atómica.

### Stack y constraints

- FastAPI + SQLAlchemy 2.0 async + PostgreSQL + pytest + pytest-asyncio
- TDD estricto activo (test rojo → verde → refactor en cada task)
- 369 tests, 383 passing / 7 failing pre-existentes
- Multi-tenant por profesional en v2.0 (no es objetivo de este change)

## Goals / Non-Goals

**Goals:**

1. **Garantizar atomicidad de operaciones compuestas** — `reprogramar_turno` ejecuta sus tres sub-operaciones en una sola transacción. Si alguna falla, rollback completo. La DB nunca queda en estado intermedio inconsistente.
2. **Adoptar un único contrato de transacciones (Patrón A)** — servicios modifican la sesión (add/delete/flush) pero **NO** hacen commit; routers y scheduler son los únicos responsables de `commit()`/`rollback()`. Esto habilita composición atómica en cualquier caller.
3. **Eliminar bugs de timezone en comparaciones de expiración** — todas las comparaciones contra `expiracion` usan `datetime.now(timezone.utc)`. El datetime persistido en `ReservaTemporal.expiracion` debe tener `tzinfo=UTC` explícito.
4. **Eliminar race condition en `confirmar_turno`** — usar `SELECT FOR UPDATE` sobre `ReservaTemporal` para serializar lecturas concurrentes durante la verificación de expiración.
5. **Manejar correctamente la expiración de la reserva temporal ofrecida en lista de espera** — `aceptar_turno_lista_espera` captura `TurnoExpiradoError`, libera el slot y re-llama a `evaluar_lista_espera` para ofrecer al siguiente paciente.
6. **Reordenar `liberar_reservas_vencidas` para una sola transacción por profesional** — sin commits intermedios, con evaluación de lista de espera dentro de la misma transacción.
7. **Extraer lógica de `completar_turno` al servicio** — el router pasa a ser un wrapper delgado que maneja HTTPException/commit/rollback.
8. **Documentar y unificar el contrato de commit en todos los routers y servicios**.

**Non-Goals:**

- No cambiar el comportamiento observable de los endpoints HTTP (status codes, response bodies, mensajes de error).
- No cambiar el schema de base de datos (no es un change de migración Alembic; los cambios son de aplicación sobre el schema actual).
- No agregar multi-tenancy, scoping adicional, ni cambios de auth.
- No tocar la lógica de Google Calendar más allá de asegurar que sigue siendo best-effort y no afecta la transacción.
- No convertir TODOS los servicios a un nuevo patrón si no son afectados por este change. Solo los identificados en el reporte de auditoría.
- No cambiar la integración con el scheduler más allá de adaptar el patrón de los servicios que invoca.
- No agregar tests de 7 failures pre-existentes (eso es de otro change).

## Decisions

### Decisión 1: Adoptar Patrón A (servicios no commitean, routers/scheduler sí)

**Elegido**: Patrón A — servicios modifican la sesión (add, delete, flush) pero NO hacen `await db.commit()`. Routers y el scheduler son los únicos responsables de commit/rollback.

**Alternativa considerada**: Patrón B — cada servicio hace su propio commit. **Rechazado** porque es exactamente el anti-patrón que produce el bug C-2 en `reprogramar_turno`: una vez que `cancelar_turno` hace commit, no hay forma de rollback si `confirmar_turno` falla.

**Rationale**:
- Es el patrón estándar de FastAPI + SQLAlchemy async (documentación oficial y ejemplos del ecosystem).
- Permite composición atómica sin esfuerzo adicional (cualquier caller puede agrupar N servicios en una transacción).
- Facilita el testing: los tests pueden verificar cambios en la sesión sin necesidad de hacer commit explícito.
- El cambio de contrato es interno; el comportamiento observable de los endpoints HTTP no cambia (siguen respondiendo igual).

**Migración del contrato (operación por servicio)**:
- `cancelar_turno` (turno_service): quitar `await db.commit()` (línea 309). El router hace commit.
- `confirmar_turno` (turno_service): quitar `await db.commit()` si lo tiene. (Verificar: ya no tenía, pero asegurar.) El router `confirmar_turno_endpoint` mantiene su `await db.commit()` y `await db.rollback()` actuales.
- `reservar_turno` (turno_service): quitar `await db.commit()` (línea 113). El router `create_turno` agrega `commit()`/`rollback()`.
- `liberar_reservas_vencidas` (turno_service): reordenar flujo (ver Decisión 5). Commit único al final por profesional, no dentro del loop.
- `marcar_turnos_completados` (turno_service): quitar `await db.commit()` (línea 276). El job del scheduler hace commit.
- `confirmar_asistencia_turno` (turno_service): quitar `await db.commit()` (línea 435). El router hace commit.
- `registrar_en_lista_espera`, `eliminar_de_lista_espera`, `notificar_y_marcar`, `aceptar_turno_lista_espera`, `rechazar_turno_lista_espera`, `procesar_timeouts_lista_espera` (lista_espera_service): quitar `await db.commit()` interno. El caller (router o scheduler) hace commit.
- `crear_o_obtener_paciente` (paciente_service): ya no commitea, mantiene su contrato actual (usa savepoint). El router hace commit.

### Decisión 2: Timezone strategy — `datetime.now(timezone.utc)` everywhere

**Elegido**: Reemplazar **todos** los `datetime.now()` por `datetime.now(timezone.utc)` en código de aplicación que compare contra `expiracion`. La columna `ReservaTemporal.expiracion` se persiste con `tzinfo=UTC` explícito (vía `datetime.now(timezone.utc)` o `datetime.now(timezone.utc).replace(tzinfo=None)` según la convención de la DB — el modelo `Turno.creado_en` ya hace `.replace(tzinfo=None)` para persistir como naive pero comparable).

**Alternativa considerada**: usar `datetime.utcnow()` (deprecado en Python 3.12). **Rechazado** — deprecation warning, y conceptualmente no es lo mismo que `datetime.now(timezone.utc)`.

**Rationale**:
- El servidor puede correr en cualquier timezone, pero las comparaciones de expiración deben ser siempre en UTC para ser correctas.
- La DB de PostgreSQL tiene su propio timezone; si guardamos naive datetimes, la comparación `naive < aware` lanza `TypeError`. Necesitamos consistencia.
- Convenir en: `expiracion` se guarda como **naive en UTC** (vía `.replace(tzinfo=None)`), y todas las comparaciones convierten a naive-UTC explícitamente (`datetime.now(timezone.utc).replace(tzinfo=None)`). Esto evita el `TypeError` y mantiene el contrato "todo en UTC".

**Lugares a modificar**:
- `reservar_turno` línea 110: `datetime.now() + timedelta(...)` → `datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(...)`
- `confirmar_turno` línea 154: `reserva.expiracion < datetime.now()` → `reserva.expiracion < datetime.now(timezone.utc).replace(tzinfo=None)`
- `liberar_reservas_vencidas` línea 206: `ReservaTemporal.expiracion < datetime.now()` → mismo cambio
- `procesar_timeouts_lista_espera` línea 344: `datetime.now() - timedelta(...)` → mismo cambio
- `notificar_y_marcar` línea 150: `datetime.now()` → mismo cambio
- `rechazar_turno_lista_espera` línea 264: `datetime.now()` → mismo cambio
- `registrar_en_lista_espera` línea 1: imports y creación (no se usa directamente en comparación, pero homogeneizar)

### Decisión 3: `SELECT FOR UPDATE` en `ReservaTemporal` en `confirmar_turno`

**Elegido**: Agregar `.with_for_update()` a la query de `ReservaTemporal` en `confirmar_turno` (turno_service.py:148-150).

**Alternativa considerada**: Mantener el SELECT sin lock y agregar retry en el caller. **Rechazado** — el lock es la solución canónica de SQL para serializar lecturas que dependen de una condición de tiempo. Es la regla dura del proyecto: "NUNCA ignorar concurrencia en reservas de turnos → usar `SELECT FOR UPDATE`".

**Rationale**:
- Cierra la race window entre SELECT y la verificación `expiracion < NOW()`.
- Consistente con el resto del código que ya usa `with_for_update()` en `Turno` (líneas 137-140, 297-298, 425-428, etc.).
- No requiere cambio de schema ni de DB (solo SQL).

**Implementación**:
```python
result = await db.execute(
    select(ReservaTemporal)
    .where(ReservaTemporal.turno_id == turno_id)
    .with_for_update()
)
reserva = result.scalar_one_or_none()
```

### Decisión 4: Manejo de `TurnoExpiradoError` en `aceptar_turno_lista_espera`

**Elegido**: Wrappear la llamada a `confirmar_turno` con un `try/except TurnoExpiradoError` que:
1. Libera el slot (`turno.estado = "DISPONIBLE"`, `turno.paciente_id = None`)
2. Elimina la `ReservaTemporal` asociada
3. Resetea el registro de lista de espera (`notificado = False`, `turno_ofrecido_id = None`, `notificado_en = None`, `creado_en = datetime.now(UTC)`)
4. Re-llama a `evaluar_lista_espera` para ofrecer al siguiente paciente
5. Propaga la excepción (o retorna None / lanza una nueva) según decisión de UX

**Alternativa considerada**: Ignorar la expiración y aceptar de todas formas. **Rechazado** — viola el contrato del dominio (la reserva expiró, el slot está libre).

**Rationale**:
- Cierra la race entre la notificación de Telegram y la aceptación del paciente.
- Mantiene la promesa de "si rechazás o no respondés a tiempo, pasa al siguiente" (RN-LE-02).
- Es consistente con el patrón de `procesar_timeouts_lista_espera` (líneas 354-398).

### Decisión 5: Reordenamiento de `liberar_reservas_vencidas`

**Elegido**: Una sola transacción por profesional con la secuencia:
1. `SELECT` de reservas vencidas (`ReservaTemporal.expiracion < NOW(UTC)`)
2. Para cada reserva: `SELECT FOR UPDATE` del `Turno`, marcar `DISPONIBLE`, `paciente_id = None`, `db.delete(reserva)`, append a `turnos_liberados`
3. **Misma transacción**: para cada `turno_liberado`, llamar a `evaluar_lista_espera` (que internamente hace `reservar_turno` y `notificar_y_marcar`, todas en la misma sesión)
4. Un solo `await db.commit()` al final

**Alternativa considerada**: Mantener el commit por turno. **Rechazado** — el antipatrón exacto del bug C-5.

**Rationale**:
- Atomicidad: si la lista de espera falla, el `liberar_reservas_vencidas` hace rollback y el slot sigue bloqueado; al próximo ciclo del scheduler (1 min) re-intenta. Esto es más conservador y más fácil de testear.
- Reduce round-trips a la DB.
- El test de integración valida: una reserva vencida + un paciente en lista → después de `liberar_reservas_vencidas`, la reserva está eliminada, el turno está `DISPONIBLE`, y existe una `ReservaTemporal` (nueva) para el paciente de lista de espera.

**Migración sutil**: `evaluar_lista_espera` actualmente llama a `reservar_turno` que **sí hace commit** (línea 113 en turno_service). Con Patrón A, `reservar_turno` ya no commitea, por lo que `evaluar_lista_espera` se ejecutará completamente dentro de la transacción del caller. Hay que **verificar que el flujo no cree una nueva `ReservaTemporal` que sobreviva si la transacción externa hace rollback** — esto es justamente el comportamiento deseado.

### Decisión 6: Extracción de `completar_turno` a servicio

**Elegido**: Crear `turno_service.completar_turno(db, profesional_id, turno_id) -> Turno` que:
1. Hace `SELECT FOR UPDATE` del turno por `id` + `profesional_id`
2. Si no existe → `TurnoNoEncontradoError`
3. Si `estado == "COMPLETADO"` → retorna el turno (idempotente)
4. Si `estado != "CONFIRMADO"` → `TurnoNoDisponibleError`
5. `turno.estado = "COMPLETADO"`, flush, return
6. **NO hace commit**

El router `completar_turno_endpoint` pasa a ser:
```python
try:
    turno = await completar_turno(db, profesional.id, turno_id)
    await db.commit()
except TurnoNoEncontradoError as exc:
    await db.rollback()
    raise HTTPException(404, exc.message)
except TurnoNoDisponibleError as exc:
    await db.rollback()
    raise HTTPException(409, exc.message)
return TurnoResponse.model_validate(turno)
```

**Rationale**:
- Consistencia con el resto de los servicios (router delgado, lógica en servicio).
- Aplica Patrón A (servicio sin commit, router con commit).
- Testeable de forma aislada sin necesidad de TestClient.

### Decisión 7: Unificar contrato de commit en `pacientes.py`

**Elegido**: Refactorizar `create_paciente` para que **siempre** llame a `crear_o_obtener_paciente` (el cual ya maneja el caso "existe por DNI" con `SELECT FOR UPDATE` + savepoint). Eliminar el `select(Paciente).where(dni=...)` duplicado del router.

```python
@router.post("", response_model=PacienteRead)
async def create_paciente(
    db: DbDep,
    profesional: CurrentProfesionalDep,
    data: PacienteCreate,
    response: Response,
) -> PacienteRead:
    existing_check = await db.execute(
        select(Paciente).where(
            Paciente.dni == data.dni,
            Paciente.profesional_id == profesional.id,
        )
    )
    if existing_check.scalar_one_or_none() is not None:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED

    try:
        paciente = await crear_o_obtener_paciente(db, profesional_id=profesional.id, data=data)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "DNI duplicado")
    return paciente
```

**Alternativa considerada**: Mantener el `select` previo en el router para evitar round-trip al servicio cuando el paciente ya existe. **Rechazado** — duplica lógica, riesgo de drift entre el SELECT del router y el del servicio.

**Rationale**:
- Una sola fuente de verdad para "existe por DNI".
- `crear_o_obtener_paciente` ya maneja el race condition con `SELECT FOR UPDATE` + savepoint.
- El router solo decide el status code y maneja errores.

### Decisión 8: Estrategia de testing — TDD estricto + tests de concurrencia

**Elegido**:
- TDD estricto en cada task: test rojo → verde → refactor.
- Para validar atomicidad: tests que inyectan mocks de `confirmar_turno` que lanzan excepciones y verifican que la DB no tiene cambios parciales.
- Para validar concurrencia: tests con `asyncio.gather` y dos sesiones distintas (`async_sessionmaker()`) ejecutando operaciones conflictivas. **Requiere el engine de PostgreSQL real** (no SQLite in-memory, que no soporta `SELECT FOR UPDATE` real).
- Para validar timezone: tests con `freezegun` o mock de `datetime.now()` que verifican comparaciones en UTC.

**Rationale**:
- El contrato de atomicidad es difícil de validar con mocks; los tests de concurrencia real son la única garantía.
- `tests/test_postgresql_infrastructure` indica que ya hay infrastructure para tests con PostgreSQL real.
- `tests/test_concurrency.py` ya existe (o debería existir) — verificar.

**Acción a tomar en la fase de apply**: Verificar que `backend/tests/test_concurrency.py` existe o crearlo. Si la infra de tests usa SQLite, agregar un guard que skipea los tests de concurrencia si el engine es SQLite.

## Risks / Trade-offs

- **R1: Tests existentes se rompen al cambiar el contrato de commit** → Mitigation: ejecutar suite completa después de cada cambio de servicio; ajustar tests que asumían commit interno (probablemente tests que verifican persistencia inmediata y no solo el resultado en memoria).

- **R2: Patrón A requiere que los routers recuerden hacer commit/rollback** → Mitigation: agregar test explícito para cada router que valide `commit()` se llama en happy path y `rollback()` se llama en cada excepción. Documentar el contrato en docstrings.

- **R3: Tests de concurrencia real son lentos y flaky** → Mitigation: usar `asyncio.gather` con `asyncpg` engine real; si flakea, agregar `await asyncio.sleep(0)` para forzar cambio de contexto. Marcar como `@pytest.mark.slow`.

- **R4: `evaluar_lista_espera` ahora se ejecuta dentro de la transacción de `liberar_reservas_vencidas`** → Mitigation: si `evaluar_lista_espera` falla (ej. error de Telegram), la transacción externa hace rollback. Esto es **deseado**: preferimos que la liberación de la reserva falle a que la reserva se libere y el paciente de lista de espera quede huérfano. Validar con test explícito.

- **R5: Reordenar `liberar_reservas_vencidas` cambia el orden de operaciones** → Mitigation: el test de integración debe verificar que después del job: (a) no hay reservas vencidas, (b) los turnos están `DISPONIBLE`, (c) los pacientes de lista de espera tienen notificaciones enviadas, todo en una sola transacción.

- **R6: 7 tests pre-existentes fallando** → Mitigation: NO son responsabilidad de este change. Documentar en el design que se asume baseline 7 failures, y el apply NO debe intentar arreglarlos. Si accidentalmente se arreglan, se acepta; si se rompen más, se investiga.

- **R7: Cambio masivo en 6 archivos de servicios** → Mitigation: aplicar cambios en orden (servicios primero, después routers, después scheduler), corriendo la suite después de cada cambio. Si la suite se rompe más allá de los 7 esperados, parar y diagnosticar.

## Migration Plan

### Fase 1 (en `apply`): Contrato de servicios
- Task 1-2: Cambiar contrato de commit en servicios (turno_service, lista_espera_service, paciente_service).
- Task 3: Adaptar routers para que hagan commit/rollback explícito.
- Task 4: Adaptar scheduler jobs.
- **Verificación**: Suite completa con baseline 7 failures conocido, no más.

### Fase 2: Atomicidad y timezone
- Task 5-6: Refactor de `reprogramar_turno` a transacción atómica + tests de atomicidad.
- Task 7: Fix timezone en todas las comparaciones.
- Task 8: `SELECT FOR UPDATE` en `ReservaTemporal`.
- **Verificación**: Tests rojos de atomicidad → verdes, tests rojos de timezone → verdes.

### Fase 3: Lista de espera y completar_turno
- Task 9: Capturar `TurnoExpiradoError` en `aceptar_turno_lista_espera`.
- Task 10: Reordenar `liberar_reservas_vencidas`.
- Task 11: Extraer `completar_turno` a servicio.
- Task 12: Unificar `pacientes.py`.
- **Verificación**: Tests de integración E2E.

### Rollback

- **No hay cambios de schema**: rollback es `git revert` del PR.
- **No hay migraciones Alembic**: no hay riesgo de datos.
- **No hay deployments especiales**: los servicios se re-deployan con el código nuevo y el scheduler se reinicia automáticamente.

## Open Questions

- **OQ-1**: ¿La `lista_espera_service.evaluar_lista_espera` debería manejar `TurnoNoDisponibleError` cuando llama a `reservar_turno`? Sí, ya lo hace (línea 319). Sin cambios.
- **OQ-2**: ¿`aceptar_turno_lista_espera` debería propagar la excepción original `TurnoExpiradoError` o lanzar una nueva `ListaEsperaOfertaExpiradaError`? **Decisión**: propagar la original; los routers la mapean a 409. No agregar nueva excepción por ahora (YAGNI).
- **OQ-3**: ¿La nueva `completar_turno` debería ser idempotente o no? **Decisión**: SÍ, idempotente — si ya está `COMPLETADO`, retorna el turno sin error (igual que el endpoint actual línea 159-160). Mantener el contrato observable.
- **OQ-4**: ¿El scheduler `liberar_reservas_vencidas` debe tener su propio try/except por profesional o uno global? **Decisión**: por profesional (como está actualmente, líneas 47-50), pero ahora el commit es al final del bloque `try` (no por reserva individual).
- **OQ-5**: ¿Vale la pena agregar un test de concurrencia con `asyncpg` real en este change o se difiere? **Decisión**: incluir al menos UN test de concurrencia real con `asyncio.gather` y dos sesiones, para validar `SELECT FOR UPDATE`. El resto se difiere a un change futuro de "concurrency-hardening" si hace falta.
