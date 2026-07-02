# recordatorio-automatico Specification

## Purpose
TBD - created by archiving change c-10-recordatorios. Update Purpose after archive.
## Requirements
### Requirement: Scheduler detecta turnos para recordar
El sistema SHALL ejecutar un job periódico que consulte la base de datos y retorne todos los turnos en estado `CONFIRMADO` cuya fecha y hora de inicio estén dentro de las próximas `RECORDATORIO_HORAS_ANTES` horas y cuyo campo `recordatorio_enviado` sea `FALSE`.

#### Scenario: Turno dentro de la ventana de recordatorio
- **WHEN** el scheduler ejecuta el job de recordatorios
- **THEN** el sistema incluye en el resultado un turno `CONFIRMADO` programado para dentro de 12 horas con `recordatorio_enviado = FALSE`

#### Scenario: Turno fuera de la ventana
- **WHEN** el scheduler ejecuta el job de recordatorios
- **THEN** el sistema excluye del resultado un turno `CONFIRMADO` programado para dentro de 48 horas (si `RECORDATORIO_HORAS_ANTES = 24`)

#### Scenario: Turno ya recordado
- **WHEN** el scheduler ejecuta el job de recordatorios
- **THEN** el sistema excluye del resultado un turno `CONFIRMADO` con `recordatorio_enviado = TRUE`

### Requirement: Envío de recordatorio por Telegram
El sistema SHALL enviar un mensaje vía Telegram para cada turno detectado, dirigido al **destinatario `TELEGRAM` del turno** (`turno_destinatario` con `canal="TELEGRAM"`), incluyendo la fecha, la hora de inicio y un teclado inline con las opciones: "Confirmar asistencia", "Cancelar" y "Reprogramar". El sistema SHALL NOT usar `paciente.telegram_chat_id` como destino (columna eliminada).

#### Scenario: Envío exitoso al destinatario del turno
- **WHEN** el job detecta un turno candidato con un destinatario `TELEGRAM`
- **THEN** el sistema envía un mensaje de Telegram al `destinatario` del turno con la información del turno y botones inline

#### Scenario: Turno sin destinatario Telegram
- **WHEN** el job detecta un turno que no tiene un destinatario en canal `TELEGRAM`
- **THEN** el sistema marca `recordatorio_enviado = TRUE` para evitar reintentos futuros, loguea un warning y no intenta enviar mensaje

#### Scenario: Recordatorios de un mismo paciente van a chats distintos
- **WHEN** el paciente con DNI `X` tiene el turno 1 con destinatario `TELEGRAM="A"` y el turno 2 con destinatario `TELEGRAM="B"`
- **AND** ambos turnos entran en la ventana de recordatorio
- **THEN** el recordatorio del turno 1 SHALL enviarse al chat `A`
- **AND** el recordatorio del turno 2 SHALL enviarse al chat `B`

#### Scenario: Falla de Telegram API
- **WHEN** el envío de Telegram falla por error de red o API
- **THEN** el sistema loguea el error y NO marca `recordatorio_enviado = TRUE`, permitiendo el reintento en la próxima ejecución del job

### Requirement: Marcado de recordatorio enviado
El sistema SHALL marcar `recordatorio_enviado = TRUE` en el turno inmediatamente después de que el mensaje de Telegram se haya enviado exitosamente.

#### Scenario: Marcado tras envío exitoso
- **WHEN** el mensaje de recordatorio se envía correctamente
- **THEN** el sistema actualiza el turno estableciendo `recordatorio_enviado = TRUE`

### Requirement: Confirmación de asistencia desde recordatorio
El sistema SHALL permitir al paciente confirmar su asistencia al turno directamente desde el mensaje de recordatorio, sin cambiar el estado del turno (permanece `CONFIRMADO`).

#### Scenario: Paciente confirma asistencia
- **WHEN** el paciente presiona el botón "Confirmar asistencia" en el mensaje de recordatorio
- **THEN** el sistema registra la confirmación y responde al paciente con un mensaje de agradecimiento

### Requirement: Cancelación y reprogramación desde recordatorio
El sistema SHALL permitir al paciente cancelar o reprogramar el turno directamente desde el mensaje de recordatorio, reutilizando la lógica existente de cancelación y reprogramación.

#### Scenario: Paciente cancela desde recordatorio
- **WHEN** el paciente presiona el botón "Cancelar" en el mensaje de recordatorio
- **THEN** el sistema ejecuta el flujo de cancelación existente (estado `CANCELADO`, elimina evento de Google Calendar)

#### Scenario: Paciente reprograma desde recordatorio
- **WHEN** el paciente presiona el botón "Reprogramar" en el mensaje de recordatorio
- **THEN** el sistema inicia el wizard conversacional de reprogramación existente (selección de nueva fecha y hora)

