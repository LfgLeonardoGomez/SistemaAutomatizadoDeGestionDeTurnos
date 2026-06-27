# test-postgresql-infrastructure Specification (delta)

## Purpose
TBD - updated by archiving change fix-test-fixtures-email. Update Purpose after archive.

This is a **delta spec** adding new requirements to the existing `test-postgresql-infrastructure` capability. See `openspec/specs/test-postgresql-infrastructure/spec.md` for the full base spec.

## ADDED Requirements

### Requirement: Factory de `Profesional` en conftest con defaults válidos
El sistema de tests SHALL proveer un factory `make_profesional(**overrides) -> Profesional` en `backend/tests/conftest.py` que genere instancias del modelo `Profesional` con defaults válidos para todos los campos requeridos por la schema de PostgreSQL (incluido `email: NOT NULL UNIQUE` introducido en C-14).

#### Scenario: Default email es único por invocación
- **WHEN** un test invoca `make_profesional()` dos veces en la misma sesión
- **THEN** las dos instancias resultantes tienen emails distintos (generados vía `uuid.uuid4().hex[:8]`)
- **AND** ambos emails pueden coexistir en la tabla `profesional` sin violar la constraint `UNIQUE`

#### Scenario: Instancia creada por el factory es insertable en PostgreSQL
- **GIVEN** un test invoca `make_profesional()` sin override
- **WHEN** la instancia se persiste con `db_session.add(p)` + `await db_session.commit()`
- **THEN** el commit NO falla con `null value in column "email" violates not-null constraint`
- **AND** la fila es visible con un `SELECT` posterior

#### Scenario: Helper `make_profesional_persisted` retorna instancia con `id`
- **GIVEN** un test invoca `await make_profesional_persisted(db_session)` 
- **WHEN** se lee el campo `id` de la instancia retornada
- **THEN** `id` es un entero positivo asignado por la secuencia de PostgreSQL

### Requirement: Aplicación del factory en archivos de test existentes
Los archivos de test que crean instancias de `Profesional` SHALL usar `make_profesional(**overrides)` o `make_profesional_persisted(db_session, **overrides)` en lugar de instanciar `Profesional(...)` directamente sin setear `email`, ya que SQLite no enforced consistentemente el `NOT NULL` constraint y esos tests fallan en PostgreSQL.

#### Scenario: Barrido completo de archivos de test
- **WHEN** se aplica el factory a los 22 archivos de test que contienen `Profesional(...)`
- **THEN** ningún archivo contiene una llamada a `Profesional(...)` sin setear `email`
- **AND** la suite completa de tests corre contra PostgreSQL sin errores `null value in column "email" violates not-null constraint` en la tabla `profesional`

#### Scenario: Excepción para el fixture `profesional` preexistente
- **WHEN** se aplica el factory al resto de la suite
- **THEN** el fixture `profesional` en `conftest.py` (que usa `email="test@local.dev"`, `password="changeme"`) se conserva sin cambios
- **AND** los tests de autenticación que dependen de estos valores específicos siguen pasando
