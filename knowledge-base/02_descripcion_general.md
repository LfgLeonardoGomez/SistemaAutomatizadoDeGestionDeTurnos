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
  - `GET /turnos/disponibles?fecha=YYYY-MM-DD` — listar slots libres para una fecha [code · routers/turnos.py:36-43].
  - `POST /turnos` — crear reserva temporal [code · routers/turnos.py:46-64].
  - `PUT /turnos/{id}/confirmar` — confirmar reserva temporal [code · routers/turnos.py:67-86].
  - `PUT /turnos/{id}/cancelar` — cancelar turno confirmado [code · routers/turnos.py:89-101].
  - `PUT /turnos/{id}/reprogramar` — reprogramar a nuevo horario [code · routers/turnos.py:104-128].
  - `PUT /turnos/{id}/completar` — marcar turno confirmado como completado [code · routers/turnos.py:131-156].
  - `PUT /turnos/{id}/confirmar-asistencia` — confirmar asistencia desde recordatorio [code · routers/turnos.py:159-171].

- **Pacientes**
  - `POST /pacientes` — registrar nuevo paciente (auto-identificación por DNI) [code · routers/pacientes.py:19-34].
  - `GET /pacientes/{id}` — obtener datos del paciente con historial [code · routers/pacientes.py:37-46].
  - `GET /pacientes/{id}/turnos` — historial de turnos del paciente [code · routers/pacientes.py:49-59].

- **Profesional / Configuración**
  - `GET /profesional/configuracion` — horarios, duración de turno, días de atención [code · routers/profesional.py:29-35].
  - `PUT /profesional/configuracion` — actualizar configuración [code · routers/profesional.py:38-59].
  - `GET /profesional/disponibilidad?fecha=YYYY-MM-DD` — slots libres calculados [code · routers/profesional.py:62-72].
  - `GET /profesional/turnos-hoy` — turnos confirmados del día [code · routers/profesional.py:75-84].
  - `GET /profesional/metricas` — métricas básicas de uso (30 días) [code · routers/profesional.py:87-135].

- **Lista de espera**
  - `POST /lista-espera` — agregar paciente a lista de espera [code · routers/lista_espera.py:14-30].
  - `DELETE /lista-espera/{id}` — remover paciente de lista de espera [code · routers/lista_espera.py:33-41].
  - *(Nota: la notificación a lista de espera es interna, disparada por cancelación/expiración; no hay endpoint REST dedicado)* [code · lista_espera_service.py:222-284].

- **Webhooks (Telegram → FastAPI)**
  - `POST /webhooks/telegram` — recibir updates del Bot API, validar secret token, encolar en background tasks [code · routers/webhooks.py:13-35].
