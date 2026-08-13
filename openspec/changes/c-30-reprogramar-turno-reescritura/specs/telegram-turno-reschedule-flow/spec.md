# Telegram Turno Reschedule Flow Specification

## Purpose

Let a patient move a confirmed turno to another slot from the Telegram chat,
picking the turno and the new slot from buttons, and learn the truth about what
happened — including when it fails.

The existing requirements describe a conversational state machine
(`reprogramando_esperando_fecha`, `reprogramando_esperando_hora`, callbacks
`fecha:<fecha>` and `hora:<hora>`) that lives in the backend's
`telegram_service` and is documented in its own source as "not the one in use"
(`backend/app/services/telegram_service.py:610`). The flow that actually serves
patients is the n8n sub-workflow `sub-flujo-reprogramar-turno`, which is
stateless and never had requirements written against it. These deltas move the
specification onto the implementation that runs.

**Non-goals**: changing `PUT /turnos/{turno_id}/reprogramar`, whose contract is
correct and tested; adding endpoints; unifying the reminder keyboard emitted by
the backend; resolving the single-tenant bot token.

## MODIFIED Requirements

### Requirement: Bot de Telegram permite reprogramar un turno confirmado

The system SHALL provide a Telegram flow that lets a patient reschedule a
confirmed turno **without ever typing a turno identifier**. The flow SHALL
present the patient's own active turnos as buttons, then the available dates,
then the available times, then a confirmation step, and SHALL invoke
`PUT /turnos/{turno_id}/reprogramar`. The flow SHALL be stateless: every button
SHALL carry in its `callback_data` everything the next step needs, and the flow
SHALL NOT depend on `$getWorkflowStaticData` or on any server-side conversation
state.

#### Scenario: El paciente elige su turno de una lista

- **WHEN** el paciente inicia una reprogramación con `cmd:reprogramar`
- **THEN** el flujo consulta los turnos activos de ese `telegram_chat_id`
- **AND** muestra un botón por turno con su fecha y hora legibles
- **AND** el `turno_id` viaja en el `callback_data`, nunca en el texto visible

#### Scenario: Un chat sin turnos activos no recibe una lista vacía

- **WHEN** el paciente inicia una reprogramación y no tiene turnos activos
- **THEN** recibe un mensaje que se lo dice
- **AND** recibe un botón para reservar un turno, en vez de una lista sin
  opciones

#### Scenario: No existe ninguna entrada tipeada

- **WHEN** el paciente escribe un identificador de turno en cualquier formato
- **THEN** el flujo lo ignora y muestra la lista de turnos activos
- **AND** ningún mensaje del bot le pide al paciente que escriba un identificador

#### Scenario: El botón del recordatorio entra por el mismo camino

- **WHEN** el paciente toca "Reprogramar" en un recordatorio, cuyo
  `callback_data` es `cmd:reprogramar:turno_id:<id>` y lo emite el backend
- **THEN** el flujo lo interpreta como la selección de ese turno
- **AND** continúa en el paso de fechas, igual que si el turno se hubiera
  elegido desde la lista

#### Scenario: Un callback que el flujo no reconoce degrada a la lista

- **WHEN** llega un `callback_data` con una forma que el flujo no sabe procesar
- **THEN** el flujo muestra la lista de turnos activos
- **AND** no emite ningún request al backend con datos derivados de ese callback

### Requirement: Selección de nueva fecha

The system SHALL offer the patient a set of candidate dates computed in the
professional's local time, labelled with the day they actually represent.

#### Scenario: Las fechas se calculan en hora local, no UTC

- **WHEN** el flujo arma la lista de fechas candidatas mientras el proceso corre
  en UTC y la agenda es local
- **THEN** las fechas ofrecidas son las del día local del profesional
- **AND** no se corren un día cuando la hora local está entre las 21:00 y la
  medianoche

#### Scenario: La etiqueta coincide con la fecha que representa

- **WHEN** un botón de fecha se muestra con una etiqueta relativa como "Hoy" o
  "Mañana"
- **THEN** esa etiqueta corresponde exactamente a la fecha que el botón envía

### Requirement: Selección de nuevo horario

The system SHALL query availability for the chosen date and present each free
slot as a button.

#### Scenario: Los horarios disponibles se muestran como botones

- **WHEN** el paciente elige una fecha con slots libres
- **THEN** el flujo muestra un botón por slot libre
- **AND** cada botón lleva turno, fecha y hora en su `callback_data`

#### Scenario: Una respuesta que es un array pelado se lee igual

- **WHEN** el backend devuelve la disponibilidad como un array JSON sin envoltura
- **THEN** el flujo lee esos slots correctamente
- **AND** no reporta "no hay horarios" cuando el backend devolvió slots

#### Scenario: Sin horarios se ofrece cambiar de fecha

- **WHEN** la fecha elegida no tiene ningún slot libre
- **THEN** el flujo se lo dice al paciente
- **AND** ofrece un botón que vuelve al paso de fechas
- **AND** no emite ningún botón cuyo `callback_data` el propio flujo no pueda
  procesar

### Requirement: Confirmación antes de ejecutar la reprogramación

The system SHALL ask the patient to confirm before moving the turno, and SHALL
re-read the patient's active turnos at confirmation time.

#### Scenario: Se confirma mostrando el cambio completo

- **WHEN** el paciente elige un horario nuevo
- **THEN** el flujo muestra el turno actual y el horario nuevo
- **AND** pide una confirmación explícita antes de ejecutar

#### Scenario: El turno que cambió entre el botón y el toque se detecta

- **WHEN** el paciente confirma un turno que fue cancelado o venció después de
  que se mostró el botón
- **THEN** el flujo se lo informa
- **AND** no emite el request de reprogramación

### Requirement: El resultado que se le informa al paciente es el resultado real

The system SHALL determine success or failure from the HTTP status code of the
reschedule request, and SHALL report failure as failure.

#### Scenario: Un fallo nunca se reporta como éxito

- **WHEN** el backend rechaza la reprogramación con cualquier código de error
- **THEN** el mensaje al paciente dice que la reprogramación no se hizo
- **AND** el turno original sigue siendo el vigente en el mensaje

#### Scenario: Un status ausente o inesperado se trata como fallo

- **WHEN** la respuesta no trae un código de estado reconocible
- **THEN** el flujo lo trata como fallo
- **AND** no le informa al paciente que su turno se movió

#### Scenario: El turno no existe

- **WHEN** el backend responde 404
- **THEN** el paciente recibe un mensaje que dice que el turno no se encontró
- **AND** se le ofrece volver a pedir su lista de turnos

#### Scenario: El horario ya fue tomado

- **WHEN** el backend responde 409
- **THEN** el paciente recibe un mensaje que dice que ese horario ya no está
  disponible
- **AND** se le ofrece elegir otro horario

#### Scenario: El mensaje de éxito identifica el turno correctamente

- **WHEN** la reprogramación tiene éxito
- **THEN** el mensaje nombra el turno con el identificador que devolvió el
  backend
- **AND** no contiene un identificador vacío ni `undefined`

#### Scenario: Un error del backend llega como mensaje, no como silencio

- **WHEN** el backend responde con un código de error
- **THEN** el paciente recibe un mensaje
- **AND** el flujo no termina sin responderle

## ADDED Requirements

### Requirement: El destinatario de cada respuesta se resuelve sin depender de la respuesta HTTP

The system SHALL resolve the Telegram `chat_id` and the selected `turno_id` from
the step that parsed the incoming command, and SHALL NOT read them from the item
produced by an HTTP request.

#### Scenario: La respuesta HTTP no arrastra el destinatario

- **WHEN** un paso del flujo necesita responderle al paciente después de llamar
  al backend
- **THEN** el `chat_id` usado es el del comando entrante
- **AND** el mensaje llega al chat correcto aunque la respuesta HTTP no contenga
  ningún `chat_id`

### Requirement: Todo `callback_data` entra en el límite de Telegram

The system SHALL keep every emitted `callback_data` within Telegram's 64-byte
limit, including the longest turno identifier the system can produce.

#### Scenario: El peor caso entra en el presupuesto

- **WHEN** se arma cualquier botón del flujo con el identificador de turno más
  largo que el sistema puede generar
- **THEN** el `callback_data` resultante mide 64 bytes o menos
