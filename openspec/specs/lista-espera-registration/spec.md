## Purpose

Definir el registro de pacientes en lista de espera para turnos liberados.

## ADDED Requirements

### Requirement: Sistema permite registrar paciente en lista de espera
El sistema SHALL permitir que un paciente se registre en `ListaDeEspera` indicando una `fecha_solicitada`. El registro SHALL persistir con `notificado=FALSE`, `turno_ofrecido_id=NULL` y `notificado_en=NULL`.

#### Scenario: Registro exitoso en lista de espera
- **WHEN** se envía `POST /lista-espera` con `paciente_id` y `fecha_solicitada`
- **THEN** el sistema SHALL crear un registro en `ListaDeEspera`
- **AND** SHALL retornar HTTP 201 con el registro creado

#### Scenario: Registro con paciente inexistente
- **WHEN** se envía `POST /lista-espera` con un `paciente_id` que no existe
- **THEN** el sistema SHALL retornar HTTP 404 Not Found

#### Scenario: Registro sin fecha solicitada
- **WHEN** se envía `POST /lista-espera` sin `fecha_solicitada`
- **THEN** el sistema SHALL retornar HTTP 422 Unprocessable Entity

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
