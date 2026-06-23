## Why

v1.0 del sistema es single-tenant por instancia: un único profesional, sin autenticación, sin aislamiento de datos entre profesionales. Para escalar a un modelo SaaS multi-tenant en v2.0, donde cada profesional independiente opera sobre su propio conjunto de pacientes, turnos y lista de espera, el primer paso indispensable es preparar el modelo de datos. Sin `profesional_id` en las tablas que hoy carecen de él, no es posible garantizar aislamiento ni implementar autenticación por profesional en C-15/C-16. Este change es el cimiento de toda la migración a multi-tenancy.

## What Changes

- **BREAKING**: Agregar `profesional_id` (FK → Profesional, NOT NULL) a `Paciente` y cambiar el constraint `UNIQUE(dni)` a `UNIQUE(profesional_id, dni)`.
- **BREAKING**: Agregar `profesional_id` (FK → Profesional, NOT NULL) a `ListaDeEspera`, con índice en `(profesional_id, paciente_id)`.
- Agregar columnas de autenticación e integración a `Profesional`: `email`, `password_hash`, `api_key`, `is_active`, `google_refresh_token`, `telegram_bot_token`, `telegram_secret_token`.
- Verificar que `ReservaTemporal` ya está correctamente scopiado indirectamente vía `turno_id` → `Turno.profesional_id`.
- Crear migración Alembic que aplica todos los cambios de schema.
- Actualizar `seed.py` para poblar el profesional por defecto con las nuevas columnas (email dummy + bcrypt hash).
- Agregar fixture `profesional` en `conftest.py` para desbloquear tests futuros.
- Agregar `SECRET_KEY` y `ALGORITHM` a `config.py` / Pydantic Settings (requerido por C-15).

## Capabilities

### New Capabilities
- `tenant-data-model`: Extensiones del schema de base de datos para soportar aislamiento por profesional (tenant) y autenticación futura.

### Modified Capabilities
- `core-patient-model`: Se agrega `profesional_id` obligatorio y se modifica la unicidad de DNI a scope por profesional (`UNIQUE(profesional_id, dni)`). Esto rompe el contrato actual de creación de pacientes sin vinculación profesional.
- `core-lista-espera-model`: Se agrega `profesional_id` obligatorio. Cualquier registro o consulta de lista de espera ahora requiere scoping por profesional.
- `core-professional-model`: Se agregan columnas de identidad y autenticación (`email`, `password_hash`, `api_key`, etc.) sin modificar el comportamiento funcional actual, preparando el terreno para C-15/C-16.

## Impact

- **Models**: `models/paciente.py`, `models/profesional.py`, `models/lista_de_espera.py`.
- **Migrations**: nueva migración Alembic en `backend/alembic/versions/`.
- **Seed**: `backend/app/seed.py` debe actualizarse para evitar fallo de inserción por columnas nuevas.
- **Config**: `backend/app/config.py` agrega `SECRET_KEY` y `ALGORITHM`.
- **Tests**: `backend/tests/conftest.py` requiere fixture `profesional`; tests existentes de `Paciente` y `ListaDeEspera` fallarán hasta que se actualicen en C-16 (se acepta intencionalmente para mantener el foco del change).
- **Routers/Services**: no se modifican en este change, pero quedan en deuda técnica: C-16 debe actualizarlos para respetar `profesional_id`.
