## ADDED Requirements

### Requirement: Workflow de reserva recibe trigger por webhook
El workflow n8n de reserva SHALL exponer un Webhook Trigger que reciba HTTP POST con el payload de update de Telegram.

#### Scenario: Recepción de mensaje de Telegram
- **WHEN** Telegram envía un update POST al webhook URL del workflow
- **THEN** el workflow captura el `chat_id` y el texto del mensaje

### Requirement: Consultar fechas disponibles
El workflow SHALL consultar el endpoint `GET /turnos/disponibles` de FastAPI para obtener las fechas disponibles.

#### Scenario: Listado de fechas
- **WHEN** el usuario envía el comando `/reservar`
- **THEN** el workflow envía una solicitud HTTP GET a `{{$FASTAPI_BASE_URL}}/turnos/disponibles`
- **AND** formatea la respuesta como botones inline de Telegram para selección de fecha

### Requirement: Consultar horarios disponibles para una fecha
El workflow SHALL consultar el endpoint `GET /turnos/disponibles?fecha=YYYY-MM-DD` para obtener los horarios de una fecha específica.

#### Scenario: Listado de horarios
- **WHEN** el usuario selecciona una fecha desde los botones inline
- **THEN** el workflow envía una solicitud HTTP GET a `{{$FASTAPI_BASE_URL}}/turnos/disponibles?fecha=<fecha>`
- **AND** formatea la respuesta como botones inline de Telegram para selección de horario

### Requirement: Realizar reserva temporal
El workflow SHALL enviar un POST a `POST /turnos` para crear una reserva temporal del slot seleccionado.

#### Scenario: Reserva temporal exitosa
- **WHEN** el usuario selecciona un horario disponible
- **THEN** el workflow envía POST a `{{$FASTAPI_BASE_URL}}/turnos` con `paciente_id` y `horario_id`
- **AND** el workflow recibe el `turno_id` y la fecha límite de confirmación
- **AND** envía un mensaje de Telegram con botón de confirmación

#### Scenario: Slot no disponible
- **WHEN** el usuario selecciona un horario que ya fue ocupado
- **THEN** el workflow recibe HTTP 409 Conflict
- **AND** envía un mensaje de Telegram indicando que el horario ya no está disponible y pidiendo que seleccione otro

### Requirement: Confirmar turno
El workflow SHALL enviar un PUT a `PUT /turnos/{id}/confirmar` cuando el usuario presiona el botón de confirmación.

#### Scenario: Confirmación exitosa
- **WHEN** el usuario presiona el botón "Confirmar"
- **THEN** el workflow envía PUT a `{{$FASTAPI_BASE_URL}}/turnos/<turno_id>/confirmar`
- **AND** envía un mensaje de Telegram confirmando el turno con fecha, hora y profesional

#### Scenario: Expiración de reserva temporal
- **WHEN** el usuario intenta confirmar después de que expiró la reserva temporal
- **THEN** el workflow recibe HTTP 410 Gone
- **AND** envía un mensaje de Telegram indicando que el tiempo de reserva expiró y debe reiniciar el proceso
