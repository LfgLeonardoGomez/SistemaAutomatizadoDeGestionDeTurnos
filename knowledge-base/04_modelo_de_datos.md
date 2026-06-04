# Modelo de Datos

## Dominios

- **Gestión de turnos**: creación, estados, confirmación, cancelación, reprogramación.
- **Gestión de pacientes**: registro, identificación, historial.
- **Configuración del profesional**: horarios, duración, días de atención.
- **Reservas temporales**: bloqueo de horarios durante el proceso de reserva.
- **Lista de espera**: registro de pacientes interesados en turnos liberados.
- **Integración externa**: eventos de Google Calendar, mensajes de Telegram.

## ERD (Entity Relationship Diagram)

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  Paciente    │       │    Turno     │       │  Profesional │
│──────────────│       │──────────────│       │──────────────│
│ id (PK)      │◄──────│ id (PK)      │──────►│ id (PK)      │
│ nombre       │  1:N  │ fecha        │  N:1  │ nombre       │
│ apellido     │       │ hora_inicio  │       │ especialidad │
│ dni          │       │ hora_fin     │       │ duracion_turno│
│ telefono     │       │ estado       │       │ horario_inicio│
│ creado_en    │       │ paciente_id  │       │ horario_fin  │
└──────────────┘       │ profesional_id│       │ dias_atencion │
                       │ creado_en    │       │ creado_en    │
                       └──────┬───────┘       └──────────────┘
                              │
                              │ 1:1
                              ▼
                       ┌──────────────┐
                       │ReservaTemporal│
                       │──────────────│
                       │ id (PK)      │
                       │ turno_id (FK)│
                       │ expiracion   │
                       └──────────────┘
```

## Entidades

### Paciente
- **id**: INTEGER, PK, auto-increment.
- **nombre**: VARCHAR, obligatorio.
- **apellido**: VARCHAR, obligatorio.
- **dni**: VARCHAR, único, obligatorio.
- **telefono**: VARCHAR, obligatorio (vinculado a Telegram).
- **creado_en**: TIMESTAMP, default NOW().
- **Relaciones**: 1:N con Turno.
- **Índices**: UNIQUE(dni), INDEX(telefono).

### Profesional
- **id**: INTEGER, PK, auto-increment.
- **nombre**: VARCHAR, obligatorio.
- **especialidad**: VARCHAR, default "Odontología general".
- **duracion_turno**: INTEGER (minutos), default 30.
- **horario_inicio**: TIME, hora de inicio de atención.
- **horario_fin**: TIME, hora de fin de atención.
- **dias_atencion**: VARCHAR o ARRAY, días de la semana habilitados.
- **creado_en**: TIMESTAMP, default NOW().
- **Relaciones**: 1:N con Turno.
- **Índices**: INDEX(id).

### Turno
- **id**: INTEGER, PK, auto-increment.
- **fecha**: DATE, obligatorio.
- **hora_inicio**: TIME, obligatorio.
- **hora_fin**: TIME, obligatorio (calculada como hora_inicio + duracion_turno).
- **estado**: ENUM('DISPONIBLE', 'RESERVADO_TEMPORAL', 'CONFIRMADO', 'CANCELADO', 'COMPLETADO'), default 'DISPONIBLE'.
- **paciente_id**: INTEGER, FK → Paciente, nullable (null cuando DISPONIBLE).
- **profesional_id**: INTEGER, FK → Profesional, obligatorio.
- **creado_en**: TIMESTAMP, default NOW().
- **Relaciones**: N:1 con Paciente; N:1 con Profesional; 1:1 con ReservaTemporal (cuando RESERVADO_TEMPORAL).
- **Constraints**: CHECK(hora_fin > hora_inicio).
- **Índices**: INDEX(fecha, hora_inicio), INDEX(estado), INDEX(paciente_id, estado) para validar "un turno activo por paciente".

### ReservaTemporal
- **id**: INTEGER, PK, auto-increment.
- **turno_id**: INTEGER, FK → Turno, UNIQUE.
- **expiracion**: TIMESTAMP, momento en que la reserva expira.
- **Relaciones**: 1:1 con Turno.
- **Índices**: INDEX(expiracion) para queries de liberación automática.

### ListaDeEspera (entidad adicional, no detallada en el doc fuente pero necesaria)
- **id**: INTEGER, PK, auto-increment.
- **paciente_id**: INTEGER, FK → Paciente.
- **fecha_solicitada**: DATE, preferencia del paciente.
- **creado_en**: TIMESTAMP, default NOW().
- **notificado**: BOOLEAN, default FALSE.
- **Relaciones**: N:1 con Paciente.

## Seed data inicial

- Un registro en **Profesional** con horarios y duración de turno por defecto.
- Estados del ENUM de Turno predefinidos por la base de datos.
