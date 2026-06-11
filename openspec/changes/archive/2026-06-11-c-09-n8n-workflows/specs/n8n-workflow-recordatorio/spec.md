## ADDED Requirements

### Requirement: Workflow de recordatorio como placeholder
El workflow n8n de recordatorio SHALL existir como un template JSON importable en n8n, preparado para activarse cuando C-10 implemente el scheduler y los endpoints de consulta de turnos pendientes.

#### Scenario: Estructura del placeholder
- **WHEN** el workflow se importa en n8n
- **THEN** contiene un Schedule Trigger configurado para ejecución diaria (o Webhook Trigger alternativo)
- **AND** contiene un HTTP Request node apuntando al endpoint de consulta de turnos pendientes (placeholder URL)
- **AND** contiene un Telegram Send Message node para enviar recordatorios

### Requirement: Consulta de turnos pendientes
El workflow SHALL (una vez activo en C-10) consultar el endpoint de turnos pendientes para el día siguiente y enviar un mensaje a cada paciente.

#### Scenario: Envío de recordatorio
- **WHEN** el scheduler dispara el workflow a las 18:00 del día anterior
- **THEN** el workflow consulta los turnos confirmados para el día siguiente
- **AND** envía un mensaje de Telegram a cada paciente recordando la fecha, hora y profesional
