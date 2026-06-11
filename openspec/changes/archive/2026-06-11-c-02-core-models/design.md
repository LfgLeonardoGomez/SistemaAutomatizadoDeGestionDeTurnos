## Context

Tras `C-01 foundation-setup`, el backend tiene FastAPI, Alembic, PostgreSQL y un health check, pero **no hay ningún modelo de dominio**. Este change define las 5 entidades base del sistema: `Paciente`, `Profesional`, `Turno`, `ReservaTemporal` y `ListaDeEspera`. Es la base de datos sobre la cual se construyen todos los servicios, endpoints, el bot de Telegram y la integración con Google Calendar. Los constraints, índices y relaciones deben estar definidos desde el inicio para evitar migraciones correctivas costosas.

## Goals / Non-Goals

**Goals:**
- Definir los 5 modelos SQLAlchemy 2.0 con tipado estricto, relaciones bidireccionales y constraints de base de datos.
- Generar la migración Alembic 001 que cree todas las tablas, índices y constraints de forma atómica.
- Proveer un seed idempotente de `Profesional` con valores por defecto (horario 08:00–18:00, duración 30 min, todos los días laborables).
- Escribir tests de integridad que validen constraints, integridad referencial y comportamiento del seed.
- Respetar las reglas de negocio del dominio: `CHECK(hora_fin > hora_inicio)`, `UNIQUE(dni)`, máquina de estados de `Turno`, y expiración de `ReservaTemporal`.

**Non-Goals:**
- No se implementan endpoints REST ni servicios de negocio (quedan para C-03 a C-12).
- No se integra Google Calendar ni Telegram en este change.
- No se implementa la lógica de liberación automática de reservas temporales (solo el modelo; el job queda para C-06).
- No se implementa el cálculo de disponibilidad de slots (queda para C-03).

## Decisions

- **SQLAlchemy 2.0 con estilo declarativo moderno**: Usamos `DeclarativeBase`, `Mapped[]`, `mapped_column()` y tipado estricto para aprovechar el auto-completado y la validación de mypy. Esto es el estándar de FastAPI + SQLAlchemy 2.0.
- **Alembic para migraciones**: La migración 001 es la creación de todas las tablas. Dado que la base está vacía, es una migración forward-only sin rollback complejo necesario (el rollback es `downgrade` con `drop_table`).
- **Enum de PostgreSQL para `Turno.estado`**: Usamos `Enum` nativo de PostgreSQL para los estados (`DISPONIBLE`, `RESERVADO_TEMPORAL`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`). Esto garantiza integridad a nivel de base de datos y es más eficiente que `VARCHAR` con `CHECK` manual.
- **Índices explícitos con SQLAlchemy**: Definimos `Index` en el modelo para `(fecha, hora_inicio)`, `(estado)`, `(paciente_id, estado)` en `Turno`, y `Index(expiracion)` en `ReservaTemporal`. Esto asegura que los índices se reflejen en la migración automáticamente.
- **Seed idempotente vía `pg_upsert` o `INSERT ... ON CONFLICT DO NOTHING`**: Como no hay un endpoint de configuración todavía, el seed se ejecuta como un script de Alembic o como un comando de inicio de la aplicación. Dado que el `Profesional` es único en v1 (solo hay uno), el seed es idempotente: si ya existe, no hace nada.
- **Tests con `pytest` + base de datos en memoria (SQLite) o PostgreSQL de test**: Preferimos SQLite en memoria para velocidad en tests unitarios, pero para tests de integridad de constraints (como `CHECK` y `UNIQUE` en PostgreSQL) usamos PostgreSQL real vía `docker-compose` o testcontainers. Dado el stack actual, optamos por SQLite en memoria para tests básicos de modelo y un test de integración con PostgreSQL local para constraints que SQLite no soporta (como `CHECK` en TIME nativo, aunque SQLAlchemy puede emularlo). Sin embargo, dado que SQLite es suficiente para validar integridad referencial y lógica de ORM, usamos SQLite para la mayoría, y dejamos un test explícito para PostgreSQL en el CI.
- **Relación `Turno` 1:1 `ReservaTemporal` con `unique=True` en la FK**: `ReservaTemporal.turno_id` es UNIQUE, garantizando la relación 1:1 a nivel de base de datos. Además, usamos `cascade="all, delete-orphan"` en la relación ORM para mantener consistencia.
- **Turno.hora_fin calculada en la app, no en DB**: No usamos un trigger de PostgreSQL para calcular `hora_fin`; lo calculamos en el código de creación del turno (aunque en este change solo se define la columna; el cálculo real ocurre en C-03/C-06). Esto es una decisión de pragmatismo: evitamos lógica en triggers para mantenerla centralizada en Python.
- **No `tenant_id` en v1**: Aunque la skill `saas-multi-tenant` recomienda `tenant_id` desde v1, el dominio de esta tesis es un solo profesional (no multi-tenant). Se omite para evitar over-engineering, pero se documenta como deuda técnica futura si el sistema escala.

## Risks / Trade-offs

- **[Riesgo] Cambios en el modelo requieren migraciones adicionales**: Si el dominio evoluciona (por ejemplo, agregar `notas` a `Turno`), se necesitará una migración Alembic posterior. **Mitigación**: El diseño actual es completo según la KB y el ERD; no anticipamos cambios mayores.
- **[Riesgo] SQLite no soporta ENUM nativo**: Los tests con SQLite usarán `VARCHAR` para el enum. **Mitigación**: Los tests de integración con PostgreSQL real validarán el ENUM nativo. Dado que SQLAlchemy abstracta el tipo, esto es aceptable.
- **[Riesgo] Seed del Profesional no es configurable vía API**: El seed está hardcodeado en el script de inicio. **Mitigación**: C-03 proveerá endpoints de configuración que permitirán editar estos valores posteriormente. El seed solo es un valor inicial razonable.
- **[Riesgo] Relación `Turno` 1:1 `ReservaTemporal` sin ON DELETE CASCADE explícito en SQLite**: SQLAlchemy maneja el cascade en la sesión, pero la DB nativa debería tener `ON DELETE CASCADE` para integridad referencial total. **Mitigación**: Alembic generará `ForeignKey(..., ondelete="CASCADE")` en la migración, y lo validamos en el test de PostgreSQL.
- **[Trade-off] No trigger de DB para `hora_fin`**: Calculamos en la app. Esto permite testing más fácil pero requiere que todos los creadores de turnos respeten la fórmula. **Mitigación**: C-03 y C-06 encapsularán la creación de turnos en un servicio único, evitando que se creen turnos directamente desde los endpoints sin calcular `hora_fin`.

## Migration Plan

- **Deploy**: Correr `alembic upgrade head` (o `docker-compose exec backend alembic upgrade head`) para aplicar la migración 001. El seed se ejecuta automáticamente al iniciar la aplicación si no hay registros en `Profesional`.
- **Rollback**: `alembic downgrade -1` elimina todas las tablas. Esto es destructivo y solo para desarrollo local.
- **Verificación**: Post-deploy, ejecutar `pytest backend/tests/test_models.py` para confirmar que los modelos, constraints y seed funcionan correctamente.

## Open Questions

- ¿El seed de `Profesional` se ejecuta en la migración Alembic o como un evento de inicio de FastAPI? **Respuesta**: Como un evento de inicio de FastAPI (`@app.on_event("startup")`) para permitir re-ejecución idempotente sin tocar migraciones.
- ¿Se usa `asyncpg` + SQLAlchemy async para tests? **Respuesta**: Sí, donde sea posible, manteniendo consistencia con el stack async. Pero para SQLite usamos `sqlite+aiosqlite`.
