## MODIFIED Requirements

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
