## MODIFIED Requirements

### Requirement: Paciente se registra con datos mínimos
El sistema SHALL permitir el registro de un paciente con nombre, apellido, DNI (único dentro del profesional) y teléfono obligatorios, vinculado obligatoriamente a un `Profesional`.

#### Scenario: Registro exitoso
- **WHEN** se crea un `Paciente` con nombre, apellido, DNI único dentro del profesional, teléfono y `profesional_id`
- **THEN** el paciente se persiste en la base de datos con `creado_en` automático

#### Scenario: DNI duplicado bloqueado
- **WHEN** se intenta crear un `Paciente` con un DNI que ya existe para el mismo `profesional_id`
- **THEN** la base de datos lanza una violación de constraint `UNIQUE` y rechaza la inserción

#### Scenario: Datos mínimos faltantes
- **WHEN** se intenta crear un `Paciente` sin nombre, apellido, DNI, teléfono o `profesional_id`
- **THEN** la base de datos rechaza la inserción por campos obligatorios

#### Scenario: Paciente con múltiples turnos
- **WHEN** un `Paciente` tiene 3 turnos asociados
- **THEN** la consulta `paciente.turnos` retorna los 3 turnos ordenados cronológicamente

#### Scenario: Eliminación de paciente con turnos
- **WHEN** se elimina un `Paciente` que tiene turnos asociados
- **THEN** la base de datos rechaza la eliminación o la maneja según la política de FK definida

#### Scenario: DNI duplicado entre profesionales permitido
- **WHEN** se crea un `Paciente` con DNI "12345678" para el profesional 1
- **AND** se crea otro `Paciente` con DNI "12345678" para el profesional 2
- **THEN** ambos registros se persisten exitosamente

## ADDED Requirements

### Requirement: Paciente tiene relación con Profesional
El sistema SHALL exigir `profesional_id` como FK a `Profesional` en `Paciente` con `ondelete="CASCADE"`.

#### Scenario: Paciente sin profesional
- **WHEN** se intenta crear un `Paciente` sin `profesional_id`
- **THEN** la base de datos rechaza la inserción

#### Scenario: Eliminación de profesional elimina pacientes
- **WHEN** se elimina un `Profesional` que tiene pacientes asociados
- **THEN** la base de datos elimina los pacientes en cascada
