## ADDED Requirements

### Requirement: Crear paciente
El sistema SHALL permitir la creación de un paciente con los datos mínimos requeridos.

#### Scenario: Creación exitosa
- **WHEN** se envía un POST a /pacientes con nombre, apellido, DNI y teléfono válidos
- **THEN** el sistema crea el paciente y retorna 201 Created con el objeto paciente

#### Scenario: DNI duplicado
- **WHEN** se envía un POST a /pacientes con un DNI que ya existe en el sistema
- **THEN** el sistema retorna 409 Conflict indicando que el DNI ya está registrado

#### Scenario: Datos incompletos
- **WHEN** se envía un POST a /pacientes sin nombre, apellido, DNI o teléfono
- **THEN** el sistema retorna 422 Unprocessable Entity indicando los campos faltantes

### Requirement: Auto-identificar paciente por DNI
El sistema SHALL identificar automáticamente un paciente existente por su DNI en lugar de crear un duplicado.

#### Scenario: Paciente nuevo
- **WHEN** se solicita la creación de un paciente con un DNI que no existe en el sistema
- **THEN** el sistema crea el paciente y retorna el objeto creado

#### Scenario: Paciente existente
- **WHEN** se solicita la creación de un paciente con un DNI que ya existe en el sistema
- **THEN** el sistema retorna el paciente existente sin crear un duplicado

### Requirement: Consultar paciente
El sistema SHALL permitir consultar los datos de un paciente por su ID, incluyendo su historial de turnos.

#### Scenario: Paciente encontrado
- **WHEN** se envía un GET a /pacientes/{id} de un paciente existente
- **THEN** el sistema retorna 200 OK con los datos del paciente y su historial de turnos

#### Scenario: Paciente no encontrado
- **WHEN** se envía un GET a /pacientes/{id} de un paciente que no existe
- **THEN** el sistema retorna 404 Not Found

### Requirement: Listar turnos de paciente
El sistema SHALL permitir listar todos los turnos asociados a un paciente.

#### Scenario: Listar turnos de paciente existente
- **WHEN** se envía un GET a /pacientes/{id}/turnos de un paciente con turnos
- **THEN** el sistema retorna 200 OK con la lista de turnos del paciente

#### Scenario: Paciente sin turnos
- **WHEN** se envía un GET a /pacientes/{id}/turnos de un paciente sin turnos
- **THEN** el sistema retorna 200 OK con una lista vacía

#### Scenario: Paciente no encontrado
- **WHEN** se envía un GET a /pacientes/{id}/turnos de un paciente que no existe
- **THEN** el sistema retorna 404 Not Found
