# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|--------|-------------|---------|
| Arquitectura basada en servicios | Sistema completo | Desacopla componentes (Telegram, n8n, FastAPI, DB, Calendar), facilita mantenimiento y escalabilidad |
| Cliente-Servidor | Interacción Telegram ↔ Backend | El bot actúa como cliente liviano; toda la lógica reside en el servidor |
| Webhook | Telegram → n8n/FastAPI | Permite recepción de mensajes en tiempo real sin polling constante |
| Repository Pattern (implícito) | FastAPI + SQLAlchemy | Abstrae el acceso a PostgreSQL, facilita testing y cambios de persistencia |
| Scheduler / Cron | APScheduler en FastAPI | Centraliza tareas temporizadas (recordatorios, liberación de reservas) |
| State Machine | Entidad Turno | Estados bien definidos (DISPONIBLE → RESERVADO_TEMPORAL → CONFIRMADO → CANCELADO/COMPLETADO) |

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
├── n8n-workflows/                   # Workflows de n8n exportados (JSON)
│   ├── flujo-reserva.json
│   ├── flujo-cancelacion.json
│   ├── flujo-recordatorio.json
│   └── flujo-lista-espera.json
├── backend/                         # Backend FastAPI
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # Punto de entrada FastAPI
│   │   ├── config.py                # Variables de entorno y settings
│   │   ├── models/                  # SQLAlchemy models
│   │   │   ├── paciente.py
│   │   │   ├── profesional.py
│   │   │   ├── turno.py
│   │   │   └── reserva_temporal.py
│   │   ├── schemas/                 # Pydantic schemas
│   │   ├── routers/                 # Endpoints API
│   │   │   ├── turnos.py
│   │   │   ├── pacientes.py
│   │   │   └── profesional.py
│   │   ├── services/                # Lógica de negocio
│   │   │   ├── turno_service.py
│   │   │   ├── paciente_service.py
│   │   │   └── notificacion_service.py
│   │   ├── scheduler/               # Tareas programadas (APScheduler)
│   │   │   └── jobs.py
│   │   └── dependencies.py          # Inyección de dependencias (DB, etc.)
│   ├── alembic/                     # Migraciones de base de datos
│   ├── tests/                       # Tests unitarios e integración
│   ├── requirements.txt
│   └── Dockerfile
├── .jr-orchestrator-state.json      # Estado del orquestador de fundación
└── CHANGES.md                       # Roadmap de cambios (generado por roadmap-generator)
```

> **Nota**: No hay frontend web propio en v1.0. La interfaz de usuario es exclusivamente el bot de Telegram.

## Seguridad

- **Autenticación**: No hay autenticación de usuarios formales en v1.0. El acceso al panel del profesional se asume restringido por red o URL en esta versión.
- **Autorización**: Basada en lógica de negocio (un paciente solo opera sobre sus propios turnos) y validación de IDs de Telegram.
- **Validación de input**: Pydantic en FastAPI para validación automática de payloads REST; validaciones de negocio en servicios.
- **Secrets management**: Variables de entorno para tokens de Telegram, credenciales de Google Calendar (OAuth 2.0), y cadena de conexión a PostgreSQL. Nunca hardcodear secrets.

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | `postgresql://user:pass@localhost/turnos` | Sí |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | `123456:ABC-DEF...` | Sí |
| `GOOGLE_CALENDAR_CREDENTIALS` | JSON de credenciales de cuenta de servicio de Google | `{...}` | Sí |
| `GOOGLE_CALENDAR_ID` | ID del calendario destino | `primary` o ID específico | No |
| `N8N_WEBHOOK_URL` | URL base para webhooks de n8n (si aplica) | `https://n8n.example.com/webhook` | No |
| `RESERVA_TEMPORAL_MINUTOS` | Tiempo de expiración de reserva temporal | `2` | No |
| `RECORDATORIO_HORAS_ANTES` | Horas antes del turno para enviar recordatorio | `24` | No |
| `ENV` | Entorno de ejecución | `development` / `production` | No |
