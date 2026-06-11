## 1. Domain & Exceptions

- [ ] 1.1 Agregar `TurnoNoEncontradoError` y `TurnoYaCanceladoError` a `backend/app/exceptions.py`
- [ ] 1.2 Agregar handlers en `backend/app/exception_handlers.py` para mapear nuevas excepciones a HTTP 404 y 409
- [ ] 1.3 Escribir tests para los nuevos handlers (404, 409)

## 2. Service Layer — Cancelación

- [ ] 2.1 Implementar `cancelar_turno(db, turno_id)` en `backend/app/services/turno_service.py`
  - Bloquear fila con `SELECT FOR UPDATE`
  - Validar existencia (404 → `TurnoNoEncontradoError`)
  - Validar estado `CONFIRMADO` (409 → `TurnoYaCanceladoError` si ya está `CANCELADO`)
  - Actualizar a `CANCELADO`, `COMMIT`
  - Invocar `CalendarService.delete_event` via `run_in_threadpool` con try/except
  - Retornar turno actualizado
- [ ] 2.2 Escribir tests de servicio para cancelación exitosa (estado `CANCELADO`, calendar delete mock)
- [ ] 2.3 Escribir tests de servicio para cancelación de turno no existente (404)
- [ ] 2.4 Escribir tests de servicio para cancelación de turno ya cancelado (409)
- [ ] 2.5 Escribir tests de servicio para cancelación con fallo de Google Calendar (graceful, log error)

## 3. Service Layer — Reprogramación

- [ ] 3.1 Implementar `reprogramar_turno(db, turno_id, nueva_fecha, nueva_hora_inicio)` en `backend/app/services/turno_service.py`
  - Validar turno existente y `CONFIRMADO`
  - Cancelar turno anterior (reutilizar lógica de cancelación)
  - Crear nuevo turno con `reservar_turno` + `confirmar_turno` (reutilizar de C-06)
  - Manejar RN-TU-01 (paciente sin otro turno activo, excluyendo el que se cancela)
  - Retornar nuevo turno `CONFIRMADO`
- [ ] 3.2 Escribir tests de servicio para reprogramación exitosa (turno anterior `CANCELADO`, nuevo `CONFIRMADO`, calendar create/delete mock)
- [ ] 3.3 Escribir tests de servicio para reprogramación con slot no disponible (409)
- [ ] 3.4 Escribir tests de servicio para reprogramación con paciente que tiene otro turno activo (409, RN-TU-01)
- [ ] 3.5 Escribir tests de servicio para reprogramación con fallo de creación de evento en Google Calendar (graceful)

## 4. Router Layer

- [ ] 4.1 Agregar `CancelarTurnoResponse` / `ReprogramarTurnoRequest` / `ReprogramarTurnoResponse` en `backend/app/schemas/turno.py`
- [ ] 4.2 Implementar `PUT /turnos/{turno_id}/cancelar` en `backend/app/routers/turnos.py` con `response_model=TurnoResponse`
- [ ] 4.3 Implementar `PUT /turnos/{turno_id}/reprogramar` en `backend/app/routers/turnos.py` con `response_model=TurnoResponse`
- [ ] 4.4 Escribir tests de router para cancelación exitosa (200, estado `CANCELADO`)
- [ ] 4.5 Escribir tests de router para cancelación 404 y 409
- [ ] 4.6 Escribir tests de router para reprogramación exitosa (200)
- [ ] 4.7 Escribir tests de router para reprogramación 404, 409 slot no disponible, 409 paciente con turno activo

## 5. Integration & QA

- [ ] 5.1 Ejecutar `pytest` completo y verificar que todos los tests pasan (meta: > 150 tests)
- [ ] 5.2 Verificar coverage de cancelación y reprogramación en `pytest --cov`
- [ ] 5.3 Validar que no se rompieron tests de C-06 (regresión)
- [ ] 5.4 Revisar type hints y `response_model` en todos los endpoints nuevos
- [ ] 5.5 Revisar que no hay código bloqueante sin `run_in_threadpool` en servicios

## 6. Documentation

- [ ] 6.1 Actualizar `CHANGES.md` marcar `[x]` en C-07 (al archivar, no ahora)
- [ ] 6.2 Agregar docstrings a `cancelar_turno` y `reprogramar_turno` en `turno_service.py`
