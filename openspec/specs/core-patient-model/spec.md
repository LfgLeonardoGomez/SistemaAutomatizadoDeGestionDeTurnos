## ADDED Requirements

### Requirement: Paciente se registra con datos mínimos
El sistema SHALL permitir el registro de un paciente con nombre, apellido, DNI (único) y teléfono obligatorios.

#### Scenario: Registro exitoso
- **WHEN** se crea un `Paciente` con nombre, apellido, DNI único y teléfono
- **THEN** el paciente se persiste en la base de datos con `creado_en` automático

#### Scenario: DNI duplicado bloqueado
- **WHEN** se intenta crear un `Paciente` con un DNI que ya existe
- **THEN** la base de datos lanza una violación de constraint `UNIQUE` y rechaza la inserción

#### Scenario: Datos mínimos faltantes
- **WHEN** se intenta crear un `Paciente` sin nombre, apellido, DNI o teléfono
- **THEN** la base de datos rechaza la inserción por campos obligatorios

### Requirement: Paciente tiene historial de turnos
El sistema SHALL permitir que un paciente tenga múltiples turnos asociados (relación 1:N).

#### Scenario: Paciente con múltiples turnos
- **WHEN** un `Paciente` tiene 3 turnos asociados
- **THEN** la consulta `paciente.turnos` retorna los 3 turnos ordenados cronológicamente

#### Scenario: Eliminación de paciente con turnos
- **WHEN** se elimina un `Paciente` que tiene turnos asociados
- **THEN** la base de datos rechaza la eliminación (no permite ON DELETE CASCADE) o la maneja según la política de negocio (por defecto, `RESTRICT` o `SET NULL` en `paciente_id`)
