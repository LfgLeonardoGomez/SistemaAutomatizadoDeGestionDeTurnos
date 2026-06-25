## MODIFIED Requirements

### Requirement: Crear paciente
El sistema SHALL permitir la creación de un paciente con los datos mínimos requeridos **asociado al profesional autenticado**. El DNI SHALL ser único dentro del scope del `profesional_id`.

#### Scenario: Creación exitosa
- **WHEN** el profesional autenticado envía un POST a /pacientes con nombre, apellido, DNI y teléfono válidos
- **THEN** el sistema crea el paciente con `profesional_id` del profesional autenticado
- **AND** retorna 201 Created con el objeto paciente

#### Scenario: DNI duplicado dentro del mismo profesional
- **WHEN** el profesional autenticado envía un POST a /pacientes con un DNI que ya existe para ese mismo profesional
- **THEN** el sistema retorna 409 Conflict indicando que el DNI ya está registrado para ese profesional

#### Scenario: DNI existente en otro profesional
- **WHEN** el profesional B envía un POST a /pacientes con un DNI que ya existe para el profesional A
- **THEN** el sistema crea el paciente para el profesional B
- **AND** retorna 201 Created

#### Scenario: Datos incompletos
- **WHEN** se envía un POST a /pacientes sin nombre, apellido, DNI o teléfono
- **THEN** el sistema retorna 422 Unprocessable Entity indicando los campos faltantes

### Requirement: Auto-identificar paciente por DNI
El sistema SHALL identificar automáticamente un paciente existente por su DNI **dentro del scope del profesional autenticado** en lugar de crear un duplicado.

#### Scenario: Paciente nuevo para el profesional
- **WHEN** el profesional autenticado solicita la creación de un paciente con un DNI que no existe para ese profesional
- **THEN** el sistema crea el paciente con `profesional_id` del profesional autenticado
- **AND** retorna el objeto creado

#### Scenario: Paciente existente para el profesional
- **WHEN** el profesional autenticado solicita la creación de un paciente con un DNI que ya existe para ese profesional
- **THEN** el sistema retorna el paciente existente sin crear un duplicado
- **AND** el `profesional_id` del paciente existente coincide con el profesional autenticado

### Requirement: Consultar paciente
El sistema SHALL permitir consultar los datos de un paciente por su ID **solo si pertenece al profesional autenticado**, incluyendo su historial de turnos.

#### Scenario: Paciente encontrado y pertenece al profesional
- **WHEN** el profesional autenticado envía un GET a /pacientes/{id} de un paciente que existe y tiene su `profesional_id`
- **THEN** el sistema retorna 200 OK con los datos del paciente y su historial de turnos

#### Scenario: Paciente no pertenece al profesional
- **WHEN** el profesional B envía un GET a /pacientes/{id} de un paciente que pertenece al profesional A
- **THEN** el sistema retorna 404 Not Found

#### Scenario: Paciente no encontrado
- **WHEN** se envía un GET a /pacientes/{id} de un paciente que no existe
- **THEN** el sistema retorna 404 Not Found

### Requirement: Listar turnos de paciente
El sistema SHALL permitir listar todos los turnos asociados a un paciente **solo si el paciente pertenece al profesional autenticado**.

#### Scenario: Listar turnos de paciente del profesional
- **WHEN** el profesional autenticado envía un GET a /pacientes/{id}/turnos de un paciente con turnos que pertenece a él
- **THEN** el sistema retorna 200 OK con la lista de turnos del paciente

#### Scenario: Paciente sin turnos
- **WHEN** el profesional autenticado envía un GET a /pacientes/{id}/turnos de un paciente sin turnos
- **THEN** el sistema retorna 200 OK con una lista vacía

#### Scenario: Paciente no pertenece al profesional
- **WHEN** el profesional B envía un GET a /pacientes/{id}/turnos de un paciente que pertenece al profesional A
- **THEN** el sistema retorna 404 Not Found
