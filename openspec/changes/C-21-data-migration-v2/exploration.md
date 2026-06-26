# Exploration: C-21 data-migration-v2

## Status
`[EXPLORED]` — Ready for proposal phase.

## Executive Summary

C-21 targets a **data migration script** for v1.0 → v2.0 installations. However, the current codebase reveals that **the schema is already fully migrated**: Alembic chain head `b2d4e6f8a0c2` already includes `profesional_id` columns in all tables, auth/integration columns in `Profesional`, the `super_admin` table, and the `email NOT NULL` constraint. The services already read `telegram_bot_token` and `google_refresh_token` **from the `Profesional` model** (not from env vars).

This fundamentally redefines C-21's scope from "migrate schema" to **"migrate data values"**: existing records need `profesional_id` backfill validation, and env-var tokens need copying into the DB for the default/legacy professional.

**Critical finding**: `GOOGLE_CALENDAR_CREDENTIALS` (service account JSON) is architecturally incompatible with the new OAuth2-per-professional model (`google_refresh_token`). This cannot be directly migrated — the script should warn and document manual steps rather than attempt an impossible conversion.

---

## Key Findings

### Finding 1: Schema is already on v2.0 — no schema migration needed

- Alembic chain (7 migrations) is complete: head `b2d4e6f8a0c2` (`profesional_email_not_null`).
  - `6c8e6fefc46f` — Core tables (incl. `turno.profesional_id` from day one)
  - `f3c8a2b91c4e` — Added `profesional_id` to `paciente` + `lista_de_espera`, auth columns, integration tokens
  - `a1b2c3d4e5f6` — `super_admin` table
  - `b2d4e6f8a0c2` — `profesional.email` NOT NULL

- `profesional` model already has all v2.0 columns: `email`, `password_hash`, `api_key`, `is_active`, `google_refresh_token`, `telegram_bot_token`, `telegram_secret_token` (see `backend/app/models/profesional.py:24-44`).

- `paciente` (line 25-27), `turno` (line 30-32), `lista_de_espera` (line 30-32) all have `profesional_id` FK columns.

- **Implication**: No Alembic revision is needed for C-21. The migration is purely a **data operation script**.

### Finding 2: `profesional_id=1` placeholder risk

- Migration `f3c8a2b91c4e` used `server_default=sa.text('1')` for `profesional_id` in `paciente` and `lista_de_espera`, then removed the server default.
- Existing (pre-migration) records have `profesional_id=1` as a hardcoded value.
- If `Profesional` id=1 does **not** exist (e.g., seed was modified, DB was manipulated, or seed created a record with a different id), FK constraints fail on reads/writes.
- The existing `seed.py` creates "Dr. Por Defecto" with auto-increment id (likely 1 on fresh DB, but not guaranteed after manual deletions or restores).

### Finding 3: Services already read tokens from DB, not env

- `telegram_service.py:683-686` — reads `profesional.telegram_bot_token`
- `calendar_service.py:33-41` — reads `profesional.google_refresh_token`
- `scheduler/jobs.py:147` — reads `profesional.telegram_bot_token`
- `lista_espera_service.py:131` — reads `profesional.telegram_bot_token`
- `Settings` (config.py:13) still declares `telegram_bot_token: str`, but **no service reads it for per-professional operations**.

- **Implication**: The env var `TELEGRAM_BOT_TOKEN` is dead code for runtime but useful for migration seeding. `GOOGLE_CALENDAR_CREDENTIALS` is completely replaced by `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` (global) + per-professional `google_refresh_token`.

### Finding 4: `GOOGLE_CALENDAR_CREDENTIALS` → `google_refresh_token` is not migratable

- Old model: Single Google service account (JSON in `GOOGLE_CALENDAR_CREDENTIALS`) → shared calendar.
- New model: OAuth2 per-professional with `google_refresh_token` + global `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`.
- These are architecturally different: a service account credential cannot be "converted" to a user OAuth2 refresh token.
- **Per BREAKING_CHANGES.md §3**: "Cada profesional debe completar el flujo OAuth2 para obtener su refresh_token."
- **Implication**: This migration step is **INFORMATIONAL ONLY** — the script should warn and point to docs, not attempt to migrate.

### Finding 5: Existing seed creates "Dr. Por Defecto" on startup

- `seed.py:13-30` creates a Profesional with `nombre="Dr. Por Defecto"`, `email="admin@local.dev"` if `count(Profesional) == 0`.
- Runs on every startup in `main.py:34`.
- After C-20, the onboarding flow via `POST /admin/profesionales` is the preferred path. The seed is legacy.
- **Implication**: The migration script should NOT rely on the seed having run; it should create a default professional independently if needed.

### Finding 6: Tests still set env vars for Settings but don't use them for per-professional operations

- Every test conftest.py and integration test `monkeypatch.setenv("TELEGRAM_BOT_TOKEN", ...)` and `GOOGLE_CALENDAR_CREDENTIALS`.
- These env vars satisfy `Settings()` validation, but actual per-professional token values come from the `Profesional` model (seeded in the `profesional` fixture).
- The existing `test_migration.py` only validates Alembic revision chain and file structure — it does NOT test data migration logic.

### Finding 7: No existing `scripts/` directory

- No `backend/scripts/` directory exists. The migration script will need a new location (recommended: `backend/scripts/migrate_v1_to_v2.py`).
- No Makefile or CLI entry point for standalone scripts.

---

## Affected Areas

| File | Role |
|------|------|
| `backend/scripts/migrate_v1_to_v2.py` | **NEW** — standalone migration script (to be created) |
| `backend/app/models/profesional.py` | Defines the target columns for env var migration |
| `backend/app/models/paciente.py` | Records needing `profesional_id` validation |
| `backend/app/models/turno.py` | Records needing `profesional_id` validation |
| `backend/app/models/lista_de_espera.py` | Records needing `profesional_id` validation |
| `backend/app/seed.py` | Reference for default professional creation logic |
| `backend/app/config.py` | Source of env var reading logic (reference) |
| `backend/tests/test_migration_data.py` | **NEW** — tests for the data migration script |
| `backend/.env.example` | Needs update to reflect deprecation of migrated env vars |
| `openspec/changes/archive/*/BREAKING_CHANGES.md` | Source of truth for the migration contract |

---

## Approaches

### Approach 1: Standalone CLI script (recommended)

A dedicated Python script `scripts/migrate_v1_to_v2.py` callable as:
```
python scripts/migrate_v1_to_v2.py
```

**Structure**:
1. Load `Settings()` to read env vars
2. Open async DB session
3. **Step 1**: Ensure default Profesional exists (if none, create one with seed defaults)
4. **Step 2**: Verify `profesional_id=1` exists for all placeholder records; if not, reassign to the default professional
5. **Step 3**: Copy `TELEGRAM_BOT_TOKEN` → `profesional.telegram_bot_token` for the default professional (if DB field is empty)
6. **Step 4**: Warn about `GOOGLE_CALENDAR_CREDENTIALS` → manual OAuth2 setup required; log guidance
7. **Step 5**: Commit if all steps succeed, rollback on any error
8. Idempotency: track completion via a sentinel (e.g., `MigrationLog` table or a flag in `settings`)

**Pros**:
- Clear responsibility separation from Alembic
- Can print human-readable progress and warnings
- Testable with in-memory SQLite (like existing tests)
- Full transactional control

**Cons**:
- Need to solve async setup (compatible with SQLAlchemy async)
- No automatic execution — operator must remember to run
- Sentinel/logic for "run once" needs design (DB flag vs file marker)

**Effort**: Medium (40-60 lines of logic + tests)

### Approach 2: Alembic migration (data + schema)

Extend an Alembic revision with `data_upgrade()` / `data_downgrade()` operations.

**Pros**:
- Runs automatically with `alembic upgrade head`
- No separate deployment step
- Rollback via `alembic downgrade`

**Cons**:
- Alembic migrations should be **schema**, not arbitrary data mutations (anti-pattern)
- Alembic downgrade is awkward for destructive data ops
- Harder to print user-facing warnings (no stdout in migration context)
- Async session setup in Alembic is non-trivial (Alembic uses sync engine)
- Tests require actual PostgreSQL (SQLite dialect differences)

**Effort**: Medium but higher risk (anti-pattern)

### Approach 3: Inline in `seed.py` / `lifespan`

Add migration logic to the existing startup seed function.

**Pros**:
- Runs automatically on every startup (idempotent by design)
- No new files or deployment steps

**Cons**:
- Mixing migration with seed is conceptually wrong — seed creates initial state, migration transforms existing state
- Error in migration blocks app startup
- Hard to test in isolation
- No explicit "I ran the migration" signal to the operator
- `GOOGLE_CALENDAR_CREDENTIALS` warning would be buried in startup logs

**Effort**: Low but poor separation of concerns

---

## Recommendation

**Approach 1** (standalone CLI script) is the right call for these reasons:

1. C-22 explicitly depends on C-21 being complete — a standalone script is a clean boundary.
2. The script can print interactive warnings about the non-migratable `GOOGLE_CALENDAR_CREDENTIALS`.
3. Tests can inject a test DB + mock env vars cleanly.
4. The "run once" requirement is naturally enforced by the script itself (check-and-exit).
5. After C-21, C-22 can safely remove `TELEGRAM_BOT_TOKEN` and `GOOGLE_CALENDAR_CREDENTIALS` from Settings.

**Rollback strategy**: Wrap all DB mutations in a single transaction. On error, rollback and exit with code 1. On success, commit and print a clear summary. No partial commits possible.

**Idempotency**: Check before each step:
- "default Profesional exists?" → skip creation if yes
- "records with invalid `profesional_id`?" → skip if none
- "`telegram_bot_token` already populated?" → skip/confirm before overwrite

**Sentinel**: Optional `create table if not exists migration_log` to record completion timestamp. Skip silently if record exists.

---

## Open Questions (for Proposal Phase)

1. **Q1**: The `GOOGLE_CALENDAR_CREDENTIALS` migration is technically impossible (service_account JSON → OAuth2 refresh_token). Should the script:
   - (a) Simply warn and skip (informational only)?
   - (b) Attempt to parse the JSON and extract `client_id`/`client_secret` for the global config?
   - (c) Do nothing and let C-22 remove the env var with a deprecation warning?

2. **Q2**: Sentinel strategy — preferred approach for "run once":
   - (a) Create a `migration_log` table with timestamp + checksum?
   - (b) Check if a Profesional with `telegram_bot_token` already populated exists (heuristic)?
   - (c) File-based marker (`/var/run/migrated_v2.flag`)?

3. **Q3**: Should the script also migrate the `super_admin` seed from env vars (C-19 seed) into the DB, or is that already handled by the startup seed?

4. **Q4**: The existing `seed_profesional()` in `main.py` creates "Dr. Por Defecto" with `email="admin@local.dev"`. Should the migration script:
   - (a) Call the same seed function (risk of tight coupling)?
   - (b) Have its own inline default-creation logic?
   - (c) Error out if no Profesional exists and let the operator create one via `POST /admin/profesionales`?

5. **Q5**: Test DB approach — should the migration script tests use:
   - (a) SQLite in-memory (consistency with existing conftest, but no FK enforcement for some cases)?
   - (b) PostgreSQL via testcontainers (more realistic, but slower and needs Docker)?

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Blocking**: `profesional_id=1` doesn't exist, FK constraints fail on script start | Medium | High | Script checks existence first, creates default Profesional if needed |
| **Blocking**: `GOOGLE_CALENDAR_CREDENTIALS` cannot be migrated; user expects magic | High | Medium | Clear warning in script output + docs; BREAKING_CHANGES.md already documents OAuth2 steps |
| **Data loss**: Rollback isn't tested; partial migration corrupts data | Medium | Critical | Wrap in single transaction; all-or-nothing; test rollback explicitly |
| **False idempotency**: Script runs twice and overwrites manual token setup | Medium | Medium | Skip if `telegram_bot_token` is already populated; add `--force` flag for override |
| **Test gap**: Migration tests use SQLite but production is PostgreSQL; subtle differences in constraint enforcement | Medium | Medium | Use SQLite for unit tests (matching existing pattern); add one Pg-specific integration test if testcontainers available |
| **Async complexity**: Standalone async script has different session lifecycle than FastAPI lifespan | Low | Medium | Use `asyncio.run()` wrapper with explicit engine create/dispose |
| **Env var not set**: `TELEGRAM_BOT_TOKEN` is empty during migration | Medium | Low | Graceful skip: "env var not set, skipping telegram_bot_token migration" |

---

## Skill Resolution

| Skill Path | Resolved | Notes |
|-----------|----------|-------|
| `/home/zen/.config/opencode/skills/work-unit-commits/SKILL.md` | ✅ Loaded | Applied for commit planning: one commit per migration step (model/sentinel → logic → tests) |
| `/home/zen/.claude/skills/chained-pr/SKILL.md` | ✅ Loaded | Estimated <200 lines for script + <200 for tests = single PR (<400) unless test data setup is extensive. Chain not needed. |

---

## Ready for Proposal
**Yes** — proceed to `/opsx:propose C-21-data-migration-v2`.

Key items to communicate to the user:
1. **Schema is already v2.0** — no new Alembic migration. C-21 is a **data migration script only**.
2. **`GOOGLE_CALENDAR_CREDENTIALS` migration is impossible** — script will warn and document manual OAuth2.
3. **Five open questions** need resolution before proposing (see above).
4. **Strict TDD is active** — but the migration script pattern (transaction + rollback) requires careful test design. Tests should verify: data state before/after, idempotency, rollback on error, and edge cases.
5. **Estimated effort**: ~150-200 lines script + ~100-150 lines tests = single PR (~350 lines, within budget).
