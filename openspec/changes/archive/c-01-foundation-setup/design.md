# Design: C-01 Foundation Setup

## Context

El proyecto Tesis-N8N-turnos es un sistema de gestión de turnos médicos (odontología) que orquesta Telegram → n8n → FastAPI → PostgreSQL → Google Calendar. En este momento no existe código de backend ni infraestructura ejecutable. Este change es el punto cero: debe dejar un monorepo estructurado, un backend corriendo con health check, y todas las herramientas de desarrollo operativas para que C-02 (core-models) pueda comenzar inmediatamente.

## Goals / Non-Goals

**Goals:**
1. Estructura de directorios del monorepo acorde a `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios.
2. FastAPI app mínima con lifecycle management (startup/shutdown) para inicializar el scheduler.
3. Configuración centralizada y tipada con Pydantic Settings v2.
4. Conexión a PostgreSQL via SQLAlchemy 2.0 async (`create_async_engine`, `AsyncSession`).
5. Alembic inicializado y configurado para usar el async driver (`asyncpg`).
6. APScheduler (`AsyncIOScheduler`) integrado en el lifespan de FastAPI.
7. Docker Compose que levante PostgreSQL + backend en red compartida.
8. Smoke test automatizado del health check.
9. `.env.example` con todas las variables del KB.

**Non-Goals:**
- No se crean modelos SQLAlchemy ni tablas (C-02).
- No se implementan routers de negocio (turnos, pacientes, etc.) — solo `/health`.
- No se configuran jobs de APScheduler con lógica de negocio (C-06, C-10).
- No se implementa autenticación ni autorización (v1.0 no tiene auth formal).
- No se conecta Google Calendar ni Telegram Bot (C-05, C-08).
- No se incluye frontend web (v1.0 es Telegram-only).
- No se versiona la API aún (no hay endpoints de negocio).

## Decisions

### DEC-01: SQLAlchemy 2.0 async desde v1
**Decisión**: Usar `create_async_engine` + `AsyncSession` con `asyncpg` desde el scaffolding.
**Rationale**: El KB §DD-04 y §DD-05 apuntan a FastAPI async. Si arrancamos con sync, migrar a async más adelante es refactor costoso. Es más fácil empezar async y usar `run_in_threadpool` para librerías sync (Google Calendar SDK) cuando sea necesario.
**Alternativas**: SQLAlchemy sync con `psycopg2`. Rechazada porque contradice la elección de FastAPI async.

### DEC-02: Pydantic Settings v2 con `pydantic-settings`
**Decisión**: Configuración via `pydantic-settings` (paquete separado en Pydantic v2) en `app/config.py`.
**Rationale**: Validación automática de tipos, parsing de env vars, valores por defecto, y falla fast al iniciar si falta algo crítico. Se alinea con las reglas duras del proyecto: "NUNCA hardcodear configuración".
**Alternativas**: `os.getenv` suelto, `python-dotenv` manual. Rechazadas por falta de validación y centralización.

### DEC-03: Alembic con `asyncpg` y URL de conexión compartida
**Decisión**: Alembic configurado para usar la misma `DATABASE_URL` que el backend, reemplazando el driver `postgresql+asyncpg` por `postgresql+psycopg` o `postgresql` en `env.py` si es necesario para las migraciones (Alembic puede correr sync).
**Rationale**: Alembic no requiere async para correr migraciones. La configuración de `alembic.ini` y `env.py` debe apuntar a la misma base de datos pero puede usar un pool sync. Esto simplifica el setup inicial.
**Nota**: Si `DATABASE_URL` contiene `+asyncpg`, el `env.py` de Alembic debe normalizarlo a `postgresql://` para el pool sync de Alembic.

### DEC-04: APScheduler `AsyncIOScheduler` integrado en lifespan
**Decisión**: Inicializar `AsyncIOScheduler` en el `lifespan` context manager de FastAPI (`@asynccontextmanager`).
**Rationale**: Garantiza que el scheduler arranca con la app y se detiene gracefulmente al cerrar. Evita inicialización global a nivel de módulo que puede causar problemas en tests.
**Alternativas**: Inicializar en `main.py` global. Rechazada porque dificulta testing y no permite lifecycle control.

### DEC-05: pytest + pytest-asyncio + httpx para tests
**Decisión**: Usar `pytest` con plugin `pytest-asyncio` y `httpx.AsyncClient` (via `fastapi.TestClient` sync como alternativa simple para smoke tests).
**Rationale**: `TestClient` de FastAPI es sync y usa `httpx` internamente; para un smoke test básico es suficiente. Cuando C-02 agregue async DB operations, `pytest-asyncio` y `AsyncClient` serán necesarios. Incluimos ambos desde ahora para no tener que cambiar el `requirements.txt` luego.
**Alternativas**: Solo `unittest`. Rechazada por ser menos productiva y no tener fixtures nativas.

### DEC-06: Docker Compose con health checks
**Decisión**: `docker-compose.yml` con servicio `db` que incluye `healthcheck` y servicio `backend` que depende de `db` en estado `service_healthy`.
**Rationale**: Evita race conditions donde el backend intenta conectar antes de que PostgreSQL esté listo. n8n se incluye como servicio opcional comentado o con `profiles: ["n8n"]` para no forzarlo en desarrollo backend.

### DEC-07: No estructura de paquetes anidada excesiva en v1
**Decisión**: Aplanar ligeramente la estructura de `backend/app/` evitando crear directorios vacíos (models/, schemas/, routers/, services/) hasta que C-02 los necesite.
**Rationale**: Directorios vacíos con `__init__.py` generan ruido y pueden confundir. Se crean los que se usan (`scheduler/`, `dependencies.py`, `config.py`, `main.py`) y se deja documentado dónde irán los demás.
**Nota**: Se crean `models/`, `schemas/`, `routers/`, `services/` como directorios vacíos con `__init__.py` vacíos para que la estructura final sea visible y C-02 solo agregue archivos. Esto evita discusiones de "dónde va cada cosa".
**Revisión**: Dado que el KB ya define la estructura y C-02 la necesita, se crean los directorios vacíos para claridad.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| `asyncpg` puede no estar disponible en Windows nativo para desarrollo | Documentar que Docker Compose es el entorno de desarrollo recomendado; `psycopg` (sync) como fallback local si es estrictamente necesario. |
| Alembic async puede confundir a developers nuevos | Comentar en `env.py` que Alembic corre sync y documentar el comando `alembic upgrade head` en README. |
| APScheduler sin jobs puede parecer "código muerto" | Documentar en `jobs.py` que es esqueleto y referenciar los changes que lo llenarán (C-06, C-10). |
| Docker Compose con n8n opcional puede confundir | Usar `profiles` de Docker Compose para n8n; el backend funciona standalone. |
| Variables de entorno sensibles en `.env.example` | `.env.example` solo tiene valores dummy/sanitizados; nunca credenciales reales. Documentar en README. |

## Migration Plan

No aplica — este es el change inicial. No hay estado previo que migrar. El "rollback" es `docker compose down -v` para destruir volúmenes de PostgreSQL.

## Open Questions

1. **IN-01 (resolución)**: `RESERVA_TEMPORAL_MINUTOS` se define en `.env.example` con valor por defecto `10` (no 2), documentando que 2 minutos es solo para casos de prueba. Esto queda reflejado en `config.py`.
2. **IN-03 (resolución)**: Panel del profesional vía Telegram en v1.0. No se crea ningún endpoint de panel web en C-01; los endpoints de profesional se agregan en C-03, C-06, C-12 y se consumen vía Telegram Bot (C-08, C-12).
3. **Scale**: Aunque el doc fuente menciona SaaS, C-01 asume single-tenant single-profesional. No se agrega `tenant_id` aún porque no hay modelos (C-02 evaluará si anticiparlo). Esto se documenta como deuda técnica consciente.
