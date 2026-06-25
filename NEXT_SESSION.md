# Next Session — Forward Look

> **Last updated**: 2026-06-25
> **Superseded by**: `CHANGES.md` (single source of truth for all changes)

---

## Current State

- **v1.0 COMPLETE**: C-01 through C-13 implemented, tested (318 tests), and archived.
- **v2.0 Foundation COMPLETE**: C-14 through C-18 implemented and archived. Multi-tenant data model, JWT auth, backend scoping, multi-bot Telegram, and multi-calendar Google are all in place.

## What's Next

The next changes to implement are in **FASE 8** (see `CHANGES.md`):

1. **C-19 `super-admin-role`** — Super-admin role and endpoints for SaaS operation.
2. **C-20 `professional-onboarding`** — Self-service registration and onboarding flow for new professionals.

C-19 and C-20 can be worked on in parallel after C-16/C-17/C-18 (all done).

Then **FASE 9**:
3. **C-21 `data-migration-v2`** — Migration script for v1.0 → v2.0 data.
4. **C-22 `hardening-config-cleanup`** — Final cleanup and security hardening.

## Important Note

> **TDD deferral**: C-14 through C-18 were implemented without strict TDD. Before starting C-19, plan a test catch-up session to add missing tests for the multi-tenant foundation.

---

For full details on dependencies, governance, and scope: read `CHANGES.md`.
