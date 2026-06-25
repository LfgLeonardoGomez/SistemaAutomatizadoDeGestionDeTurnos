# Design: C-19 Super-admin Role

## Technical Approach

Add a dedicated `SuperAdmin` SQLAlchemy model and table, isolated from `Profesional`. Reuse the existing JWT library, `CryptContext`, and `Settings` for token signing and password hashing. Introduce a `require_super_admin` dependency that validates a `role: "super_admin"` claim, and expose a new `/admin` router for login, professional management, and global metrics. The first super-admin is bootstrapped from environment variables during application startup seed.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Admin storage | A) `role` column on `Profesional`<br>B) Separate `SuperAdmin` table | A) Pollutes professional fields and risks scoping leakage.<br>B) Clean boundary, no `profesional_id` confusion. | **B** |
| Auth mechanism | A) Long-lived API key<br>B) JWT with role claim | A) Simpler but no multi-admin/audit path.<br>B) Aligns with existing JWT flow. | **B** |
| Service layout | A) Extend `auth_service.py`<br>B) New `super_admin_service.py` | A) Mixes auth concerns.<br>B) Isolates admin logic while reusing helpers. | **B** |
| Bootstrap | A) Insert in migration<br>B) Seed in `lifespan` | A) Env-dependent migrations are fragile.<br>B) Idempotent and env-aware. | **B** |

## Data Flow

```
POST /admin/auth/login
  → routers/admin.py
    → super_admin_service.authenticate_super_admin(email, password)
      → auth_service.verify_password()
      → auth_service.create_super_admin_access_token(id, email, settings)
  ← TokenResponse

GET /admin/profesionales (protected)
  → routers/admin.py
    → dependencies.require_super_admin(token) → SuperAdmin
    → super_admin_service.list_profesionales(db, skip, limit)
  ← list[ProfesionalAdminResponse]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/super_admin.py` | Create | `SuperAdmin` SQLAlchemy model. |
| `backend/app/models/__init__.py` | Modify | Export `SuperAdmin`. |
| `backend/app/schemas/super_admin.py` | Create | Login, professional admin, and metrics response schemas. |
| `backend/app/services/auth_service.py` | Modify | Add `create_super_admin_access_token`; keep professional token unchanged. |
| `backend/app/services/super_admin_service.py` | Create | Auth, professional CRUD, and metrics aggregation. |
| `backend/app/dependencies.py` | Modify | Add `require_super_admin` and `CurrentSuperAdminDep`. |
| `backend/app/routers/admin.py` | Create | `/admin` endpoints. |
| `backend/app/main.py` | Modify | Include admin router; call `seed_super_admin` in lifespan. |
| `backend/app/seed.py` | Modify | Add `seed_super_admin`. |
| `backend/app/config.py` | Modify | Add `super_admin_email` and `super_admin_password_hash`. |
| `backend/alembic/versions/..._create_super_admin_table.py` | Create | Migration for `super_admin` table. |
| `.env.example` | Modify | Add super-admin env vars. |

## Interfaces / Contracts

### Model

```python
class SuperAdmin(Base):
    __tablename__ = "super_admin"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
```

### Schemas

- `SuperAdminLoginRequest`: `email: EmailStr`, `password: str`
- `ProfesionalAdminResponse`: `id`, `nombre`, `especialidad`, `email`, `is_active`, `creado_en`
- `GlobalMetricsResponse`: exact fields and types from the spec
- `TokenResponse`: reused from `schemas/auth.py`

### Dependency

```python
async def require_super_admin(
    token: Annotated[str, Depends(admin_oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SuperAdmin:
    # 401 on missing/invalid/expired token
    # 403 on valid non-super-admin token
```

### Service API

- `authenticate_super_admin(db, email, password) -> SuperAdmin | None`
- `create_super_admin_access_token(id, email, settings) -> str`
- `list_profesionales(db, skip, limit)`, `get_profesional(db, id)`, `activate_profesional(db, id)`, `deactivate_profesional(db, id)`
- `compute_global_metrics(db) -> GlobalMetricsResponse`

## Security Design

- **Isolation**: `SuperAdmin` has no `profesional_id`; admin endpoints never use `get_current_profesional` and never implicitly scope by professional.
- **JWT boundary**: Super-admin tokens carry `role: "super_admin"`. `require_super_admin` rejects professional or roleless tokens with `403 Forbidden`.
- **Token exposure**: Use HTTPS in production, keep `SECRET_KEY` in a secret manager, and reuse `ACCESS_TOKEN_EXPIRE_MINUTES`.
- **Bootstrap**: Credentials come from `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD_HASH`. The pre-computed bcrypt hash is never logged. `.env` remains in `.gitignore`.
- **Deactivate safety**: Deactivation flips `Profesional.is_active` only; related data is preserved. Deactivated professionals cannot log in because `authenticate_profesional` checks `is_active == True`.

## Migration / Rollout

1. Run Alembic upgrade to create the `super_admin` table.
2. Set `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD_HASH`.
3. Restart the backend; `seed_super_admin` creates the initial row only if the table is empty.
4. Rollback: revert the migration, remove the admin router, and revert dependency changes.

## Testing Strategy

Tests are deferred per project directive. When resumed:

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `require_super_admin` rejects professional/missing tokens | Dependency injection with mocked JWT and DB |
| Unit | `compute_global_metrics` ratios | Test DB with seeded rows |
| Integration | `POST /admin/auth/login` | FastAPI test client with bcrypt hash |
| Integration | Admin endpoint isolation | Professional JWT returns 403; admin token returns 200 |
| E2E | Activate/deactivate professional | Verify login behavior changes |

## Open Questions

- Should super-admin tokens use a separate `SUPER_ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES`? This design reuses the existing setting.
- Should the Alembic migration also insert the seed admin for environments that bypass startup seed? This design uses startup seed only.
