# Design: Accept API-Key auth on n8n-called turno endpoints

## Technical Approach

Add ONE new dependency `get_current_profesional_flexible` in `dependencies.py` that resolves a `Profesional` from either header, trying `X-API-Key` first, then `Authorization: Bearer` (JWT). Both headers are individually optional; if neither yields a valid active professional it raises a single generic `401 "Credenciales inválidas"`. Replace `CurrentProfesionalDep` with a new `FlexibleProfesionalDep` alias on the 7 `turnos.py` endpoints only. JWT and API-key are treated as equivalent professional-scoped identities on these routes. n8n HTTP nodes swap their header-auth credential from Bearer JWT to `X-API-Key`. No DB migration (the `api_key` column already exists on `Profesional`).

## Architecture Decisions

| Decision | Choice | Alternatives rejected | Rationale |
|----------|--------|----------------------|-----------|
| Header precedence | Try `X-API-Key` first, then Bearer | Bearer-first; require both | M2M caller (n8n) is the primary consumer; api-key is the durable credential. Locked by user. |
| Both headers optional (no `auto_error`) | Extract raw headers with `Header(default=None)`; decode manually | Reuse `HTTPBearer(auto_error=True)` / `Header(alias=...)` without default | `auto_error`/required headers raise 401/422 *before* the fallback can run, breaking the OR. Must read both optionally, then decide. |
| Error surface | Single generic `401 "Credenciales inválidas"`, `WWW-Authenticate: Bearer` | Distinct per-scheme messages (`"API Key inválida"` vs `"Credenciales inválidas"`) | Distinct messages leak which scheme was attempted → oracle for enumeration. Sub-agent flagged this scheme-leak. |
| Reuse vs. new dep | New composite dep; leave `get_current_profesional` / `get_profesional_by_api_key` intact | Modify existing deps in place | Existing deps still serve JWT-only human routes and the recordatorios api-key route. Additive = safe rollback. |
| Scope | `turnos.py` only | Also `pacientes.py` / `lista_espera.py` | Verified: n8n active workflows call only `/turnos/*`. Narrower surface. Locked by user. |
| api_key hashing | Deferred to C-27 (plaintext column stays) | Hash-at-rest now | Locked; keeps C-26 focused. Residual risk carried below. |

## Data Flow

    n8n HTTP node ──X-API-Key: <key>──▶ /turnos/* ─▶ get_current_profesional_flexible
    human dashboard ─Authorization: Bearer <jwt>─▶ /turnos/* ─┘
                                                              │
      1. X-API-Key present?  ─yes─▶ SELECT Profesional WHERE api_key=? AND is_active ─hit─▶ return
                              │                                                        └miss─┐
      2. Bearer present?     ─yes─▶ decode JWT ─▶ SELECT Profesional WHERE id=sub AND is_active ─hit─▶ return
                              │                                                                  └miss─┐
      3. neither valid ───────────────────────────────────────────────────────────────────▶ raise 401 (generic)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/dependencies.py` | Modify | Add `get_current_profesional_flexible` + `FlexibleProfesionalDep` alias. No change to existing deps. |
| `backend/app/routers/turnos.py` | Modify | Import + swap `CurrentProfesionalDep` → `FlexibleProfesionalDep` on all 7 endpoints. Body unchanged. |
| `backend/tests/test_turnos_router.py` (or new `test_flexible_auth.py`) | Modify/Create | Add auth-matrix tests (see plan). |
| `n8n-workflows/sub-flujo-{crear,cancelar,reprogramar}-turno.json` | Modify | Rebind `httpHeaderAuth` credential from `"Authorization"` (id `Aaw5tL1OiWSNc2Eg`) to the `X-API-Key` credential (mirror `flujo-recordatorio`: id `profesional-api-key`). |

## Interface / Contract

`get_current_profesional_flexible(x_api_key: str | None = Header(None, alias="X-API-Key"), authorization: str | None = Header(None), db) -> Profesional`. Reads both headers optionally, applies precedence, raises the shared generic 401 on total failure. Both branches filter `is_active == True`, so an inactive professional is rejected on either scheme. Resolves to exactly one `profesional.id` → tenant/professional isolation preserved.

## Testing Strategy (Strict TDD — pytest, RED first)

| Case | Setup | Expect |
|------|-------|--------|
| api-key valid | `X-API-Key` = active prof's key | 200, resolves that prof |
| jwt valid | `Authorization: Bearer <jwt>` only | 200, resolves that prof |
| both present → api-key wins | valid key of prof A + valid jwt of prof B | 200, resolves **A** |
| both invalid | bad key + bad jwt | 401, detail `"Credenciales inválidas"` |
| neither header | no auth headers | 401 (generic, no scheme leak) |
| inactive professional (api-key) | active-key of `is_active=False` prof | 401 |
| inactive professional (jwt) | jwt of deactivated prof | 401 |

Unit-test the dependency via one `/turnos/*` endpoint (e.g. `GET /turnos/disponibles`) using `TestClient` and real seeded `Profesional` rows (mirror `test_recordatorio_router` api-key seeding + `authenticated_client` JWT). Assert the 401 body is identical across all failure cases (no scheme-specific string).

## Migration / Rollout

No DB migration (column exists). Backend dep is additive — JWT keeps working during transition, so n8n workflows can be re-bound one at a time. Rollback: revert routers to `CurrentProfesionalDep`; restore `Authorization` credential on n8n nodes.

## Open Questions / Residual Risks

- [ ] **api_key stored plaintext** (High, pre-existing) — deferred to C-27; a DB leak exposes all keys. Not introduced here but broadening its use raises stakes.
- [ ] **api_key must never reach n8n execution logs** — use the n8n *credential* (httpHeaderAuth), never an inline header parameter; credential values are masked in execution logs. Confirm no node inlines the key.
- [ ] No rate limiting / revocation-endpoint (deferred to C-27); revoke = overwrite-on-regenerate only.
