# Descripción General

## Stack tecnológico

| Capa | Tecnología | Versión / Notas |
|------|-----------|-----------------|
| Automatización / Orquestación | n8n | Workflow engine visual, nodos para APIs y webhooks |
| Backend | FastAPI (Python) | Framework moderno, async, auto-documentación OpenAPI |
| Base de datos | PostgreSQL | Relacional, robusto, manejo de concurrencia |
| Scheduler | APScheduler (Python) | Tareas programadas dentro del backend FastAPI |
| Mensajería (UI) | Telegram Bot API | Bot conversacional como interfaz principal del usuario |
| Calendario | Google Calendar API | Agenda espejo sincronizada, evita desarrollo propio |
| Infraestructura | Docker (implícito por SaaS) | Contenerización recomendada para despliegue |

## Arquitectura general

El sistema adopta una arquitectura **cliente-servidor desacoplada** orientada a servicios:

```
┌─────────────────┐
│   Usuario       │
│  (Telegram)     │
└────────┬────────┘
         │ HTTP / Webhook
         ▼
┌─────────────────┐
│   n8n           │
│ (Orquestador)   │
│  - Webhooks     │
│  - Lógica de    │
│    flujo        │
└────────┬────────┘
         │ HTTP REST
         ▼
┌─────────────────┐
│   FastAPI       │
│   Backend       │
│  - Lógica de    │
│    negocio      │
│  - Validaciones │
│  - Scheduler    │
└────────┬────────┘
         │ SQL
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   Base de Datos │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Google Calendar │
│   API (REST)    │
└─────────────────┘
```

**Justificación**: n8n actúa como orquestador de procesos visuales, gestionando la comunicación entre Telegram y el backend. FastAPI centraliza la lógica de negocio y la persistencia. Google Calendar se utiliza como agenda espejo para aprovechar una herramienta robusta y consolidada.

## Integraciones externas

| Servicio | Propósicio | Tipo |
|----------|-----------|------|
| Telegram Bot API | Interfaz conversacional con pacientes | Webhook + REST |
| Google Calendar API | Creación, actualización y eliminación de eventos de turnos | REST OAuth 2.0 |
| PostgreSQL | Persistencia de pacientes, turnos, configuraciones y estados | SQL / SQLAlchemy |

## API REST (FastAPI)

Endpoints principales agrupados por recurso (inferidos del diseño):

- **Turnos**
  - `GET /turnos/disponibles` — listar fechas y horarios libres.
  - `POST /turnos` — crear reserva temporal o confirmar turno.
  - `PUT /turnos/{id}/confirmar` — confirmar reserva temporal.
  - `PUT /turnos/{id}/cancelar` — cancelar turno confirmado.
  - `PUT /turnos/{id}/reprogramar` — reprogramar a nuevo horario.
  - `GET /turnos/{id}` — obtener detalle de un turno.

- **Pacientes**
  - `POST /pacientes` — registrar nuevo paciente.
  - `GET /pacientes/{id}` — obtener datos del paciente.
  - `GET /pacientes/{id}/turnos` — historial de turnos del paciente.

- **Profesional / Configuración**
  - `GET /profesional/turnos-hoy` — turnos programados para el día.
  - `GET /profesional/metricas` — métricas básicas de uso.
  - `GET /profesional/configuracion` — horarios, duración de turno, días de atención.

- **Lista de espera**
  - `POST /lista-espera` — agregar paciente a lista de espera.
  - `DELETE /lista-espera/{id}` — remover paciente de lista de espera.
  - `POST /lista-espera/notificar` — notificar disponibilidad a pacientes en espera.

- **Webhooks (n8n → FastAPI)**
  - `POST /webhooks/telegram` — recibir mensajes del bot de Telegram.
