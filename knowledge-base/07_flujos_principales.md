# Flujos Principales

Cada flujo se documenta extremo a extremo, mostrando interacciones entre componentes.

## Flujo 1: Reserva de turno

**Disparador**: El usuario envía "Quiero un turno" al bot de Telegram.
**Actor**: Paciente.

**Pasos**:
1. **Telegram** recibe el mensaje y envía el webhook al backend (n8n o FastAPI directamente).
2. **n8n** (si actúa como proxy/orquestador) reenvía la solicitud al **FastAPI** backend.
3. **FastAPI** consulta la **Base de Datos (PostgreSQL)** para obtener disponibilidad según configuración del profesional.
4. **FastAPI** devuelve las fechas disponibles al usuario vía respuesta a n8n → Telegram.
5. El usuario selecciona fecha → **FastAPI** consulta horarios disponibles (filtrando CONFIRMADOS y RESERVADOS_TEMPORAL).
6. El usuario selecciona horario → **FastAPI** crea el Turno en estado `RESERVADO_TEMPORAL` y genera una **ReservaTemporal** con tiempo de expiración.
7. **FastAPI** solicita datos del paciente (nombre, apellido, DNI).
8. El usuario ingresa datos y confirma → **FastAPI**:
   - Valida que el paciente no tenga otro turno activo (RN-TU-01).
   - Registra o identifica al **Paciente** en la base de datos.
   - Actualiza el Turno a `CONFIRMADO`.
   - Elimina la **ReservaTemporal**.
   - Crea el evento en **Google Calendar**.
   - Envía confirmación al usuario vía **Telegram**.

**Diagrama de secuencia** (simplificado):
```
Paciente → Telegram → n8n → FastAPI → PostgreSQL
                          ← respuesta (fechas)
Paciente → Telegram → n8n → FastAPI → PostgreSQL
                          ← respuesta (horarios)
Paciente → Telegram → n8n → FastAPI → PostgreSQL
                                    → Google Calendar
                          ← confirmación
```

**Casos de error**:
- Sin disponibilidad → Notificar que no hay turnos y ofrecer lista de espera.
- Paciente con turno activo → Bloquear nueva reserva y ofrecer reprogramación.
- Falla de Google Calendar → Registrar error, reintentar, notificar al profesional si persiste.
- Expiración de reserva temporal → Scheduler libera el turno, notifica al usuario.

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

**Disparador**: Scheduler (APScheduler) detecta turnos confirmados en las próximas 24 horas.
**Actor**: Sistema automatizado.

**Pasos**:
1. **Scheduler** ejecuta tarea programada cada X minutos (o una vez al día).
2. **Scheduler** consulta **PostgreSQL** por turnos `CONFIRMADO` con fecha/hora dentro de las próximas 24h y sin recordatorio enviado.
3. **FastAPI** (o el scheduler directamente) envía mensaje de recordatorio al paciente vía **Telegram**.
4. El mensaje incluye opciones interactivas: **Confirmar**, **Cancelar**, **Reprogramar**.
5. Según la respuesta del paciente, se dispara Flujo 1 (si reprograma), Flujo 2 (si cancela) o se marca como confirmado.

**Casos de error**:
- Paciente no responde → Sin acción adicional; el turno sigue CONFIRMADO.
- Falla de envío de Telegram → Reintentar y registrar en logs.

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
