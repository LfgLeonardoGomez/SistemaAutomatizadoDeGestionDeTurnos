## ADDED Requirements

### Requirement: Bot de Telegram permite reprogramar un turno confirmado
El sistema SHALL proporcionar un flujo conversacional en Telegram que permita a un paciente reprogramar su turno confirmado. El flujo SHALL mostrar fechas disponibles, luego horarios disponibles, y SHALL invocar `reprogramar_turno()` del backend. El bot SHALL manejar errores (slot no disponible, turno no encontrado) notificando al usuario amigablemente.

#### Scenario: Usuario inicia reprogramación desde recordatorio
- **WHEN** el usuario presiona el botón "Reprogramar" en un mensaje de recordatorio (callback_data `reprogramar:<turno_id>`)
- **THEN** el bot SHALL guardar el `turno_id` en el estado conversacional
- **AND** el bot SHALL mostrar las próximas fechas disponibles con teclado inline
- **AND** el estado conversacional SHALL pasar a `reprogramando_esperando_fecha`

#### Scenario: Usuario selecciona nueva fecha
- **WHEN** el usuario selecciona una fecha del teclado inline (callback_data `fecha:<fecha>`) estando en estado `reprogramando_esperando_fecha`
- **THEN** el bot SHALL consultar disponibilidad para esa fecha
- **AND** el bot SHALL mostrar los horarios disponibles con teclado inline
- **AND** el estado conversacional SHALL pasar a `reprogramando_esperando_hora`

#### Scenario: Usuario selecciona nuevo horario y reprogramación exitosa
- **WHEN** el usuario selecciona un horario del teclado inline (callback_data `hora:<hora>`) estando en estado `reprogramando_esperando_hora`
- **THEN** el bot SHALL invocar `reprogramar_turno()` con la fecha y hora seleccionadas
- **AND** el bot SHALL enviar un mensaje de confirmación con la nueva fecha y hora
- **AND** el bot SHALL limpiar el estado conversacional

#### Scenario: Reprogramación falla por slot no disponible
- **WHEN** el usuario selecciona un horario que ya no está disponible
- **THEN** el bot SHALL notificar al usuario que el horario ya no está disponible
- **AND** el bot SHALL ofrecer seleccionar otra fecha
- **AND** el estado conversacional SHALL permanecer en `reprogramando_esperando_fecha`

#### Scenario: Reprogramación falla por turno cancelado
- **WHEN** el bot intenta reprogramar un turno que fue cancelado entre el inicio del flujo y la selección de horario
- **THEN** el bot SHALL notificar al usuario que el turno ya no puede reprogramarse
- **AND** el bot SHALL limpiar el estado conversacional

#### Scenario: Usuario cancela flujo de reprogramación
- **WHEN** el usuario presiona "Cancelar" en cualquier paso del flujo de reprogramación
- **THEN** el bot SHALL limpiar el estado conversacional
- **AND** el bot SHALL notificar que la operación fue cancelada

## MODIFIED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
