## 1. Migración y Modelo — `google_event_id`

- [x] 1.1 Crear migración Alembic para agregar columna `google_event_id VARCHAR(255), nullable=True` a tabla `turno`
- [x] 1.2 Agregar campo `google_event_id: Mapped[Optional[str]]` al modelo SQLAlchemy `Turno` con índice `ix_turno_google_event_id`
- [x] 1.3 Actualizar `TurnoResponse` schema para incluir `google_event_id: Optional[str] = None`
- [x] 1.4 Escribir test de modelo: verificar que `Turno` acepta y persiste `google_event_id`
- [x] 1.5 Ejecutar `alembic upgrade head` y verificar que la columna existe en SQLite de tests

## 2. Servicio — Persistencia en Confirmación

- [x] 2.1 Modificar `confirmar_turno()` en `turno_service.py` para capturar el retorno de `CalendarService.create_event()`
- [x] 2.2 Asignar `turno.google_event_id = event_id` y hacer `await db.commit()` tras crear el evento en calendar
- [x] 2.3 Escribir test TDD: `confirmar_turno` con mock de `CalendarService.create_event` retornando `"event_123"` verifica que `google_event_id` queda en DB
- [x] 2.4 Escribir test TDD: si `create_event` falla, el turno sigue `CONFIRMADO` y `google_event_id` es `NULL`

## 3. Servicio — Lectura en Cancelación

- [x] 3.1 Modificar `cancelar_turno()` en `turno_service.py` para leer `turno.google_event_id` directamente en lugar de `getattr(turno, "google_event_id", None)`
- [x] 3.2 Escribir test TDD: cancelar turno con `google_event_id = "event_456"` en DB invoca `CalendarService.delete_event("event_456")`
- [x] 3.3 Escribir test TDD: cancelar turno con `google_event_id = NULL` no invoca `delete_event`
- [x] 3.4 Verificar que tests existentes de cancelación siguen pasando (regresión)

## 4. Servicio — Propagación en Reprogramación

- [x] 4.1 Verificar que `reprogramar_turno()` lee `google_event_id` viejo de DB vía `cancelar_turno()` y persiste el nuevo vía `confirmar_turno()`
- [x] 4.2 Escribir test TDD: reprogramar turno con `google_event_id = "event_old"` en DB invoca `delete_event("event_old")` y el nuevo turno tiene `google_event_id` del mock
- [x] 4.3 Escribir test TDD: reprogramar turno cuyo `google_event_id` es `NULL` no invoca `delete_event`
- [x] 4.4 Verificar que tests existentes de reprogramación siguen pasando (regresión)

## 5. Transición a Estado `COMPLETADO`

- [x] 5.1 Implementar `marcar_turnos_completados(db)` en `turno_service.py`
  - Query: turnos `CONFIRMADO` donde `fecha + hora_fin < NOW()`
  - Usar `SELECT FOR UPDATE` para evitar race conditions
  - Actualizar a `COMPLETADO`, retornar cantidad
- [x] 5.2 Escribir test TDD: turno `CONFIRMADO` pasado se marca `COMPLETADO`
- [x] 5.3 Escribir test TDD: turno `CONFIRMADO` futuro no se modifica
- [x] 5.4 Escribir test TDD: turno `CANCELADO` pasado no se modifica
- [x] 5.5 Implementar endpoint `PUT /turnos/{id}/completar` en `turnos.py` con `response_model=TurnoResponse`
- [x] 5.6 Escribir test TDD: endpoint completar turno `CONFIRMADO` → 200 + `COMPLETADO`
- [x] 5.7 Escribir test TDD: endpoint completar turno inexistente → 404
- [x] 5.8 Escribir test TDD: endpoint completar turno `CANCELADO` → 409
- [x] 5.9 Escribir test TDD: endpoint completar turno ya `COMPLETADO` → 200 idempotente
- [x] 5.10 Registrar job `marcar_turnos_completados` en `scheduler/jobs.py` con intervalo configurable (default 5 minutos)
- [x] 5.11 Escribir test TDD: scheduler ejecuta `marcar_turnos_completados` sin errores y loguea excepciones

## 6. Flujo de Reprogramación en Telegram

- [x] 6.1 Implementar estados conversacionales en `telegram_service.py`: `reprogramando_esperando_fecha`, `reprogramando_esperando_hora`
- [x] 6.2 Implementar `accion_iniciar_reprogramacion(db, chat_id, turno_id)` que guarda `turno_id` en estado y muestra fechas disponibles
- [x] 6.3 Implementar manejo de callback `reprogramar:<turno_id>` en `procesar_mensaje`
- [x] 6.4 Implementar selección de fecha en estado `reprogramando_esperando_fecha` → muestra horarios
- [x] 6.5 Implementar selección de hora en estado `reprogramando_esperando_hora` → llama `reprogramar_turno()` y envía confirmación
- [x] 6.6 Implementar manejo de errores: slot no disponible (ofrecer otra fecha), turno cancelado (limpiar estado), calendar falla (notificar pero confirmar reprogramación)
- [x] 6.7 Implementar botón "Cancelar" en flujo de reprogramación que limpia estado
- [x] 6.8 Escribir test TDD: callback `reprogramar:123` inicia flujo y cambia estado
- [x] 6.9 Escribir test TDD: selección de fecha en reprogramación muestra horarios
- [x] 6.10 Escribir test TDD: selección de horario exitoso llama `reprogramar_turno` y envía confirmación
- [x] 6.11 Escribir test TDD: selección de horario no disponible notifica error y permite reintentar
- [x] 6.12 Escribir test TDD: cancelación del flujo de reprogramación limpia estado

## 7. Tests de Integración y Regresión

- [x] 7.1 Ejecutar suite completa de `test_turno_service.py` — verificar que todos pasan
- [x] 7.2 Ejecutar suite completa de `test_telegram_conversation.py` — verificar que todos pasan
- [x] 7.3 Ejecutar suite completa de `test_telegram_e2e.py` — verificar que todos pasan
- [x] 7.4 Ejecutar `pytest --cov` y verificar cobertura de nuevos caminos > 90%
- [x] 7.5 Verificar que no hay `getattr` con `google_event_id` en ningún archivo del backend
- [x] 7.6 Verificar type hints estrictos en funciones modificadas
- [x] 7.7 Verificar `response_model` en endpoint nuevo (`/completar`)

## 8. Documentación y Cierre

- [x] 8.1 Actualizar docstrings de `confirmar_turno`, `cancelar_turno`, `reprogramar_turno` explicando manejo de `google_event_id`
- [x] 8.2 Actualizar docstring de `marcar_turnos_completados`
- [x] 8.3 Actualizar `CHANGES.md` para agregar C-13 en el árbol de dependencias
- [x] 8.4 Ejecutar `pytest` completo y reportar resultados
