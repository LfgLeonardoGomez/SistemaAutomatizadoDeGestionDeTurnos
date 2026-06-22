## ADDED Requirements

### Requirement: Sistema envía mensaje Telegram con botones Aceptar y Rechazar
El sistema SHALL enviar un mensaje al `chat_id` del paciente (derivado de su registro) con la fecha y hora del turno ofrecido, incluyendo un teclado inline con botones "Aceptar" y "Rechazar". El mensaje SHALL usar MarkdownV2 con escape apropiado.

#### Scenario: Notificación exitosa de turno liberado
- **WHEN** el sistema asigna un turno liberado a un paciente en lista de espera
- **THEN** SHALL enviar mensaje Telegram con texto descriptivo del turno
- **AND** SHALL incluir botón Aceptar con `callback_data="lista_espera:aceptar:<turno_id>"`
- **AND** SHALL incluir botón Rechazar con `callback_data="lista_espera:rechazar:<turno_id>"`

#### Scenario: Fallo de envío de notificación Telegram
- **WHEN** el envío de Telegram falla
- **THEN** el sistema SHALL registrar el error en logs
- **AND** SHALL NO actualizar `notificado=TRUE` en `ListaDeEspera`
- **AND** SHALL reintentar en la próxima evaluación de lista de espera

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
