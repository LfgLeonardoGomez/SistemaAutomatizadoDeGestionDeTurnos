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
│ telegram_chat_id│    │ paciente_id  │       │ horario_fin  │
│ creado_en    │       │ profesional_id│      │ dias_atencion │
└──────────────┘       │ google_event_id│     └──────────────┘
                       │ recordatorio_enviado│
                       │ creado_en    │
                       └──────┬───────┘
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
- **nombre**: VARCHAR(255), obligatorio.
- **apellido**: VARCHAR(255), obligatorio.
- **dni**: VARCHAR(50), único, obligatorio.
- **telefono**: VARCHAR(50), obligatorio (vinculado a Telegram).
- **telegram_chat_id**: VARCHAR(50), nullable. Chat ID de Telegram para notificaciones push [code · paciente.py:18-20].
- **creado_en**: TIMESTAMP, default NOW().
- **Relaciones**: 1:N con Turno; 1:N con ListaDeEspera.
- **Índices**: UNIQUE(dni).

### Profesional
- **id**: INTEGER, PK, auto-increment.
- **nombre**: VARCHAR(255), obligatorio.
- **especialidad**: VARCHAR(255), obligatorio. *(Nota: el default "Odontología general" se aplica vía seed, no a nivel de columna)* [code · seed.py:14].
- **duracion_turno**: INTEGER (minutos), obligatorio. *(Nota: el default 30 se aplica vía seed)* [code · seed.py:15].
- **horario_inicio**: VARCHAR(5), obligatorio (formato HH:MM).
- **horario_fin**: VARCHAR(5), obligatorio (formato HH:MM).
- **dias_atencion**: JSON (lista de strings), días de la semana habilitados [code · profesional.py:19].
- **creado_en**: TIMESTAMP, default NOW().
- **Relaciones**: 1:N con Turno.
- **Índices**: INDEX(id).

### Turno
- **id**: INTEGER, PK, auto-increment.
- **fecha**: DATE, obligatorio.
- **hora_inicio**: TIME, obligatorio.
- **hora_fin**: TIME, obligatorio (calculada como hora_inicio + duracion_turno).
- **estado**: VARCHAR(50) con valores permitidos `DISPONIBLE`, `RESERVADO_TEMPORAL`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`; default `DISPONIBLE` [code · turno.py:24-26].
- **paciente_id**: INTEGER, FK → Paciente, nullable (null cuando DISPONIBLE).
- **profesional_id**: INTEGER, FK → Profesional, obligatorio.
- **google_event_id**: VARCHAR(255), nullable. ID del evento en Google Calendar [code · turno.py:33-35].
- **recordatorio_enviado**: BOOLEAN, default FALSE. Flag para evitar duplicar recordatorios [code · turno.py:36-38].
- **creado_en**: TIMESTAMP, default NOW().
- **Relaciones**: N:1 con Paciente; N:1 con Profesional; 1:1 con ReservaTemporal (cuando RESERVADO_TEMPORAL).
- **Constraints**: CHECK(hora_fin > hora_inicio) [code · turno.py:58].
- **Índices**: INDEX(fecha, hora_inicio), INDEX(estado), INDEX(paciente_id, estado), INDEX(google_event_id) [code · turno.py:59-62].

### ReservaTemporal
- **id**: INTEGER, PK, auto-increment.
- **turno_id**: INTEGER, FK → Turno, UNIQUE.
- **expiracion**: TIMESTAMP, momento en que la reserva expira.
- **Relaciones**: 1:1 con Turno.
- **Índices**: INDEX(expiracion) para queries de liberación automática.

### ListaDeEspera (entidad adicional, no detallada en el doc fuente pero necesaria)
- **id**: INTEGER, PK, auto-increment.
- **paciente_id**: INTEGER, FK → Paciente, `ondelete="CASCADE"`.
- **fecha_solicitada**: DATE, preferencia del paciente.
- **creado_en**: TIMESTAMP, default NOW().
- **notificado**: BOOLEAN, default FALSE.
- **turno_ofrecido_id**: INTEGER, FK → Turno, nullable. Turno temporal reservado para ofrecer al paciente.
- **notificado_en**: TIMESTAMP, nullable. Momento en que se envió la notificación Telegram.
- **telegram_chat_id**: VARCHAR, nullable. Chat ID de Telegram para notificar al paciente.
- **Relaciones**: N:1 con Paciente; N:1 con Turno (vía turno_ofrecido_id).

## Seed data inicial

- Un registro en **Profesional** con horarios y duración de turno por defecto.
- Estados del ENUM de Turno predefinidos por la base de datos.
