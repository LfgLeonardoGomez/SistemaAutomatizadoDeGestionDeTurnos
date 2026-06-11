## Why

El sistema de turnos necesita una base de pacientes identificados para permitir reservas recurrentes, trazabilidad de historial y comunicación automatizada. Actualmente, el modelo `Paciente` existe (C-02) pero no hay endpoints ni lógica de negocio para interactuar con él. Este change habilita el registro, identificación y consulta de pacientes como prerrequisito para los flujos de reserva y recordatorio.

## What Changes

- **Nuevos endpoints REST** para gestión de pacientes:
  - `POST /pacientes` — crea paciente con validación de DNI único y teléfono requerido.
  - `GET /pacientes/{id}` — retorna paciente con historial de turnos.
  - `GET /pacientes/{id}/turnos` — lista turnos asociados al paciente.
- **Nuevo servicio** `paciente_service.py` con lógica de auto-identificación por DNI: si el paciente ya existe, se retorna el registro existente en lugar de crear uno duplicado.
- **Nuevos schemas Pydantic** para validación de entrada y serialización de respuestas (`PacienteCreate`, `PacienteRead`, `PacienteConHistorial`).
- **Router** `pacientes.py` registrado en `main.py`.
- **Tests** que cubren: creación, unicidad de DNI, auto-identificación, consulta con historial y listado de turnos.

## Capabilities

### New Capabilities
- `patient-management`: Gestión de pacientes — creación, identificación, consulta e historial de turnos.

### Modified Capabilities
<!-- Ninguna existente requiere cambios en sus requisitos. -->

## Impact

- **Código**: `backend/app/routers/pacientes.py`, `backend/app/services/paciente_service.py`, `backend/app/schemas/paciente.py`.
- **API**: Nuevos endpoints bajo el prefijo `/pacientes`.
- **Dependencias**: Requiere modelos de `Paciente` y `Turno` (C-02 completado).
- **Tests**: `backend/tests/test_pacientes.py`, `backend/tests/test_paciente_service.py`.
