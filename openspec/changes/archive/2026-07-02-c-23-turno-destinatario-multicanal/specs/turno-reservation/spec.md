## ADDED Requirements

### Requirement: La reserva registra el destinatario de origen
El sistema SHALL aceptar de forma opcional un `telegram_chat_id` al reservar un turno. Cuando se provea, el sistema SHALL registrar un `turno_destinatario` con `canal="TELEGRAM"` y `destinatario=telegram_chat_id` para el turno recién creado, dentro de la misma transacción de la reserva (Patrón A: sin commit propio). Cuando no se provea, el sistema SHALL crear el turno sin destinatario y SHALL diferir el registro del destinatario a la confirmación.

#### Scenario: Reserva desde Telegram fija el destinatario
- **WHEN** el paciente reserva un slot desde el chat de Telegram `"555001"`
- **THEN** el sistema SHALL crear el `Turno` en estado `RESERVADO_TEMPORAL`
- **AND** el sistema SHALL registrar un destinatario `TELEGRAM` con valor `"555001"` para ese turno

#### Scenario: Reserva sin chat_id no crea destinatario
- **WHEN** se reserva un turno sin proporcionar `telegram_chat_id`
- **THEN** el sistema SHALL crear el `Turno` sin destinatarios
- **AND** el registro del destinatario SHALL quedar pendiente para la confirmación

### Requirement: La confirmación registra o actualiza los destinatarios del turno
El sistema SHALL aceptar en la confirmación un `telegram_chat_id` opcional y un `email` opcional, además de los datos del beneficiario (nombre, apellido, DNI, teléfono). El sistema SHALL resolver al beneficiario por DNI reutilizando `crear_o_obtener_paciente`, y SHALL registrar o actualizar (upsert por `UNIQUE(turno_id, canal)`) los `turno_destinatario` correspondientes: un destinatario `TELEGRAM` si se provee `telegram_chat_id`, y un destinatario `EMAIL` si se provee `email`. La operación SHALL ejecutarse dentro de la transacción de la confirmación (Patrón A).

#### Scenario: Confirmación con Telegram fija el destinatario Telegram
- **WHEN** se confirma un turno proporcionando `telegram_chat_id="555002"` y datos del beneficiario
- **THEN** el sistema SHALL identificar/crear al beneficiario por DNI
- **AND** el turno confirmado SHALL tener un destinatario `TELEGRAM` con valor `"555002"`

#### Scenario: Confirmación con email modela el canal EMAIL
- **WHEN** se confirma un turno proporcionando `email="abuela@example.com"`
- **THEN** el turno confirmado SHALL tener un destinatario `EMAIL` con valor `"abuela@example.com"`
- **AND** el sistema SHALL persistir el destinatario aunque el envío por email no esté implementado

#### Scenario: Confirmación con ambos canales
- **WHEN** se confirma un turno proporcionando `telegram_chat_id` y `email`
- **THEN** el turno SHALL tener dos destinatarios, uno `TELEGRAM` y uno `EMAIL`

#### Scenario: Confirmación no sobrescribe el destinatario de otro turno del mismo paciente
- **WHEN** el paciente con DNI `X` ya tiene el turno 1 con destinatario `TELEGRAM="A"`
- **AND** se confirma un turno 2 del mismo DNI `X` con `telegram_chat_id="B"`
- **THEN** el turno 2 SHALL tener destinatario `TELEGRAM="B"`
- **AND** el turno 1 SHALL conservar su destinatario `TELEGRAM="A"` sin cambios
