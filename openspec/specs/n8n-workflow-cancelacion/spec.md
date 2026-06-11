## ADDED Requirements

### Requirement: Workflow de cancelación recibe trigger por webhook
El workflow n8n de cancelación SHALL exponer un Webhook Trigger que reciba HTTP POST con el payload de update de Telegram.

#### Scenario: Recepción de comando de cancelación
- **WHEN** Telegram envía un update POST al webhook URL del workflow
- **THEN** el workflow captura el `chat_id` y el texto del mensaje

### Requirement: Cancelar turno por ID
El workflow SHALL enviar un PUT a `PUT /turnos/{id}/cancelar` para cancelar el turno del usuario.

#### Scenario: Cancelación exitosa
- **WHEN** el usuario envía el comando `/cancelar <turno_id>` o selecciona un turno desde un botón inline
- **THEN** el workflow envía PUT a `{{$FASTAPI_BASE_URL}}/turnos/<turno_id>/cancelar`
- **AND** recibe HTTP 200 OK con la confirmación de cancelación
- **AND** envía un mensaje de Telegram confirmando la cancelación y ofreciendo reprogramar

#### Scenario: Turno no encontrado
- **WHEN** el usuario envía un `turno_id` inexistente
- **THEN** el workflow recibe HTTP 404 Not Found
- **AND** envía un mensaje de Telegram indicando que el turno no fue encontrado

#### Scenario: Turno ya cancelado
- **WHEN** el usuario intenta cancelar un turno que ya está cancelado
- **THEN** el workflow recibe HTTP 400 Bad Request
- **AND** envía un mensaje de Telegram indicando que el turno ya fue cancelado previamente
