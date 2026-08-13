# Telegram Message Formatting Specification

## Purpose

Tell the patient, at the moment they book, the same things the reminder tells
them the day before — including who the turno is with.

Before this change the booking confirmation was assembled inside an n8n
expression and named only the patient, the date and the time. The reminder,
assembled by the backend, also named the professional. The patient learned who
they were seeing a day before the appointment instead of when they chose it.

**Non-goals**: changing `format_recordatorio_mensaje`; moving the rest of the
n8n-authored messages into the backend.

## ADDED Requirements

### Requirement: El mensaje de confirmación de reserva lo arma el backend

The system SHALL provide a formatter that builds the complete booking
confirmation message from the turno, the patient and the professional, and the
Telegram flow SHALL transport that text without composing any part of it.

#### Scenario: La confirmación nombra al profesional

- **WHEN** se confirma una reserva y el profesional está disponible
- **THEN** el mensaje incluye el nombre del profesional
- **AND** incluye su especialidad cuando la tiene

#### Scenario: La confirmación nombra fecha, hora y paciente

- **WHEN** se confirma una reserva
- **THEN** el mensaje incluye la fecha y la hora del turno
- **AND** identifica al paciente para el que se reservó

#### Scenario: Sin profesional el mensaje sale igual

- **WHEN** se confirma una reserva y el profesional no se pudo cargar
- **THEN** el mensaje se genera igual, sin la línea del profesional
- **AND** no contiene una línea vacía ni un rótulo sin valor

#### Scenario: Una especialidad ausente no deja un paréntesis colgado

- **WHEN** el profesional tiene nombre pero no tiene especialidad
- **THEN** el mensaje nombra al profesional
- **AND** no contiene un paréntesis vacío ni un separador sin contenido

### Requirement: El mensaje de confirmación está escapado para MarkdownV2

The system SHALL escape every interpolated value according to MarkdownV2, and the
message SHALL be sent declaring that parse mode.

#### Scenario: Los datos con caracteres reservados se escapan

- **WHEN** el nombre, el apellido o la especialidad contienen caracteres
  reservados de MarkdownV2
- **THEN** esos caracteres viajan escapados en el mensaje
- **AND** Telegram acepta el mensaje en vez de rechazarlo

#### Scenario: El mensaje se envía con el parse mode que corresponde

- **WHEN** el flujo envía la confirmación
- **THEN** declara `MarkdownV2` como parse mode
- **AND** el paciente ve el texto formateado, sin barras de escape visibles

#### Scenario: Una fecha no se muestra con sus escapes

- **WHEN** el mensaje incluye una fecha, cuyo guión es un carácter reservado
- **THEN** el paciente la lee como fecha
- **AND** no ve los caracteres de escape en el chat

### Requirement: La confirmación viaja con la respuesta de la confirmación del turno

The system SHALL return the formatted message together with the confirmed turno,
and SHALL NOT require a second request to obtain it.

#### Scenario: Confirmar un turno devuelve su mensaje

- **WHEN** se confirma un turno con éxito
- **THEN** la respuesta incluye el turno confirmado
- **AND** incluye el mensaje ya formateado para el paciente

#### Scenario: Los demás endpoints de turno no cambian su respuesta

- **WHEN** se cancela, se reprograma, se completa o se confirma la asistencia de
  un turno
- **THEN** la respuesta mantiene la forma que ya tenía
- **AND** no incluye ningún campo de presentación
