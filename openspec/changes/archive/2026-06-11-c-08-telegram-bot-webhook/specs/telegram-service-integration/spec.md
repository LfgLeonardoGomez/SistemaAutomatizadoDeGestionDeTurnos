## ADDED Requirements

### Requirement: Telegram service orchestrates business actions
The system SHALL provide a `telegram_service.py` module with functions that orchestrate calls to existing business services (`turno_service`, `paciente_service`, `availability_service`) to fulfill conversational actions.

#### Scenario: Process message delegates to correct action
- **WHEN** `procesar_mensaje(update)` is called with a valid Telegram update
- **THEN** it parses the update, determines the conversation state, and delegates to the appropriate service method

#### Scenario: Show availability formats slots
- **WHEN** `mostrar_disponibilidad(fecha)` is called
- **THEN** it calls `availability_service.calcular_disponibilidad` and `turno_service.consultar_disponibilidad`, formats the result, and returns message text and inline keyboard

#### Scenario: Confirm reservation formats confirmation message
- **WHEN** `confirmar_reserva(turno_id)` is called
- **THEN** it calls `turno_service.confirmar_turno`, formats the confirmation details, and returns the message text

#### Scenario: Notify expiration formats release message
- **WHEN** `notificar_expiracion()` is called (or triggered by scheduler)
- **THEN** it formats a message informing the user that their temporary reservation has expired

### Requirement: Service layer calls existing services directly
The system SHALL call existing service methods directly, not via HTTP or TestClient.

#### Scenario: Reserve temporary calls turno_service directly
- **WHEN** the user selects a time slot
- **THEN** the telegram service calls `turno_service.reservar_turno` directly with the required parameters

#### Scenario: Confirm turn calls turno_service directly
- **WHEN** the user confirms patient data
- **THEN** the telegram service calls `turno_service.confirmar_turno` directly with the turno ID

### Requirement: Error handling in service layer returns friendly messages
The system SHALL catch exceptions from business services and return user-friendly Telegram messages.

#### Scenario: Turno no longer available
- **WHEN** `turno_service.reservar_turno` raises a `TurnoNoDisponibleException`
- **THEN** the telegram service sends a friendly message explaining the slot is no longer available and offers to show other dates

#### Scenario: Unrecognized message
- **WHEN** the router receives a message it cannot parse
- **THEN** the telegram service sends a help message listing available commands

#### Scenario: Generic service error
- **WHEN** any business service raises an unexpected exception
- **THEN** the telegram service logs the error and sends a generic friendly message to the user without exposing internal details
