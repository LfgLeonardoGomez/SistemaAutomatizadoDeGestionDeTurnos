## Context

v1.0 del sistema Tesis-N8N-turnos está completamente implementado y opera como single-tenant por instancia. No existe autenticación de profesionales ni aislamiento de datos: cualquier paciente creado es global, y la lista de espera no tiene scoping por profesional. El modelo `Turno` ya tiene `profesional_id`, pero `Paciente` y `ListaDeEspera` carecen de él.

Este change es el **primer paso** de la migración a multi-tenancy en v2.0. Su única responsabilidad es modificar el schema de base de datos para que, en changes posteriores (C-15 auth, C-16 Google Calendar per-professional, C-17 bot per-professional), cada tabla tenant-scoped pueda filtrarse por `profesional_id`.

## Goals / Non-Goals

**Goals:**
1. Aislar datos de `Paciente` por profesional mediante `profesional_id` NOT NULL.
2. Aislar datos de `ListaDeEspera` por profesional mediante `profesional_id` NOT NULL.
3. Preparar `Profesional` para autenticación e integraciones futuras (email, password_hash, api_key, tokens).
4. Proveer migración Alembic reproducible y fixture de test reutilizable.
5. Establecer `SECRET_KEY` y `ALGORITHM` en Settings para JWT (C-15).

**Non-Goals:**
- No se modifica lógica de negocio de routers ni services (eso es C-16).
- No se implementa autenticación ni JWT (C-15).
- No se actualizan todos los tests rotos por `profesional_id` obligatorio (se hace en C-16).
- No se agrega `tenant_id` como concepto separado; `profesional_id` ES el tenant en v2.0.

## Decisions

### 1. Paciente: `profesional_id` NOT NULL + `UNIQUE(profesional_id, dni)`
- **Rationale**: En un modelo SaaS multi-profesional, dos profesionales independientes pueden tener pacientes con el mismo DNI (ej. dos dentistas en ciudades distintas). El DNI solo debe ser único dentro del scope del profesional.
- **Alternatives considered**: Mantener `UNIQUE(dni)` global y agregar `profesional_id` nullable. Rechazado: rompe el modelo SaaS y deja datos huérfanos.
- **SQLAlchemy change**:
  ```python
  profesional_id: Mapped[int] = mapped_column(
      ForeignKey("profesional.id", ondelete="CASCADE"), nullable=False
  )
  profesional: Mapped["Profesional"] = relationship("Profesional", lazy="selectin")
  ```
  Reemplazar `unique=True` en `dni` por `UniqueConstraint("profesional_id", "dni", name="uq_paciente_profesional_dni")` en `__table_args__`.

### 2. ListaDeEspera: `profesional_id` NOT NULL + índice compuesto
- **Rationale**: La lista de espera es una cola por profesional. Las queries futuras serán del tipo "dame los primeros N pacientes en espera del profesional X". Un índice en `(profesional_id, paciente_id)` optimiza joins y búsquedas.
- **SQLAlchemy change**:
  ```python
  profesional_id: Mapped[int] = mapped_column(
      ForeignKey("profesional.id", ondelete="CASCADE"), nullable=False
  )
  profesional: Mapped["Profesional"] = relationship("Profesional", lazy="selectin")
  ```
  Agregar `Index("ix_lista_de_espera_profesional_paciente", "profesional_id", "paciente_id")` en `__table_args__`.

### 3. Profesional: columnas de auth e integración
- **Rationale**: C-15 implementará login con JWT; C-16 sincronizará Google Calendar por profesional (no global); C-17 enrutará webhooks de Telegram por bot token. Estas columnas deben existir en el schema antes de que esos changes comiencen.
- **Columnas exactas**:
  ```python
  email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
  password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
  api_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
  is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
  google_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  telegram_bot_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
  telegram_secret_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
  ```
- **Nota**: `email` es nullable inicialmente porque el seed existente no tiene email. C-15 hará un data migration para popular emails y luego aplicará `nullable=False`.

### 4. ReservaTemporal: scoping implícito, sin cambios
- **Rationale**: `ReservaTemporal` tiene `turno_id` → `Turno` ya tiene `profesional_id`. No es necesario agregar `profesional_id` directamente; cualquier query que necesite scoping debe hacer `JOIN turno ON reserva_temporal.turno_id = turno.id WHERE turno.profesional_id = X`. Esto evita redundancia y mantiene la integridad referencial simple.

### 5. Alembic: autogenerate + manual review
- **Rationale**: Las columnas nuevas y los constraints son cambios estructurales estándar. `alembic revision --autogenerate` capturará la mayoría, pero:
  - El cambio de `UNIQUE(dni)` a `UNIQUE(profesional_id, dni)` requiere verificación manual (Alembic a veces genera `DROP CONSTRAINT` + `ADD CONSTRAINT`, a veces no).
  - Los índices nuevos deben verificarse.
  - Las foreign keys deben tener nombres explícitos para evitar conflictos de generación.
- **Estrategia**: autogenerate → revisar diff → ajustar manualmente si es necesario → ejecutar en test DB para validar.

### 6. Fixture `profesional` en `conftest.py`
- **Rationale**: Todos los tests que crean `Paciente` o `ListaDeEspera` ahora requieren un `Profesional` existente. Un fixture reutilizable evita duplicación.
- **Diseño**:
  ```python
  @pytest_asyncio.fixture
  async def profesional(db_session: AsyncSession) -> Profesional:
      profesional = Profesional(
          nombre="Dr. Test",
          especialidad="Odontología general",
          duracion_turno=30,
          horario_inicio="08:00",
          horario_fin="18:00",
          dias_atencion=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
          email="test@local.dev",
          password_hash="$2b$12$...",  # dummy bcrypt hash
      )
      db_session.add(profesional)
      await db_session.commit()
      await db_session.refresh(profesional)
      return profesional
  ```
- **Impact**: Los tests existentes que crean `Paciente` o `ListaDeEspera` fallarán hasta C-16. Esto es aceptado intencionalmente para mantener el foco del change en schema + migración.

### 7. Config: `SECRET_KEY` y `ALGORITHM`
- **Rationale**: C-15 necesitará firmar JWT. El config debe existir en C-14 para que el change C-15 no toque config.
- **Valores por defecto**: `SECRET_KEY` obligatorio (sin default, raise en startup si falta en prod), `ALGORITHM="HS256"` con default seguro.

## Risks / Trade-offs

- **[Risk] Tests existentes rotos** → **Mitigation**: Aceptado como deuda técnica controlada. C-16 actualizará todos los tests. Se documenta explícitamente en el change.
- **[Risk] Migración en instancias con datos** → **Mitigation**: No aplica (tesis sin producción real). De todas formas la migración es escrita correctamente con `ALTER TABLE ADD COLUMN` + `UPDATE` si fuera necesario. En este caso, como no hay datos, es un simple schema change.
- **[Risk] Índices adicionales ralentizan escrituras** → **Mitigation**: Los índices son pequeños (INTEGER + INTEGER / INTEGER + VARCHAR). El overhead es negligible para el volumen esperado (< 10k registros/profesional).
- **[Trade-off] `email` nullable inicialmente** → Permite aplicar el change sin necesidad de data migration compleja en C-14, pero requiere que C-15 haga una migración adicional para hacerlo NOT NULL después de poblar datos.

## Migration Plan

1. **Preparación**: Asegurar que `alembic.ini` apunta a la DB correcta.
2. **Autogenerate**:
   ```bash
   alembic revision --autogenerate -m "add profesional_id and auth columns"
   ```
3. **Review manual**: Verificar que el migration script incluye:
   - `ALTER TABLE paciente ADD COLUMN profesional_id INTEGER NOT NULL` (con FK)
   - `DROP CONSTRAINT uq_paciente_dni` + `ADD CONSTRAINT uq_paciente_profesional_dni UNIQUE(profesional_id, dni)`
   - `ALTER TABLE lista_de_espera ADD COLUMN profesional_id INTEGER NOT NULL` (con FK)
   - `CREATE INDEX ix_lista_de_espera_profesional_paciente ON lista_de_espera(profesional_id, paciente_id)`
   - `ALTER TABLE profesional ADD COLUMN email VARCHAR(255) UNIQUE`, `password_hash`, `api_key`, `is_active`, `google_refresh_token`, `telegram_bot_token`, `telegram_secret_token`
4. **Ejecución en test**: `pytest backend/tests/` (esperar fallos en tests no actualizados, pero la migración debe aplicarse sin errores de schema).
5. **Rollback**: `alembic downgrade -1`.

## Open Questions

1. ¿Debe `Paciente` tener `ondelete="CASCADE"` en la FK a `Profesional`? **Decisión**: Sí, porque si se elimina un profesional (administrativo), sus pacientes deben limpiarse. Esto es consistente con el modelo SaaS donde el profesional es el tenant.
2. ¿Debe `ListaDeEspera` también tener `ondelete="CASCADE"` en la FK a `Profesional`? **Decisión**: Sí, mismo razonamiento.
3. ¿Es necesario agregar `profesional_id` a `ReservaTemporal` para performance de queries? **Decisión**: No por ahora. Si en C-16 aparece un bottleneck en queries de "reservas temporales del profesional X", se evaluará denormalizar. Hoy el JOIN es suficiente.

## Files to Update

| File | Change |
|------|--------|
| `backend/app/models/paciente.py` | Add `profesional_id`, relationship, `__table_args__` with `UniqueConstraint` |
| `backend/app/models/profesional.py` | Add auth/integration columns |
| `backend/app/models/lista_de_espera.py` | Add `profesional_id`, relationship, `__table_args__` with `Index` |
| `backend/app/config.py` | Add `secret_key`, `algorithm` |
| `backend/app/seed.py` | Populate new `Profesional` columns (email, password_hash) |
| `backend/alembic/versions/<new>.py` | Migration script |
| `backend/tests/conftest.py` | Add `profesional` fixture |
| `.env.example` | Add `SECRET_KEY` and `ALGORITHM` |

## Backward Compatibility

No hay compatibilidad hacia atrás intencional. Este es un **breaking change** de schema. Todos los inserts a `Paciente` y `ListaDeEspera` que no incluyan `profesional_id` fallarán. Como no hay datos de producción y el sistema está en etapa de tesis, se opta por un enfoque directo en lugar de mantener columnas nullable con migración de datos compleja.
