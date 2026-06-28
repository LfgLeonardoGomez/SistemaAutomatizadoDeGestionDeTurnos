## MODIFIED Requirements

### Requirement: Sistema permite reservar un turno temporalmente
El sistema SHALL permitir la creación de un turno en estado `RESERVADO_TEMPORAL` con una `ReservaTemporal` asociada que incluya fecha de expiración. La expiración SHALL ser calculada como `NOW_UTC() + RESERVA_TEMPORAL_MINUTOS` (default 10 minutos). El timestamp de expiración SHALL ser timezone-aware en UTC al momento de calcularse y SHALL persistirse como naive UTC (`datetime.now(timezone.utc).replace(tzinfo=None)`) para mantener compatibilidad con la columna `TIMESTAMP WITHOUT TIME ZONE` de PostgreSQL.

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

### Requirement: Sistema permite confirmar un turno reservado
El sistema SHALL permitir confirmar un turno en estado `RESERVADO_TEMPORAL`. Al confirmar, el sistema SHALL validar que el paciente no tenga otro turno activo, SHALL registrar/identificar al paciente, SHALL pasar el turno a `CONFIRMADO`, SHALL eliminar la `ReservaTemporal` asociada y SHALL crear un evento en Google Calendar. **El sistema SHALL obtener la `ReservaTemporal` con `SELECT FOR UPDATE` para serializar lecturas concurrentes durante la verificación de expiración, y SHALL comparar `reserva.expiracion` contra `datetime.now(timezone.utc).replace(tzinfo=None)` para garantizar consistencia temporal independientemente del timezone del servidor.**

#### Scenario: Confirmación exitosa
- **WHEN** el paciente confirma un turno en `RESERVADO_TEMPORAL` proporcionando sus datos
- **THEN** el sistema SHALL validar que el paciente no tenga otro turno activo
- **AND** el sistema SHALL registrar o identificar al paciente
- **AND** el sistema SHALL actualizar el turno a estado `CONFIRMADO`
- **AND** el sistema SHALL eliminar la `ReservaTemporal` asociada
- **AND** el sistema SHALL crear un evento en Google Calendar
- **AND** el sistema SHALL retornar el turno confirmado con HTTP 200

#### Scenario: Confirmación de turno ya expirado
- **WHEN** el paciente intenta confirmar un turno cuya `ReservaTemporal` ya expiró
- **THEN** el sistema SHALL rechazar la operación con error de negocio (`TurnoExpiradoError`)
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Confirmación de turno con comparación timezone-aware
- **WHEN** el servidor está configurado con un timezone distinto a UTC (ej. `America/Argentina/Buenos_Aires`)
- **AND** una `ReservaTemporal` tiene `expiracion = 2026-06-27 12:00:00` (naive UTC)
- **AND** la hora actual UTC es `2026-06-27 12:00:30`
- **THEN** el sistema SHALL detectar la expiración correctamente usando `datetime.now(timezone.utc).replace(tzinfo=None)`
- **AND** SHALL lanzar `TurnoExpiradoError`

#### Scenario: Confirmación con doble turno activo del mismo paciente
- **WHEN** el paciente intenta confirmar un turno pero adquiere otro turno activo en paralelo
- **THEN** el sistema SHALL detectar la violación de RN-TU-01 atomically
- **AND** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Confirmación persiste event_id de Google Calendar
- **WHEN** se confirma un turno y `CalendarService.create_event()` retorna `"event_abc123"`
- **THEN** el sistema SHALL asignar `turno.google_event_id = "event_abc123"`
- **AND** el sistema SHALL hacer commit para persistir el valor en base de datos
- **AND** el sistema SHALL retornar el turno con `google_event_id` poblado

#### Scenario: Confirmación con fallo de Google Calendar no persiste event_id
- **WHEN** se confirma un turno y `CalendarService.create_event()` lanza una excepción
- **THEN** el turno SHALL quedar en estado `CONFIRMADO`
- **AND** `turno.google_event_id` SHALL ser `NULL`
- **AND** el sistema SHALL registrar el error en logs

#### Scenario: Confirmación con SELECT FOR UPDATE sobre ReservaTemporal
- **WHEN** dos requests concurrentes intentan confirmar el mismo `turno_id` simultáneamente
- **THEN** el segundo SHALL esperar a que el primero libere el lock sobre `ReservaTemporal`
- **AND** SHALL ver el estado actualizado (reserva eliminada si el primero confirmó, o turno ya no en `RESERVADO_TEMPORAL`)

### Requirement: Sistema libera reservas temporales vencidas automáticamente
El sistema SHALL ejecutar un job periódico que identifique las `ReservaTemporal` cuya `expiracion` sea menor a `NOW_UTC()`, actualice los `Turno` asociados a estado `DISPONIBLE` y elimine las `ReservaTemporal` vencidas. **El job SHALL ejecutar todas las liberaciones de un profesional en una sola transacción, y SHALL evaluar la lista de espera para cada slot liberado dentro de la misma transacción antes de hacer el commit final.**

#### Scenario: Expiración automática de reserva temporal
- **WHEN** el job de limpieza ejecuta y encuentra una `ReservaTemporal` vencida
- **THEN** el sistema SHALL actualizar el `Turno` asociado a estado `DISPONIBLE`
- **AND** el sistema SHALL eliminar la `ReservaTemporal`
- **AND** el sistema SHALL registrar la operación en logs

#### Scenario: No hay reservas vencidas
- **WHEN** el job de limpieza ejecuta y no encuentra reservas vencidas
- **THEN** el sistema SHALL no modificar ningún registro
- **AND** el sistema SHALL registrar que no hubo acciones

#### Scenario: Liberación con evaluación de lista de espera atómica
- **WHEN** el job libera una reserva vencida y existe un paciente en lista de espera para esa fecha
- **THEN** el sistema SHALL evaluar la lista de espera dentro de la misma transacción
- **AND** SHALL crear una nueva `ReservaTemporal` para el paciente notificado
- **AND** SHALL commitear todo el bloque (liberación + nueva reserva) en una sola operación atómica
- **AND** si la notificación a Telegram falla, SHALL hacer rollback completo (la reserva original queda en su estado, sin liberar)

## ADDED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
