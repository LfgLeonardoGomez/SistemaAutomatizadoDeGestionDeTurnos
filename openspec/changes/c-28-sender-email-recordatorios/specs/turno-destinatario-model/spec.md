# turno-destinatario-model — Delta (C-28)

> The blocks below are written in Spanish to match the capability they merge into
> (`openspec/specs/turno-destinatario-model/spec.md`). A MODIFIED block must carry the
> full text of the requirement it replaces, and mixing languages inside one spec file
> would make the merged document unreadable.

## MODIFIED Requirements

### Requirement: Canal de notificación como ENUM extensible
El sistema SHALL definir el canal de un destinatario como un ENUM `canal_notificacion_enum` con los valores `TELEGRAM` y `EMAIL`. El sistema SHALL aceptar `TELEGRAM` y `EMAIL` como canales operativos: ambos tienen un sender que entrega de verdad, y un destinatario `EMAIL` SHALL ser leído por el envío de recordatorios en las mismas condiciones que uno `TELEGRAM`.

#### Scenario: Canal válido
- **WHEN** se crea un `turno_destinatario` con `canal="TELEGRAM"`
- **THEN** la inserción es exitosa

#### Scenario: Canal inválido
- **WHEN** se intenta crear un `turno_destinatario` con un canal no definido en el ENUM
- **THEN** la base de datos rechaza la operación

#### Scenario: El canal EMAIL es operativo
- **WHEN** un turno tiene un destinatario con `canal="EMAIL"` marcado para notificar
- **THEN** el envío de recordatorios SHALL entregar por ese canal, y SHALL NOT tratarlo como un canal reservado para uso futuro

## ADDED Requirements

### Requirement: El destinatario declara si debe recibir notificaciones
El sistema SHALL almacenar en cada `turno_destinatario` una marca `notificar` (BOOLEAN NOT NULL DEFAULT TRUE) que indica si ese canal debe recibir el recordatorio. El sistema SHALL usar esa marca — y NO la existencia de la fila — para decidir si entrega por ese canal, de modo que un destinatario silenciado siga siendo utilizable como índice de chat a turno.

#### Scenario: Filas existentes conservan el comportamiento actual
- **WHEN** se aplica la migración sobre destinatarios ya existentes
- **THEN** todos quedan con `notificar = TRUE` y siguen recibiendo el recordatorio exactamente como antes

#### Scenario: Silenciar un canal no rompe la gestión del turno
- **GIVEN** un turno cuyo destinatario `TELEGRAM` tiene `notificar = FALSE`
- **WHEN** el chat consulta sus turnos gestionables
- **THEN** el turno SHALL seguir apareciendo, porque la fila `TELEGRAM` sigue existiendo
- **AND** el recordatorio SHALL NOT enviarse por Telegram

#### Scenario: Un destinatario nuevo notifica por defecto
- **WHEN** se registra un destinatario sin especificar la marca
- **THEN** queda con `notificar = TRUE`

### Requirement: El destinatario registra su propia entrega
El sistema SHALL almacenar en cada `turno_destinatario` la marca temporal `enviado_en` (TIMESTAMP NULL), que registra cuándo se entregó el recordatorio por ESE canal. `NULL` SHALL significar "todavía no entregado".

#### Scenario: Marca temporal por canal
- **WHEN** el recordatorio se entrega por el canal `EMAIL` de un turno que también tiene `TELEGRAM`
- **THEN** solo el destinatario `EMAIL` queda con `enviado_en` seteado

#### Scenario: Filas existentes arrancan sin entregar
- **WHEN** se aplica la migración sobre destinatarios ya existentes
- **THEN** todos quedan con `enviado_en = NULL`

#### Scenario: Eliminación de turno elimina sus destinatarios y sus marcas
- **WHEN** se elimina un `Turno` que tiene destinatarios con marcas de entrega
- **THEN** la base de datos SHALL eliminar los `turno_destinatario` en cascada, junto con sus marcas
