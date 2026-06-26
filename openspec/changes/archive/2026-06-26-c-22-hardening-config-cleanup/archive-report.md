# Archive Report: C-22 `hardening-config-cleanup`

## Status

`archive`

## Summary

C-22 completed the v2.0 configuration cleanup: removed three deprecated global env vars (`TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_CREDENTIALS`, `GOOGLE_CALENDAR_ID`) from Pydantic Settings, added `profesional.google_calendar_id` with `"primary"` server default, updated the integration API, and ran a security/scoping audit. All 15/15 tasks complete.

## Verdict

**PASS** — Verify report confirmed no CRITICAL issues. Two warnings (root `.env.example` and `docker-compose.yml`) were resolved.

## Test Execution Note

Tests were NOT executed per explicit user directive. All verification was based on static source inspection and grep evidence. The archive report records this as a known limitation.

## Specs Synced to Main Specs

| Domain | Action | Details |
|--------|--------|---------|
| `configuration-management` | Updated | Added 3 REMOVED requirements (TELEGRAM_BOT_TOKEN, GOOGLE_CALENDAR_CREDENTIALS, GOOGLE_CALENDAR_ID) with Reason/Migration notes. Added "Startup without deprecated variables" scenario to existing requirement. |
| `professional-integration-setup` | Updated | Modified "Update integration tokens" to include `google_calendar_id` with 4 scenarios. Modified "Read integration status" to include `google_calendar_id` in response. Added "Default calendar ID" requirement. |
| `google-calendar-sync` | Updated | Replaced "Autenticación OAuth 2.0 con cuenta de servicio" with "Google Calendar authentication per professional" (OAuth refresh tokens). Updated "Pydantic Settings for Google Calendar" to reflect new field set. Added "Calendar target per professional" requirement. |

## Archive Contents

- proposal.md ✅
- spec.md ✅
- specs/ (configuration-management, professional-integration-setup, google-calendar-sync) ✅
- design.md ✅
- tasks.md ✅ (15/15 tasks complete)
- apply-progress.md ✅
- verify-report.md ✅ (PASS)
- exploration-env-vars.md ✅
- exploration-tests.md ✅

## Source of Truth Updated

The following main specs now reflect the new behavior:
- `openspec/specs/configuration-management/spec.md`
- `openspec/specs/professional-integration-setup/spec.md`
- `openspec/specs/google-calendar-sync/spec.md`

## CHANGES.md Update

- C-22 status changed from `[ ]` pendiente → `[x]` archivado (both in main entry and summary table)
- C-21 remains `[N/A]` (unchanged)

## Security / Scoping Audit

All 16 checks passed. No gaps found — all endpoints authenticated and scoped by `profesional_id`. See apply-progress for full checklist.

## Task Completion

All 15 tasks marked `[x]` in persisted `tasks.md`. No stale unchecked tasks. No exceptional reconciliation performed.

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
Ready for the next change.
