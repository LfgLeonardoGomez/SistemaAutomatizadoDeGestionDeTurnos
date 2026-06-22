## Purpose

Definir el manejo de timeouts para notificaciones de lista de espera, permitiendo reasignar turnos liberados cuando un paciente no responde.

## ADDED Requirements

### Requirement: Sistema maneja timeout de notificación de lista de espera
El sistema SHALL ejecutar un job periódico (`AsyncIOScheduler`) que identifique registros en `ListaDeEspera` con `notificado=TRUE` y `notificado_en < NOW() - LISTA_ESPERA_MINUTOS`. Para cada registro vencido, SHALL resetear `notificado=FALSE`, `turno_ofrecido_id=NULL`, `notificado_en=NULL`, y SHALL re-evaluar la lista de espera para la `fecha_solicitada` correspondiente.

#### Scenario: Timeout de paciente notificado
- **WHEN** un paciente fue notificado hace más de `LISTA_ESPERA_MINUTOS` y no respondió
- **THEN** el job SHALL resetear su registro en `ListaDeEspera`
- **AND** SHALL invocar la lógica de ofrecimiento al siguiente paciente en cola

#### Scenario: Paciente responde antes del timeout
- **WHEN** un paciente acepta o rechaza el turno antes de que venza el timeout
- **THEN** el job posterior no SHALL actuar sobre ese registro porque ya fue eliminado (aceptación) o reseteado (rechazo)

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
