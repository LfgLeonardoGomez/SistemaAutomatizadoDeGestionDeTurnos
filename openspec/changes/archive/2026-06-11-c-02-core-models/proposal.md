## Why

El proyecto `Tesis-N8N-turnos` ya tiene el scaffolding de FastAPI, Alembic y PostgreSQL listo tras `C-01 foundation-setup`, pero **no tiene ningún modelo de datos definido**. Sin las entidades base del dominio (`Paciente`, `Profesional`, `Turno`, `ReservaTemporal`, `ListaDeEspera`), ningún endpoint, servicio ni integración puede funcionar. Este change es el **cimiento de la capa de dominio**: todos los changes siguientes (C-03 a C-12) dependen directamente de estos modelos. Es crítico hacerlo ahora y hacerlo bien, porque un error en la base de datos se propaga exponencialmente.

## What Changes

- Crear **5 modelos SQLAlchemy 2.0** en `backend/app/models/`:
  - `Paciente` — id, nombre, apellido, dni (UNIQUE), telefono, creado_en.
  - `Profesional` — id, nombre, especialidad, duracion_turno, horario_inicio, horario_fin, dias_atencion, creado_en.
  - `Turno` — id, fecha, hora_inicio, hora_fin, estado (ENUM), paciente_id (FK nullable), profesional_id (FK), creado_en.
  - `ReservaTemporal` — id, turno_id (FK, UNIQUE), expiracion.
  - `ListaDeEspera` — id, paciente_id (FK), fecha_solicitada, creado_en, notificado.
- Crear **Alembic migration 001** con todas las tablas, constraints (`CHECK`, `UNIQUE`), índices y relaciones.
- Agregar **seed idempotente** de `Profesional` con valores por defecto (horarios 08:00–18:00, duración 30 min).
- Crear **tests** de integridad: constraints, integridad referencial, idempotencia del seed, verificación de índices.

## Capabilities

### New Capabilities
- `core-patient-model`: Modelo y persistencia de la entidad `Paciente` (registro, identificación por DNI, historial de turnos).
- `core-professional-model`: Modelo y persistencia de la entidad `Profesional` (configuración de agenda, duración de turnos, días de atención).
- `core-turno-model`: Modelo y persistencia de la entidad `Turno` con máquina de estados (DISPONIBLE → RESERVADO_TEMPORAL → CONFIRMADO → CANCELADO/COMPLETADO).
- `core-reserva-temporal-model`: Modelo y persistencia de `ReservaTemporal` para bloqueo de horarios con expiración.
- `core-lista-espera-model`: Modelo y persistencia de `ListaDeEspera` para reasignación de turnos liberados.

### Modified Capabilities
<!-- No hay capabilities existentes en este proyecto; es el primer change de dominio. -->

## Impact

- `backend/app/models/`: nuevo directorio con 5 módulos de modelos.
- `backend/alembic/versions/`: nueva migración `001` (creación de tablas).
- `backend/tests/`: nuevos tests de integridad y seed.
- `backend/app/config.py`: posible ampliación para incluir variables de seed (ej. `RESERVA_TEMPORAL_MINUTOS`).
- Ningún impacto en APIs públicas (aún no hay endpoints de negocio); este change es puramente de capa de datos.
