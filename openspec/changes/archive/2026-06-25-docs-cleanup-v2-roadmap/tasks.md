# Tasks: Documentation and v2.0 Roadmap Cleanup

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 180–280 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr-default |
| Chain strategy | none |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: none
400-line budget risk: Low

## Phase 1: Archive File Operations

- [x] 1.1 `git mv openspec/changes/c-16-tenant-backend-scoping/ openspec/changes/archive/2026-06-25-c-16-tenant-backend-scoping/` — archive completed C-16 with all its artifacts (`.openspec.yaml`, `proposal.md`, `design.md`, `tasks.md`, `specs/`, `BREAKING_CHANGES.md`).
- [x] 1.2 `git mv openspec/changes/archive/2026-06-22-tenant-auth-professional/ openspec/changes/archive/2026-06-22-c-15-tenant-auth-professional/` — add missing `c-15-` prefix to align with canonical numbering.
- [x] 1.3 Create archive stub `openspec/changes/archive/2026-06-25-c-17-telegram-multi-bot/` with minimal `.openspec.yaml` (`schema: spec-driven`, `created: 2026-06-25`) and a one-line `README.md` noting this was implemented inline without a full SDD cycle.
- [x] 1.4 Create archive stub `openspec/changes/archive/2026-06-25-c-18-google-multi-calendar/` with same minimal structure as 1.3.

## Phase 2: CHANGES.md Rewrite

- [x] 2.1 Update **dependency tree** ASCII art: add C-14 → C-15 → C-16 chain under FASE 7, then C-17/C-18 branching from C-15, and C-19–C-22 as forward items.
- [x] 2.2 Update **Paralelismo por fase** gates: add GATE 7 (C-14 ✓) → C-15, GATE 8 (C-15 ✓) → C-16 + C-17 + C-18 parallel, GATE 9 (C-16+C-17+C-18 ✓) → C-19 + C-20 parallel, GATE 10 → C-21, GATE 11 → C-22.
- [x] 2.3 Update **Camino crítico**: extend to `C-01 → C-02 → C-14 → C-15 → C-16 → C-19 → C-21 → C-22` (or equivalent based on actual dependency analysis).
- [x] 2.4 Update **Plan óptimo con 3 agentes**: add rows for steps covering C-14 through C-22.
- [x] 2.5 Mark C-14, C-15, C-16, C-17, C-18 as `[x] archivado` / `[x] completado` in their FASE 7 entries. Add C-17 and C-18 entries in FASE 7 if not present (multi-bot Telegram, multi-calendar Google).
- [x] 2.6 Add FASE 8 — Super-Admin & Onboarding with C-19 (`super-admin-role`), C-20 (`professional-onboarding`).
- [x] 2.7 Add FASE 9 — Migration & Hardening with C-21 (`data-migration-v2`), C-22 (`hardening-config-cleanup`).
- [x] 2.8 Rewrite **Resumen** table: add rows for C-16 through C-22 with correct fase, estado, governance, and dependencies.
- [x] 2.9 Update **"Primer change recomendado"** footer to point to C-19 (or next unimplemented change).

## Phase 3: NEXT_SESSION.md Resolution

- [x] 3.1 Replace `NEXT_SESSION.md` content with a short forward-looking note: summarize that v1.0 is complete, multi-tenant v2.0 foundation (C-14–C-18) is done, and next steps are C-19 (super-admin) onward. Remove the stale detailed implementation plan that is now captured in CHANGES.md.

## Phase 4: Link Verification

- [x] 4.1 Grep all `*.md` files for references to `openspec/changes/c-16-tenant-backend-scoping` (old path) and update to the new archive path.
- [x] 4.2 Grep for references to `2026-06-22-tenant-auth-professional` (old archive name) and update to `2026-06-22-c-15-tenant-auth-professional`.
- [x] 4.3 Verify every `C-NN` reference in CHANGES.md has a matching archive folder or active change folder. Fix any orphans.
