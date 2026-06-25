## 1. Dependencies & Config

- [x] 1.1 Add `python-jose[cryptography]` and `passlib[bcrypt]` to `backend/requirements.txt`
- [x] 1.2 Extend `app/config.py` with JWT settings: `secret_key: str`, `algorithm: str = "HS256"`, `access_token_expire_minutes: int = 1440`
- [x] 1.3 Add JWT env vars to `.env.example`: `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`

## 2. Domain & Schemas

- [x] 2.1 Create `app/schemas/auth.py` with Pydantic v2 schemas:
  - `ProfesionalRegisterRequest` (email, password with min_length=8, nombre, especialidad, duracion_turno, horario_inicio, horario_fin, dias_atencion)
  - `ProfesionalLoginRequest` (email, password)
  - `TokenResponse` (access_token: str, token_type: str = "bearer")
  - `ApiKeyResponse` (api_key: str)
- [x] 2.2 Ensure `password_hash` and `api_key` are excluded from all existing `Profesional` response schemas (audit `schemas/profesional.py`)

## 3. Service Layer

- [x] 3.1 Create `app/services/auth_service.py` with functions:
  - `hash_password(plain: str) -> str` using `passlib`
  - `verify_password(plain: str, hashed: str) -> bool`
  - `create_access_token(profesional_id: int, email: str, settings: Settings) -> str` (JWT with `sub`, `email`, `exp`, `iat`)
  - `register_profesional(db, data: ProfesionalRegisterRequest) -> Profesional` (hash password, create record, handle `IntegrityError` for duplicate email → raise 409)
  - `authenticate_profesional(db, email: str, password: str) -> Profesional | None` (verify hash, check `is_active`)
  - `generate_api_key() -> str` using `secrets.token_urlsafe(32)`
  - `set_profesional_api_key(db, profesional: Profesional) -> str` (generate, assign, commit)

## 4. Dependencies (JWT & API Key)

- [x] 4.1 Extend `app/dependencies.py`:
  - Add `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)` (or `auto_error=True`)
  - Implement `async def get_current_profesional(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Profesional`
    - Decode JWT with `python-jose`
    - Extract `sub` claim as `int`
    - Query DB for `Profesional` where `id == sub AND is_active == True`
    - Raise `HTTPException(401/403)` on any failure
  - Implement `async def get_profesional_by_api_key(api_key: str = Header(..., alias="X-API-Key"), db: AsyncSession = Depends(get_db)) -> Profesional`
    - Query DB for `Profesional` where `api_key == value AND is_active == True`
    - Raise `HTTPException(401)` on missing/inactive

## 5. Router

- [x] 5.1 Create `app/routers/auth.py` with `APIRouter(prefix="/auth", tags=["auth"])`:
  - `POST /register` (`response_model=TokenResponse`, status_code=201)
    - Call `auth_service.register_profesional`
    - Return JWT via `create_access_token`
  - `POST /login` (`response_model=TokenResponse`)
    - Use `OAuth2PasswordRequestForm` or JSON body (`ProfesionalLoginRequest`)
    - Call `auth_service.authenticate_profesional`
    - Return JWT or 401
  - `POST /api-key` (protected by `Depends(get_current_profesional)`)
    - Call `auth_service.set_profesional_api_key`
    - Return `ApiKeyResponse` with plaintext key
- [x] 5.2 Register `auth_router` in `app/main.py` with `app.include_router(auth_router)`

## 6. Tests

- [x] 6.1 Create `backend/tests/test_auth_password.py` — unit tests:
  - `hash_password` produces different hashes for same input (salt)
  - `verify_password` returns True for correct password
  - `verify_password` returns False for incorrect password
- [x] 6.2 Create `backend/tests/test_auth_jwt.py` — unit tests:
  - `create_access_token` returns a non-empty string
  - Decoding valid token returns correct `sub` and `email`
  - Decoding expired token raises `JWTError`/expired exception
  - Decoding malformed token raises exception
- [x] 6.3 Create `backend/tests/test_auth_integration.py` — integration tests with TestClient + async DB:
  - `POST /auth/register` with valid data returns 201 + token
  - `POST /auth/register` with duplicate email returns 409
  - `POST /auth/register` with password < 8 chars returns 422
  - `POST /auth/login` with valid credentials returns 200 + token
  - `POST /auth/login` with wrong password returns 401
  - `POST /auth/login` with unknown email returns 401
  - Access protected endpoint (e.g., `POST /auth/api-key`) with valid token returns 200 + api_key
  - Access protected endpoint with invalid token returns 401
  - Access protected endpoint with valid token for inactive professional returns 401 (requires setting `is_active=False` in fixture)
- [x] 6.4 Create/update `backend/tests/conftest.py` fixture:
  - Extend `profesional` fixture (from C-14) to include `email`, `password_hash`, `is_active=True`
  - Add `authenticated_client` fixture that logs in and sets `Authorization` header

## 7. Validation & Cleanup

- [x] 7.1 Run `pytest backend/tests/test_auth_*.py` and ensure all tests pass
- [x] 7.2 Run `mypy` (if configured) or manual type-check on new auth modules
- [x] 7.3 Verify `openspec validate` passes for this change
- [x] 7.4 Ensure no `password_hash` or `api_key` leaks in any response model
