# Funcionalidades

Organizadas por **épica** y luego por **historia de usuario** (formato US-NNN).

## Épica 1: Reserva y confirmación de turnos

### US-001 — Solicitar turno vía Telegram
**Como** paciente
**Quiero** solicitar un turno odontológico a través de un bot de Telegram
**Para** agendar una cita de forma rápida y sin necesidad de llamar por teléfono

**Criterios de aceptación**:
- [x] El bot responde al mensaje "Quiero un turno" o `/reservar` con las fechas disponibles.
- [x] El usuario puede seleccionar una fecha y ver los horarios disponibles.
- [x] Al seleccionar un horario, el sistema bloquea temporalmente la franja (RESERVADO_TEMPORAL).
- [x] El sistema solicita nombre, apellido y DNI del paciente.
- [x] El usuario confirma el turno y el sistema cambia el estado a CONFIRMADO.
- [x] Se envía confirmación al usuario y se crea el evento en Google Calendar.
- [x] **(C-24)** El bot es atendido por el **orquestador n8n** (`orquestador.json` + `sub-flujo-crear-turno.json`), que llama al backend con `X-API-Key` por profesional.
- [x] **(C-23)** El turno queda con su destinatario `TELEGRAM` (y opcionalmente `EMAIL`) en `turno_destinatario`, no en una columna del paciente.
- [x] **(C-23)** El beneficiario se resuelve por DNI scoped por profesional (`UNIQUE(profesional_id, dni)`); no se hardcodea `paciente_id` en el body de la reserva.

**Reglas relacionadas**: RN-TU-01, RN-TU-03, RN-TU-06, RN-TU-07, RN-PA-01, RN-PA-02, RN-RE-03

### US-002 — Expiración automática de reserva temporal
**Como** sistema
**Quiero** liberar automáticamente una reserva temporal si no se confirma
**Para** que el horario vuelva a estar disponible para otros pacientes

**Criterios de aceptación**:
- [x] Si el usuario no confirma en el tiempo configurado (ej. 2 minutos), la reserva temporal se elimina.
- [x] El turno vuelve a estado DISPONIBLE.
- [x] El usuario recibe notificación de liberación por inactividad.

**Reglas relacionadas**: RN-TU-03

## Épica 2: Gestión del ciclo de turnos

### US-003 — Cancelar turno
**Como** paciente
**Quiero** cancelar un turno previamente confirmado
**Para** liberar el horario y avisar al profesional

**Criterios de aceptación**:
- [x] El usuario puede solicitar la cancelación mediante comando en Telegram.
- [x] El sistema pide confirmación antes de cancelar.
- [x] Al confirmar, el turno pasa a estado CANCELADO.
- [x] Se elimina el evento de Google Calendar.
- [x] El horario vuelve a estar disponible.

**Reglas relacionadas**: RN-TU-04, RN-TU-08

### US-004 — Reprogramar turno
**Como** paciente
**Quiero** cambiar la fecha/hora de mi turno confirmado
**Para** ajustar la cita a mi disponibilidad

**Criterios de aceptación**:
- [x] El usuario solicita reprogramación y el sistema muestra nuevas disponibilidades.
- [x] Al seleccionar nuevo horario, el turno anterior pasa a CANCELADO y se crea uno nuevo CONFIRMADO.
- [x] Google Calendar se actualiza (evento anterior eliminado, nuevo creado).
- [x] El horario anterior vuelve a estar disponible.

**Reglas relacionadas**: RN-TU-05, RN-TU-09

### US-005 — Consultar turnos del día (profesional)
**Como** profesional
**Quiero** ver los turnos programados para el día actual
**Para** organizar mi agenda de atención

**Criterios de aceptación**:
- [x] El sistema muestra lista de turnos CONFIRMADOS para el día.
- [x] Cada turno indica hora, nombre del paciente y estado.

## Épica 3: Comunicaciones automáticas

### US-006 — Recordatorio automático 24h antes
**Como** sistema
**Quiero** enviar un recordatorio al paciente 24 horas antes de su turno
**Para** reducir la tasa de inasistencias

**Criterios de aceptación**:
- [x] El scheduler detecta turnos próximos y dispara el envío de mensajes.
- [x] El mensaje incluye fecha, hora y opciones para confirmar, cancelar o reprogramar.
- [x] El paciente puede interactuar directamente desde el mensaje de recordatorio.
- [x] **(C-24)** El envío puede dispararse por **dos motores**: n8n (`flujo-recordatorio.json` con `Schedule Trigger` cron diario → `POST /api/v1/recordatorios/run?fecha=mañana`) **o** APScheduler del backend (fallback). El flag `turno.recordatorio_enviado` evita doble dispatch entre ambos.
- [x] **(C-23)** El destinatario del recordatorio se lee del `turno_destinatario` (canal `TELEGRAM`), no de `paciente.telegram_chat_id` (que ya no existe).
- [x] **(C-23)** Si el turno no tiene destinatario `TELEGRAM`, el envío se omite con warning y `recordatorio_enviado` se marca `True` (sin reintento — RN-RE-05).

**Reglas relacionadas**: RN-RE-01, RN-RE-02, RN-RE-03, RN-RE-04, RN-RE-05, RN-RE-06

## Épica 4: Lista de espera

### US-007 — Registrar en lista de espera
**Como** paciente
**Quiero** anotarme en lista de espera cuando no haya turnos disponibles
**Para** ser notificado si se libera un horario

**Criterios de aceptación**:
- [x] El sistema permite inscribirse en lista de espera indicando preferencia de fecha.
- [x] El paciente queda registrado en orden de llegada.

### US-008 — Notificación de turno liberado
**Como** sistema
**Quiero** ofrecer automáticamente un turno liberado al primer paciente en lista de espera
**Para** maximizar la ocupación de la agenda

**Criterios de aceptación**:
- [x] Ante una cancelación o expiración, el sistema detecta la lista de espera.
- [x] Notifica al primer paciente disponible.
- [x] Si el paciente acepta, el turno se confirma y se actualiza Google Calendar.
- [x] Si no acepta en el tiempo definido, se pasa al siguiente.

**Reglas relacionadas**: RN-LE-01, RN-LE-02

## Épica 5: Métricas y configuración

### US-009 — Ver métricas básicas
**Como** profesional
**Quiero** consultar métricas simples del sistema
**Para** evaluar el uso y la eficiencia de la agenda

**Criterios de aceptación**:
- [x] El sistema muestra número de turnos por día.
- [x] El sistema muestra tasa de confirmación.
- [x] El sistema muestra tasa de cancelación/inasistencia.

### US-010 — Configurar horarios de atención
**Como** profesional
**Quiero** definir mis días y horarios de atención, y la duración de cada turno
**Para** que el sistema calcule correctamente la disponibilidad

**Criterios de aceptación**:
- [x] El profesional puede modificar horario de inicio, fin, días de atención y duración del turno.
- [x] Los cambios se reflejan en el cálculo de disponibilidad futura.

## Épica 6: Registro de pacientes

### US-011 — Registrar paciente nuevo
**Como** sistema
**Quiero** registrar los datos de un paciente nuevo al momento de la reserva
**Para** mantener una base de datos de pacientes y permitir identificación recurrente

**Criterios de aceptación**:
- [x] Se solicitan nombre, apellido, DNI y teléfono.
- [x] El DNI se valida como único.
- [x] Si el paciente ya existe, se identifica automáticamente.

**Reglas relacionadas**: RN-PA-01, RN-PA-02
