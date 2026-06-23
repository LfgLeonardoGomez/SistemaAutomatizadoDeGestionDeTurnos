## MODIFIED Requirements

### Requirement: Sistema permite consultar disponibilidad de turnos
El sistema SHALL exponer un endpoint que devuelva los slots disponibles para una fecha dada **del profesional autenticado**, calculados como horarios posibles según configuración del profesional MINUS turnos en estado `CONFIRMADO` o `RESERVADO_TEMPORAL` que pertenezcan a ese profesional.

#### Scenario: Consulta con slots disponibles
- **WHEN** el profesional autenticado solicita disponibilidad para una fecha con horarios libres
- **THEN** el sistema SHALL retornar la lista de slots disponibles con hora de inicio y fin
- **AND** SHALL filtrar por `profesional_id` del profesional autenticado

#### Scenario: Consulta sin slots disponibles
- **WHEN** el profesional autenticado solicita disponibilidad para una fecha donde todos los slots están ocupados
- **THEN** el sistema SHALL retornar una lista vacía
- **AND** el sistema SHALL responder con HTTP 200

### Requirement: Sistema permite reservar un turno temporalmente
El sistema SHALL permitir la creación de un turno en estado `RESERVADO_TEMPORAL` con una `ReservaTemporal` asociada que incluya fecha de expiración. La reserva SHALL pertenecer al `profesional_id` del profesional autenticado o explicitamente proporcionado. La validación de RN-TU-01 SHALL considerar únicamente turnos activos del mismo `profesional_id`.

#### Scenario: Reserva temporal exitosa
- **WHEN** el paciente selecciona un slot disponible del profesional autenticado
- **THEN** el sistema SHALL crear un `Turno` en estado `RESERVADO_TEMPORAL` con `profesional_id` del profesional autenticado
- **AND** el sistema SHALL crear una `ReservaTemporal` con `expiracion` calculada
- **AND** el sistema SHALL retornar el turno creado con HTTP 201

#### Scenario: Reserva temporal bloqueada por turno activo del mismo paciente con el mismo profesional
- **WHEN** el paciente intenta reservar un slot del profesional A pero ya tiene un turno activo con el profesional A
- **THEN** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

#### Scenario: Reserva temporal permitida con otro profesional
- **WHEN** el paciente tiene un turno activo con el profesional A
- **AND** intenta reservar un slot con el profesional B
- **THEN** el sistema SHALL permitir la reserva

#### Scenario: Condición de carrera en reserva simultánea
- **WHEN** dos pacientes intentan reservar el mismo slot disponible exactamente al mismo tiempo con el mismo profesional
- **THEN** el sistema SHALL garantizar que solo uno de los dos obtenga la reserva
- **AND** el segundo SHALL recibir un error indicando que el slot ya no está disponible

### Requirement: Sistema permite confirmar un turno reservado
El sistema SHALL permitir confirmar un turno en estado `RESERVADO_TEMPORAL` **que pertenezca al profesional autenticado**. Al confirmar, el sistema SHALL validar que el paciente no tenga otro turno activo **con ese mismo profesional**, SHALL registrar/identificar al paciente (scopado por `profesional_id`), SHALL pasar el turno a `CONFIRMADO`, SHALL eliminar la `ReservaTemporal` asociada y SHALL crear un evento en Google Calendar usando las credenciales del profesional.

#### Scenario: Confirmación exitosa
- **WHEN** el paciente confirma un turno en `RESERVADO_TEMPORAL` del profesional autenticado proporcionando sus datos
- **THEN** el sistema SHALL validar que el paciente no tenga otro turno activo con ese profesional
- **AND** el sistema SHALL registrar o identificar al paciente con `profesional_id` del profesional autenticado
- **AND** el sistema SHALL actualizar el turno a estado `CONFIRMADO`
- **AND** el sistema SHALL eliminar la `ReservaTemporal` asociada
- **AND** el sistema SHALL crear un evento en Google Calendar del profesional
- **AND** el sistema SHALL retornar el turno confirmado con HTTP 200

#### Scenario: Confirmación de turno de otro profesional
- **WHEN** el profesional B intenta confirmar un turno que pertenece al profesional A
- **THEN** el sistema SHALL retornar HTTP 404 Not Found

#### Scenario: Confirmación con doble turno activo del mismo paciente con el mismo profesional
- **WHEN** el paciente intenta confirmar un turno pero adquiere otro turno activo con el mismo profesional en paralelo
- **THEN** el sistema SHALL detectar la violación de RN-TU-01 atomically
- **AND** el sistema SHALL rechazar la operación con error de negocio
- **AND** el sistema SHALL retornar HTTP 409 Conflict

### Requirement: Sistema libera reservas temporales vencidas automáticamente
El sistema SHALL ejecutar un job periódico que identifique las `ReservaTemporal` cuya `expiracion` sea menor a `NOW()`, actualice los `Turno` asociados a estado `DISPONIBLE` y elimine las `ReservaTemporal` vencidas. El job SHALL operar sobre todos los profesionales activos iterando por `profesional_id`.

#### Scenario: Expiración automática de reserva temporal
- **WHEN** el job de limpieza ejecuta y encuentra una `ReservaTemporal` vencida del profesional A
- **THEN** el sistema SHALL actualizar el `Turno` asociado a estado `DISPONIBLE`
- **AND** el sistema SHALL eliminar la `ReservaTemporal`
- **AND** el sistema SHALL registrar la operación en logs incluyendo el `profesional_id`
