## ADDED Requirements

### Requirement: Workflow de lista de espera como placeholder
El workflow n8n de lista de espera SHALL existir como un template JSON importable en n8n, preparado para activarse cuando C-11 implemente el módulo de lista de espera y sus endpoints.

#### Scenario: Estructura del placeholder
- **WHEN** el workflow se importa en n8n
- **THEN** contiene un Webhook Trigger para recibir notificaciones de slot libre
- **AND** contiene un HTTP Request node apuntando al endpoint de lista de espera (placeholder URL)
- **AND** contiene un Telegram Send Message node para notificar al usuario

### Requirement: Notificar usuario cuando se libera un slot
El workflow SHALL (una vez activo en C-11) recibir una notificación cuando se cancela un turno y ofrecer el slot al siguiente paciente en la lista de espera.

#### Scenario: Notificación de slot libre
- **WHEN** se cancela un turno y queda un slot disponible
- **THEN** el backend invoca el webhook del workflow de lista de espera
- **AND** el workflow consulta el siguiente paciente en lista de espera
- **AND** envía un mensaje de Telegram a ese paciente ofreciendo el slot con botón de reserva
