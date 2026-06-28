## MODIFIED Requirements

### Requirement: Sistema permite reservar un turno temporalmente
El sistema SHALL permitir la creación de un turno en estado `RESERVADO_TEMPORAL` con una `ReservaTemporal` asociada que incluya fecha de expiración. La expiración SHALL ser calculada como `NOW_UTC() + RESERVA_TEMPORAL_MINUTOS` (default 10 minutos). El timestamp de expiración SHALL ser timezone-aware en UTC al momento de calcularse y SHALL persistirse como naive UTC (`datetime.now(timezone.utc).replace(tzinfo=None)`) para mantener compatibilidad con la columna `TIMESTAMP WITHOUT TIME ZONE` de PostgreSQL. **El sistema SHALL garantizar que solo un Turno activo (`DISPONIBLE`, `RESERVADO_TEMPORAL` o `CONFIRMADO`) puede existir por `(profesional_id, fecha, hora_inicio)` mediante un índice único parcial en la tabla `turno`. Si dos requests concurrentes intentan crear el mismo slot activo, el segundo SHALL recibir `TurnoNoDisponibleError` por violación de la constraint `uq_turno_active_slot` (traducido de `IntegrityError` pgcode `23505`).**

#### Scenario: Reserva temporal exitosa
- **WHEN** el paciente selecciona un slot disponible
- **THEN** el sistema SHALL crear un `Turno` en estado `RESERVADO_TEMPORAL`
- **AND** el sistema SHALL crear una `ReservaTemporal` con `expiracion` calculada
- **AND** el sistema SHALL retornar el turno creado con HTTP 201

#### Scenario: Reserva temporal bloqueada por turno activo del mismo paciente
- **WHEN** el paciente intenta reservar un slot pero ya tiene un turno en estado `RESERVADO_TEMPORAL` o `CONFIRMADO`
- **THEN** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Condición de carrera en reserva simultánea
- **WHEN** dos pacientes intentan reservar el mismo slot disponible exactamente al mismo tiempo
- **THEN** el sistema SHALL garantizar que solo uno de los dos obtenga la reserva
- **AND** el segundo SHALL recibir un error indicando que el slot ya no está disponible
- **AND** la garantía SHALL ser provista por la constraint de base de datos `uq_turno_active_slot` (no solo por la lógica de aplicación)

#### Scenario: Constraint única parcial permite múltiples Turnos CANCELADOS para el mismo slot
- **WHEN** un paciente cancela su turno (estado pasa a `CANCELADO`)
- **AND** otro paciente intenta reservar el mismo slot
- **THEN** el sistema SHALL permitir la nueva reserva porque la constraint `uq_turno_active_slot` solo aplica a estados activos (`DISPONIBLE`, `RESERVADO_TEMPORAL`, `CONFIRMADO`)
- **AND** SHALL haber dos `Turno` rows en la DB con el mismo `(profesional_id, fecha, hora_inicio)`: uno `CANCELADO` (histórico) y uno `RESERVADO_TEMPORAL` (nuevo)

#### Scenario: Reserva con IntegrityError se traduce a TurnoNoDisponibleError
- **WHEN** el servicio `reservar_turno` intenta hacer `db.flush()` de un nuevo Turno
- **AND** PostgreSQL rechaza el INSERT por violación de la constraint `uq_turno_active_slot` (`IntegrityError`, pgcode `23505`)
- **THEN** el servicio SHALL capturar el `IntegrityError`
- **AND** SHALL hacer `db.rollback()` para limpiar la sesión
- **AND** SHALL lanzar `TurnoNoDisponibleError` con mensaje genérico
- **AND** el router SHALL mapear a HTTP 409 Conflict
