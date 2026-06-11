## ADDED Requirements

### Requirement: ReservaTemporal bloquea un turno único
El sistema SHALL permitir que una `ReservaTemporal` esté asociada a exactamente un `Turno` mediante `turno_id` con constraint `UNIQUE`.

#### Scenario: Reserva exitosa
- **WHEN** se crea una `ReservaTemporal` con `turno_id` válido y `expiracion` futura
- **THEN** la reserva se persiste correctamente

#### Scenario: Reserva duplicada bloqueada
- **WHEN** se intenta crear una segunda `ReservaTemporal` con el mismo `turno_id`
- **THEN** la base de datos rechaza la inserción por violación de `UNIQUE`

### Requirement: ReservaTemporal tiene tiempo de expiración
El sistema SHALL almacenar `expiracion` como TIMESTAMP en `ReservaTemporal`.

#### Scenario: Expiración futura
- **WHEN** se crea una `ReservaTemporal` con `expiracion` dentro de 2 minutos
- **THEN** la reserva se persiste con el timestamp correcto

### Requirement: ReservaTemporal tiene índice para liberación automática
El sistema SHALL crear un índice en `ReservaTemporal` para la columna `expiracion`.

#### Scenario: Índice existe
- **WHEN** se inspecciona el esquema de la tabla `reserva_temporal` en PostgreSQL
- **THEN** el índice `ix_reserva_temporal_expiracion` existe

### Requirement: ReservaTemporal se elimina al confirmar o cancelar turno
El sistema SHALL garantizar que al confirmar o cancelar un `Turno`, la `ReservaTemporal` asociada se elimine (cascade ORM).

#### Scenario: Confirmación elimina reserva
- **WHEN** un `Turno` en estado `RESERVADO_TEMPORAL` pasa a `CONFIRMADO`
- **THEN** la `ReservaTemporal` asociada ya no existe en la base de datos
