## 1. Config model cleanup

- [x] 1.1 Remove `n8n_webhook_url` and `telegram_webhook_secret` from `backend/app/config.py`.
- [x] 1.2 Rename `super_admin_password_hash` → `super_admin_password` in `backend/app/config.py`.
- [x] 1.3 Run existing config tests to ensure `Settings()` instantiates without the removed fields and with the renamed field.

## 2. .env.example unification

- [ ] 2.1 Rewrite root `.env.example` to match the updated `config.py` exactly (all variables, descriptive comments, sensible defaults).
- [ ] 2.2 Delete `backend/.env.example`.
- [ ] 2.3 Cross-check that `.env.example` has no variables absent from `config.py` and vice versa.

## 3. Docker compose environment

- [ ] 3.1 Add all missing variables to the `backend` service `environment` block in `docker-compose.yml`, using `${VAR:-default}` for optional ones.
- [ ] 3.2 Validate `docker-compose.yml` syntax with `docker compose config`.

## 4. Super-admin seed

- [ ] 4.1 Update `seed_super_admin` in `backend/app/seed.py` to hash `settings.super_admin_password` with `pwd_context.hash()` before storing.
- [ ] 4.2 Add/update tests for `seed_super_admin` verifying bcrypt hashing and that login succeeds with the seeded password.
- [ ] 4.3 Update `docker-compose.yml` to inject `SUPER_ADMIN_PASSWORD` instead of `SUPER_ADMIN_PASSWORD_HASH`.

## 5. Repository cleanup

- [ ] 5.1 Delete `backend/test_migrate.db`.
- [ ] 5.2 Add `*.db` to `.gitignore`.
- [ ] 5.3 Confirm no `*.db` files remain tracked by git (`git ls-files *.db`).

## 6. Integration verification

- [ ] 6.1 Run full `pytest` suite.
- [ ] 6.2 Verify that `Settings()` loads correctly with the canonical `.env.example` values.
