## ADDED Requirements

### Requirement: ListaDeEspera registra pacientes interesados en turnos liberados
El sistema SHALL permitir que un `Paciente` se registre en `ListaDeEspera` con una `fecha_solicitada`.

#### Scenario: Registro en lista de espera
- **WHEN** un `Paciente` se registra en `ListaDeEspera` con `fecha_solicitada="2026-06-15"`
- **THEN** el registro se persiste con `notificado=FALSE` y `creado_en` automático

#### Scenario: Múltiples registros por paciente
- **WHEN** un mismo `Paciente` se registra dos veces en `ListaDeEspera` con fechas diferentes
- **THEN** ambos registros se persisten (no hay restricción de único paciente por fecha a nivel de DB en este change)

### Requirement: ListaDeEspera indica si el paciente fue notificado
El sistema SHALL almacenar `notificado` como BOOLEAN con valor por defecto `FALSE`.

#### Scenario: Estado inicial
- **WHEN** se crea un registro en `ListaDeEspera`
- **THEN** `notificado` es `FALSE`

#### Scenario: Actualización a notificado
- **WHEN** se actualiza `notificado` a `TRUE` para un registro existente
- **THEN** el campo se actualiza correctamente

### Requirement: ListaDeEspera tiene relación con Paciente
El sistema SHALL exigir `paciente_id` como FK a `Paciente` en `ListaDeEspera`.

#### Scenario: Registro sin paciente
- **WHEN** se intenta crear un registro en `ListaDeEspera` sin `paciente_id`
- **THEN** la base de datos rechaza la inserción

#### Scenario: Paciente eliminado
- **WHEN** se elimina un `Paciente` que tiene registros en `ListaDeEspera`
- **THEN** la base de datos elimina los registros en cascada o rechaza la eliminación según la política de FK definida
