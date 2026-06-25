## ADDED Requirements

### Requirement: Scoping obligatorio por profesional_id en todas las operaciones
El sistema SHALL garantizar que toda operación de lectura o escritura en el backend esté scopeada por `profesional_id`. Ningún endpoint, servicio o job del scheduler SHALL retornar o modificar datos que no pertenezcan al profesional autenticado o especificado.

#### Scenario: Endpoint rechaza request sin autenticación
- **WHEN** se envía un GET a /turnos/disponibles sin header Authorization
- **THEN** el sistema SHALL retornar HTTP 401 Unauthorized

#### Scenario: Endpoint filtra datos por profesional autenticado
- **WHEN** el profesional A envía un GET a /pacientes con un token JWT válido
- **THEN** el sistema SHALL retornar únicamente los pacientes cuyo `profesional_id` coincida con el del profesional A
- **AND** SHALL excluir pacientes del profesional B

#### Scenario: Servicio rechaza operación sin profesional_id
- **WHEN** se invoca `turno_service.reservar_turno(db, fecha, hora_inicio)` sin proporcionar `profesional_id`
- **THEN** el sistema SHALL rechazar la invocación en tiempo de tipado (TypeError) o fallar la validación

### Requirement: Eliminar _get_profesional_default
El sistema SHALL eliminar completamente la función `_get_profesional_default()` y todos sus call sites. Ningún servicio SHALL asumir un único profesional global.

#### Scenario: Código sin _get_profesional_default
- **WHEN** se ejecuta `grep -r "_get_profesional_default" app/`
- **THEN** no SHALL encontrar coincidencias

### Requirement: Tests de aislamiento entre profesionales
El sistema SHALL incluir tests que verifiquen que un profesional no puede acceder ni modificar datos de otro profesional.

#### Scenario: Aislamiento de pacientes
- **WHEN** el profesional A crea un paciente con DNI "12345678"
- **AND** el profesional B intenta obtener ese paciente por ID vía GET /pacientes/{id}
- **THEN** el sistema SHALL retornar HTTP 404 Not Found al profesional B

#### Scenario: Aislamiento de turnos
- **WHEN** el profesional A crea un turno confirmado
- **AND** el profesional B intenta cancelar ese turno vía PUT /turnos/{id}/cancelar
- **THEN** el sistema SHALL retornar HTTP 404 Not Found al profesional B

#### Scenario: Aislamiento de API Key
- **WHEN** se envía una request con X-API-Key del profesional A a un endpoint que expone datos del profesional B
- **THEN** el sistema SHALL retornar HTTP 404 Not Found o una lista vacía

#### Scenario: Aislamiento de autenticación JWT
- **WHEN** se decodifica un token JWT válido del profesional A
- **THEN** `get_current_profesional` SHALL retornar el objeto Profesional A
- **AND** SHALL NOT retornar el Profesional B

### Requirement: RN-TU-01 scopado por profesional
El sistema SHALL permitir que un paciente tenga turnos activos (RESERVADO_TEMPORAL o CONFIRMADO) con diferentes profesionales simultáneamente. La validación de "un turno activo a la vez" SHALL aplicar únicamente dentro del mismo `profesional_id`.

#### Scenario: Paciente con turnos activos en diferentes profesionales
- **WHEN** el paciente P tiene un turno CONFIRMADO con el profesional A
- **AND** el paciente P intenta reservar un turno con el profesional B
- **THEN** el sistema SHALL permitir la reserva con el profesional B
- **AND** SHALL NOT lanzar PacienteConTurnoActivoError

#### Scenario: Paciente con turno activo en el mismo profesional
- **WHEN** el paciente P tiene un turno CONFIRMADO con el profesional A
- **AND** el paciente P intenta reservar otro turno con el profesional A
- **THEN** el sistema SHALL rechazar la reserva con PacienteConTurnoActivoError
