# Tasks: C-01 Foundation Setup

## 1. Monorepo Structure

- [x] 1.1 Create `backend/` directory with `app/`, `alembic/`, and `tests/` subdirectories.
- [x] 1.2 Create `n8n-workflows/` directory with placeholder `README.md`.
- [x] 1.3 Create empty package directories under `backend/app/`: `models/`, `schemas/`, `routers/`, `services/` each with `__init__.py`.
- [x] 1.4 Create `backend/app/scheduler/` with `__init__.py` and `jobs.py` (esqueleto).
- [x] 1.5 Write `.gitignore` (Python + Docker + env files) at project root.

## 2. Dependencies and Configuration

- [x] 2.1 Write `backend/requirements.txt` with FastAPI, uvicorn, SQLAlchemy 2.0, alembic, asyncpg, pydantic-settings, APScheduler, python-telegram-bot, google-api-python-client, pytest, pytest-asyncio, httpx.
- [x] 2.2 Write `backend/app/config.py` with Pydantic Settings class loading all env vars from KB §Variables de entorno.
- [x] 2.3 Write `.env.example` at project root with dummy values for all variables (sanitized, no real credentials).
- [x] 2.4 Verify that starting the app without required env vars raises `ValidationError` with clear message.

## 3. FastAPI Minimal App

- [x] 3.1 Write `backend/app/main.py` with lifespan context manager, FastAPI app instance, and `GET /health` endpoint.
- [x] 3.2 Health check response SHALL include `status`, `version`, `timestamp`, and `environment`.
- [x] 3.3 Write `backend/app/dependencies.py` with `get_settings()` and `get_db()` (async session factory) dependencies.
- [x] 3.4 Ensure `main.py` imports and exposes the app correctly for `uvicorn`.

## 4. Database and Migrations

- [x] 4.1 Run `alembic init alembic` inside `backend/` and adjust `alembic.ini` to use `DATABASE_URL` env var.
- [x] 4.2 Configure `backend/alembic/env.py` to create a sync SQLAlchemy engine from the async URL (strip `+asyncpg` if present).
- [x] 4.3 Verify `alembic current` runs without errors against a local/dev PostgreSQL instance (or Docker).

## 5. Scheduler Skeleton

- [x] 5.1 Write `backend/app/scheduler/jobs.py` with `init_scheduler(app)` and `shutdown_scheduler(app)` functions.
- [x] 5.2 Integrate scheduler lifecycle into FastAPI lifespan in `main.py`.
- [x] 5.3 Add a dummy job registration in `init_scheduler` to verify the scheduler accepts jobs (remove or keep as example).
- [x] 5.4 Verify scheduler starts and shuts down without errors in tests.

## 6. Docker Compose

- [x] 6.1 Write `docker-compose.yml` with services `db` (PostgreSQL 15+), `backend` (FastAPI app), and optional `n8n` using Docker Compose `profiles`.
- [x] 6.2 Add `healthcheck` to `db` service and `depends_on` with `condition: service_healthy` for `backend`.
- [x] 6.3 Add `backend/Dockerfile` (multi-stage o single-stage simple) with Python 3.11+.
- [x] 6.4 Verify `docker compose up --build` levanta backend y db sin errores y `/health` responde.

## 7. Tests

- [x] 7.1 Write `backend/tests/conftest.py` with pytest fixtures para `client` (TestClient) y `settings`.
- [x] 7.2 Write `backend/tests/test_health.py` con smoke test: `GET /health` → `200 OK` y campos requeridos presentes.
- [x] 7.3 Write `backend/tests/test_config.py` con test de validación de env vars faltantes.
- [x] 7.4 Run `pytest` desde `backend/` y confirmar que todos los tests pasan.

## 8. Documentation

- [x] 8.1 Write minimal `backend/README.md` con instrucciones de setup local (venv, pip install, .env, pytest).
- [x] 8.2 Documentar en `backend/README.md` el comando para levantar con Docker Compose.
- [x] 8.3 Agregar comentario en `jobs.py` indicando que es esqueleto y que los jobs de negocio se agregarán en C-06 y C-10.
