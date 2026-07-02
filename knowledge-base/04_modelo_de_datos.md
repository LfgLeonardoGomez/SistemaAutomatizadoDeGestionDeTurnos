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
│ profesional_id│      │ paciente_id  │       │ horario_fin  │
│ creado_en    │       │ profesional_id│      │ dias_atencion │
└──────────────┘       │ google_event_id│     │ telegram_bot_token│
                       │ recordatorio_enviado│ │ api_key      │
                       │ creado_en    │       │ is_active    │
                       └──────┬───────┘       └──────┬───────┘
                              │ 1:N                  │
                              ▼                      │ 1:N
                       ┌──────────────┐              │
                       │TurnoDestinatario│           │
                       │──────────────│              │
                       │ id (PK)      │              │
                       │ turno_id (FK)│              │
                       │ canal (ENUM) │              │
                       │ destinatario │              │
                       │ UNIQUE(turno_id,canal)      │
                       │ creado_en    │              │
                       └──────────────┘              │
                              │ 1:1                  │
                              ▼                      ▼
                       ┌──────────────┐       ┌──────────────┐
                       │ReservaTemporal│       │ ListaDeEspera│
                       │──────────────│       │──────────────│
                       │ id (PK)      │       │ id (PK)      │
                       │ turno_id (FK)│       │ paciente_id  │
                       │ expiracion   │       │ fecha_solic. │
                       └──────────────┘       │ telegram_chat_id│
                                              │ notificado   │
                                              │ turno_ofrecido_id│
                                              └──────────────┘
```

## Entidades

### Paciente
- **id**: INTEGER, PK, auto-increment.
- **nombre**: VARCHAR(255), obligatorio.
- **apellido**: VARCHAR(255), obligatorio.
- **dni**: VARCHAR(50), obligatorio.
- **telefono**: VARCHAR(50), obligatorio (vinculado a Telegram).
- **profesional_id**: INTEGER, FK → Profesional, `ondelete="CASCADE"`, obligatorio.
- **creado_en**: TIMESTAMP, default NOW().
- **Relaciones**: N:1 con Profesional; 1:N con Turno; 1:N con ListaDeEspera.
- **Índices**: `UNIQUE(profesional_id, dni)` — el DNI es único **scoped por profesional** (un mismo DNI puede existir en distintos profesionales, no es globalmente único) [code · paciente.py:36-39].
- ⚠️ **Columna eliminada (C-23)**: la columna `telegram_chat_id` se eliminó del modelo `paciente` porque era **código muerto** — ningún flujo del backend la escribía, por lo que siempre era `NULL` y el job de recordatorios la leía vacía, marcaba `recordatorio_enviado=True` y nunca enviaba nada. El destinatario de notificación ahora vive en `turno_destinatario` (ver más abajo) [code · paciente.py, openspec · archive/2026-07-02-c-23-turno-destinatario-multicanal/design.md §Decisión 2].

### Profesional
- **id**: INTEGER, PK, auto-increment.
- **nombre**: VARCHAR(255), obligatorio.
- **especialidad**: VARCHAR(255), obligatorio. *(Nota: el default "Odontología general" se aplica vía seed, no a nivel de columna)*.
- **duracion_turno**: INTEGER (minutos), obligatorio. *(Nota: el default 30 se aplica vía seed)*.
- **horario_inicio**: VARCHAR(5), obligatorio (formato HH:MM).
- **horario_fin**: VARCHAR(5), obligatorio (formato HH:MM).
- **dias_atencion**: JSON (lista de strings), días de la semana habilitados.
- **telegram_bot_token**: VARCHAR, nullable. Token del bot de Telegram del profesional (C-15). Multi-tenant: cada profesional tiene su propio bot [code · profesional.py].
- **api_key**: VARCHAR, nullable. API key del profesional para auth server-to-server (n8n, integraciones) [code · dependencies.py#get_profesional_by_api_key].
- **is_active**: BOOLEAN, default TRUE. Flag para activar/desactivar profesionales sin borrarlos (usado por `POST /api/v1/recordatorios/run` que itera solo `is_active=True`) [code · recordatorio_service.py:133].
- **creado_en**: TIMESTAMP, default NOW().
- **Relaciones**: 1:N con Turno; 1:N con Paciente; 1:N con CredencialesGoogle.

### Turno
- **id**: INTEGER, PK, auto-increment.
- **fecha**: DATE, obligatorio.
- **hora_inicio**: TIME, obligatorio.
- **hora_fin**: TIME, obligatorio (calculada como hora_inicio + duracion_turno).
- **estado**: ENUM PostgreSQL `turno_estado_enum` con valores `DISPONIBLE`, `RESERVADO_TEMPORAL`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`; default `DISPONIBLE` [code · turno.py:27-40].
- **paciente_id**: INTEGER, FK → Paciente, `ondelete="SET NULL"`, nullable (null cuando DISPONIBLE).
- **profesional_id**: INTEGER, FK → Profesional, `ondelete="CASCADE"`, obligatorio.
- **google_event_id**: VARCHAR(255), nullable. ID del evento en Google Calendar.
- **recordatorio_enviado**: BOOLEAN, default FALSE. Flag para evitar duplicar recordatorios (compartido por los dos motores — ver [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) §"Dos motores de recordatorio").
- **creado_en**: TIMESTAMP, default NOW().
- **Relaciones**: N:1 con Paciente; N:1 con Profesional; 1:1 con ReservaTemporal (cuando RESERVADO_TEMPORAL); 1:N con TurnoDestinatario.
- **Constraints**: `CHECK(hora_fin > hora_inicio)` [code · turno.py:78].
- **Índices**: `INDEX(fecha, hora_inicio)`, `INDEX(estado)`, `INDEX(paciente_id, estado)`, `INDEX(google_event_id)`, `uq_turno_active_slot` UNIQUE PARCIAL sobre `(profesional_id, fecha, hora_inicio) WHERE estado IN ('DISPONIBLE', 'RESERVADO_TEMPORAL', 'CONFIRMADO')` (permite múltiples CANCELADO/COMPLETADO en el mismo slot para preservar historial) [code · turno.py:79-94].

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

> **Nota histórica (C-23)**: `ListaDeEspera.telegram_chat_id` se mantiene **por registro** (precedente del modelo destinatario) — el sistema notifica a este chat específico cuando se libera un turno. NO se eliminó porque es la única vía de contactar a un paciente que está en lista de espera pero no tiene turno asociado (no hay `turno_destinatario` que lo cubra).

### TurnoDestinatario *(C-23 — modelo de destinatario por turno)*

> **Nuevo en C-23** [openspec · archive/2026-07-02-c-23-turno-destinatario-multicanal/proposal.md]. Modela **a quién** y **por qué canal** se notifica un turno específico, separado de **quién** es el paciente (modelado por `paciente` con DNI).

- **id**: INTEGER, PK, auto-increment.
- **turno_id**: INTEGER, FK → Turno, `ondelete="CASCADE"`, obligatorio.
- **canal**: ENUM PostgreSQL `canal_notificacion_enum` con valores `TELEGRAM`, `EMAIL`; obligatorio.
- **destinatario**: VARCHAR(255), obligatorio. Valor del contacto en el canal:
  - Si `canal=TELEGRAM` → `telegram_chat_id` (string con el ID numérico del chat).
  - Si `canal=EMAIL` → dirección de email.
- **creado_en**: TIMESTAMP, default NOW().
- **Relaciones**: N:1 con Turno (cascade).
- **Constraints**: `UNIQUE(turno_id, canal)` con nombre `uq_turno_destinatario_canal` — garantiza a lo sumo un destinatario por canal por turno [code · turno_destinatario.py:48].
- **Índices**: `ix_turno_destinatario_turno_id` sobre `turno_id` [code · turno_destinatario.py:49].
- **Cardinalidad**: un turno tiene **0..N destinatarios**, uno por canal. Lo típico es 1 (TELEGRAM) o 2 (TELEGRAM + EMAIL); puede ser 0 (turnos legacy o administrativos donde el recordatorio se omite con warning).

> **Por qué existe esta tabla** (no columnas en `turno`): la relación "turno → canal → contacto" es **M:N a nivel conceptual** (un paciente con varios chats puede recibir el mismo turno en distintos chats, un mismo email puede recibir varios turnos). Modelar con una tabla hija + UNIQUE(turno_id, canal) es la forma normalizada mínima que permite "uno o **ambos** canales" sin migraciones adicionales cuando aparezca un tercer canal [openspec · archive/2026-07-02-c-23-.../design.md §Decisión 1].

> **Estado del envío por canal**: el **sender de `EMAIL` no está implementado** (C-23 lo deja como modelo preparado). Si un turno tiene destinatario `EMAIL`, el modelo lo persiste pero el envío queda fuera de alcance (log informativo). Solo `TELEGRAM` se envía efectivamente vía `enviar_recordatorio_telegram` [code · notificacion_service.py:67-77].

## Seed data inicial

- Un registro en **Profesional** con horarios y duración de turno por defecto.
- Estados del ENUM de Turno predefinidos por la base de datos.
