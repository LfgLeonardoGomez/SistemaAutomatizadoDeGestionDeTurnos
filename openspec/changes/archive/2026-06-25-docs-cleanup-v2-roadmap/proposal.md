# Proposal: Documentation and v2.0 Roadmap Cleanup

## Intent

Clean up documentation/tracking drift so `CHANGES.md` becomes the single source of truth for the remaining v2.0 work. Remove contradictions with `NEXT_SESSION.md`, archive already-implemented changes, and align canonical numbering with the actual code state.

## Scope

### In Scope
- Archive `openspec/changes/c-16-tenant-backend-scoping/` into `openspec/changes/archive/2026-06-25-c-16-tenant-backend-scoping/`.
- Rename `openspec/changes/archive/2026-06-22-tenant-auth-professional/` to `openspec/changes/archive/2026-06-22-c-15-tenant-auth-professional/`.
- Create archive stubs for the already-implemented multi-bot Telegram and multi-calendar Google work.
- Update `CHANGES.md`:
  - Mark C-14, C-15, C-16, C-17, C-18 as completed/archived.
  - Add C-19 (super-admin role + endpoints), C-20 (professional onboarding), C-21 (v1.0 → v2.0 data migration script), C-22 (hardening + config cleanup).
  - Refresh dependency tree, critical path, and summary table.
- Decide the fate of `NEXT_SESSION.md` (update to a short forward-looking note or remove if redundant) and act accordingly.
- Note the explicit TDD deferral in the risks section.

### Out of Scope
- Any backend business code changes.
- New features or behavior changes.
- Tests for this documentation-only change (per user directive).

## Capabilities

### New Capabilities
- None — this is a documentation/tracking-only change; no new spec-level behavior is introduced.

### Modified Capabilities
- None — no existing capability requirements are changing.

## Approach

File-system operations plus targeted edits to `CHANGES.md` and `NEXT_SESSION.md`. Use `roadmap-generator` conventions for numbering, phases, and structure. Preserve existing archive contents (`.openspec.yaml`, `proposal.md`, `design.md`, `tasks.md`, specs) when moving or creating stubs.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/changes/c-16-tenant-backend-scoping/` | Removed (archived) | Move complete change folder into archive. |
| `openspec/changes/archive/2026-06-22-tenant-auth-professional/` | Renamed | Add missing `c-15-` prefix. |
| `openspec/changes/archive/2026-06-25-c-16-tenant-backend-scoping/` | New | Final archive of C-16. |
| `openspec/changes/archive/2026-06-25-c-17-telegram-multi-bot/` | New | Stub archive for already-implemented multi-bot Telegram work. |
| `openspec/changes/archive/2026-06-25-c-18-google-multi-calendar/` | New | Stub archive for already-implemented per-professional Google Calendar work. |
| `CHANGES.md` | Modified | Single source of truth for v2.0 roadmap. |
| `NEXT_SESSION.md` | Modified or Removed | Reconcile/deprecate stale forward-looking notes. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Renaming archive folder breaks internal or generated links | Low | Use `git mv`; verify no hardcoded references. |
| `CHANGES.md` numbering still inconsistent with archive state | Low | Cross-check every C-NN against archive folders and code state. |
| TDD deferral is forgotten after docs cleanup | Medium | Add explicit risk note and schedule a test catch-up before backend v2.0 work resumes. |

## Rollback Plan

Revert the specific file operations and markdown edits via git. Archive moves are reversible with `git mv`. `CHANGES.md` and `NEXT_SESSION.md` can be restored from git history.

## Dependencies

- None external.

## Success Criteria

- [ ] C-16 active folder archived and removed from `openspec/changes/`.
- [ ] C-15 archive folder renamed with the `c-15-` prefix.
- [ ] C-17 and C-18 archive stubs exist in `openspec/changes/archive/`.
- [ ] `CHANGES.md` marks C-14 through C-18 as completed and lists C-19 through C-22.
- [ ] `CHANGES.md` dependency tree, critical path, and summary table are consistent.
- [ ] `NEXT_SESSION.md` is either updated to a short forward note or removed.
- [ ] No contradictions remain between `CHANGES.md`, archive state, and actual code.
