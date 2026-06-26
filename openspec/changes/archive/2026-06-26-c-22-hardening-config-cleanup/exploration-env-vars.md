## Exploration: C-22 deprecated env vars

### Current State

Three env vars are suspected of being deprecated in favor of per-professional database config.

| Env Var | In config.py | Used in production? | Migration status |
|---------|-------------|---------------------|-----------------|
| `TELEGRAM_BOT_TOKEN` | Line 13 — `telegram_bot_token: str` | **No** — all reads are `profesional.telegram_bot_token` | Fully migrated |
| `GOOGLE_CALENDAR_CREDENTIALS` | Line 17 — `google_calendar_credentials: str = "{}"` | **No** — CalendarService uses OAuth with `google_refresh_token` (per-prof) + `google_client_id/secret` (global) | Fully migrated |
| `GOOGLE_CALENDAR_ID` | Line 18 — `google_calendar_id: str = "primary"` | **Yes** — `calendar_service.py` lines 79, 92, 101 use `self.settings.google_calendar_id` | NOT migrated — global |

### Affected Areas

- `backend/app/config.py` — `telegram_bot_token` (L13), `google_calendar_credentials` (L17), `google_calendar_id` (L18) declared
- `backend/app/services/calendar_service.py` — `self.settings.google_calendar_id` used on lines 79, 92, 101 as `calendarId` for all API calls
- `backend/.env.example` — lines 2, 5, 6 reference all three
- `backend/tests/conftest.py` + `test_config.py` — set env vars in tests
- `backend/tests/test_migration.py` — migration drops `telegram_bot_token` column (L86)

### Analysis

#### `TELEGRAM_BOT_TOKEN` / `telegram_bot_token` (config-level)
- **Status**: Dead code. The field is declared in `Settings` but never read by any production code.
- All production reads are from `profesional.telegram_bot_token` (model column, set per-profesional).
- `telegram_service.py` L683-686: `profesional.telegram_bot_token`
- `lista_espera_service.py` L131: `profesional.telegram_bot_token`
- `scheduler/jobs.py` L147: `profesional.telegram_bot_token`
- **Verdict**: **Safe to remove** from `Settings` and `.env.example`.

#### `GOOGLE_CALENDAR_CREDENTIALS` / `google_calendar_credentials`
- **Status**: Completely unused. The JSON credentials string is never read anywhere.
- `CalendarService.__init__` uses `google_refresh_token` (per-prof) + `google_client_id` + `google_client_secret` (global from Settings).
- **Verdict**: **Safe to remove** from `Settings` and `.env.example`.

#### `GOOGLE_CALENDAR_ID` / `google_calendar_id`
- **Status**: Still actively used — but should arguably be per-profesional.
- All three `calendar_service.py` API calls (insert/update/delete) pass `calendarId=self.settings.google_calendar_id`.
- Currently a global default `"primary"` — every profesional shares the same Google Calendar.
- The per-profesional `google_refresh_token` was already migrated (C-14), but `google_calendar_id` was not.
- **Design question**: Should each profesional have their own `google_calendar_id` (new DB column), or is sharing one calendar per instance acceptable for v1.0?
- **Verdict**: **Needs design decision before removing**. Options:
  1. **Remove entirely** — hardcode `"primary"`, no config needed (simplest, breaks multi-calendar).
  2. **Keep global as fallback** — add `google_calendar_id` column to `profesional`, fall back to `settings.google_calendar_id` if null.
  3. **Per-prof only** — add column, remove global, require every profesional to set it.

### Risks

- `TELEGRAM_BOT_TOKEN`: Low risk — dead code removal.
- `GOOGLE_CALENDAR_CREDENTIALS`: Low risk — dead code removal.
- `GOOGLE_CALENDAR_ID`: Medium risk — if removed without per-professional replacement, all calendar operations will use the hardcoded `"primary"` calendar. If this is acceptable for v1.0, it's a simple removal. If not, needs schema migration + schema update.

### Ready for Proposal

**No** — `GOOGLE_CALENDAR_ID` needs a design decision from the user/orchestrator:
> "Should `google_calendar_id` become per-profesional (new DB column), or is keeping it as a global fallback acceptable for v1.0?"

The other two (`TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`) are ready for immediate removal tasks once the proposal is approved.
