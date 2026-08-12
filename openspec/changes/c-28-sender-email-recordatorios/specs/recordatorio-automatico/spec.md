# recordatorio-automatico — Delta (C-28)

> The blocks below are written in Spanish to match the capability they merge into
> (`openspec/specs/recordatorio-automatico/spec.md`). A MODIFIED block must carry the
> full text of the requirement it replaces.

## MODIFIED Requirements

### Requirement: Envío de recordatorio por Telegram
El sistema SHALL enviar un mensaje vía Telegram para cada turno detectado que tenga un destinatario `TELEGRAM` marcado para notificar (`turno_destinatario` con `canal="TELEGRAM"` y `notificar = TRUE`), incluyendo la fecha, la hora de inicio y un teclado inline con las opciones: "Confirmar asistencia", "Cancelar" y "Reprogramar". El sistema SHALL NOT usar `paciente.telegram_chat_id` como destino (columna eliminada). El canal Telegram SHALL ser uno de los canales del envío multicanal, no el único: la decisión de "no hay a quién notificar" SHALL NOT tomarse dentro de este canal, sino sobre el conjunto de destinatarios del turno.

#### Scenario: Envío exitoso al destinatario del turno
- **WHEN** el job detecta un turno candidato con un destinatario `TELEGRAM` marcado para notificar
- **THEN** el sistema envía un mensaje de Telegram al `destinatario` del turno con la información del turno y botones inline

#### Scenario: Turno sin destinatario Telegram pero con email
- **WHEN** el job detecta un turno sin destinatario `TELEGRAM` y con un destinatario `EMAIL` marcado para notificar
- **THEN** el sistema SHALL NOT loguear "sin destinatario Telegram" ni marcar el recordatorio como enviado por esa razón
- **AND** SHALL entregar el recordatorio por email

#### Scenario: Turno sin ningún destinatario a notificar
- **WHEN** el job detecta un turno que no tiene ningún destinatario marcado para notificar en ningún canal
- **THEN** el sistema marca `recordatorio_enviado = TRUE` para evitar reintentos futuros, loguea un warning y no intenta enviar mensaje

#### Scenario: Recordatorios de un mismo paciente van a chats distintos
- **WHEN** el paciente con DNI `X` tiene el turno 1 con destinatario `TELEGRAM="A"` y el turno 2 con destinatario `TELEGRAM="B"`
- **AND** ambos turnos entran en la ventana de recordatorio
- **THEN** el recordatorio del turno 1 SHALL enviarse al chat `A`
- **AND** el recordatorio del turno 2 SHALL enviarse al chat `B`

#### Scenario: Falla de Telegram API
- **WHEN** el envío de Telegram falla por error de red o API
- **THEN** el sistema loguea el error y NO marca `recordatorio_enviado = TRUE`, permitiendo el reintento en la próxima ejecución del job
- **AND** el destinatario `TELEGRAM` queda sin marca de entrega, de modo que el reintento vuelva a intentar ese canal

### Requirement: Marcado de recordatorio enviado
El sistema SHALL marcar `recordatorio_enviado = TRUE` en el turno cuando **todos** sus destinatarios marcados para notificar hayan sido entregados, y SHALL registrar la entrega de cada canal en su propio `turno_destinatario.enviado_en`. El sistema SHALL NOT marcar el turno como recordado mientras quede un canal elegible sin entregar.

#### Scenario: Marcado tras envío exitoso en todos los canales
- **WHEN** el recordatorio se envía correctamente por todos los canales elegibles del turno
- **THEN** el sistema actualiza el turno estableciendo `recordatorio_enviado = TRUE`

#### Scenario: Entrega parcial no marca el turno
- **WHEN** un canal entrega correctamente y otro falla
- **THEN** el turno SHALL quedar con `recordatorio_enviado = FALSE`
- **AND** solo el canal que entregó SHALL quedar con `enviado_en` seteado

#### Scenario: El reintento no duplica el canal que ya entregó
- **GIVEN** un turno con una entrega parcial de la ejecución anterior
- **WHEN** el job vuelve a ejecutarse
- **THEN** el sistema SHALL reintentar únicamente el canal sin `enviado_en`
- **AND** SHALL NOT enviar un segundo mensaje por el canal ya entregado
