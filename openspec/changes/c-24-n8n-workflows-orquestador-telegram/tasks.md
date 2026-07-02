# Tasks — c-24-n8n-workflows-orquestador-telegram

> No hay código de backend. Los "tests" para n8n son: (1) parseo estático del JSON con `jq`/`python -c "import json; json.load(...)"`, (2) validación de estructura (presencia de nodos esperados y referencia a `Header Auth` credential en los `HTTP Request` nodes), (3) verificación E2E manual con backend + Telegram real, documentada con checklist binario.

## 0. Gate de gobernanza (BAJA — confirmación de OQ)

- [x] 0.1 Confirmar con el usuario la respuesta a **OQ-1** del design.md: ¿`@BotFather` apunta al orquestador n8n (recomendado), al webhook del backend, o ambos? → **RESUELTA (2026-07-01)**: n8n como entry point principal. El webhook del backend queda como alternativa documentada en el README.
- [x] 0.2 Confirmar con el usuario la respuesta a **OQ-2** del design.md: wizard de datos del paciente en `Crear_turno` con (a) un único mensaje CSV parseado por coma, o (b) paso a paso con `Send and Wait for Response` por cada campo. → **RESUELTA (2026-07-01)**: opción (a), consistente con C-08. Documentado en Decisión 3 como C3-i.
- [x] 0.3 Confirmar con el usuario la respuesta a **OQ-3** del design.md (decisión mixta): `flujo-lista-espera` queda como placeholder (deuda C-11), `flujo-recordatorio` se IMPLEMENTA con cron diario + endpoint nuevo del backend `POST /api/v1/recordatorios/run`. → **RESUELTA (2026-07-01)**: ver Decisión 5 y Decisión 8 del design.md.

## 1. Análisis y diseño (cubierto por proposal + design + spec)

- [x] 1.1 Analizar la estructura del orquestador modelo (`My workflow (4).json`, 16 nodos): identificar qué nodos reutilizar (Switch × 3) y qué eliminar (Forms, mock DB, postgres node aislado, Merge). → Cubierto en design.md §Context.
- [x] 1.2 Analizar los 4 workflows actuales (`flujo-reserva`, `flujo-cancelacion`, `flujo-lista-espera`, `flujo-recordatorio`) y mapear cada nodo a su endpoint del backend. → Cubierto en design.md §Context (matriz de gaps).
- [x] 1.3 Analizar el backend: `backend/app/dependencies.py:98-139` (auth), `backend/app/routers/turnos.py` y `routers/lista_espera.py` (endpoints). → Cubierto en design.md §Context y Decisión 4.
- [x] 1.4 Identificar gaps: `flujo-reprogramar` NO existe (hay que crearlo), `flujo-lista-espera` apunta a endpoint inexistente, `flujo-recordatorio` apunta a endpoint inexistente, los 4 workflows carecen de `X-API-Key`. → Cubierto en design.md §Context "Gaps identificados".
- [x] 1.5 Documentar el mapeo orquestador ↔ workflows reales (3 sub-workflows, 2 workflows independientes, 2 eliminados). → Cubierto en design.md §Decisión 5.

## 2. Implementar el orquestador (`n8n-workflows/orquestador.json`)

- [x] 2.1 Crear `n8n-workflows/orquistador.json` desde cero (no usar el esqueleto del usuario como base — es inspiration, no foundation). Estructura: `Telegram Trigger` → `Code` (normalizar) → `Switch` × 3 → `executeWorkflow` × 3.
- [x] 2.2 Configurar el nodo `Telegram Trigger` con la credencial `Telegram Bot` (placeholder `telegramApi: { id: "telegram-bot-credentials", name: "Telegram Bot Credentials" }`, se reconfigura al importar).
- [x] 2.3 Implementar el nodo `Code` que normaliza `message.text` y `callback_query.data` a `{ comando, chat_id, payload }`. Documentar las dos formas con comentarios en el JS. Devolver `{ comando: "desconocido" }` si no matchea.
- [x] 2.4 Configurar el `Switch` con 3 reglas: `comando === "crear"` → output 0, `comando === "cancelar"` → output 1, `comando === "reprogramar"` → output 2.
- [x] 2.5 Agregar 3 nodos `executeWorkflow` cableados a las 3 salidas del Switch, referenciando los sub-workflows por nombre (`sub-flujo-crear-turno`, `sub-flujo-cancelar-turno`, `sub-flujo-reprogramar-turno`). Configurar `onError: "continueRegularOutput"` para que un error en un sub-workflow no rompa el orquestador.
- [x] 2.6 Agregar un nodo `Telegram - Mensaje de ayuda` (catch-all del `Code`) que se dispara cuando `comando === "desconocido"`. Conectar con un `Switch` extra o con un `IF` post-Code.
- [x] 2.7 **Validación estática**: `python -c "import json; json.load(open('n8n-workflows/orquestador.json'))"` retorna sin error. Test pasa.

## 3. Implementar el sub-workflow de crear turno (`n8n-workflows/sub-flujo-crear-turno.json`)

- [x] 3.1 Crear el sub-workflow con trigger `Execute Workflow Trigger` (que es el entry point cuando lo invoca el orquestador vía `executeWorkflow`).
- [x] 3.2 Nodo 1: `Telegram - Send and Wait for Response` con mensaje "Seleccioná una fecha" y `Send and Wait for Response` configured para esperar `callback_data` con prefijo `fecha:`. Documentar timeout = 10 min.
- [x] 3.3 Nodo 2: `HTTP Request - GET Disponibilidad` con método `GET`, URL `{{$env.FASTAPI_BASE_URL}}/turnos/disponibles?fecha=<fecha extraída>`, autenticación `Header Auth` (credencial `Profesional API Key`).
- [x] 3.4 Nodo 3: `Code` para formatear la lista de slots como botones inline (similar a `flujo-reserva.json:46-49` original, pero con callback_data `hora:HH:MM`).
- [x] 3.5 Nodo 4: `Telegram - Send and Wait for Response` con mensaje "Seleccioná un horario" y los botones generados.
- [x] 3.6 Nodo 5: `HTTP Request - POST Reserva` con método `POST`, URL `{{$env.FASTAPI_BASE_URL}}/turnos`, body `{"fecha": "<fecha>", "hora_inicio": "<hora>"}` (sin `paciente_id` — el backend lo resuelve en confirmación; sin `telegram_chat_id` — el bot lo inyecta el orquestador en el payload), autenticación `Header Auth`.
- [x] 3.7 Nodo 6: `Telegram - Send Message` con mensaje "Reserva creada. Ingresá tus datos como CSV: Nombre, Apellido, DNI, Teléfono" (consistente con C-08 y OQ-2 resuelta como opción a).
- [x] 3.8 Nodo 7: `Telegram - Send and Wait for Response` esperando el texto CSV del paciente.
- [x] 3.9 Nodo 8: `Code` para parsear el CSV (`split(",").map(s => s.trim())` → `nombre`, `apellido`, `dni`, `telefono`) y mergear con `telegram_chat_id` del payload del orquestador.
- [x] 3.10 Nodo 9: `HTTP Request - PUT Confirmar` con método `PUT`, URL `{{$env.FASTAPI_BASE_URL}}/turnos/<turno_id>/confirmar`, body con `nombre, apellido, dni, telefono, telegram_chat_id`, autenticación `Header Auth`.
- [x] 3.11 Nodo 10: `Telegram - Send Message` con confirmación final (fecha, hora, paciente). Manejo de error: si HTTP retorna 409/404, enviar mensaje de error legible.
- [x] 3.12 **Validación estática**: `python -c "import json; json.load(...)"` OK. Test pasa.

## 4. Implementar el sub-workflow de cancelar turno (`n8n-workflows/sub-flujo-cancelar-turno.json`)

- [x] 4.1 Crear el sub-workflow con trigger `Execute Workflow Trigger`.
- [x] 4.2 Nodo 1: `Code` que extrae `turno_id` del payload del orquestador (parsing según convención: el orquestador pasa `{ comando: "cancelar", chat_id, payload: { turno_id } }` cuando el callback fue `cancelar:{id}`; o el orquestador lo pidió vía `Send and Wait for Response` con un mensaje que pide el ID).
- [x] 4.3 Nodo 2: `HTTP Request - PUT Cancelar` con método `PUT`, URL `{{$env.FASTAPI_BASE_URL}}/turnos/<turno_id>/cancelar`, autenticación `Header Auth`. **No enviar body** (PUT sin body).
- [x] 4.4 Nodo 3: `Code` que formatea la respuesta (turno cancelado) y maneja errores 404 (turno no encontrado) y 409 (ya cancelado) con mensajes legibles.
- [x] 4.5 Nodo 4: `Telegram - Send Message` con el resultado. Agregar un botón inline "Reprogramar turno" con `callback_data: "reprogramar:{turno_id}"` si la cancelación fue exitosa.
- [x] 4.6 **Validación estática**: `python -c "import json; json.load(...)"` OK.

## 5. Implementar el sub-workflow de reprogramar turno (`n8n-workflows/sub-flujo-reprogramar-turno.json`)

- [x] 5.1 Crear el sub-workflow con trigger `Execute Workflow Trigger`. **Este workflow NO existía** en el repo.
- [x] 5.2 Nodo 1: `Code` que extrae `turno_id` del payload del orquestador.
- [x] 5.3 Nodo 2: `Telegram - Send and Wait for Response` con mensaje "Seleccioná la nueva fecha" y `Send and Wait for Response` para esperar callback con `fecha:`.
- [x] 5.4 Nodo 3: `HTTP Request - GET Disponibilidad` con método `GET`, URL `{{$env.FASTAPI_BASE_URL}}/turnos/disponibles?fecha=<nueva_fecha>`, autenticación `Header Auth`.
- [x] 5.5 Nodo 4: `Code` para formatear slots como botones inline (callback_data `hora:HH:MM`).
- [x] 5.6 Nodo 5: `Telegram - Send and Wait for Response` con mensaje "Seleccioná el nuevo horario" y los botones.
- [x] 5.7 Nodo 6: `HTTP Request - PUT Reprogramar` con método `PUT`, URL `{{$env.FASTAPI_BASE_URL}}/turnos/<turno_id>/reprogramar`, body `{"nueva_fecha": "<fecha>", "nueva_hora_inicio": "<hora>"}` (sin `paciente_data` — el backend preserva al paciente del turno original; sin `telegram_chat_id` — el bot lo inyecta el orquestador en el payload), autenticación `Header Auth`.
- [x] 5.8 Nodo 7: `Telegram - Send Message` con confirmación de la reprogramación. Manejo de error 409/404.
- [x] 5.9 **Validación estática**: `python -c "import json; json.load(...)"` OK.

## 6. Actualizar workflows independientes (`flujo-lista-espera` placeholder + `flujo-recordatorio` reescrito)

- [x] 6.1 `flujo-lista-espera.json`: agregar la credencial `Header Auth` (`X-API-Key`) al nodo `HTTP Request - Placeholder Lista Espera`. Dejar el `notes: "PLACEHOLDER: endpoint /lista-espera/siguiente no existe en backend, deuda C-11"` intacto. NO se reimplementa en este change.
- [x] 6.2 `flujo-recordatorio.json`: **reescribir** desde cero como workflow funcional (Decisión 5 + 8):
  - `Schedule Trigger` con cron configurable, default `0 10 * * *` (todos los días a las 10:00 hora local del servidor).
  - `Code` node: calcula `fecha_maniana = new Date(now + 1 day).toISOString().slice(0, 10)` (YYYY-MM-DD).
  - `HTTP Request` node: `POST { { $env.BACKEND_URL } }/api/v1/recordatorios/run?fecha={{ $json.fecha_maniana }}` con `Header Auth` credential (`X-API-Key`).
  - Manejo de respuesta: loguear `total_enviados` y errores; no romper el workflow si falla un profesional (n8n HTTP Request node tiene `onError: "continueRegularOutput"`).
- [x] 6.3 **Validación estática**: ambos JSON parsean OK (`python -c "import json; json.load(open('n8n-workflows/flujo-*.json'))"`).

## 7. Backend: nuevo endpoint `POST /api/v1/recordatorios/run` (Decisión 8)

### 7.1 Schemas Pydantic

- [x] 7.1.1 RED: test que valida el schema `RecordatorioRunResponse` con campos `total_candidatos`, `total_enviados`, `total_fallidos`, `errores: list[RecordatorioError]`.
- [x] 7.1.2 RED: test que valida `RecordatorioError` con `profesional_id`, `turno_id`, `mensaje`.
- [x] 7.1.3 GREEN: crear `backend/app/schemas/recordatorio.py` con ambos schemas (Pydantic v2, `model_config = ConfigDict(from_attributes=True)` si es necesario para serializar desde el service).

### 7.2 Service: `recordatorio_service.py`

- [x] 7.2.1 RED: test unitario `recordatorio_service.run_recordatorios_para_todos(db, fecha)` con 0 profesionales → response con `total_candidatos=0, total_enviados=0, total_fallidos=0, errores=[]`.
- [x] 7.2.2 RED: test con 1 profesional activo + 1 turno CONFIRMADO sin recordatorio + destinatario TELEGRAM → response `total_candidatos=1, total_enviados=1, total_fallidos=0`. El turno queda con `recordatorio_enviado=True` después del commit.
- [x] 7.2.3 RED: test con 1 profesional activo + 1 turno CONFIRMADO sin recordatorio SIN destinatario TELEGRAM → response `total_candidatos=1, total_enviados=1` (no-falla — el comportamiento de C-23 TAREA 8.4 es warning + return True + marca enviado sin enviar). El turno queda con `recordatorio_enviado=True`.
- [x] 7.2.4 RED: test con 1 profesional activo + 1 turno CONFIRMADO sin recordatorio cuyo envío FALLA (mock de `enviar_recordatorio_telegram` que retorna False) → response `total_candidatos=1, total_enviados=0, total_fallidos=1, errores=[RecordatorioError(...)]`. El turno NO queda con `recordatorio_enviado=True` (reintento futuro).
- [x] 7.2.5 RED: test con 2 profesionales activos: el primero falla, el segundo OK → el batch continúa, response con errores=[1], total_enviados del segundo = 1.
- [x] 7.2.6 RED: test con 1 profesional sin `telegram_bot_token` → warning logueado, response saltea al profesional (`total_candidatos=0` para ese profesional).
- [x] 7.2.7 GREEN: implementar `recordatorio_service.py` con la función `run_recordatorios_para_todos(db, fecha: date) -> RecordatorioRunResponse`. Internamente itera por `Profesional where is_active=True`, llama a `obtener_turnos_para_recordar` + `enviar_recordatorio_telegram` + `marcar_recordatorio_enviado` por profesional. Commit por profesional (Patrón A). Try/except por profesional para que un error no rompa el batch.
- [x] 7.2.8 TRIANGULATE: test que valida el formato del `RecordatorioError` cuando hay fallo (campos `profesional_id`, `turno_id`, `mensaje` con traceback corto).
- [x] 7.2.9 SAFETY NET: el scheduler interno APScheduler del backend (`scheduler.jobs._enviar_recordatorios_job`) sigue funcionando. NO se reemplaza. Solo se agrega el endpoint nuevo como trigger alternativo (n8n).

### 7.3 Router: `recordatorios.py`

- [x] 7.3.1 RED: test de integración `POST /api/v1/recordatorios/run?fecha=YYYY-MM-DD` SIN `X-API-Key` → 401.
- [x] 7.3.2 RED: test de integración `POST /api/v1/recordatorios/run?fecha=YYYY-MM-DD` CON `X-API-Key` válida + 1 turno candidato → 200 con `RecordatorioRunResponse` no-vacío. El turno queda con `recordatorio_enviado=True` después del commit.
- [x] 7.3.3 RED: test de integración con `fecha` con formato inválido (`?fecha=foo`) → 422.
- [x] 7.3.4 RED: test de integración con `fecha` en el pasado lejano (no hay candidatos) → 200 con `total_candidatos=0`.
- [x] 7.3.5 GREEN: crear `backend/app/routers/recordatorios.py` con un solo endpoint `POST /run`. Usa `Depends(get_profesional_by_api_key)` (NO `CurrentProfesionalDep` — el endpoint NO está scoped a un profesional específico, dispara sobre TODOS los activos, ver Decisión 8). El servicio hace el resto.
- [x] 7.3.6 GREEN: registrar el router en `backend/app/main.py` con `prefix="/api/v1/recordatorios"` y `tags=["recordatorios"]`.
- [x] 7.3.7 TRIANGULATE: test que verifica que el router **no** rompe el `pytest` suite del backend (no regresión sobre 448 tests).

### 7.4 Endpoints existentes (NO se modifican)

- [x] 7.4.1 Verificar que el scheduler APScheduler (`scheduler.jobs._enviar_recordatorios_job`) sigue activo. Documentar en el design que coexisten **dos motores** de recordatorio: n8n como trigger principal (vía este endpoint), APScheduler como fallback (cron interno). Ambos usan `notificacion_service` y respetan `recordatorio_enviado` para evitar doble dispatch.

## 8. Eliminar workflows viejos

- [x] 8.1 `git rm n8n-workflows/flujo-reserva.json`. Su funcionalidad vive en `sub-flujo-crear-turno.json`.
- [x] 8.2 `git rm n8n-workflows/flujo-cancelacion.json`. Su funcionalidad vive en `sub-flujo-cancelar-turno.json`.
- [x] 8.3 Verificar que el `git status` muestra solo esos 2 archivos eliminados.

## 9. Actualizar `n8n-workflows/README.md`

- [x] 9.1 Reemplazar la tabla "Workflows" por la nueva topología: `orquestador.json`, `sub-flujo-crear-turno.json`, `sub-flujo-cancelar-turno.json`, `sub-flujo-reprogramar-turno.json`, `flujo-lista-espera.json` (modificado), `flujo-recordatorio.json` (modificado). Marcar los 2 eliminados como tal en la sección histórica.
- [x] 9.2 Agregar sección "Patrón de credenciales": documentar las 2 credenciales (`Telegram Bot` y `Header Auth`), sus valores por profesional, y dónde se asignan en n8n.
- [x] 9.3 Reemplazar la sección "Cómo configurar webhooks en Telegram" por "Configurar `@BotFather` una vez por profesional con la URL del `Telegram Trigger` del orquestador" (que n8n registra al activar el workflow).
- [x] 9.4 Reemplazar la sección "Cómo importar workflows" por "Importar **una vez por profesional**: orquestador + 3 sub-workflows + 2 workflows independientes". Documentar el orden de import.
- [x] 9.5 Actualizar la tabla "Mapeo de workflows ↔ endpoints FastAPI" con la nueva matriz (orquestador no consume REST, sub-workflows consumen los endpoints, workflows independientes consumen los placeholders o el endpoint nuevo del recordatorio).
- [ ] 9.6 Agregar sección "Coexistencia con el webhook del backend" que documente la decisión de OQ-1.
- [x] 9.7 Agregar sección "Dos motores de recordatorio (n8n + APScheduler)" que documente que ambos coexisten, comparten `notificacion_service`, y respetan `recordatorio_enviado` para evitar doble dispatch.

## 10. Verificación

- [ ] 10.1 **Test de parseo estático de los workflows n8n**: ejecutar `for f in n8n-workflows/*.json; do python -c "import json; json.load(open('$f'))" || echo "FAIL: $f"; done`. Todos pasan (6 archivos: orquestador, 3 sub-workflows, 2 workflows modificados).
- [ ] 10.2 **Test de estructura con grep**: para cada sub-workflow y workflow independiente modificado, verificar que el JSON contiene al menos un nodo con `type: "n8n-nodes-base.httpRequest"` Y que ese nodo tiene `"authentication": "genericCredentialType"` Y `"genericAuthType": "httpHeaderAuth"`. Comando: `jq '.nodes[] | select(.type == "n8n-nodes-base.httpRequest") | .parameters.authentication' n8n-workflows/sub-flujo-crear-turno.json` retorna `"genericCredentialType"` (o equivalente).
- [ ] 10.3 **Test de dependencias**: verificar que el orquestador referencia por nombre los 3 sub-workflows. `jq '.nodes[] | select(.type == "n8n-nodes-base.executeWorkflow") | .parameters.workflowId' n8n-workflows/orquestador.json` lista los 3.
- [x] 10.4 **Test de regresión del backend**: `cd backend && pytest` retorna 0 failed (la suite actual de 448 tests + los ~7 tests nuevos del endpoint del recordatorio). Confirma que el orquestador n8n y el endpoint nuevo no rompieron nada.
- [x] 10.5 `openspec validate c-24-n8n-workflows-orquestador-telegram --strict` sin errores. Output esperado: `Change 'c-24-n8n-workflows-orquestador-telegram' is valid`.
- [x] 10.6 **Verificación E2E manual** (fuera de CI, requiere n8n local + bot real + backend levantado):
  1. Levantar backend con seed: `cd backend && uvicorn app.main:app --reload`.
  2. Importar los 6 workflows en n8n local. Configurar las 2 credenciales.
  3. Activar el orquestador.
  4. Enviar `/reservar` al bot en Telegram.
  5. Verificar en n8n Executions que el orquestador dispatch-ea a `Crear_turno` y los HTTP Request retornan 200.
  6. Verificar en backend logs que el turno se crea con el `profesional_id` correcto del profesional dueño del bot.
  7. Repetir con `/cancelar` y `/reprogramar` para los otros 2 sub-workflows.
  8. **Probar el recordatorio**: trigger manual del cron (o esperar a la hora) y verificar que el endpoint `POST /api/v1/recordatorios/run` itera y envía los mensajes del día siguiente. Confirmar que el turno queda con `recordatorio_enviado=True`.
  9. Documentar el resultado (OK/KO) en el PR o en el comentario del commit.

## 11. Cierre (post-archive)

- [ ] 11.1 Archivar el change con `openspec archive c-24-n8n-workflows-orquestador-telegram --yes`. Esto sincroniza la spec `n8n-workflow-orquestador-telegram` a `openspec/specs/`.
- [ ] 11.2 **Chronicle update de la KB**: actualizar `knowledge-base/08_arquitectura_propuesta.md` §Integración n8n con la nueva topología (orquestador + sub-workflows + credenciales + endpoint nuevo del recordatorio). Actualizar `CHANGES.md` marcando C-24 como archivado.
- [ ] 11.3 (Opcional, post-demo) Evaluar si el orquestador n8n reemplaza al webhook del backend en producción, o si ambos conviven con `@BotFather` apuntando a uno solo. Documentar la decisión en `NEXT_SESSION.md`.
