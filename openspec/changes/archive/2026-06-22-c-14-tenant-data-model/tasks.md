## 1. Schema — Modelos SQLAlchemy

- [ ] 1.1 Modificar `models/paciente.py`: agregar `profesional_id` (FK NOT NULL), relationship a `Profesional`, y `UniqueConstraint("profesional_id", "dni")` en `__table_args__`. Quitar `unique=True` de `dni`.
- [ ] 1.2 Modificar `models/profesional.py`: agregar `email`, `password_hash`, `api_key`, `is_active`, `google_refresh_token`, `telegram_bot_token`, `telegram_secret_token` con tipos y constraints correctos.
- [ ] 1.3 Modificar `models/lista_de_espera.py`: agregar `profesional_id` (FK NOT NULL), relationship a `Profesional`, e `Index("ix_lista_de_espera_profesional_paciente", "profesional_id", "paciente_id")` en `__table_args__`.
- [ ] 1.4 Verificar que `models/reserva_temporal.py` NO requiere cambios (scoping implícito vía `turno_id`).
- [ ] 1.5 Ejecutar `alembic revision --autogenerate -m "add profesional_id and auth columns"` y revisar el script generado.
- [ ] 1.6 Corregir manualmente el migration script si es necesario (nombres de constraints, orden de operaciones, `ondelete` explícito).
- [ ] 1.7 Validar que `Base.metadata.create_all()` refleja el schema esperado ejecutando un smoke test de modelos.

## 2. Configuración y Seed

- [ ] 2.1 Modificar `app/config.py`: agregar `secret_key: str` y `algorithm: str = "HS256"` a `Settings`.
- [ ] 2.2 Actualizar `.env.example` con `SECRET_KEY=` y `ALGORITHM=HS256`.
- [ ] 2.3 Modificar `app/seed.py`: poblar `email="admin@local.dev"`, `password_hash` con bcrypt dummy (ej. de un password conocido como "changeme"), e `is_active=True` en el seed de `Profesional`.
- [ ] 2.4 Verificar que el seed es idempotente: al reiniciar la app no se duplica el profesional.

## 3. Tests — Fixture y Cobertura

- [ ] 3.1 Modificar `tests/conftest.py`: agregar fixture `profesional` que crea y persiste un `Profesional` completo con todos los campos obligatorios y nuevos columnas.
- [ ] 3.2 Escribir test de modelo para `Paciente`: verificar que `profesional_id` es obligatorio y que `UNIQUE(profesional_id, dni)` funciona.
- [ ] 3.3 Escribir test de modelo para `ListaDeEspera`: verificar que `profesional_id` es obligatorio y que el índice existe en el schema.
- [ ] 3.4 Escribir test de modelo para `Profesional`: verificar que `email` y `api_key` son únicos, y que las nuevas columnas aceptan valores nulos salvo `is_active`.
- [ ] 3.5 Escribir test de integración para la migración Alembic: aplicar upgrade y downgrade en una DB de test vacía y verificar que no falla.
- [ ] 3.6 Verificar que `pytest backend/tests/` ejecuta sin errores de schema (se esperan fallos en tests de routers/services no actualizados; esos se ignoran en este change).

## 4. Validación y Documentación

- [ ] 4.1 Ejecutar `openspec validate` y confirmar que pasa sin errores.
- [ ] 4.2 Revisar que todos los archivos mencionados en `design.md` fueron actualizados.
- [ ] 4.3 Actualizar `CHANGES.md` (si aplica) para reflejar que C-14 está en progreso.
