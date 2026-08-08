# Proposal — c-27-confirmacion-turno-telegram

## Why

The Telegram booking flow only executes the first half of the turno state machine. It calls `POST /turnos`, which leaves the turno in `RESERVADO_TEMPORAL`, and never calls `PUT /turnos/{id}/confirmar`. The scheduler then releases the reservation after `reserva_temporal_minutos` (10) and the slot silently returns to the pool. The system has produced **zero** `CONFIRMADO` turnos to date.

The blocker is data, not wiring: `ConfirmarTurnoRequest` requires `nombre`, `apellido`, `dni` and `telefono`, and the bot never collects any of them.

This is the tightest constraint in the product right now, because everything downstream depends on a confirmed turno:

- `cancelar_turno` rejects any turno whose state is not `CONFIRMADO` (`turno_service.py:418`).
- `reprogramar_turno` does the same (`turno_service.py:480`).
- Reminders only ever target confirmed turnos.

Concretely, this already blocked verification of c-26: task 8.3 asked for a smoke test of all three sub-flows and could only be completed for `crear`, because no confirmed turno exists to cancel or reschedule. Closing this gap unblocks that follow-up and the two flows behind it.

## What Changes

**Conversational capture in n8n (DNI-first).** After the slot is reserved, the bot asks for the patient's DNI and looks it up. A returning patient is confirmed immediately — one question. A new patient is asked for name + surname, then phone + email — three questions total. This optimises the frequent case: in a practice, most bookings belong to patients who have been seen before.

- Extend `sub-flujo-crear-turno` past `HTTP - POST Crear Turno` with the capture steps and a `PUT /turnos/{id}/confirmar` call. The existing `Code - Extraer Turno ID` node already surfaces the `turno_id` the confirm call needs.
- Handle the reservation expiring mid-conversation: `PUT /confirmar` answers `409` once the 10-minute window closes, and the flow must report that instead of failing silently.

**Patient lookup by DNI (backend).** Add a lookup that answers whether a DNI already belongs to a patient of the authenticated professional, and returns that patient's data when it does. No such lookup exists today — `GET /pacientes` only pages through the full list with no filter.

**Flexible auth on `pacientes.py` (backend).** Every endpoint in `pacientes.py` still depends on `CurrentProfesionalDep`, which accepts a Bearer JWT only. c-26 migrated `turnos.py` alone, so n8n — which authenticates with `X-API-Key` — receives `401` from every patient endpoint. The lookup is unreachable from the bot until this is migrated, reusing the `get_current_profesional_flexible` dependency delivered by c-26.

**Email captured, not yet delivered.** `TurnoDestinatario` already models `canal ∈ {TELEGRAM, EMAIL}` with `UNIQUE(turno_id, canal)`, and `_upsert_destinatarios_confirmacion` already registers both channels when the payload carries `telegram_chat_id` and `email`. The bot will collect the email so the data exists going forward, but **no email is sent**: the backend has no mail sender of any kind. The bot must not promise the patient a reminder on a channel that cannot deliver.

### Non-goals

- Integrating a mail provider (SMTP/SendGrid) or sending email reminders. Separate change.
- Making the n8n path multi-tenant. The professional is still resolved from a single static `X-API-Key` credential; see the multitenancy change queued after this one.
- Relaxing `telefono` to optional in `ConfirmarTurnoRequest`. Kept required — the DNI-first design already spares returning patients from retyping it.
- Rebuilding `cancelar` or `reprogramar`. This change only makes them testable.

## Capabilities

### New Capabilities

- `telegram-turno-confirmation-flow`: the DNI-first conversational capture that carries a turno from `RESERVADO_TEMPORAL` to `CONFIRMADO` over Telegram — branching on whether the patient exists, collecting the missing fields, calling confirm, and handling reservation expiry mid-conversation.
- `patient-dni-lookup`: resolving a patient by `(profesional_id, dni)` through the API, so a caller can tell an existing patient from a new one before confirming.

### Modified Capabilities

- `patient-management`: patient endpoints accept `X-API-Key` in addition to a Bearer JWT, so machine callers (n8n) can reach them. Authorisation scope is unchanged — the professional is still resolved per request and every query stays scoped to `profesional_id`.

## Impact

**Backend**
- `backend/app/routers/pacientes.py` — all four endpoints migrate from `CurrentProfesionalDep` to `FlexibleProfesionalDep`; new DNI lookup.
- `backend/app/services/paciente_service.py` — lookup by `(profesional_id, dni)`. Note `crear_o_obtener_paciente` already performs an upsert on exactly that key with `SELECT FOR UPDATE`, so confirmation stays correct even if two conversations race on the same DNI.
- `backend/app/schemas/paciente.py` — response shape for the lookup.
- `backend/tests/` — new tests under the project's strict TDD rule (RED before GREEN).

**n8n**
- `n8n-workflows/sub-flujo-crear-turno.json` — capture nodes, lookup branch, confirm call, expiry handling.
- `n8n-workflows/README.md` — the workflow table still marks `sub-flujo-crear-turno` as "✅ Completo" and describes a `CSV → confirmar` step that was never built. Correct both.

**Unchanged**
- `turno_service.confirmar_turno` and `_upsert_destinatarios_confirmacion` are already correct for this flow and are not modified.
- `ConfirmarTurnoRequest` keeps its current required fields.

**Risks**
- The 10-minute reservation window now spans a conversation. A slow patient loses the slot. Mitigated by keeping the new-patient path to three questions and by reporting the `409` clearly; revisiting the window itself is out of scope.
- Migrating `pacientes.py` to flexible auth widens what the n8n credential can reach. It stays within one professional's own data, but it is an auth-surface change and is treated as such — CRITICAL governance, explicit tests per endpoint.
