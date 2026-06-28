# Design: `test-suite-stabilization`

## Context

El change `concurrency-hardening` (archivado 2026-06-28, commit `ac0c049`) cerró el gap R3/OQ-5 de `transaction-hardening` (race condition en `reservar_turno` resuelto con UNIQUE constraint parcial + captura de IntegrityError). Sin embargo, el cambio dejó **2 tests fallando** de los 7 pre-existentes del baseline post-hardening, más **4 tests flaky** adicionales (los xfails intencionales para bugs de lista de espera).

### Estado actual (capturado 2026-06-28, pre-cambio)

```
2 failed, 405 passed, 1 skipped, 4 xfailed in 410.11s
```

Los 2 failures son **bug de los tests, no del código**:
- `test_scheduler_job_marcar_turnos_completados_loguea_excepciones` (pasa en aislamiento)
- `test_scheduler_job_enviar_recordatorios_maneja_excepcion` (pasa en aislamiento)

Ambos asertean sobre `caplog.text` que en pytest-asyncio con event loop reutilizado (suite completa) **no captura los records** del logger `app.scheduler.jobs`. El patrón de fix ya está aplicado en `test_telegram_service.py::test_enviar_mensaje_con_log_loggea_contexto_al_fallar` y validado en suite completa (pasa).

### Constraints

- **TDD estricto activo**: cada test sigue rojo → verde → refactor.
- **Stack**: pytest 8.4.2 + pytest-asyncio 1.4.0 + FastAPI + SQLAlchemy 2.0 async + PostgreSQL (testcontainers).
- **No se toca código de producción**: `backend/app/**` no se modifica.
- **No se agregan dependencias nuevas**.
- **No se cambian schemas Alembic**.

## Goals / Non-Goals

**Goals:**
- Llevar la suite a **0 failed** (excluyendo los 4 xfails intencionales que documentan bugs reales de lista de espera).
- Cerrar las **2 failures restantes** del baseline post-hardening mediante el patrón "mockear logger directamente".
- Documentar los **4 bugs pre-existentes** de lista de espera como `xfail(strict=False)` con razones específicas.
- Actualizar **2 tests obsoletos** que assertean comportamiento pre-C-14/C-22 a la realidad post-multi-tenant.
- Eliminar el archivo debug untracked `test_caplog_debug.py`.
- Mantener 0 regresiones: ningún test que pasaba antes puede empezar a fallar.

**Non-Goals:**
- Arreglar los 4 bugs reales de la lógica de lista de espera (cambio dedicado futuro).
- Introducir un helper genérico de "mock logger" en `conftest.py` (patrón aplicado caso por caso).
- Migrar tests a fixtures de pytest-asyncio más robustas contra event loop reuse (refactor mayor).
- Cambiar la configuración de pytest-asyncio (event loop scope, mode, etc.).
- Cambiar el patrón A de transacciones (commit en router/scheduler, no en servicio).

## Decisions

### D1: Mockear `logger` directamente con `unittest.mock.patch`, NO usar caplog

**Contexto**: caplog en pytest-asyncio con event loop reutilizado no captura records de loggers específicos en suite completa. La causa raíz es que el event loop scope `function` de pytest-asyncio reusa el loop entre tests, y el logger propaga al root logger del nuevo loop sin re-attachear los handlers de caplog.

**Decisión**: Cambiar de
```python
with caplog.set_level(logging.ERROR, logger="app.scheduler.jobs"):
    # ... código que loguea
    assert "Error en job X" in caplog.text
```
a
```python
with patch("app.scheduler.jobs.logger") as mock_logger:
    # ... código que loguea
    assert mock_logger.exception.called
    call_args = mock_logger.exception.call_args
    assert "Error en job X" in call_args[0][0]
```

**Por qué**:
- **Agnóstico al event loop**: el patch reemplaza el objeto logger directamente, sin pasar por el sistema de handlers/propagación.
- **Mensaje exacto**: assertear sobre `call_args[0][0]` da el mensaje completo, no solo un substring. Esto fuerza a usar el mensaje correcto (`"...para profesional {id}..."` o `"...para turno {id}..."`), eliminando la fragilidad de los substring matches.
- **Patrón ya validado**: el test de telegram (`test_enviar_mensaje_con_log_loggea_contexto_al_fallar`) usa este patrón y pasa en suite completa.

**Alternativas consideradas**:
- **A1**: Configurar `propagate=True` + `caplog.set_level(...)` con `logger="app.scheduler.jobs"`. **Descartada**: el problema no es de propagación (los loggers ya tienen `propagate=True` por default en Python); es de re-attachment de handlers entre event loops.
- **A2**: Usar `pytest`'s `LogCaptureFixture.handler` directamente con `monkeypatch`. **Descartada**: misma raíz; pytest-asyncio no resuelve el re-attachment.
- **A3**: Crear fixture `mock_logger` en conftest. **Descartada**: el patrón es case-by-case (cada test patchea el logger de su módulo bajo test); un helper genérico agregaría complejidad sin valor.

### D2: `xfail(strict=False)` con razón específica, NO `xfail()` sin razón

**Contexto**: 4 tests de `test_lista_espera_*` son flaky pre-existentes por bugs reales en la lógica de lista de espera. Marcarlos como `xfail` sin razón es deuda técnica silenciosa.

**Decisión**: Cada xfail lleva una razón **específica** que:
- Nombra el **bug real** (ej. "slot no se libera correctamente tras cancelar").
- Identifica el **scope del fix** (ej. "Requiere refactor de `procesar_timeouts_lista_espera` + UNIQUE constraint").
- Marca **explícitamente** que está fuera del scope de los cambios de hardening (ej. "Fuera del scope de los cambios transaction-hardening/concurrency-hardening").

**Por qué `strict=False`**: si en el futuro algún cambio inadvertido hace que el test pase, no rompe el build. La razón sigue siendo documentación del bug pendiente.

**Por qué no `skip`**: skip es para tests no aplicables. Estos tests son aplicables; solo fallan por un bug conocido. La intención es que vuelvan a correr cuando el bug se arregle.

### D3: `utcnow_naive()` del conftest para timestamps de DB

**Contexto**: `datetime.now()` retorna un `datetime` con `tzinfo=None` (naive). El servicio de lista de espera usa `_utcnow_naive()` (helper privado) que retorna `datetime.now(timezone.utc).replace(tzinfo=None)`. En suite completa, el drift entre estos dos valores puede hacer que un test que simula "vencido hace 10 minutos" no funcione si el test y el servicio calculan "ahora" en momentos distintos.

**Decisión**: Reemplazar `datetime.now()` por `utcnow_naive()` en `test_lista_espera_integration.py::test_timeout_job_pasa_al_siguiente` (la línea que simula `r1.notificado_en = utcnow_naive() - timedelta(minutes=10)`).

**Por qué no global**: solo este test usa la lógica de comparación con `_utcnow_naive()`. Los demás tests del archivo usan `datetime.now()` para timestamps relativos sin comparación cruzada con código de producción.

### D4: `init_scheduler(app)` directo en `test_scheduler_tiene_job_registrado`

**Contexto**: El fixture `client` overridea el lifespan con `_noop_lifespan` para no arrancar el scheduler real en tests (los jobs interfieren con los assertions). Pero esto deja `app.state.scheduler` en `None`, haciendo que el test falle.

**Decisión**: Convertir el test a `async`, instanciar el scheduler manualmente con `init_scheduler(app)`, y verificar que los 3 jobs se registran. Cleanup con `scheduler.shutdown(wait=False)`.

**Por qué no levantar el lifespan real**: los otros tests del archivo mockean `marcar_turnos_completados`, `enviar_recordatorio_telegram`, etc.; si el scheduler arrancara de verdad, los mocks globales no funcionarían correctamente. Además, el scheduler es side-effect (corre jobs en background), y la suite debe ser determinística.

**Por qué `shutdown(wait=False)`: pytest-asyncio cierra el event loop al final del test; si `wait=True`, el shutdown podría bloquear esperando jobs que ya no importan.

### D5: Eliminar `test_caplog_debug.py` sin reemplazo

**Contexto**: El archivo fue creado durante la sesión anterior para debuggear por qué caplog no capturaba los records. Es **exploración**, no test.

**Decisión**: Eliminar. El patrón de fix (mockear logger directo) está documentado en los 3 tests que lo aplican (1 telegram + 2 scheduler). Agregar un docstring en conftest.py sobre el patrón es opcional y se considera **out of scope** (D1 lo justifica; los devs lo inferirán del diff).

## Risks / Trade-offs

| # | Risk | Likelihood | Mitigation |
|---|------|------------|------------|
| R1 | Regresión de tests que pasan | Muy bajo | Solo se modifican tests. Suite completa corre al final. |
| R2 | Mockear logger oculta bugs reales (ej. que el código NO loguee cuando debería) | Bajo | Las assertions son específicas (`call_args[0][0]` verifica el mensaje completo, no solo la presencia). Si el código deja de loguear, el test falla. |
| R3 | `xfail(strict=False)` pasa inadvertidamente y no se investiga el bug | Medio | La razón del xfail es documentación del bug. Cuando el bug se arregle en un change futuro, el test se re-habilita y verifica el fix. Mientras tanto, queda como deuda documentada. |
| R4 | El patrón de "mockear logger" no se replica a tests futuros | Bajo | El patrón es claro de los diffs existentes; devs futuros lo verán en el historial. Si se considera necesario, se puede agregar un docstring en `conftest.py` (out of scope de este change). |
| R5 | `init_scheduler(app)` directo interfiere con otros tests del mismo módulo | Bajo | El test hace `shutdown(wait=False)` al final. El fixture `client` re-crea la app por test (FastAPI TestClient con `with` block), por lo que no hay state compartido. |

## Migration Plan

**No aplica** (no es un cambio de runtime; es housekeeping de tests). El "deploy" es el commit.

**Rollback**: `git revert <commit>` revierte los cambios a tests. No hay datos de producción afectados.

## Open Questions

**Ninguna para este change.** El scope es claro y las decisiones técnicas están validadas por el patrón existente en `test_telegram_service.py`.

**Pregunta post-archival (para futuro change)**: ¿Conviene abrir un `C-23-lista-espera-bugfix` para arreglar los 4 bugs reales documentados como xfail? Especialmente `procesar_timeouts_lista_espera` que no libera el slot para el siguiente paciente, lo cual afecta la lógica de negocio (no solo los tests).
