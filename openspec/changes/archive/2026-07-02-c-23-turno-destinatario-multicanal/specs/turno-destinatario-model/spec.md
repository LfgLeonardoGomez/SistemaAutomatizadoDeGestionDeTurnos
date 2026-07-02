## ADDED Requirements

### Requirement: La identidad del paciente se desacopla del destinatario de notificación
El sistema SHALL identificar al paciente (beneficiario del turno) exclusivamente por su DNI, único dentro del profesional (`UNIQUE(profesional_id, dni)`), y SHALL modelar el destinatario de notificación (a quién se contacta por ESTE turno) en una entidad separada asociada al `Turno`, no al `Paciente`. El sistema SHALL NOT usar un identificador de chat almacenado en `Paciente` como destinatario de notificaciones. La columna `paciente.telegram_chat_id` SHALL ser eliminada.

#### Scenario: Un mismo paciente gestionado desde múltiples chats
- **WHEN** un paciente con DNI `X` es reservado desde el chat de Telegram `A` para el turno 1
- **AND** el mismo paciente con DNI `X` es reservado desde el chat de Telegram `B` para el turno 2
- **THEN** el sistema SHALL persistir un único `Paciente` (DNI `X`) para el profesional
- **AND** el turno 1 SHALL tener un destinatario `TELEGRAM` con valor `A`
- **AND** el turno 2 SHALL tener un destinatario `TELEGRAM` con valor `B`
- **AND** ninguna de las dos reservas SHALL sobrescribir el destinatario de la otra

#### Scenario: El paciente ya no expone un chat_id propio
- **WHEN** se inspecciona el esquema de la tabla `paciente`
- **THEN** la columna `telegram_chat_id` SHALL NOT existir

### Requirement: Canal de notificación como ENUM extensible
El sistema SHALL definir el canal de un destinatario como un ENUM `canal_notificacion_enum` con los valores `TELEGRAM` y `EMAIL`. El sistema SHALL aceptar `TELEGRAM` como canal operativo en esta versión y SHALL modelar `EMAIL` para uso futuro sin requerir cambios de esquema adicionales.

#### Scenario: Canal válido
- **WHEN** se crea un `turno_destinatario` con `canal="TELEGRAM"`
- **THEN** la inserción es exitosa

#### Scenario: Canal inválido
- **WHEN** se intenta crear un `turno_destinatario` con un canal no definido en el ENUM
- **THEN** la base de datos rechaza la operación

### Requirement: Turno tiene destinatarios de notificación por canal
El sistema SHALL permitir que un `Turno` tenga cero o más `turno_destinatario`, cada uno con `turno_id` (FK a `turno`, `ondelete="CASCADE"`), `canal` (ENUM) y `destinatario` (VARCHAR(255): `chat_id` para `TELEGRAM`, dirección de email para `EMAIL`). El sistema SHALL garantizar como máximo un destinatario por canal por turno mediante `UNIQUE(turno_id, canal)`.

#### Scenario: Turno con un solo canal (Telegram)
- **WHEN** se registra para un turno un destinatario `TELEGRAM` con valor `"123456"`
- **THEN** el turno SHALL exponer exactamente un destinatario en canal `TELEGRAM` con ese valor

#### Scenario: Turno con ambos canales
- **WHEN** se registra para un turno un destinatario `TELEGRAM` y un destinatario `EMAIL`
- **THEN** el turno SHALL exponer dos destinatarios, uno por canal

#### Scenario: Un destinatario por canal (idempotencia)
- **WHEN** se registra un segundo destinatario `TELEGRAM` para un turno que ya tiene uno
- **THEN** el sistema SHALL actualizar el destinatario `TELEGRAM` existente en lugar de crear un duplicado
- **AND** la constraint `UNIQUE(turno_id, canal)` SHALL impedir dos filas del mismo canal para el mismo turno

#### Scenario: Eliminación de turno elimina sus destinatarios
- **WHEN** se elimina un `Turno` que tiene destinatarios asociados
- **THEN** la base de datos SHALL eliminar los `turno_destinatario` en cascada
