# Backend — Tesis N8N Turnos

FastAPI backend para el sistema de gestión de turnos médicos (odontología).

## Setup local

1. Crear entorno virtual e instalar dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copiar `.env.example` a `.env` y completar las variables.

3. Correr tests:
   ```bash
   pytest
   ```

4. Levantar la app:
   ```bash
   uvicorn app.main:app --reload
   ```

## Docker Compose

Levantar PostgreSQL + backend:

```bash
docker compose up -d --build backend
```

El servicio `backend` espera a que `db` esté healthy antes de iniciar.

Para incluir n8n:

```bash
docker compose --profile n8n up -d
```

## Alembic

Alembic está configurado para usar el mismo `DATABASE_URL` que el backend.
El driver `+asyncpg` se normaliza automáticamente a `+psycopg` para las migraciones sync.

```bash
cd backend
alembic current
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

## Scheduler

APScheduler (`AsyncIOScheduler`) se inicializa en el lifespan de FastAPI.
Los jobs de negocio se agregarán en changes futuros (C-06, C-10).

## Estructura de paquetes

```
app/
├── config.py          # Pydantic Settings
├── dependencies.py    # Inyección de dependencias (DB, settings)
├── main.py            # FastAPI app + lifespan
├── models/            # SQLAlchemy models (C-02)
├── routers/           # Endpoints API (C-03)
├── schemas/           # Pydantic schemas (C-02)
├── scheduler/
│   └── jobs.py        # Tareas programadas (skeleton)
└── services/          # Lógica de negocio (C-03)
```
