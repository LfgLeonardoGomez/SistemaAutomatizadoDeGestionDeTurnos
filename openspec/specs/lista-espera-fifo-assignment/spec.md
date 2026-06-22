## Purpose

Definir la asignación FIFO de turnos liberados a pacientes en lista de espera, incluyendo manejo de concurrencia mediante `SELECT FOR UPDATE`.

## ADDED Requirements

### Requirement: Sistema asigna turno liberado al primer paciente en lista de espera FIFO
El sistema SHALL, al liberarse un slot (cancelación o expiración de reserva temporal), consultar `ListaDeEspera` filtrando por `fecha_solicitada = fecha_del_slot`, ordenando por `creado_en ASC`, y seleccionar el primer registro con `notificado=FALSE` y `turno_ofrecido_id=NULL`. La consulta del primer candidato y su actualización SHALL ser atómica mediante `SELECT FOR UPDATE`.

#### Scenario: Un paciente en lista de espera recibe oferta de turno liberado
- **WHEN** se cancela un turno confirmado para el 2026-06-15 y existe un registro en `ListaDeEspera` para esa fecha
- **THEN** el sistema SHALL seleccionar el primer registro ordenado por `creado_en ASC`
- **AND** SHALL actualizar `turno_ofrecido_id` al turno liberado, `notificado=TRUE` y `notificado_en=NOW()`
- **AND** SHALL enviar notificación Telegram al paciente

#### Scenario: Sin pacientes en lista de espera para la fecha liberada
- **WHEN** se cancela un turno para el 2026-06-15 y no hay registros en `ListaDeEspera` para esa fecha
- **THEN** el turno SHALL quedar en estado `DISPONIBLE`
- **AND** no se SHALL enviar ninguna notificación

#### Scenario: Condición de carrera en asignación FIFO
- **WHEN** dos slots se liberan simultáneamente para la misma fecha
- **THEN** el sistema SHALL asignar el primer slot al primer paciente y el segundo slot al segundo paciente
- **AND** no se SHALL notificar dos veces al mismo paciente

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
