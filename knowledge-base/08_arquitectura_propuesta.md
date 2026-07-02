# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|--------|-------------|---------|
| Arquitectura basada en servicios | Sistema completo | Desacopla componentes (Telegram, n8n, FastAPI, DB, Calendar), facilita mantenimiento y escalabilidad |
| Cliente-Servidor | Interacción Telegram ↔ Backend | El bot actúa como cliente liviano; toda la lógica reside en el servidor |
| Webhook | Telegram → n8n/FastAPI | Permite recepción de mensajes en tiempo real sin polling constante |
| Repository Pattern (implícito) | FastAPI + SQLAlchemy | Abstrae el acceso a PostgreSQL, facilita testing y cambios de persistencia |
| Scheduler / Cron | APScheduler en FastAPI (fallback) **+ n8n Schedule Trigger** (primario) | Centraliza tareas temporizadas (recordatorios, liberación de reservas). **C-24** sumó n8n como motor primario con `Schedule Trigger` cron y HTTP al backend; APScheduler queda como fallback [code · n8n-workflows/flujo-recordatorio.json] |
| State Machine | Entidad Turno | Estados bien definidos (DISPONIBLE → RESERVADO_TEMPORAL → CONFIRMADO → CANCELADO/COMPLETADO) |
| Orquestador (Router) | `orquestador.json` (n8n) | **C-24**: single entry point del bot. Normaliza payload Telegram (text o callback_query) → `comando` → Switch × 3 → `executeWorkflow` × 3. Mantiene los sub-workflows stateless y desacoplados [code · n8n-workflows/orquestador.json, openspec · archive/2026-07-02-c-24-.../design.md §Decisión 2] |
| Upsert por clave natural | `destinatario_service.upsert_destinatario` | **C-23**: upsert de `TurnoDestinatario` por `(turno_id, canal)`. Centraliza la lógica y respeta `UNIQUE(turno_id, canal)` sin duplicar código en cada punto donde se asigna un destinatario [code · destinatario_service.py] |

## Estructura de directorios

```
Tesis-N8N-turnos/
├── docs/
│   └── cuarta-iteracion.md          # Documento fuente del proyecto
├── knowledge-base/                  # Base de conocimiento generada (este directorio)
├── openspec/                        # Configuración de OpenSpec
│   └── .opencode/
│       ├── commands.json
│       └── skills.json
├── n8n-workflows/                   # Workflows de n8n exportados (JSON) — topología C-24
│   ├── orquestador.json             # Single entry point del bot (Telegram Trigger + Switch × 3)
│   ├── sub-flujo-crear-turno.json   # Sub-workflow invocado por orquestador: rama "crear"
│   ├── sub-flujo-cancelar-turno.json
│   ├── sub-flujo-reprogramar-turno.json
│   ├── flujo-recordatorio.json      # Workflow independiente: cron diario → POST /api/v1/recordatorios/run
│   ├── flujo-lista-espera.json      # Placeholder (deuda C-11, no se ejecuta realmente)
│   └── README.md                    # Topología, credenciales, procedimiento de import
├── backend/                         # Backend FastAPI
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # Punto de entrada FastAPI (incluye router de recordatorios)
│   │   ├── config.py                # Variables de entorno y settings (Pydantic v2)
│   │   ├── dependencies.py          # Inyección de dependencias (DB, settings, X-API-Key)
│   │   ├── seed.py                  # Seed de profesional por defecto
│   │   ├── exceptions.py            # Excepciones de dominio personalizadas
│   │   ├── exception_handlers.py    # Handlers globales de excepciones
│   │   ├── models/                  # SQLAlchemy 2.0 models
│   │   │   ├── base.py
│   │   │   ├── paciente.py
│   │   │   ├── profesional.py
│   │   │   ├── turno.py
│   │   │   ├── turno_destinatario.py    # C-23: destinatario por turno
│   │   │   ├── reserva_temporal.py
│   │   │   └── lista_de_espera.py
│   │   ├── schemas/                 # Pydantic v2 schemas
│   │   │   ├── paciente.py
│   │   │   ├── profesional.py
│   │   │   ├── turno.py             # ReservaTurnoRequest/ConfirmarTurnoRequest con telegram_chat_id opcional (C-23)
│   │   │   ├── recordatorio.py      # C-24: RecordatorioRunResponse, RecordatorioError
│   │   │   ├── lista_espera.py
│   │   │   └── telegram.py
│   │   ├── routers/                 # Endpoints API
│   │   │   ├── turnos.py
│   │   │   ├── pacientes.py
│   │   │   ├── profesional.py
│   │   │   ├── webhooks.py
│   │   │   ├── recordatorios.py     # C-24: POST /api/v1/recordatorios/run
│   │   │   └── lista_espera.py
│   │   ├── services/                # Lógica de negocio
│   │   │   ├── turno_service.py
│   │   │   ├── paciente_service.py
│   │   │   ├── availability_service.py
│   │   │   ├── calendar_service.py
│   │   │   ├── telegram_service.py
│   │   │   ├── notificacion_service.py    # Lee destinatario del turno (C-23)
│   │   │   ├── destinatario_service.py    # C-23: upsert_destinatario(db, turno_id, canal, destinatario)
│   │   │   ├── recordatorio_service.py    # C-24: run_recordatorios_para_todos
│   │   │   └── lista_espera_service.py
│   │   └── scheduler/               # Tareas programadas (APScheduler AsyncIO) — fallback recordatorios
│   │       ├── __init__.py
│   │       └── jobs.py
│   ├── alembic/                     # Migraciones de base de datos (incluye C-23: turno_destinatario + drop telegram_chat_id)
│   ├── tests/                       # Tests unitarios e integración (~40 archivos + tests C-23/C-24)
│   ├── requirements.txt
│   └── Dockerfile
├── .atl/                            # Registry de skills (auto-generado)
└── CHANGES.md                       # Roadmap de cambios (generado por roadmap-generator)
```

> **Nota**: No hay frontend web propio en v1.0. La interfaz de usuario es exclusivamente el bot de Telegram.

## Integración n8n — topología y credenciales (C-24)

> **Actualizado en C-24**. Pre-C-24 los workflows n8n enviaban requests sin `X-API-Key` y el backend las rechazaba con 401 (E2E Telegram → n8n → backend roto). C-24 introduce el **orquestador** como single entry point del bot y agrega el header `X-API-Key` en todos los HTTP Request al backend.

### Topología

El bot del profesional es atendido por **un orquestador** que dispatch-ea a sub-workflows según el comando. Los flujos viejos (1 webhook por flujo) fueron **eliminados** — ver `n8n-workflows/README.md` §"Workflows eliminados" [code · n8n-workflows/README.md].

```
Bot del Profesional
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│  orquestador.json (Telegram Trigger + Code normalizar + Switch × 3)│
│  - Normaliza message.text / callback_query.data → { comando }     │
│  - Switch: crear | cancelar | reprogramar | desconocido (fallback)│
└──────────────────────────────────────────────────────────────────┘
        │
        ├─ "crear"       → sub-flujo-crear-turno.json
        ├─ "cancelar"    → sub-flujo-cancelar-turno.json
        └─ "reprogramar" → sub-flujo-reprogramar-turno.json

Workflows independientes (no dispatch-ados por el orquestador):
  - flujo-recordatorio.json  (Schedule Trigger diario → POST /api/v1/recordatorios/run)
  - flujo-lista-espera.json  (placeholder, deuda C-11, no se ejecuta)
```

**Modelo "1 orquestador por bot"** (Decisión 1 de C-24): el nodo `Telegram Trigger` de n8n autentica con UN token por workflow, por lo que cada profesional importa su propia instancia del orquestador + 3 sub-workflows. Se importan **una vez por profesional**, no por bot compartido.

### Credenciales multi-tenant (patrón C-24)

Por cada profesional, en n8n **Settings → Credentials → New** se configuran **2 credenciales**:

| Credencial | Tipo n8n | Header / Campo | Valor | Dónde se usa |
|------------|----------|----------------|-------|--------------|
| `Telegram Bot` | `telegramApi` | (token interno de n8n) | `<profesional.telegram_bot_token>` | `Telegram Trigger` (orquestador) + todos los `Telegram` nodes de los sub-workflows |
| `Profesional API Key` | `httpHeaderAuth` | Header `X-API-Key` | `<profesional.api_key>` | Todos los `HTTP Request` nodes de los 3 sub-workflows + `flujo-recordatorio` + `flujo-lista-espera` |

Los `HTTP Request` nodes referencian `Profesional API Key` vía `Authentication → Generic Credential Type → httpHeaderAuth`. **No se hardcodea** el `X-API-Key` en ningún campo de expresión; la credencial se configura una vez y se reusa en todos los nodos. n8n enmascara credentials en exec logs [openspec · archive/2026-07-02-c-24-.../design.md §Decisión 4, code · n8n-workflows/README.md §"Patrón de credenciales"].

> 🔁 **Rotación de `api_key`**: tocar solo la credencial en n8n (un cambio, todos los nodos actualizados). No requiere redeploy.

### Flujo de datos E2E

```
Paciente (Telegram) → @BotFather → orquestador.json
                                   └→ Code "Normalizar Comando" (message.text | callback_query.data)
                                      └→ Switch (3 ramas)
                                         └→ executeWorkflow → sub-flujo-X.json
                                            └→ HTTP Request (Header Auth: X-API-Key)
                                               └→ FastAPI (validates X-API-Key → profesional_id)
                                                  └→ SQLAlchemy → PostgreSQL
                                                  └→ (si confirma) Google Calendar
                                                  └→ (al confirmar) upsert TurnoDestinatario
                                                  └→ Telegram - Send Message (al paciente)
```

### Coexistencia con el webhook del backend

El backend expone `POST /api/v1/webhooks/telegram` (C-08) que procesa updates de Telegram directamente con la lógica conversacional completa (`telegram_service.procesar_mensaje`). El orquestador n8n es una **alternativa** que delega a los mismos endpoints REST saltándose la lógica conversacional del backend.

**Decisión OQ-1 resuelta**: `@BotFather` apunta al `Telegram Trigger` del orquestador n8n. El webhook del backend queda ocioso para este profesional, pero disponible como fallback (si n8n se cae, cambiar `@BotFather` al webhook del backend).

Telegram solo enruta updates al **último** webhook configurado, así que no hay duplicación si se configura solo el orquestador.

## Dos motores de recordatorio (n8n + APScheduler)

El sistema de recordatorios tiene **dos motores** que conviven y comparten la **misma lógica** de `notificacion_service` (`obtener_turnos_para_recordar` + `enviar_recordatorio_telegram` + `marcar_recordatorio_enviado`):

1. **n8n primario** (`flujo-recordatorio.json`): corre via `Schedule Trigger` con cron `0 10 * * *` (default 10:00 hora local). Llama a `POST /api/v1/recordatorios/run?fecha=mañana` y el backend itera por profesionales activos, busca turnos a recordar y los envía.
2. **APScheduler fallback** (`scheduler.jobs._enviar_recordatorios_job` en el backend, C-08): corre en el backend, también diario. Útil si n8n está caído o si el profesional no configuró n8n.

El campo `turno.recordatorio_enviado` en la DB evita **doble dispatch**: el primer motor que envíe el recordatorio lo marca como enviado, y el segundo lo skipea. En v1.0 se recomienda activar **solo uno** de los dos motores por profesional [code · n8n-workflows/README.md §"Dos motores de recordatorio"].

### Endpoint backend del recordatorio (C-24)

Nuevo endpoint `POST /api/v1/recordatorios/run` consumido por `flujo-recordatorio.json` [code · routers/recordatorios.py]:

- **Auth**: `X-API-Key` header (vía `get_profesional_by_api_key`).
- **Query param**: `?fecha=YYYY-MM-DD` (default: mañana).
- **Comportamiento**: itera por `Profesional where is_active=True`, llama a `obtener_turnos_para_recordar` + `enviar_recordatorio_telegram` + `marcar_recordatorio_enviado`. Patrón A: `commit` por profesional; try/except por profesional y por turno (un error no rompe el batch).
- **Response**: `RecordatorioRunResponse { fecha, total_candidatos, total_enviados, total_fallidos, errores: list[RecordatorioError] }` [code · schemas/recordatorio.py].
- **Auth semantics**: la `X-API-Key` válida autoriza al caller; el endpoint itera sobre **TODOS** los profesionales activos — el caller no es el destinatario, es el invocador del batch [code · routers/recordatorios.py:32-44].

## Seguridad

- **Autenticación profesional (multi-tenant)**: cada request REST a `/turnos/*`, `/pacientes/*`, `/lista-espera/*`, `/api/v1/recordatorios/*` exige `X-API-Key` header válido (mapea a `profesional_id` vía `get_profesional_by_api_key` en `backend/app/dependencies.py`). Sin él, **401** [code · dependencies.py:98-115].
- **Autenticación webhook Telegram**: `POST /webhooks/telegram` exige `X-Telegram-Bot-Api-Secret-Token` válido. Sin él, **403** [code · dependencies.py:118-139].
- **Identificación de pacientes**: el paciente **nunca se autentica** — se identifica por DNI (scoped por `profesional_id` vía `UniqueConstraint(profesional_id, dni)`). La `X-API-Key` la presenta el profesional (o n8n en su nombre) [code · paciente.py:36-39, openspec · archive/2026-07-02-c-23-.../design.md §Context].
- **Validación de input**: Pydantic en FastAPI para validación automática de payloads REST; validaciones de negocio en servicios.
- **Secrets management**: Variables de entorno para credenciales OAuth de Google Calendar (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) y cadena de conexión a PostgreSQL. Los tokens de Telegram y Google Calendar por profesional se almacenan en la base de datos (`profesional.telegram_bot_token`, `credenciales_google.*`). En n8n, los secrets se inyectan vía `httpHeaderAuth` credential (enmascarado en logs). Nunca hardcodear secrets.

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | `postgresql+asyncpg://user:pass@localhost/turnos` | Sí |
| `TELEGRAM_WEBHOOK_SECRET` | Secret token para validar webhooks de Telegram | `mi-secreto` | Sí |
| `GOOGLE_CLIENT_ID` | Client ID de OAuth 2.0 para Google Calendar | `abc123.apps.googleusercontent.com` | Sí |
| `GOOGLE_CLIENT_SECRET` | Client Secret de OAuth 2.0 para Google Calendar | `GOCSPX-abc123...` | Sí |
| `GOOGLE_CALENDAR_MAX_RETRIES` | Máximo de reintentos ante errores 5xx de Google Calendar | `3` | No |
| `GOOGLE_CALENDAR_BASE_DELAY` | Delay inicial (segundos) para backoff exponencial | `1.0` | No |
| `GOOGLE_CALENDAR_MAX_DELAY` | Delay máximo (segundos) para backoff exponencial | `10.0` | No |
| `N8N_WEBHOOK_URL` | URL base para webhooks de n8n (legacy) | `https://n8n.example.com/webhook` | No |
| `RESERVA_TEMPORAL_MINUTOS` | Tiempo de expiración de reserva temporal | `10` | No |
| `LISTA_ESPERA_MINUTOS` | Tiempo de espera para aceptar turno ofrecido desde lista | `5` | No |
| `RECORDATORIO_HORAS_ANTES` | Horas antes del turno para enviar recordatorio (criterio general; el endpoint usa una ventana calculada) | `24` | No |
| `RECORDATORIO_JOB_INTERVAL_MINUTOS` | Intervalo del job de recordatorios (APScheduler fallback) | `60` | No |
| `COMPLETADO_JOB_INTERVAL_MINUTOS` | Intervalo del job de marcar turnos completados | `5` | No |
| `ENV` | Entorno de ejecución | `development` / `production` | No |

**Variables de n8n (no backend)**: `BACKEND_URL` (URL del backend, usada por los workflows C-24) y `FASTAPI_BASE_URL` (legacy, solo `flujo-lista-espera`). Documentadas en `n8n-workflows/README.md` §"Variables de entorno en n8n".

## Seguridad

- **Autenticación**: No hay autenticación de usuarios formales en v1.0. El acceso al panel del profesional se asume restringido por red o URL en esta versión.
- **Autorización**: Basada en lógica de negocio (un paciente solo opera sobre sus propios turnos) y validación de IDs de Telegram.
- **Validación de input**: Pydantic en FastAPI para validación automática de payloads REST; validaciones de negocio en servicios.
- **Secrets management**: Variables de entorno para credenciales OAuth de Google Calendar (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) y cadena de conexión a PostgreSQL. Los tokens de Telegram y Google Calendar por profesional se almacenan en la base de datos. Nunca hardcodear secrets.

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | `postgresql+asyncpg://user:pass@localhost/turnos` | Sí |
| `TELEGRAM_WEBHOOK_SECRET` | Secret token para validar webhooks de Telegram | `mi-secreto` | Sí |
| `GOOGLE_CLIENT_ID` | Client ID de OAuth 2.0 para Google Calendar | `abc123.apps.googleusercontent.com` | Sí |
| `GOOGLE_CLIENT_SECRET` | Client Secret de OAuth 2.0 para Google Calendar | `GOCSPX-abc123...` | Sí |
| `GOOGLE_CALENDAR_MAX_RETRIES` | Máximo de reintentos ante errores 5xx de Google Calendar | `3` | No |
| `GOOGLE_CALENDAR_BASE_DELAY` | Delay inicial (segundos) para backoff exponencial | `1.0` | No |
| `GOOGLE_CALENDAR_MAX_DELAY` | Delay máximo (segundos) para backoff exponencial | `10.0` | No |
| `N8N_WEBHOOK_URL` | URL base para webhooks de n8n (si aplica) | `https://n8n.example.com/webhook` | No |
| `RESERVA_TEMPORAL_MINUTOS` | Tiempo de expiración de reserva temporal | `10` | No |
| `LISTA_ESPERA_MINUTOS` | Tiempo de espera para aceptar turno ofrecido desde lista | `5` | No |
| `RECORDATORIO_HORAS_ANTES` | Horas antes del turno para enviar recordatorio | `24` | No |
| `RECORDATORIO_JOB_INTERVAL_MINUTOS` | Intervalo del job de recordatorios (APScheduler) | `60` | No |
| `COMPLETADO_JOB_INTERVAL_MINUTOS` | Intervalo del job de marcar turnos completados | `5` | No |
| `ENV` | Entorno de ejecución | `development` / `production` | No |
