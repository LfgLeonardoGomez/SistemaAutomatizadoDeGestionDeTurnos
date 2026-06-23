## MODIFIED Requirements

### Requirement: ListaDeEspera registra pacientes interesados en turnos liberados
El sistema SHALL permitir que un `Paciente` se registre en `ListaDeEspera` con una `fecha_solicitada`, vinculado obligatoriamente a un `Profesional`.

#### Scenario: Registro en lista de espera
- **WHEN** un `Paciente` se registra en `ListaDeEspera` con `fecha_solicitada="2026-06-15"` y `profesional_id`
- **THEN** el registro se persiste con `notificado=FALSE`, `turno_ofrecido_id=NULL`, `notificado_en=NULL` y `creado_en` automático

#### Scenario: Múltiples registros por paciente
- **WHEN** un mismo `Paciente` se registra dos veces en `ListaDeEspera` con fechas diferentes para el mismo profesional
- **THEN** ambos registros se persisten

#### Scenario: ListaDeEspera indica si el paciente fue notificado
- **WHEN** se crea un registro en `ListaDeEspera`
- **THEN** `notificado` es `FALSE`
- **AND** `turno_ofrecido_id` es `NULL`
- **AND** `notificado_en` es `NULL`

#### Scenario: Actualización a notificado
- **WHEN** se actualiza `notificado` a `TRUE` para un registro existente
- **THEN** el campo se actualiza correctamente
- **AND** `notificado_en` se actualiza simultáneamente

#### Scenario: ListaDeEspera registra qué turno fue ofrecido y cuándo se notificó
- **WHEN** el sistema ofrece un turno liberado a un paciente en lista de espera
- **THEN** `turno_ofrecido_id` se actualiza al ID del turno ofrecido
- **AND** `notificado_en` se actualiza a la fecha/hora actual

#### Scenario: ListaDeEspera tiene relación con Paciente
- **WHEN** se intenta crear un registro en `ListaDeEspera` sin `paciente_id`
- **THEN** la base de datos rechaza la inserción

#### Scenario: Paciente eliminado
- **WHEN** se elimina un `Paciente` que tiene registros en `ListaDeEspera`
- **THEN** la base de datos elimina los registros en cascada o rechaza la eliminación según la política de FK definida

#### Scenario: Registro en lista de espera sin profesional
- **WHEN** se intenta crear un registro en `ListaDeEspera` sin `profesional_id`
- **THEN** la base de datos rechaza la inserción

## ADDED Requirements

### Requirement: ListaDeEspera tiene índice por profesional y paciente
El sistema SHALL crear un índice en `ListaDeEspera` sobre las columnas `(profesional_id, paciente_id)` para optimizar queries de búsqueda por profesional.

#### Scenario: Índice existe
- **WHEN** se inspecciona el schema de `lista_de_espera`
- **THEN** existe un índice llamado `ix_lista_de_espera_profesional_paciente` sobre `(profesional_id, paciente_id)`
