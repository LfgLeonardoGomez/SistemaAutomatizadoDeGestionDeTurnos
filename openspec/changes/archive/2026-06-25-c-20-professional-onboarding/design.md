# Design: Professional Onboarding

## Technical Approach

Replace the public `/auth/register` self-service flow with an invitation-only, super-admin-driven creation endpoint. The admin creates a professional with a minimal payload; the backend applies default schedule values, hashes the password, generates an `api_key` and a `telegram_secret_token`, and returns both plaintext secrets exactly once. A new authenticated endpoint lets the professional configure Telegram and Google Calendar tokens afterwards; read responses always mask the stored secrets.

## Architecture Decisions

| Decision | Options Considered | Tradeoffs | Chosen |
|----------|-------------------|-----------|--------|
| Creation service location | `auth_service.py` vs `super_admin_service.py` | Auth service owns hashing/token helpers; admin service owns professional lifecycle. | Implement `create_profesional` in `super_admin_service.py`, reusing `hash_password`, `generate_api_key`, and a new `generate_telegram_secret_token` from `auth_service.py`. |
| Secret generation | `secrets.token_urlsafe(32)` vs UUID | URL-safe token is compact and already used for `api_key`. | Use `secrets.token_urlsafe(32)` for both `api_key` and `telegram_secret_token`. |
| Plaintext exposure | Return once on creation only; never again | Required for initial credentials; any later exposure is a security regression. | Return plaintext `api_key` and `telegram_secret_token` only in the `201 Created` response of `POST /admin/profesionales`. |
| Integration endpoint scope | Separate `PUT /profesional/integraciones` vs extend `/profesional/configuracion` | Mixing schedule config with secret tokens complicates masking and partial updates. | Dedicated `PUT /profesional/integraciones` plus `GET /profesional/integraciones` for status. |
| Partial token updates | Nullable fields with `None` skip vs explicit sentinel | Pydantic `Optional` plus `None` skip matches existing `ProfesionalConfigUpdate` pattern. | Accept `telegram_bot_token` and `google_refresh_token` as optional; update only provided non-empty values. |
| Masking strategy | Computed booleans vs redacted strings | Booleans (`has_telegram`, `has_google`) are unambiguous and leak nothing. | Return boolean flags and omit token fields from all read schemas. |
| HTTPS enforcement | Middleware vs dependency per route | Middleware is global but may misbehave behind proxies; per-route dependency is explicit and testable. | Add `require_https` dependency applied to `/admin/profesionales` and `/profesional/integraciones`, trusting `X-Forwarded-Proto` when behind a proxy. |
| `email` NOT NULL | Alter column vs keep nullable | Existing seed and all v1 professionals already have emails; NOT NULL aligns with invitation-only onboarding. | Migration to alter `profesional.email` to `nullable=False`; unique constraint already exists. |

## Data Flow

```
Super-admin JWT
       │
       ▼
POST /admin/profesionales ──► admin router ──► super_admin_service.create_profesional()
                                                    │
                    ┌───────────────────────────────┼───────────────────────────────┐
                    ▼                               ▼                               ▼
              hash_password()            generate_api_key()          generate_telegram_secret_token()
                    │                               │                               │
                    └───────────────────────────────┼───────────────────────────────┘
                                                    ▼
                                            INSERT INTO profesional
                                                    │
                                                    ▼
                            201 Created with profile + plaintext secrets (one-time)

Professional JWT
       │
       ▼
PUT /profesional/integraciones ──► profesional router ──► update only provided tokens
       │
       ▼
GET /profesional/integraciones ──► returns {has_telegram, has_google} only
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/profesional.py` | Modify | Change `email` to `Mapped[str]` NOT NULL. |
| `backend/alembic/versions/xxxxxxxx_profesional_email_not_null.py` | Create | Migration to alter `email` column to `nullable=False`. |
| `backend/app/services/auth_service.py` | Modify | Remove `register_profesional` and `ProfesionalRegisterRequest` import; add `generate_telegram_secret_token()`. |
| `backend/app/services/super_admin_service.py` | Modify | Add `create_profesional()` with default schedule, hashing, token generation, and duplicate-email handling. |
| `backend/app/routers/auth.py` | Modify | Remove `/auth/register` route and `ProfesionalRegisterRequest` schema usage. |
| `backend/app/routers/admin.py` | Modify | Add `POST /admin/profesionales` protected by `CurrentSuperAdminDep`. |
| `backend/app/routers/profesional.py` | Modify | Add `PUT /profesional/integraciones` and `GET /profesional/integraciones`. |
| `backend/app/schemas/auth.py` | Modify | Remove `ProfesionalRegisterRequest`. |
| `backend/app/schemas/profesional.py` | Modify | Add `ProfesionalCreateRequest`, `ProfesionalCreateResponse`, `ProfesionalIntegracionesUpdate`, `ProfesionalIntegracionesResponse`. |
| `backend/app/dependencies.py` | Modify | Add `require_https` dependency for production HTTPS enforcement. |
| `backend/tests/test_auth_integration.py` | Modify | Remove `TestRegister`; keep login/API-key tests. |

## Interfaces / Contracts

### Request/Response Schemas

```python
class ProfesionalCreateRequest(BaseModel):
    nombre: str
    email: EmailStr
    password: str = Field(..., min_length=8)
    especialidad: str

class ProfesionalCreateResponse(BaseModel):
    id: int
    nombre: str
    email: str
    especialidad: str
    is_active: bool
    duracion_turno: int
    horario_inicio: str
    horario_fin: str
    dias_atencion: list[str]
    api_key: str
    telegram_secret_token: str

class ProfesionalIntegracionesUpdate(BaseModel):
    telegram_bot_token: Optional[str] = None
    google_refresh_token: Optional[str] = None

    @field_validator("telegram_bot_token", "google_refresh_token")
    @classmethod
    def reject_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() == "":
            raise ValueError("token cannot be empty")
        return v

class ProfesionalIntegracionesResponse(BaseModel):
    has_telegram: bool
    has_google: bool
```

### Default Schedule

New professionals receive:
- `duracion_turno = 30`
- `horario_inicio = "09:00"`
- `horario_fin = "17:00"`
- `dias_atencion = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]`

### Security Contract

- Plaintext `api_key`, `telegram_secret_token`, `telegram_bot_token`, `google_refresh_token`, and `password_hash` are never logged.
- `POST /admin/profesionales` and `/profesional/integraciones` require HTTPS when `ENV=production`.
- Admin list/detail responses continue to use `ProfesionalAdminResponse`, which excludes all secrets.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `super_admin_service.create_profesional` hashing, defaults, duplicate 409 | Async test against `db_session` fixture |
| Unit | `generate_api_key` / `generate_telegram_secret_token` | Assert length and uniqueness |
| Integration | `POST /admin/profesionales` 201, 409, 422, 403 | Use `api_client` + seeded super-admin |
| Integration | `PUT /profesional/integraciones` partial update and empty-token rejection | Authenticated as professional |
| Integration | `GET /profesional/integraciones` masks secrets | Assert no token fields in JSON |
| Integration | `/auth/register` returns 404 | Confirm route removal |
| Migration | `email` NOT NULL applied | Alembic upgrade/downgrade round-trip |

> Note: tests are deferred per user directive but are specified here for the catch-up phase.

## Migration / Rollout

1. Create Alembic revision to alter `profesional.email` to `nullable=False`.
2. Run `alembic upgrade head` in all environments.
3. Deploy backend code.
4. Update any n8n workflows or clients still calling `/auth/register` to use `POST /admin/profesionales`.

Rollback: revert code and run `alembic downgrade` one revision; no data loss because `email` values remain populated.

## Open Questions

- None
