## Exploration: C-22 test/fixture dependencies on deprecated env vars

### Current State
- `TELEGRAM_BOT_TOKEN` and `GOOGLE_CALENDAR_CREDENTIALS` are set as global env vars in multiple test files via `monkeypatch.setenv`.
- `GOOGLE_CALENDAR_ID` is set as global env var and also passed directly to `Settings` in some fixtures.
- The `profesional` model does NOT yet have a `google_calendar_id` field.
- `calendar_service.py` uses `self.settings.google_calendar_id` (global) — will need to switch to `profesional.google_calendar_id` with global fallback.

---

### Findings Table

| File | Line(s) | Pattern | Adjustment Needed |
|------|---------|---------|-------------------|
| `backend/tests/conftest.py` | 22 | `monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")` in `client` fixture | **Remove** — deprecated env var |
| `backend/tests/conftest.py` | 91 | `monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")` in `api_client` fixture | **Remove** — deprecated env var |
| `backend/tests/conftest.py` | 66–84 | `profesional` fixture creates `Profesional` without `google_calendar_id` | **No immediate change**, but will need `google_calendar_id` field once model is updated |
| `backend/tests/test_config.py` | 12–14, 29–31, 46–48, 65–67, 85–87, 100–102, 116–118 | All 7 test methods set `TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, `GOOGLE_CALENDAR_ID` | **Remove all 3 monkeypatches** from each test; `test_settings_calendar_retry_vars` assertion on `settings.google_calendar_id` must be removed/revised |
| `backend/tests/test_turno_service.py` | 28–29 | `test_settings` fixture: `google_calendar_credentials=…`, `google_calendar_id="primary"` | **Remove both** from fixture; Settings no longer needs them |
| `backend/tests/test_lista_espera_service.py` | 28–29 | Same as above in `test_settings` fixture | **Remove both** from fixture |
| `backend/tests/test_scheduler_job.py` | 33–34, 74–75, 100–101, 138–139, 152–153, 176–177, 221–222, 236, 279 | `GOOGLE_CALENDAR_CREDENTIALS` + `GOOGLE_CALENDAR_ID` monkeypatches (9 test methods) | **Remove** `GOOGLE_CALENDAR_*` monkeypatches; keep `TELEGRAM_BOT_TOKEN` if still used by bot init |
| `backend/tests/test_scheduler_isolation.py` | 34–36 | `TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, `GOOGLE_CALENDAR_ID` | **Remove** `GOOGLE_CALENDAR_*` monkeypatches |
| `backend/tests/test_scheduler.py` | 24 | `TELEGRAM_BOT_TOKEN` | **Remove** |
| `backend/tests/test_scheduler_timeout.py` | 28, 41 | `TELEGRAM_BOT_TOKEN` | **Remove** |
| `backend/tests/test_telegram_service.py` | 328 | `TELEGRAM_BOT_TOKEN` | **Remove** |
| `backend/tests/test_auth_jwt.py` | 14 | `TELEGRAM_BOT_TOKEN` | **Remove** |
| `backend/tests/test_database.py` | 14, 48 | `TELEGRAM_BOT_TOKEN` | **Remove** |
| `backend/tests/test_lista_espera_integration.py` | 47 | `TELEGRAM_BOT_TOKEN` | **Remove** |
| `backend/tests/test_calendar_service.py` | 50, 76, 103, 128, 157, 184, 215, 236 | `google_calendar_id="primary"` passed to `Settings()` in 8 test methods | **After** `calendar_service.py` migrates to `profesional.google_calendar_id`: add `google_calendar_id="primary"` to `profesional_con_refresh` fixture; stop passing it to `Settings()` |
| `backend/app/services/calendar_service.py` | 79, 92, 101 | `calendarId=self.settings.google_calendar_id` | **After** `profesional.google_calendar_id` is added: use `profesional.google_calendar_id or self.settings.google_calendar_id` as fallback |
| `backend/app/schemas/profesional.py` | 90–99 | `ProfesionalIntegracionesUpdate` only has `telegram_bot_token` + `google_refresh_token` | **Add** `google_calendar_id: Optional[str] = None`; add validator |
| `backend/app/routers/profesional.py` | 63–66 | `PUT /profesional/integraciones` only handles 2 fields | **Add** handling for `google_calendar_id` update |
| `backend/app/routers/profesional.py` | 81–83 | `ProfesionalIntegracionesResponse` only has `has_telegram` + `has_google` | **Add** `google_calendar_id: Optional[str]` to response schema |
| `backend/app/seed.py` | — | No references to deprecated vars | **No change needed** |

---

### Risks
1. **test_config.py overhaul**: All 7 tests validate global settings that are being deprecated. The test class may need significant rewrites or removal of tests that no longer apply.
2. **test_calendar_service.py**: The `profesional_con_refresh` fixture needs `google_calendar_id` added, which cascades to all 8 test methods.
3. **Breaking bot init**: Some tests may still need `TELEGRAM_BOT_TOKEN` if the Telegram bot is initialized at app startup — confirm whether `app.main` still requires it.
4. **test_scheduler_job.py**: Heavily depends on both deprecated vars; 9 test methods need cleanup.

### Recommendation
- Remove `GOOGLE_CALENDAR_CREDENTIALS` and `GOOGLE_CALENDAR_ID` monkeypatches first (lowest risk).
- Remove `TELEGRAM_BOT_TOKEN` monkeypatches second, verifying no bot-init breakage.
- Handle `test_config.py` last — it tests the deprecated globals directly and may need a dedicated rewrite task.
- The `profesional.google_calendar_id` model field and schema/router updates should happen in a single coherent step before updating `calendar_service.py`.
