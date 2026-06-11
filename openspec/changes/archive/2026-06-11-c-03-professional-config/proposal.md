## Why

El profesional necesita controlar sus horarios de atención y la duración de los turnos para que el sistema calcule correctamente la disponibilidad. Sin esta configuración, los slots de turnos se generan con valores fijos o seed data, lo cual no refleja la realidad de la práctica odontológica. Este change habilita la gestión de la configuración del profesional y el cálculo dinámico de disponibilidad, bloqueando a su vez la funcionalidad de reserva (C-04 y siguientes).

## What Changes

- **Nuevo endpoint** `GET /profesional/configuracion` — retorna la configuración actual del profesional (horarios, días, duración).
- **Nuevo endpoint** `PUT /profesional/configuracion` — permite actualizar los campos editables de la configuración.
- **Nuevo servicio** `availability_service.py` — calcula slots libres para una fecha dada, respetando la configuración del profesional y los turnos ocupados.
- **Reglas de validación** en los endpoints: horario_inicio < horario_fin, días_atención válidos, duración_turno positiva.
- **Tests** que cubren recálculo de slots al cambiar duración, filtrado por días no laborables, prevención de solapamientos y validación de horarios.

## Capabilities

### New Capabilities
- `professional-config`: Gestión de la configuración del profesional (lectura y actualización de horarios, días de atención y duración de turnos).
- `availability-calculation`: Cálculo de slots disponibles para una fecha dada, basado en la configuración del profesional y los turnos existentes.

### Modified Capabilities
- *(ninguno — este change no altera los requisitos de capabilities existentes)*

## Impact

- **Backend**: nuevo router `profesional.py`, nuevo servicio `availability_service.py`, schemas Pydantic para configuración.
- **API**: dos endpoints REST bajo el prefijo `/profesional`.
- **Base de datos**: reutiliza el modelo `Profesional` de C-02; no requiere nuevas migraciones.
- **Tests**: tests unitarios e integración para endpoints y servicio de disponibilidad.
- **Dependencias**: requiere C-02 (modelos SQLAlchemy) completado.
