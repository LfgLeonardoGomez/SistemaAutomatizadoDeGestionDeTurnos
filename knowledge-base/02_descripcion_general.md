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

El sistema adopta una arquitectura **cliente-servidor desacoplada** orientada a servicios. **Actualizado en C-24**: el n8n es ahora el **orquestador de Telegram como single entry point** (no un proxy 1:1); los sub-workflows y el flujo de recordatorios llaman al backend con `X-API-Key`:

```
┌─────────────────┐
│   Usuario       │
│  (Telegram)     │
└────────┬────────┘
         │ Webhook (Telegram Trigger)
         ▼
┌─────────────────────────────────────────────┐
│   n8n — orquestador (C-24)                  │
│  - orquestador.json (Telegram Trigger +     │
│    Code + Switch × 3 + executeWorkflow × 3) │
│  - sub-flujo-crear-turno.json               │
│  - sub-flujo-cancelar-turno.json            │
│  - sub-flujo-reprogramar-turno.json         │
│  - flujo-recordatorio.json (Schedule        │
│    Trigger diario, independiente)           │
└────────┬────────────────────────────────────┘
         │ HTTP REST + X-API-Key
         ▼
┌─────────────────────────────────────────────┐
│   FastAPI Backend                            │
│  - Lógica de negocio (turno, paciente)       │
│  - Validaciones (Pydantic v2)                │
│  - APScheduler (fallback recordatorios)      │
│  - 401 sin X-API-Key válida                  │
└────────┬────────────────────────────────────┘
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

**Justificación**: n8n actúa como **capa de orquestación visible** del bot de Telegram. Cada profesional importa su propia instancia (1 orquestador + 3 sub-workflows + flujo-recordatorio) con 2 credenciales (`Telegram Bot` y `Header Auth X-API-Key`). FastAPI centraliza la lógica de negocio y la persistencia, y expone endpoints REST multi-tenant con `X-API-Key` por profesional. Google Calendar se utiliza como agenda espejo para aprovechar una herramienta robusta y consolidada. El backend también procesa updates de Telegram vía `POST /api/v1/webhooks/telegram` (C-08) como **alternativa documentada** al orquestador n8n (OQ-1 resuelta en C-24).

## Integraciones externas

| Servicio | Propósito | Tipo |
|----------|-----------|------|
| Telegram Bot API | Interfaz conversacional con pacientes. Bot consumido por n8n orquestador (C-24, entry point principal) **o** por el webhook del backend (`POST /api/v1/webhooks/telegram`, C-08, alternativa) | Webhook + REST |
| n8n (orquestador) | C-24 — single entry point del bot; switch por comando (text o callback); dispatch a sub-workflows; cron de recordatorios | n8n workflows (orquestador.json + 3 sub-flujos + flujo-recordatorio) |
| Google Calendar API | Creación, actualización y eliminación de eventos de turnos | REST OAuth 2.0 |
| PostgreSQL | Persistencia de pacientes, turnos, configuraciones, estados, destinatarios de notificación (C-23) | SQL / SQLAlchemy |

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
  - `POST /webhooks/telegram` — recibir updates del Bot API, validar secret token, encolar en background tasks [code · routers/webhooks.py:13-35]. **Alternativa** al orquestador n8n (C-24); por defecto `@BotFather` apunta al `Telegram Trigger` del orquestador.

- **Recordatorios (C-24)**
  - `POST /api/v1/recordatorios/run?fecha=YYYY-MM-DD` — itera por profesionales activos y envía recordatorios del día objetivo [code · routers/recordatorios.py:32-44]. Consumido por `flujo-recordatorio.json` (n8n primario). El APScheduler del backend sigue activo como fallback y respeta el flag `turno.recordatorio_enviado` para evitar doble dispatch.
