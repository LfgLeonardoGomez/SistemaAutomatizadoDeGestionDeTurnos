## 1. Modelo y Migración

- [x] 1.1 Crear Alembic migration para agregar `turno_ofrecido_id` (FK nullable a `turno.id`) e `notificado_en` (TIMESTAMP nullable) a `lista_de_espera`.
- [x] 1.2 Actualizar `backend/app/models/lista_de_espera.py` con los nuevos campos (`turno_ofrecido_id`, `notificado_en`).
- [x] 1.3 Ejecutar migration y verificar schema en PostgreSQL.

## 2. Configuración

- [x] 2.1 Agregar `lista_espera_minutos: int = 5` a `backend/app/config.py` (Pydantic Settings).
- [x] 2.2 Agregar `LISTA_ESPERA_MINUTOS` a `.env.example`.
- [x] 2.3 Verificar que `Settings` carga correctamente la nueva variable.

## 3. Servicio de Lista de Espera (TDD)

- [x] 3.1 Escribir tests en `backend/tests/test_lista_espera_service.py` (vacíos/fallando) para:
  - `registrar_en_lista_espera`
  - `eliminar_de_lista_espera`
  - `obtener_siguiente_paciente_fifo` (valida orden `creado_en`)
  - `notificar_y_marcar` (valida `SELECT FOR UPDATE`)
  - `aceptar_turno_lista_espera`
  - `rechazar_turno_lista_espera`
  - `procesar_timeouts` (valida reset y re-evaluación)
- [x] 3.2 Implementar `backend/app/services/lista_espera_service.py` con type hints estrictos en todas las funciones públicas.
- [x] 3.3 Implementar `obtener_siguiente_paciente_fifo` usando `SELECT FOR UPDATE` sobre `ListaDeEspera` filtrando por fecha y `notificado=FALSE`.
- [x] 3.4 Implementar `notificar_y_marcar` que actualiza atómicamente `turno_ofrecido_id`, `notificado=TRUE`, `notificado_en`, y delega envío Telegram.
- [x] 3.5 Implementar `aceptar_turno_lista_espera` que reutiliza `confirmar_turno` de `turno_service` y elimina el registro de `ListaDeEspera`.
- [x] 3.6 Implementar `rechazar_turno_lista_espera` que resetea `notificado=FALSE`, `turno_ofrecido_id=NULL`, `notificado_en=NULL`, y re-evalúa la cola.
- [x] 3.7 Hacer pasar todos los tests del servicio (green).

## 4. Hook Post-Cancelación y Post-Expiración

- [x] 4.1 Escribir test en `backend/tests/test_turno_service.py` (fallando) que verifique que `cancelar_turno` dispara `evaluar_lista_espera`.
- [x] 4.2 Implementar `evaluar_lista_espera(fecha, db)` en `lista_espera_service.py`.
- [x] 4.3 Modificar `cancelar_turno` en `backend/app/services/turno_service.py` para llamar a `evaluar_lista_espera` después del `COMMIT` de cancelación (antes de retornar).
- [x] 4.4 Modificar `liberar_reservas_vencidas` en `backend/app/services/turno_service.py` para llamar a `evaluar_lista_espera` por cada turno liberado (después del commit).
- [x] 4.5 Hacer pasar los tests de hook.

## 5. Endpoints REST

- [x] 5.1 Crear `backend/app/api/lista_espera.py` con:
  - `POST /lista-espera` → `response_model` definido, type hints estrictos.
  - `DELETE /lista-espera/{id}` → retorna 204.
- [x] 5.2 Escribir tests en `backend/tests/test_lista_espera_api.py` (TDD: red → green).
- [x] 5.3 Registrar router en `backend/app/main.py`.
- [x] 5.4 Hacer pasar todos los tests de API.

## 6. Integración Telegram

- [x] 6.1 Implementar `format_lista_espera_keyboard(turno_id)` en `telegram_service.py` con botones Aceptar/Rechazar.
- [x] 6.2 Implementar `format_lista_espera_mensaje(turno)` con MarkdownV2 escape.
- [x] 6.3 Implementar `enviar_notificacion_lista_espera(chat_id, turno)` en `telegram_service.py`.
- [x] 6.4 Implementar `accion_aceptar_lista_espera(db, chat_id, turno_id)` y `accion_rechazar_lista_espera(db, chat_id, turno_id)` en `telegram_service.py`.
- [x] 6.5 Extender `procesar_mensaje` en `telegram_service.py` para enrutar callbacks `lista_espera:aceptar:<id>` y `lista_espera:rechazar:<id>`.
- [x] 6.6 Escribir tests en `backend/tests/test_telegram_service.py` para mensajes de lista de espera y callbacks.
- [x] 6.7 Hacer pasar tests de Telegram.

## 7. Scheduler Timeout

- [x] 7.1 Implementar `procesar_timeouts_lista_espera(db)` en `lista_espera_service.py` que:
  - Busca registros con `notificado=TRUE` y `notificado_en < NOW() - LISTA_ESPERA_MINUTOS`.
  - Usa `SELECT FOR UPDATE` por registro.
  - Resetea y re-evalúa cola para la fecha.
- [x] 7.2 Implementar `_procesar_timeouts_lista_espera_job` en `backend/app/scheduler/jobs.py` (AsyncIOScheduler compatible).
- [x] 7.3 Registrar job en `init_scheduler` con intervalo configurable (default 1 minuto).
- [x] 7.4 Escribir tests para el job de timeout (mock del scheduler o ejecución directa).
- [x] 7.5 Hacer pasar tests de scheduler.

## 8. Tests de Integración y Concurrency

- [x] 8.1 Escribir test de integración E2E: cancelar turno → notificación Telegram (mock) → aceptar → turno confirmado → registro eliminado de lista.
- [x] 8.2 Escribir test de race condition: dos cancelaciones simultáneas para la misma fecha con un solo paciente en lista → solo una notificación.
- [x] 8.3 Escribir test de timeout: notificar → esperar vencimiento → job timeout → siguiente paciente notificado.
- [x] 8.4 Verificar coverage mínimo 80% para `lista_espera_service.py`.

## 9. Documentación y Cierre

- [x] 9.1 Actualizar `CHANGES.md` marcando C-11 como completado.
- [x] 9.2 Verificar que todos los endpoints tienen `response_model`.
- [x] 9.3 Verificar que ninguna función pública carece de type hints.
- [x] 9.4 Ejecutar `pytest` completo y confirmar que no hay regresiones.
