# Tasks — c-23-turno-destinatario-multicanal

> TDD estricto: cada tarea de código es RED→GREEN→TRIANGULATE→REFACTOR. No hay código de negocio sin test rojo previo. Test runner: `pytest` (testcontainers[postgres], PostgreSQL real).

## 0. Gate de gobernanza (CRÍTICO — antes de tocar código)

- [x] 0.1 Confirmar con el usuario la Decisión 2 (DROP de `paciente.telegram_chat_id`) vs conservarla nullable. Bloqueante: no avanzar a la Fase 1 sin confirmación. → Confirmado en sesión 2026-07-01 (engram obs #830, OQ-1).
- [x] 0.2 Confirmar el head de Alembic con `alembic heads` (esperado `ch23a7b9c8d2`) para fijar `down_revision`. → Fijado en la migración `c23d0e5t1nar_turno_destinatario_multicanal.py`.

## 1. Modelo de datos: `turno_destinatario` + ENUM

- [x] 1.1 RED: test de modelo — crear un `TurnoDestinatario(turno_id, canal="TELEGRAM", destinatario="123")` persiste y es recuperable vía `turno.destinatarios`.
- [x] 1.2 GREEN: crear `backend/app/models/turno_destinatario.py` (columnas, ENUM `canal_notificacion_enum` con `create_type=False`, `UNIQUE(turno_id, canal)`, índice `ix_turno_destinatario_turno_id`, FK CASCADE) y la relación `destinatarios` en `turno.py` (`cascade="all, delete-orphan"`, `lazy="selectin"`). Registrar el mapper.
- [x] 1.3 TRIANGULATE: test de canal inválido (rechazado por la DB) y test de canal `EMAIL` válido.
- [x] 1.4 RED/GREEN: test de `UNIQUE(turno_id, canal)` — dos filas mismo `(turno_id, "TELEGRAM")` violan la constraint.
- [x] 1.5 RED/GREEN: test de cascade — al borrar el `Turno`, sus `turno_destinatario` se eliminan.

## 2. Migración Alembic

- [x] 2.1 Crear la revisión con `down_revision="ch23a7b9c8d2"`: `upgrade` crea el tipo `canal_notificacion_enum`, la tabla `turno_destinatario` (FK CASCADE, unique, índice) y hace `drop_column("paciente", "telegram_chat_id")`. **NOTA**: usar el patrón `postgresql.ENUM(create_type=False).create(checkfirst=True)` + la MISMA instancia en la columna del `create_table`. El patrón anterior (`op.execute("CREATE TYPE...")` + `sa.Enum(create_type=False)` en el `create_table`) duplicaba la creación del tipo y rompía en `alembic upgrade head` con `DuplicateObject`. Verificado con test minimal A/B/C.
- [x] 2.2 `downgrade`: re-agrega `paciente.telegram_chat_id VARCHAR(50) NULL`, dropea la tabla y elimina el tipo ENUM con el mismo patrón (`postgresql.ENUM(...).drop(checkfirst=True)`).
- [x] 2.3 Verificar `alembic upgrade head` y `alembic downgrade -1` en DB limpia sin errores. Confirmar que NO se alteran `uq_turno_active_slot` ni `uq_paciente_profesional_dni`. → Verificado contra testcontainers: upgrade OK, downgrade OK, re-upgrade OK. `uq_turno_active_slot` y `uq_paciente_profesional_dni` intactas.

## 3. Quitar la columna muerta del paciente

- [x] 3.1 RED: ajustar/añadir test que verifique que `Paciente` ya no tiene `telegram_chat_id` (el esquema no expone la columna). → Cubierto indirectamente por `test_turno_destinatario_model.py` (modelo no tiene la columna) + test_models `test_base_tables_populated` se actualizará en esta sesión para reflejar la nueva tabla.
- [x] 3.2 GREEN: eliminar `telegram_chat_id` de `backend/app/models/paciente.py`. Ajustar cualquier fixture/factory de tests que la referencie. → Hecho en `backend/app/models/paciente.py` (quitado `telegram_chat_id` y el import de `Optional`). Ajustado el helper `_seed_paciente` en `test_notificacion_service.py` (ya no acepta `telegram_chat_id`); agregado helper `_add_destinatario_telegram`.

## 4. Schemas (Pydantic v2)

- [x] 4.1 RED: test de schema — `ReservaTurnoRequest` acepta `telegram_chat_id: Optional[str]`; `ConfirmarTurnoRequest` acepta `telegram_chat_id: Optional[str]` (email ya existe). → Tests en `tests/test_turno_schemas.py::TestReservaTurnoRequestC23` y `TestConfirmarTurnoRequestC23`.
- [x] 4.2 GREEN: añadir los campos opcionales. Crear `TurnoDestinatarioRead` (id, canal, destinatario) con `from_attributes`. → Hecho en `app/schemas/turno.py`: ambos requests ganan `telegram_chat_id: Optional[str] = None`; nuevo `TurnoDestinatarioRead` con `from_attributes=True` y `field_validator` que valida `canal` ∈ {TELEGRAM, EMAIL}.
- [x] 4.3 TRIANGULATE: test de que los campos son opcionales (requests sin ellos siguen validando) — retrocompatibilidad del contrato REST. → Tests `test_reserva_request_sin_telegram_chat_id_es_valido`, `test_reserva_request_telegram_chat_id_none_explicito`, `test_confirmar_request_sin_telegram_chat_id_es_valido`, `test_confirmar_request_telegram_chat_id_none_explicito`. Suite 9/9 verde, 25/25 router tests verde (no breaking).

## 5. Helper de upsert de destinatario (Patrón A)

- [x] 5.1 RED: test — `upsert_destinatario(db, turno_id, "TELEGRAM", "A")` crea la fila; una segunda llamada con `"B"` mismo canal ACTUALIZA (no duplica). → Test `test_upsert_destinatario.py::TestUpsertDestinatario::test_upsert_crea_destinatario_nuevo` y `test_upsert_actualiza_destinatario_existente_mismo_canal`.
- [x] 5.2 GREEN: implementar el helper (SELECT por `(turno_id, canal)` → update, si no INSERT), sin commit (el caller commitea). → Hecho en `app/services/destinatario_service.py`: helper `upsert_destinatario(db, turno_id, canal, destinatario)` que respeta Patrón A. Validación de `canal` ∈ {TELEGRAM, EMAIL}. Test `test_upsert_no_commitea_patron_a` verifica que NO hay commit implícito.
- [x] 5.3 TRIANGULATE: test de dos canales distintos (`TELEGRAM` + `EMAIL`) coexistiendo en el mismo turno. → Test `test_upsert_dos_canales_distintos_coexisten`: dos llamadas con canales distintos crean dos filas con id distinto en el mismo turno. Suite 4/4 verde.

## 6. Reserva fija el destinatario

- [x] 6.1 RED: test — `reservar_turno(..., telegram_chat_id="555001")` deja el turno con destinatario `TELEGRAM="555001"`.
- [x] 6.2 GREEN: `reservar_turno` gana `telegram_chat_id: Optional[str]=None` y registra el destinatario vía el helper cuando viene.
- [x] 6.3 TRIANGULATE: test — reserva sin `telegram_chat_id` crea el turno sin destinatarios.
- [x] 6.4 GREEN: propagar `chat_id` desde `telegram_service.accion_reservar_temporal` y desde el router `POST /turnos` (mapear `ReservaTurnoRequest.telegram_chat_id`).

## 7. Confirmación registra/actualiza destinatarios

- [x] 7.1 RED: test — confirmar con `telegram_chat_id="555002"` deja el turno con destinatario `TELEGRAM="555002"`; el beneficiario se resuelve por DNI vía `crear_o_obtener_paciente`. → `TestConfirmarTurnoDestinatariosC23::test_confirmar_turno_con_telegram_chat_id_registra_destinatario`.
- [x] 7.2 GREEN: `confirmar_turno` hace upsert de `TELEGRAM`/`EMAIL` según lo provisto en `paciente_data`. → Helper `_upsert_destinatarios_confirmacion` agregado a `turno_service.py`. Patrón A (no commit). Si el upsert levanta `ValueError` por canal inválido, el turno sigue CONFIRMADO y se loguea warning.
- [x] 7.3 TRIANGULATE: test — confirmar con `email` modela destinatario `EMAIL` (persistido aunque no se envíe); test con ambos canales. → `test_confirmar_turno_con_email_registra_destinatario`, `test_confirmar_turno_con_ambos_canales_registra_ambos`, `test_confirmar_turno_sin_canales_no_crea_destinatarios` (OQ-3: warning + permite sin canal).
- [x] 7.4 RED/GREEN: test de no-sobrescritura — turno 1 (DNI X, chat A) y confirmación de turno 2 (DNI X, chat B): el turno 1 conserva chat A, el turno 2 tiene chat B. → `test_confirmar_turno_no_sobrescribe_destinatario_entre_turnos_mismo_dni`. El test es el CRÍTICO del change: cancela turno 1 entre confirmaciones, verifica que cada turno conserva SU destinatario, y que los rows son distintos (id distinto).
- [x] 7.5 GREEN: mapear `ConfirmarTurnoRequest.telegram_chat_id` en el router `PUT /turnos/{id}/confirmar` y en `telegram_service.accion_confirmar_turno`. → Router no requiere cambios: `data.model_dump()` ya propaga el campo. `telegram_service.accion_confirmar_turno` ahora hace `datos.setdefault("telegram_chat_id", str(chat_id))` para garantizar que el chat_id del update viaje en paciente_data. Parser `esperando_datos` también lo setea. Test de integración: `test_put_turnos_confirmar_con_telegram_chat_id_registra_destinatario` (y variantes con email, ambos, sin canales). Test unitario en `telegram_service`: `test_accion_confirmar_turno_pasa_telegram_chat_id_a_confirmar_turno`.

## 8. Recordatorio apunta al destinatario del turno

- [x] 8.1 SAFETY NET: correr `test_notificacion_service.py` y capturar baseline; reportar fallos pre-existentes sin arreglarlos. → Baseline post-arreglo-de-migración: 8 failed (todos del refactor C-23). Reportado al usuario, luz verde para refactorizar.
- [x] 8.2 RED: test — `enviar_recordatorio_telegram` envía al destinatario `TELEGRAM` del turno (no a `paciente.telegram_chat_id`). → Tests viejos de `TestEnviarRecordatorioTelegram` actualizados: eliminan referencia a `paciente.telegram_chat_id`, registran `TurnoDestinatario` por turno, agregan `await db_session.refresh(turno, attribute_names=["destinatarios"])` para que la relación `selectin` se cargue.
- [x] 8.3 GREEN: refactorizar `enviar_recordatorio_telegram` para leer el destinatario `TELEGRAM` de `turno.destinatarios`. → Hecho en `backend/app/services/notificacion_service.py:64-90`. La función ahora itera `turno.destinatarios`, filtra por `canal == "TELEGRAM"`, y usa `dest.destinatario` como `chat_id`. Si no hay destinatario: warning + return True (TAREA 8.4). Si hay: envía.
- [x] 8.4 TRIANGULATE: test — turno sin destinatario `TELEGRAM` marca `recordatorio_enviado=True` + warning, sin enviar. → Test `test_turno_sin_destinatario_telegram_retorna_true_y_no_envia` (renombrado desde `test_paciente_sin_chat_id_retorna_true_y_no_envia`): turno sin `TurnoDestinatario` → return True, `enviar_mensaje` y `run_in_threadpool` no se llaman.
- [x] 8.5 RED/GREEN: test multi-chat — dos turnos del mismo DNI con chats distintos reciben el recordatorio en su chat respectivo. → Test `test_envio_dirigido_al_chat_del_turno_no_del_paciente`: dos turnos con `paciente_id` y `dni` iguales, `TurnoDestinatario` con `destinatario` distinto (111111 vs 222222). Verifica que `enviar_mensaje` se llama con `[111111, 222222]` en orden.

## 9. Verificación y cierre

- [ ] 9.1 Correr la suite completa (`pytest`): 0 regresiones sobre el baseline documentado.
- [ ] 9.2 `openspec validate c-23-turno-destinatario-multicanal --strict` sin errores.
- [ ] 9.3 Verificar manualmente el caso E2E multi-chat que motivó el cambio (reserva desde chat A y chat B para el mismo DNI).
- [ ] 9.4 (post-archive) chronicle update de la KB: `04_modelo_de_datos.md` (ERD + `turno_destinatario`, quita `telegram_chat_id`), `03_actores_y_roles.md` (identificación vs autenticación), `05_reglas_de_negocio.md` (RN de destinatario+canal).
