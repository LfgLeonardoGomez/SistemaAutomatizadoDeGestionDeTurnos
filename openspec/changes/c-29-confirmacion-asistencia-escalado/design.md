# Design — c-29-confirmacion-asistencia-escalado

## Context

The reminder asks "¿Confirmás tu asistencia?" and offers three buttons. C-27 wired the buttons so the callbacks reach the orquestador; commit `46d5eb9` made the `confirmar` answer land somewhere. What is still missing is the half that carries the product value: **when the patient never answers, nothing happens**. The slot stays held, the professional loses the hour, and nobody else can take it.

### What already shipped (commit `46d5eb9`)

The first slice of this change is on `main`. It is described here because the rest of the design is built on top of it, not beside it.

- `turno.asistencia_confirmada_en` — `TIMESTAMP NULL` (migration `c29b4e7a2f10`). `NULL` means "did not answer"; the instant is what lets the escalation compute its windows.
- `turno_service.confirmar_asistencia_turno` (`turno_service.py:530`) now seals that mark. It was a validated no-op before — it checked ownership and state and returned the turno unchanged, so a patient who confirmed was byte-for-byte indistinguishable from one who ignored the message. The seal is written **once**: Telegram redelivers updates and the patient can tap the button twice, and overwriting the mark would push the escalation window forward on every tap.
- `PUT /turnos/{id}/confirmar-asistencia` (`routers/turnos.py:280`) on `FlexibleProfesionalDep`; `404` unknown turno, `409` not `CONFIRMADO`.
- `orquestador.json` calls that endpoint before replying, with `neverError` + `fullResponse`, so a `404`/`409` reaches the patient as a message instead of as silence.
- `backend/tests/test_confirmacion_asistencia.py` — 178 lines covering the seal, its idempotency, the untouched `estado`, persistence across sessions, and the three pre-existing guards.

`turno.estado` was deliberately not touched. The confirmation is a **fact about** the turno, not a **state of** it, so the professional's view is unchanged — which is what the product owner asked for.

### The three constraints that shape what is left

**There is no record of when the first reminder went out.** `turno.recordatorio_enviado` is a `bool` (`models/turno.py:50`). The escalation's first question is "has the patient had `N` hours to answer?", and a boolean cannot answer it. This is the single largest gap between the proposal and the code, and it is not visible from the proposal.

**Two clocks, and mixing them is a silent bug.** `app/tiempo.py` exists because this repo has already shipped that bug: `turno.fecha` / `turno.hora_inicio` are **local** naive (the appointment as a human agreed it), while `creado_en`, `reserva_temporal.expiracion` and `asistencia_confirmada_en` are **naive UTC**, and the backend container runs in UTC. The escalation job compares against agenda columns *and* computes elapsed durations, so it is the first piece of code in this codebase that genuinely straddles both. Section D3 is the most important paragraph in this document.

**This change cancels real patients' appointments without a human in the loop.** Governance is MEDIUM in the proposal, and every decision below that had a choice between "cancels more" and "cancels less" resolves toward cancelling less.

### Stated precondition

The proposal declares `Depende de: C-27 archivado`. C-27 is **not** archived — roughly ten tasks remain open, concentrated in its groups 8 (n8n end-to-end) and 9 (the c-26 follow-up). Planning proceeds now; the implementation groups that touch the Telegram path (§7 of `tasks.md` onward) wait on C-27 closing, because they exercise the same orquestador nodes C-27 is still verifying. Task 1.1 makes that gate explicit.

## Goals / Non-Goals

**Goals:**

- A patient who ignores the reminder gets a second, explicitly final warning, and then loses the slot.
- A patient who answered `confirmar` is never chased and never auto-cancelled.
- An auto-cancelled slot is offered again by availability.
- The escalation never starts for a turno whose full window does not fit before the appointment begins.
- The job is safe to run twice: no double warning, no double cancellation.

**Non-Goals:**

- **Offering the freed slot to the waiting list.** `lista_espera_service` is deliberately not wired in — see D5. It is future work with its own change.
- Changing `turno.estado`, its enum, or anything the professional sees. The professional's view of who confirmed is unchanged, per the product decision.
- Redesigning the `cancelar` / `reprogramar` sub-flows. A patient who answers those follows the path that already exists, untouched.
- Escalating anything other than the attendance reminder (no escalation for temporary reservations, waiting-list offers, or bookings).
- Notifying the professional that a turno was auto-cancelled. Out of scope; noted as a risk.

## Decisions

### D1 — Escalation state is three nullable timestamps, not a state column

The escalation is a three-step walk, and each step is represented by the instant it happened:

| Column | Meaning when non-`NULL` | Clock |
|---|---|---|
| `recordatorio_enviado_en` | the first reminder left the system | naive UTC |
| `asistencia_confirmada_en` | the patient answered `confirmar` (shipped in `46d5eb9`) | naive UTC |
| `segundo_aviso_enviado_en` | the final warning left the system | naive UTC |

The current step is **derived**, never stored:

```
asistencia_confirmada_en is not NULL          -> done, skip forever
recordatorio_enviado_en   is NULL             -> not reminded yet, not our business
segundo_aviso_enviado_en  is NULL             -> candidate for the second notice
otherwise                                     -> candidate for cancellation
```

Rejected: a `estado_escalado` enum column. It would be a second source of truth that can contradict the timestamps (`estado_escalado='avisado'` with `segundo_aviso_enviado_en IS NULL`), and it would need its own migration of legal transitions. Deriving the step makes the contradictory states unrepresentable rather than merely unlikely — the same reasoning C-27's D3 applied to `derivar_paso`.

Rejected: a new value in `turno_estado_enum`. The product decision is explicit that `estado` stays `CONFIRMADO` and the professional sees nothing new. A new enum value would leak into `calcular_disponibilidad`, `marcar_turnos_completados`, the metrics endpoints and the professional dashboard — everything that switches on `estado`.

### D2 — `recordatorio_enviado` gains an instant; the boolean stays

`marcar_recordatorio_enviado` (`notificacion_service.py:116`) sets `recordatorio_enviado = True` and nothing else. This change adds `recordatorio_enviado_en` and stamps it in the same place, in the same transaction.

Rejected: converting `recordatorio_enviado` from `bool` to a nullable timestamp. It is read as a boolean in `obtener_turnos_para_recordar`, in the metrics queries and in the test suite; the conversion buys one fewer column at the cost of touching every reader. Additive is the cheaper and safer shape, and it keeps the reminder job's own contract byte-identical.

**The backfill is `NULL`, and that is a decision, not an omission.** Every turno already carrying `recordatorio_enviado = TRUE` gets `recordatorio_enviado_en = NULL`, which by D1 means the escalation never starts for it. That is the fail-safe direction: we cannot time a reminder we did not stamp, and at MEDIUM governance an escalation we cannot time must not cancel anything. It self-heals within one reminder cycle — every reminder sent after deployment stamps the column.

### D3 — The two clocks: exactly one conversion, and it is the guard

This is the highest-risk detail in the change. The rule:

- **Durations use UTC and never convert.** `recordatorio_enviado_en + espera` and `segundo_aviso_enviado_en + gracia` are elapsed-time arithmetic between two audit stamps, compared against `_utcnow_naive()` (`turno_service.py:37`). Both operands are naive UTC; converting either one would be wrong, and the arithmetic is timezone-invariant anyway.
- **The guard converts, because it touches an agenda column.** The appointment's start is `datetime.combine(turno.fecha, turno.hora_inicio)` — **local** naive. Anything compared against it must go through `a_local()` first.

So `a_local()` appears in the escalation exactly once, wrapping the UTC stamp before it meets the agenda column:

```python
inicio_local    = datetime.combine(turno.fecha, turno.hora_inicio)   # local naive
arranque_local  = a_local(turno.recordatorio_enviado_en)             # UTC -> local naive
```

**What the wrong version does.** Writing `datetime.combine(turno.fecha, turno.hora_inicio) - _utcnow_naive()` reads the appointment as three hours later than it is (in UTC−3). A turno starting in 30 minutes looks 3.5 hours away, the fit guard passes, and the escalation starts a window it cannot finish — cancelling a turno minutes before, or after, the patient was due to arrive. That is the exact failure `app/tiempo.py` was written to prevent.

**An adjacent instance of the same bug already exists and is left alone.** `marcar_turnos_completados` (`turno_service.py:380-384`) compares `datetime.combine(turno.fecha, turno.hora_fin)` against `_utcnow_naive()`, so in UTC−3 it marks turnos `COMPLETADO` three hours early. It is real, it is pre-existing, and fixing it here would widen the blast radius of a change that already auto-cancels appointments. Recorded as OQ-2 so it is not rediscovered by accident.

### D4 — The fit guard is evaluated once, against the first reminder's instant

Requirement, from the product decision: **never auto-cancel when the full escalation window does not fit before the turno starts.** If it does not fit, do not run the escalation for that turno at all — not the second notice either.

The guard is a predicate on values that never change after the first reminder:

```
a_local(recordatorio_enviado_en) + espera + gracia  <=  datetime.combine(fecha, hora_inicio)
```

Evaluating it against `recordatorio_enviado_en` rather than against "now" is what makes it stable. A guard written as `ahora_local() + espera + gracia <= inicio_local` would be *true* on the run that sends the second notice and *false* on the run that would cancel — leaving the patient warned that their turno will be cancelled, and then not cancelling it. The window either fits from the start or the turno is never escalated; there is no half-escalated state.

A second, cheaper guard sits on the cancellation step alone: **never cancel a turno whose start has already passed** (`ahora_local() >= inicio_local`). It is redundant while the job runs on schedule and load-bearing when it does not — a job that was down for six hours must not wake up and cancel appointments that are already underway or over. `marcar_turnos_completados` owns those.

### D5 — Auto-cancel releases the slot to the pool and does **not** consult the waiting list

**Product decision, fixed:** the slot goes back to the pool and whoever asks first takes it. Offering it to the waiting list is a separate future change. Rationale: this change already auto-cancels real patients' appointments, so the blast radius stays small.

Two consequences worth stating precisely, because both are non-obvious from the outside:

**"Returns to `DISPONIBLE`" is satisfied by `CANCELADO`, not by writing `DISPONIBLE`.** Availability in this codebase is computed, not stored: `calcular_disponibilidad` (`availability_service.py:63-70`) generates the professional's slots and subtracts only the turnos in `CONFIRMADO` or `RESERVADO_TEMPORAL`. A `CANCELADO` turno is invisible to it, so the slot reappears in the very next availability query. The partial unique index `uq_turno_active_slot` (`models/turno.py:97`) covers only the active states, so the `CANCELADO` row does not block a fresh booking of the same slot either. Writing `estado = 'DISPONIBLE'` on the existing row would instead **destroy the audit trail** of who lost the turno and why — precisely what a MEDIUM-governance automatic cancellation must keep.

**The escalation cannot reuse `cancelar_turno` as it stands.** `cancelar_turno` (`turno_service.py:397`) ends by calling `evaluar_lista_espera`, which is exactly what this decision forbids. The fix is to extract the shared core rather than to fork the function:

- `_cancelar_turno_core(db, profesional_id, turno_id)` — lock the row `FOR UPDATE`, validate it is `CONFIRMADO`, set `CANCELADO`, delete the Google Calendar event best-effort. Patrón A: no commit.
- `cancelar_turno` = core + `evaluar_lista_espera` (unchanged from the caller's point of view).
- `cancelar_turno_por_falta_de_confirmacion` = core only, plus the escalation-specific guards from D4.

The asymmetry — a manual cancellation feeds the waiting list, an automatic one does not — is deliberate but is a genuine wart, recorded under Risks.

### D6 — Send first, stamp second; cancel first, notify second

The two steps fail in opposite directions, so they are ordered in opposite ways.

**Second notice: send to Telegram, then stamp `segundo_aviso_enviado_en`, then commit.** If the send fails, nothing is stamped and the next run retries — the same shape `marcar_recordatorio_enviado` already uses. The residual hole is a crash between a successful send and the commit, which re-sends the warning on the next run. Accepted deliberately: **a duplicate warning is recoverable by the patient; an un-warned cancellation is not.**

**Cancellation: commit the state change, then notify best-effort.** The database is the source of truth — the same rule `cancelar_turno` already states for its Calendar deletion. Notifying first would risk telling a patient their turno was cancelled when it was not. A failed notification is logged at `ERROR` and not retried: once the turno is `CANCELADO` it falls out of the candidate query, so there is no second attempt. That is a known, accepted hole (Risks).

**Idempotency, stated as a property rather than hoped for.** Each transition (a) requires its predecessor stamp to be non-`NULL`, (b) requires its own stamp to be `NULL`, and (c) writes its own stamp under `SELECT FOR UPDATE` in the same transaction that reads it. Two concurrent job runs therefore serialise on the row lock and the second one re-reads a stamp that is already set. The cancellation adds its own belt: `_cancelar_turno_core` raises `TurnoYaCanceladoError` on anything that is not `CONFIRMADO`, so a second attempt is a no-op rather than a second cancellation. The one thing not protected by the database is the Telegram send itself, because it is not transactional — that is the D6 trade-off above and nothing else.

**Partial failure mid-batch** follows the existing scheduler shape: commit per professional, `try/except` per professional and per turno (`scheduler/jobs.py:144-172`). One patient's failed send does not roll back another patient's cancellation, and one professional's exception does not abort the batch.

**Recovering a wrongly cancelled turno.** Nothing is deleted: the row keeps `paciente_id`, its `TurnoDestinatario` rows, and the full escalation trail (`recordatorio_enviado_en` set, `segundo_aviso_enviado_en` set, `asistencia_confirmada_en` `NULL`) — which is the evidence of *why* it was cancelled. The slot is bookable again immediately, so recovery is re-booking the same patient into the same slot through the normal path; that produces a new turno row and a new Calendar event. Un-cancelling in place is deliberately **not** offered: the Calendar event is already gone and another patient may have taken the slot in the meantime, so an in-place revival would be reviving a slot that no longer belongs to anyone.

### D7 — Intervals are Pydantic Settings, never constants

Project hard rule: *"NUNCA hardcodear configuración (URLs, tokens, tiempos de expiración)."* Three new settings, named and defaulted alongside the existing scheduler configuration in `app/config.py`:

| Setting | Env var | Default | Meaning |
|---|---|---|---|
| `asistencia_espera_horas` | `ASISTENCIA_ESPERA_HORAS` | `2` | How long the patient has to answer the first reminder before the final warning is sent. The proposal's "one or two hours"; the upper bound is the default because it is the one that chases the patient less. |
| `asistencia_gracia_horas` | `ASISTENCIA_GRACIA_HORAS` | `1` | How long the patient has to answer the final warning before the turno is cancelled. The proposal's "next hour". |
| `asistencia_job_interval_minutos` | `ASISTENCIA_JOB_INTERVAL_MINUTOS` | `5` | How often the escalation job runs. Matches `completado_job_interval_minutos`; the windows are measured in hours, so a five-minute granularity is well inside the noise. |

Hours rather than minutes because both values are stated in hours by the product owner and no known use case needs sub-hour precision. They are declared with defaults, so a deployment that sets nothing still starts — consistent with the `configuration-management` spec's "optional variables use their documented default".

### D8 — A kill switch, defaulted off

`asistencia_escalado_habilitado: bool = False` (`ASISTENCIA_ESCALADO_HABILITADO`). The job is always registered; when the flag is off it logs once and returns without reading a single turno.

At MEDIUM governance, for a feature whose failure mode is *"wipes a patient's agenda"*, rollback must not require a code revert and a redeploy. With the flag, rollback is an environment variable and a restart. Defaulting to `False` means the change ships inert and is switched on deliberately after the live verification in `tasks.md` §11 — which is the point at which somebody has actually watched it cancel a test turno and not a real one.

Rejected: gating on the interval (setting it to zero or a huge number). It disables the job by accident-prone arithmetic rather than by intent, and it reads as a tuning value rather than as a switch.

### D9 — The job lives in `scheduler/jobs.py`, the logic does not

`jobs.py` gets `_escalar_confirmaciones_job` in the shape of its four siblings: read `Settings`, open a session if none was injected, iterate `Profesional where is_active`, commit per professional, `logger.exception` per failure. The job is plumbing and is tested through the same seam the others use (the injected `session` parameter).

The decision logic goes into a new `app/services/escalado_service.py` and is written as **pure functions over values**, not over the session:

- `escalado_encaja_antes_del_turno(recordatorio_enviado_en, fecha, hora_inicio, espera, gracia) -> bool` — D4's guard.
- `paso_de_escalado(turno_stamps, ahora_utc, espera, gracia) -> Paso` — D1's derivation, returning `NADA` / `SEGUNDO_AVISO` / `CANCELAR`.

Both are total functions of their arguments with no I/O, which is what makes the timezone arithmetic and the window boundaries testable without a database, a scheduler or a Telegram mock. Given how much of this change's risk is concentrated in arithmetic (D3, D4), that seam is the point: the boundary cases — the window that fits by one minute, the window that misses by one minute, the reminder stamped at 22:00 local — are unit tests over pure values, and the service and job layers only have to be tested for wiring.

The second notice's text is a new `format_segundo_aviso_mensaje` in `telegram_service.py`, next to `format_recordatorio_mensaje`. It reuses `format_recordatorio_keyboard` unchanged: the three buttons already emit the `cmd:*` vocabulary the orquestador routes (C-27's D4), so the final warning's buttons work on the day it is written, with no n8n change. **The escalation therefore requires no new n8n node at all** — the only workflow-side work is the cancellation notice, which is an outbound message with no callback.

## Risks / Trade-offs

**An automatic cancellation is invisible to the professional until they look at their agenda.** → Accepted for this change and explicitly out of scope; the row carries a complete audit trail (D6) so the *why* is always answerable. If professionals report being surprised, notifying them is a small follow-up: the recipient machinery (`TurnoDestinatario`) already exists.

**A failed cancellation notice is never retried.** → The turno leaves the candidate query the moment it is `CANCELADO`, so the patient can arrive at a turno that no longer exists. Logged at `ERROR` with the turno id. Mitigated in practice by the fact that the patient has already ignored two messages on that same chat, which is weak evidence that the chat is reachable. A `cancelacion_notificada_en` stamp plus a retry sweep is the obvious fix and is deliberately not built here — it is a fourth timestamp and a second job for a failure mode that has not been observed.

**A crash between sending the final warning and committing its stamp re-sends the warning.** → Deliberate, per D6: chosen over the alternative ordering, which risks cancelling a turno whose warning never arrived.

**Manual cancellation feeds the waiting list; automatic cancellation does not.** → Direct consequence of the product decision (D5), and a genuine inconsistency: two ways of freeing the same slot behave differently. Contained by routing both through `_cancelar_turno_core`, so the difference is one explicit call site rather than two divergent implementations. The waiting-list integration is recorded as future work; when it lands it is a one-line addition at a known place.

**Turnos reminded before this deploys never escalate.** → D2's `NULL` backfill. Fail-safe and self-healing within one reminder cycle. The cost is one cycle of the old behaviour after deployment; the alternative — backfilling a guessed instant — would let the job cancel turnos on a timestamp nobody measured.

**The escalation and the reminder job read the same rows.** → `obtener_turnos_para_recordar` takes `SELECT FOR UPDATE` on its candidates and the escalation does the same, so the two serialise rather than interleave. They cannot in fact collide on the same turno — the reminder job filters `recordatorio_enviado == False` and the escalation requires `recordatorio_enviado_en IS NOT NULL` — but they will contend on the lock, and the escalation's interval (5 min) is twelve times the reminder's (60 min), so the contention is one-sided and brief.

**A patient who answers `cancelar` or `reprogramar` mid-escalation.** → No special handling, by construction: both paths move the turno out of `CONFIRMADO`, and every escalation step requires `CONFIRMADO`. The turno silently stops being a candidate. This is worth an explicit scenario in the spec precisely because it is handled by absence rather than by code, and absence is what a later refactor deletes.

**The whole feature is inert until somebody sets an environment variable.** → Deliberate (D8), and the reason `tasks.md` ends with enabling it rather than beginning with it. The risk it creates is the opposite one: a change believed to be live that is not. Task 11.4 makes the flag flip an explicit, evidenced step.

## Migration Plan

One migration, `down_revision = 'c29b4e7a2f10'` (the slice-1 migration already on `main`), adding two columns to `turno`:

- `recordatorio_enviado_en TIMESTAMP NULL`
- `segundo_aviso_enviado_en TIMESTAMP NULL`

Both nullable with no server default, so the migration is instant on an existing table and safe with reminders in flight: a turno mid-cycle simply looks like one that has not been stamped, which by D2 means it is not escalated. Nothing else is touched — not `turno_estado_enum`, not `uq_turno_active_slot`, not any existing index. Downgrade drops the two columns; `asistencia_confirmada_en` belongs to `c29b4e7a2f10` and is not this migration's to remove.

Deployment order:

1. Migration.
2. Backend, with `ASISTENCIA_ESCALADO_HABILITADO` unset (`False`). The job registers and no-ops; `marcar_recordatorio_enviado` starts stamping `recordatorio_enviado_en` immediately, so the data the escalation needs begins accumulating before the escalation exists.
3. Wait at least one reminder cycle (`RECORDATORIO_JOB_INTERVAL_MINUTOS`, default 60), so there is a stamped population to verify against.
4. Live verification (`tasks.md` §11) against a turno created for the purpose, with the intervals temporarily shortened.
5. Flip `ASISTENCIA_ESCALADO_HABILITADO=true`.

Rollback at any point after step 2 is unsetting the flag and restarting. Rolling the migration back is not required to stop the behaviour and should not be the first response to an incident — the columns are inert without the flag, and dropping them destroys the audit trail of whatever went wrong.

No n8n deployment is required (D9). The cancellation notice is sent by the backend through `telegram_service`, on the same path the reminder already uses.

## Open Questions

Four questions were open in the proposal. All four were answered by the product owner on 2026-08-12 and are recorded here as closed, not deleted, because the reasoning constrains the design:

- ~~**Does the automatic cancellation release the slot as `DISPONIBLE` or offer it to the waiting list?**~~ **RESOLVED — released to the pool, no waiting list.** See D5, including why "released to the pool" is spelled `CANCELADO` in this codebase. Waiting-list integration is explicit future work.
- ~~**Are the intervals (1–2h, 1h) configuration or constants?**~~ **RESOLVED — configuration**, per the project hard rule. See D7 for names and defaults.
- ~~**What happens if the second notice would fall after the turno's start time?**~~ **RESOLVED — the escalation does not run for that turno at all.** See D4; this is the change's main safety rail and it has its own spec requirement and scenarios.
- ~~**Can the professional see who confirmed and who did not?**~~ **RESOLVED — unchanged.** `estado` stays `CONFIRMADO`, the professional's view is untouched. The confirmation is data, not a state.

Still open:

- **OQ-1 — Should the professional be notified when a turno is auto-cancelled?** Out of scope here (Non-Goals), but it is the most likely first complaint once the flag is on. Deferred until there is a real user asking, because the answer determines the channel and this project has exactly one working channel today.
- **OQ-2 — When is the `marcar_turnos_completados` timezone bug fixed?** `turno_service.py:380-384` compares a local agenda column against `_utcnow_naive()` and marks turnos `COMPLETADO` three hours early in UTC−3 (D3). Confirmed by reading, not yet by a failing test. Deliberately not fixed here — it deserves its own change with its own regression suite rather than a drive-by inside a change that auto-cancels appointments.
- **OQ-3 — Is two hours the right wait?** The proposal says "one or two"; D7 picks two as the default because it chases the patient less. It is configuration, so the question is answered by operating it, not by arguing about it. Worth revisiting after the first month of real escalations.
