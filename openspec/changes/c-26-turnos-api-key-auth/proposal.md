# Proposal: Accept API-Key auth on n8n-called turno endpoints

## Intent

n8n authenticates to the backend with a professional **JWT** that expires in 24h (`ACCESS_TOKEN_EXPIRE_MINUTES=1440`). On expiry every `/turnos/*` call returns `401 "Credenciales inválidas"` and the workflow dies (verified in n8n executions 201/203 on `GET /turnos/disponibles`), forcing manual credential rotation daily. A short-lived user session token is the wrong primitive for a 24/7 machine-to-machine (M2M) caller. The non-expiring API-key infrastructure already exists (`get_profesional_by_api_key`, `POST /auth/api-key`, `Profesional.api_key`) and is already used by `recordatorios.py`, but the `/turnos/*` endpoints are JWT-only.

## Scope

### In Scope
- New combined dependency `get_current_profesional_flexible`: authenticate via `Authorization: Bearer <jwt>` **OR** header `X-API-Key`, professional-scoped, active only.
- Apply it to `turnos.py` (all 7 endpoints) and any other n8n-called professional router (`pacientes.py`, `lista_espera.py`) — confirm exact set in design.
- Switch n8n HTTP nodes in `sub-flujo-crear-turno.json` / `-cancelar-` / `-reprogramar-` from `httpHeaderAuth` bound to `Authorization` to `X-API-Key` (aligns with README convention + working `flujo-recordatorio`/`flujo-lista-espera`).
- Preserve JWT for human/dashboard callers unchanged.

### Out of Scope
- API-key hashing-at-rest migration (flagged as open decision; separate change if approved).
- Rate limiting / key rotation UX / revocation endpoint.
- Telegram-secret-token path (`webhooks.py`) and super-admin auth — untouched.

## Capabilities

### New Capabilities
- `professional-flexible-auth`: reusable dependency accepting Bearer JWT OR `X-API-Key` on machine-callable professional endpoints; 401 when neither is valid; never leaks which scheme failed.

### Modified Capabilities
- `professional-api-key`: extend accepted-endpoints scope to turno/paciente/lista-espera; state that JWT and API-key are equivalent professional-scoped identities on these routes.
- `n8n-workflow-reserva`, `n8n-workflow-cancelacion`: auth header switches from `Authorization` to `X-API-Key` (confirm in design).

## Approach

Add `get_current_profesional_flexible` in `dependencies.py` that tries `X-API-Key` first, falls back to Bearer JWT, returns the active `Profesional` or raises a single generic 401. Replace `CurrentProfesionalDep` with the flexible dep only on n8n-called routers. Tenant isolation is preserved: both paths resolve to one `profesional.id`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/dependencies.py` | New | Combined JWT/API-key dependency |
| `backend/app/routers/turnos.py` | Modified | Swap dep on 7 endpoints |
| `backend/app/routers/{pacientes,lista_espera}.py` | Modified | Swap dep (if n8n-called) |
| `n8n-workflows/sub-flujo-*.json` | Modified | Header-auth → `X-API-Key` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `api_key` stored plaintext — DB leak exposes all keys | High (existing) | Flag now; recommend hashed-at-rest follow-up |
| Broadening auth widens attack surface | Med | Keep dep professional-scoped + active-only; single generic 401 |
| n8n header misconfig breaks live flows | Med | Roll out per-workflow; keep JWT accepted during transition |

## Rollback Plan

Backend: revert routers to `CurrentProfesionalDep` (flexible dep is additive; JWT still works). n8n: restore `Authorization` header-auth credential on the HTTP nodes. No DB migration, so no data rollback.

## Dependencies

- Existing `Profesional.api_key` column + `POST /auth/api-key` (C-14). Professional must generate/store one key in n8n.

## Success Criteria

- [ ] n8n `/turnos/*` calls succeed with `X-API-Key` and never 401 on JWT expiry.
- [ ] Human JWT callers keep working unchanged.
- [ ] Invalid/missing credential returns 401; inactive professional rejected.
- [ ] Auth remains professional-scoped (no cross-tenant access).
