# Flujos Principales

Cada flujo se documenta extremo a extremo, mostrando interacciones entre componentes.

## Flujo 1: Reserva de turno

**Disparador**: El usuario envía "Quiero un turno" (o `/reservar`) al bot de Telegram.
**Actor**: Paciente.

**Pasos (C-24 — topología orquestador)**:
1. **Telegram** entrega el update al `Telegram Trigger` del **orquestador** (`orquestador.json`, configurado en `@BotFather`).
2. El nodo `Code "Normalizar Comando"` del orquestador extrae `message.text` (o `callback_query.data`) y deriva `comando = "crear"`.
3. El `Switch Comando` dispatch-ea a `sub-flujo-crear-turno.json` vía `executeWorkflow`.
4. **sub-flujo-crear-turno** (stateless) ejecuta el wizard con `Send and Wait for Response`:
   - Lista fechas disponibles llamando a `GET /turnos/disponibles` (Header Auth: `X-API-Key` del profesional del bot).
   - Lista horarios disponibles para la fecha seleccionada.
   - Crea reserva llamando a `POST /turnos` con `telegram_chat_id` opcional (C-23: si viene, se registra destinatario `TELEGRAM`; si no, se difiere a confirmación).
5. El sub-workflow pide los datos del paciente (nombre, apellido, DNI, teléfono, email opcional) como CSV parseado por coma.
6. El usuario confirma → **sub-flujo** llama a `PUT /turnos/{id}/confirmar` con `paciente_data` (incluye `telegram_chat_id`).
7. **FastAPI** resuelve beneficiario por DNI vía `crear_o_obtener_paciente` (DNI scoped por profesional — `UNIQUE(profesional_id, dni)`), hace **upsert** de destinatarios `TELEGRAM` (y `EMAIL` si vino) en `turno_destinatario`, valida RN-TU-01, actualiza el Turno a `CONFIRMADO`, elimina la `ReservaTemporal`, crea el evento en **Google Calendar**.
8. **FastAPI** responde 200 al sub-workflow, que envía confirmación al usuario vía **Telegram**.

**Diagrama de secuencia** (C-24 — orquestador):
```
Paciente → Telegram → @BotFather → orquestador.json
                                        └→ Code normalizar → Switch "crear"
                                            └→ executeWorkflow → sub-flujo-crear-turno
                                                ├→ GET /turnos/disponibles (X-API-Key)
                                                ├→ POST /turnos {telegram_chat_id}        (Header Auth)
                                                └→ PUT /turnos/{id}/confirmar             (Header Auth)
                                                    └→ upsert TurnoDestinatario (TELEGRAM/EMAIL)
                                                    └→ Google Calendar
                                                    └→ Telegram send (confirmación)
```

**Casos de error**:
- Sin disponibilidad → Notificar que no hay turnos y ofrecer lista de espera.
- Paciente con turno activo → Bloquear nueva reserva y ofrecer reprogramación.
- Falla de Google Calendar → Registrar error, reintentar, notificar al profesional si persiste.
- Expiración de reserva temporal → Scheduler libera el turno, notifica al usuario.
- `X-API-Key` inválida o faltante → 401; el sub-workflow no avanza (el orquestador recibe el error y puede responder "Servicio no disponible, intentá más tarde").
- Turno sin destinatario `TELEGRAM` al confirmar → se permite y el recordatorio posterior hace no-op con warning (RN-RE-05).

---

## Flujo 2: Cancelación de turno

**Disparador**: El usuario solicita cancelar un turno confirmado.
**Actor**: Paciente.

**Pasos**:
1. **Telegram** recibe la solicitud y la envía al backend.
2. **FastAPI** valida la existencia del turno confirmado del paciente.
3. **FastAPI** pide confirmación explícita al usuario.
4. El usuario confirma → **FastAPI**:
   - Actualiza el Turno a estado `CANCELADO`.
   - Elimina el evento de **Google Calendar**.
   - Consulta la **Lista de Espera** para esa fecha.
5. Si hay pacientes en espera → ejecutar Flujo 5 (Lista de Espera).
6. **FastAPI** envía confirmación de cancelación al usuario.

**Casos de error**:
- Turno no encontrado o ya cancelado → Notificar error amigable.
- Falla de Google Calendar → Registrar error y reintentar; no revertir cancelación en base de datos.

---

## Flujo 3: Reprogramación de turno

**Disparador**: El usuario solicita reprogramar un turno confirmado.
**Actor**: Paciente.

**Pasos**:
1. **FastAPI** valida el turno actual del paciente.
2. **FastAPI** muestra nuevas disponibilidades (horarios DISPONIBLES).
3. El usuario selecciona nuevo horario → **FastAPI**:
   - Cancela el turno anterior (estado `CANCELADO`).
   - Elimina el evento anterior de **Google Calendar**.
   - Crea un nuevo Turno en estado `CONFIRMADO`.
   - Crea el nuevo evento en **Google Calendar**.
4. **FastAPI** envía confirmación de reprogramación.
5. El horario anterior vuelve a estar disponible (se evalúa lista de espera).

**Casos de error**:
- Nuevo horario ya no disponible → Notificar y ofrecer alternativas.
- Falla de Google Calendar → Reintentar; mantener base de datos como fuente de verdad.

---

## Flujo 4: Recordatorio automático

**Disparador (C-24)**: **dos motores independientes** comparten la responsabilidad.
- **n8n primario**: `flujo-recordatorio.json` con `Schedule Trigger` cron `0 10 * * *` (default 10:00 hora local).
- **APScheduler fallback**: job interno en el backend (`scheduler.jobs._enviar_recordatorios_job`, C-08).

El flag `turno.recordatorio_enviado` en la DB evita doble dispatch entre los dos motores. En v1.0 se recomienda activar **solo uno** por profesional.

**Actor**: Sistema automatizado.

**Pasos (camino n8n primario, C-24)**:
1. **n8n** (`Schedule Trigger` cron) ejecuta `flujo-recordatorio.json`.
2. El nodo `Code "Calcular Fecha Mañana"` calcula `fecha_maniana` (YYYY-MM-DD).
3. **HTTP Request** → `POST {BACKEND_URL}/api/v1/recordatorios/run?fecha={fecha_maniana}` con Header Auth `X-API-Key`.
4. **FastAPI** autentica al caller, calcula la ventana de horas (heurística `(fecha - hoy).days * 24 + 12`).
5. **FastAPI** itera por `Profesional where is_active=True`. Para cada uno:
   - Llama a `obtener_turnos_para_recordar(db, profesional_id, horas_antes)` → turnos `CONFIRMADO` con `recordatorio_enviado=False` en la ventana.
   - Para cada turno: `enviar_recordatorio_telegram(turno, bot_token=profesional.telegram_bot_token)` lee el destinatario `TELEGRAM` de `turno.destinatarios` (C-23) y envía el mensaje.
   - Si envío OK o no hay destinatario → `marcar_recordatorio_enviado(db, turno.id, profesional.id)`.
   - `commit` por profesional (Patrón A).
6. **FastAPI** responde `RecordatorioRunResponse { total_candidatos, total_enviados, total_fallidos, errores }` (200 OK). Errores por turno/profesional no rompen el batch.

**Pasos (camino APScheduler fallback, C-08)**:
1. **APScheduler** del backend dispara el job a la hora configurada.
2. El job invoca la misma lógica de `notificacion_service` (`obtener_turnos_para_recordar` + `enviar_recordatorio_telegram` + `marcar_recordatorio_enviado`).
3. Si n8n ya marcó el flag, el query de `obtener_turnos_para_recordar` no retorna esos turnos.

**Diagrama de secuencia (C-24)**:
```
   n8n (cron 0 10 * * *)                    APScheduler (fallback)
        │                                            │
        ├─ Code: fecha_maniana                       ├─ job interno
        │                                            │
        └─ POST /api/v1/recordatorios/run?fecha=X    └─ llama notificacion_service
                    │                                       │
                    ├─ itera Profesionales activos ─────────┤
                    │                                       │
                    ├─ obtener_turnos_para_recordar        │
                    ├─ enviar_recordatorio_telegram (lee TurnoDestinatario.C-23)
                    └─ marcar_recordatorio_enviado
                                  │
                                  └─ Telegram API → paciente
```

**Casos de error**:
- Paciente no responde → Sin acción adicional; el turno sigue CONFIRMADO.
- Falla de envío de Telegram → El turno queda con `recordatorio_enviado=False` y se reintenta en el próximo run (acumulado en `total_fallidos`/`errores`).
- Turno sin destinatario `TELEGRAM` configurado → se omite con warning y se marca `recordatorio_enviado=True` (no se reintenta) — RN-RE-05.
- Ambos motores activos → el segundo motor skipea los turnos ya marcados (sin doble dispatch).

---

## Flujo 5: Lista de espera

**Disparador**: Un turno pasa a estado `CANCELADO` o una ReservaTemporal expira.
**Actor**: Sistema automatizado.

**Pasos**:
1. **FastAPI** (o scheduler al liberar por expiración) detecta que se liberó un horario.
2. **FastAPI** consulta **ListaDeEspera** para la fecha liberada, ordenada por `creado_en`.
3. Si existe al menos un registro, **FastAPI** notifica al primer paciente vía **Telegram**.
4. El mensaje ofrece el turno liberado con opciones: **Aceptar** / **Rechazar**.
5. Si el paciente acepta:
   - Se confirma el Turno para ese paciente.
   - Se crea evento en **Google Calendar**.
   - Se elimina al paciente de la **ListaDeEspera**.
   - Se envía confirmación.
6. Si el paciente rechaza o no responde en el tiempo definido:
   - Se pasa al siguiente paciente en la lista de espera.
   - Se repite desde el paso 3.
7. Si nadie acepta, el turno queda `DISPONIBLE`.

**Casos de error**:
- Notificación fallida a un paciente → Reintentar con el siguiente de la lista y marcar al primero para revisión.
- Paciente acepta pero el turno ya fue tomado por otro (condición de carrera) → Validar atomicidad en base de datos.
