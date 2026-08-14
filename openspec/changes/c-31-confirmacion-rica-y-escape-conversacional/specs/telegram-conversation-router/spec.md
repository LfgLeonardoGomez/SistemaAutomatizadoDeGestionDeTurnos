# Telegram Conversation Router Specification

## Purpose

Let a patient leave a half-finished conversation by writing, not only by finding
a button.

The router already abandons a pending capture whenever it recognises a command —
that is what `fresh_start` does. What it lacks is a command whose purpose is to
leave: all four recognised commands start another flow. A patient in the middle
of a booking who is being asked for their DNI sees a question, not a menu, and
has nothing to type.

**Non-goals**: changing how the four existing commands route; adding `/start`
(see OQ-1 in `design.md`); accepting bare words without a slash.

## ADDED Requirements

### Requirement: Comandos de escape conversacional

The system SHALL recognise `/menu`, `/salir`, `/esc`, `/volver` and `/start` as
commands that abandon whatever the patient was doing and return them to the main
menu.

#### Scenario: Escapar de una captura pendiente

- **WHEN** el paciente está respondiendo una captura de datos y escribe uno de
  los comandos de escape
- **THEN** la captura pendiente se abandona
- **AND** el texto del comando no se registra como respuesta a la pregunta
  pendiente

#### Scenario: El escape devuelve el menú principal

- **WHEN** el paciente escribe un comando de escape
- **THEN** recibe el menú principal con sus opciones
- **AND** no recibe solamente un acuse de que la conversación terminó

#### Scenario: Escapar sin nada que abandonar es inofensivo

- **WHEN** el paciente escribe un comando de escape sin ninguna conversación en
  curso
- **THEN** recibe el menú principal
- **AND** no se produce ningún error ni ningún efecto sobre sus turnos

#### Scenario: Todos los comandos de escape son equivalentes

- **WHEN** el paciente escribe cualquiera de los comandos de escape
- **THEN** el resultado es el mismo en todos los casos

#### Scenario: La primera interacción de un paciente nuevo llega al menú

- **WHEN** un paciente abre el chat con el bot por primera vez y su cliente de
  Telegram envía `/start`
- **THEN** recibe el menú principal

#### Scenario: Volver a abrir el chat rescata a quien quedó a mitad de camino

- **WHEN** un paciente con una captura pendiente vuelve a abrir el chat y se
  envía `/start`
- **THEN** la captura pendiente se abandona
- **AND** el texto del comando no se registra como respuesta a la pregunta
  pendiente

### Requirement: El menú principal enseña cómo salir

The system SHALL state, in the main menu message itself, how the patient can
leave a conversation in progress, as text rather than as a button.

#### Scenario: El menú nombra el comando de escape

- **WHEN** el paciente recibe el menú principal
- **THEN** el mensaje menciona explícitamente un comando para volver al menú
- **AND** lo hace como texto legible, no como un botón

#### Scenario: El comando que el menú nombra funciona

- **WHEN** el paciente escribe el comando que el menú le indicó, en cualquier
  punto de una conversación
- **THEN** vuelve al menú principal

#### Scenario: El escape se reconoce sin importar mayúsculas ni espacios sobrantes

- **WHEN** el paciente escribe un comando de escape con mayúsculas o con espacios
  alrededor
- **THEN** se reconoce igual

### Requirement: El escape no se dispara desde un dato del paciente

The system SHALL match escape commands by exact equality against the trimmed
text, and SHALL NOT match them as a substring of a longer message.

#### Scenario: Una palabra parecida dentro de una frase no escapa

- **WHEN** el paciente envía un mensaje más largo que contiene un comando de
  escape como parte del texto
- **THEN** el mensaje no se interpreta como escape
- **AND** sigue el camino que le corresponde según la conversación en curso

#### Scenario: Un dato de captura que se parece a un escape no escapa

- **WHEN** el bot pide un dato y el paciente responde una palabra que contiene un
  comando de escape sin la barra
- **THEN** la respuesta se registra como el dato pedido
- **AND** la captura continúa

### Requirement: Un comando reconocido abandona siempre la captura pendiente

The system SHALL mark every recognised command as a fresh start, so that no
recognised command is ever consumed as an answer to a pending capture question.

#### Scenario: Ningún comando reconocido se registra como respuesta

- **WHEN** llega un comando reconocido mientras hay una captura pendiente
- **THEN** el comando se ejecuta como comando
- **AND** su texto no queda registrado como el dato que se estaba pidiendo

#### Scenario: Un paso dentro de un flujo no abandona la captura

- **WHEN** llega la selección de un horario, que es un paso dentro del flujo de
  reserva y no un comando
- **THEN** no se trata como un comando que abandona lo que estaba en curso
