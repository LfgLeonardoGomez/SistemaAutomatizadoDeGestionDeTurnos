# Proposal: C-01 Foundation Setup

## Why

El proyecto requiere una base sólida de infraestructura y scaffolding antes de poder implementar lógica de negocio. Sin una estructura de directorios coherente, configuración centralizada, contenerización y tests de smoke, cada change subsiguiente arrastra deuda técnica. Este change establece el monorepo, el backend mínimo funcional y las herramientas de desarrollo necesarias para que C-02 (core-models) y los demás changes tengan dónde anclarse.

## What Changes

- Crear estructura de directorios del monorepo (`backend/`, `n8n-workflows/`, `docs/`, `knowledge-base/` ya existe).
- Scaffolding del backend FastAPI: app mínima con endpoint `/health`.
- Configuración centralizada via Pydantic Settings (`app/config.py`) con validación de variables de entorno.
- Inyección de dependencias (`app/dependencies.py`): sesión de DB y settings.
- Alembic inicializado en `backend/alembic/` con configuración para PostgreSQL async.
- Esqueleto de APScheduler (`app/scheduler/jobs.py`) sin jobs de negocio aún.
- `docker-compose.yml` con servicios PostgreSQL, backend y n8n (opcional).
- `.env.example` con todas las variables documentadas en `knowledge-base/08_arquitectura_propuesta.md`.
- `requirements.txt` con dependencias del stack (FastAPI, SQLAlchemy 2.0, Alembic, APScheduler, python-telegram-bot, google-api-python-client, pytest, httpx).
- `.gitignore`, `README.md` técnico mínimo.
- Tests: smoke test del health check (`GET /health` → `200 OK`).

## Capabilities

### New Capabilities
- `backend-health-check`: El backend expone un endpoint `/health` que responde `200 OK` con metadata básica (versión, entorno, timestamp).
- `configuration-management`: El sistema carga y valida variables de entorno via Pydantic Settings al iniciar; falla fast con mensaje claro si falta una variable obligatoria.
- `database-connectivity`: El backend puede establecer conexión a PostgreSQL via SQLAlchemy 2.0 async; Alembic está inicializado y listo para correr migraciones (aunque aún no haya modelos).
- `scheduler-skeleton`: APScheduler se inicializa al arrancar la aplicación FastAPI, corre sin errores y está listo para registrar jobs en changes futuros.

### Modified Capabilities
- *(ninguna — este change no modifica comportamiento existente)*

## Impact

- **Código**: Nuevo directorio `backend/` con toda la estructura de app FastAPI.
- **Infraestructura**: Nuevo `docker-compose.yml` y `.env.example`.
- **Dependencias**: Nuevas dependencias Python en `requirements.txt`.
- **Sistemas**: PostgreSQL y n8n se levantan via Docker Compose.
- **Tests**: Primer suite de tests con pytest + smoke test.
