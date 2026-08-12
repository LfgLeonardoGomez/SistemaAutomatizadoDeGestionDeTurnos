# Tasks — c-29-confirmacion-asistencia-escalado

> Strict TDD is active for backend work: RED before GREEN, triangulate, refactor green.
> Governance is **MEDIUM** — this change cancels real patients' appointments automatically.
> Group 2 is **already delivered** on `main` (commit `46d5eb9`) and is recorded here so the
> checklist reflects reality rather than restating work as pending.
> Groups 4–6 are pure arithmetic and carry most of the risk (design § D3, D4); they are
> unit-testable without a database, a scheduler or a Telegram mock, and should be written first.
> Nothing ships enabled: the feature flag stays off until group 11 (design § D8).

## 1. Preconditions and baseline

- [ ] 1.1 Confirm C-27 is archived before starting group 7 onward. The proposal declares `Depende de: C-27 archivado` and C-27 still has ~10 open tasks (its groups 8 and 9). Groups 3–6 are backend-only and independent of it; record the gate rather than silently crossing it.
- [ ] 1.2 Capture the backend test baseline (`cd backend && pytest --tb=no -q`) and record the pass/fail counts and the exact ids of any pre-existing failures, so group 10's regression check has something to diff against. Do **not** fix pre-existing failures — report them.
- [ ] 1.3 Confirm migration `c29b4e7a2f10` is applied in the target database, since this change's migration chains off it.

## 2. Slice 1 — record the patient's answer (ALREADY DELIVERED)

> Delivered by commit `46d5eb9` ("feat(c-29): registra la confirmacion de asistencia del paciente"),
> 5 files, +319/−3. Verified against the commit contents; no re-implementation is needed.

- [x] 2.1 Add `turno.asistencia_confirmada_en` as a nullable timestamp, with `NULL` meaning "did not answer" and the instant enabling the escalation window. **`46d5eb9` — `backend/app/models/turno.py:53-62`, `DateTime(), nullable=True`, documented in place as data and not as a state.**
- [x] 2.2 Write the Alembic migration for the column. **`46d5eb9` — `c29b4e7a2f10`, `down_revision = c27a1b3d9e40`; existing rows left `NULL`; `uq_turno_active_slot`, `turno_estado_enum` and every index untouched.**
- [x] 2.3 Make `confirmar_asistencia_turno` actually seal the mark — it validated ownership and state and returned the turno unmodified. **`46d5eb9` — `backend/app/services/turno_service.py:530-559`, stamps `_utcnow_naive()` and flushes; Patrón A preserved (no commit in the service).**
- [x] 2.4 Seal the mark **once only**: Telegram redelivers updates and the patient can tap twice; overwriting would push the escalation window forward on every tap. **`46d5eb9` — guarded by `if turno.asistencia_confirmada_en is None`.**
- [x] 2.5 Keep `turno.estado` at `CONFIRMADO` and the professional's view unchanged. **`46d5eb9` — no state write; asserted by `test_el_estado_no_cambia`.**
- [x] 2.6 Cover the behaviour with tests. **`46d5eb9` — `backend/tests/test_confirmacion_asistencia.py`, 178 lines / 8 tests: the seal, its idempotency, the untouched state, persistence across sessions, and the three pre-existing guards (cancelled turno, unknown turno, other professional's turno).**
- [x] 2.7 Wire the orquestador to call `PUT /turnos/{id}/confirmar-asistencia` before replying, with `neverError` + `fullResponse` so a `404`/`409` surfaces as a message instead of silence. **`46d5eb9` — `n8n-workflows/orquestador.json`: new `HTTP - PUT Confirmar Asistencia` → `Code - Evaluar Asistencia` → renamed `Telegram - Respuesta Asistencia`; `Code - Evaluar Asistencia` reads `chat_id` via the named-node pattern and branches on `statusCode` for 2xx / 404 / 409 / other.**

## 3. Configuration — RED then GREEN

- [ ] 3.1 Write a failing test: the backend starts with none of `ASISTENCIA_ESPERA_HORAS`, `ASISTENCIA_GRACIA_HORAS`, `ASISTENCIA_JOB_INTERVAL_MINUTOS`, `ASISTENCIA_ESCALADO_HABILITADO` set, and the settings hold `2`, `1`, `5`, `False`. Follow the existing style in `backend/tests/test_config.py`.
- [ ] 3.2 Write a failing test: each variable is overridable from the environment, and a non-integer value for an interval raises a validation error naming that variable.
- [ ] 3.3 Add the four settings to `backend/app/config.py`, alongside the existing scheduler settings (design § D7, D8). Hours, not minutes, for the two windows — both are stated in hours by the product owner.
- [ ] 3.4 Run group 3 to green.

## 4. Schema — the escalation timestamps

- [ ] 4.1 Write a failing test: a newly created `Turno` has `recordatorio_enviado_en is None` and `segundo_aviso_enviado_en is None`.
- [ ] 4.2 Add both columns to `backend/app/models/turno.py` as `DateTime(), nullable=True`, documenting in place that they are naive **UTC** audit stamps (like `creado_en`), not agenda columns. Leave `recordatorio_enviado` a `bool` — it is read as one in `obtener_turnos_para_recordar`, in the metrics queries and across the suite (design § D2).
- [ ] 4.3 Write the Alembic migration with `down_revision = 'c29b4e7a2f10'`, adding both columns nullable with no server default. Document in the docstring that the `NULL` backfill is deliberate: a turno already reminded before this deploy is never escalated, because a reminder we did not stamp cannot be timed, and at MEDIUM governance the fail-safe direction is to cancel nothing. Do not touch `turno_estado_enum`, `uq_turno_active_slot` or any index. `downgrade` drops only these two columns — `asistencia_confirmada_en` belongs to `c29b4e7a2f10`.
- [ ] 4.4 Run group 4 to green and confirm the migration applies and reverts cleanly against a real PostgreSQL.

## 5. Stamp the first reminder's instant

- [ ] 5.1 Write a failing test: `marcar_recordatorio_enviado` sets `recordatorio_enviado = True` **and** `recordatorio_enviado_en` to the current naive-UTC instant, in the same transaction.
- [ ] 5.2 Write a failing test (regression guard): `obtener_turnos_para_recordar` still selects exactly the same candidates as before — the reminder job's contract must not move. Assert the `recordatorio_enviado == False` filter specifically.
- [ ] 5.3 Stamp `recordatorio_enviado_en` in `notificacion_service.marcar_recordatorio_enviado`, using `_utcnow_naive` semantics and preserving Patrón A (no commit).
- [ ] 5.4 Run groups 4–5 plus the existing `test_notificacion_service.py` and `test_recordatorio_service.py` to green.

## 6. The escalation decision — pure functions, no I/O

> This is where the change's risk lives (design § D3, D4). Every case below is a total function
> of its arguments, so the boundaries get real tests instead of a mocked scheduler.

- [ ] 6.1 Write a failing test for `paso_de_escalado`: a turno with `asistencia_confirmada_en` set returns `NADA`, however long ago the reminder was sent.
- [ ] 6.2 Write a failing test: a turno with `recordatorio_enviado_en is None` returns `NADA` (the pre-deploy backfill case).
- [ ] 6.3 Write a failing test: reminder stamped, unconfirmed, no second notice yet, wait **not** elapsed → `NADA`; wait elapsed → `SEGUNDO_AVISO`. Assert the exact boundary (one minute short and one minute past), not a comfortable midpoint.
- [ ] 6.4 Write a failing test: second notice stamped, unconfirmed, grace **not** elapsed → `NADA`; grace elapsed → `CANCELAR`. Same boundary discipline.
- [ ] 6.5 Write a failing test for `escalado_encaja_antes_del_turno`: with the reminder stamped at a UTC instant, the turno's start built from `fecha` + `hora_inicio`, and `espera + gracia`, the guard is true when the window ends at or before the start and false when it ends after. Assert the exact boundary.
- [ ] 6.6 Write the test that catches the timezone bug this change is most likely to ship: a reminder stamped at `22:00` **local** (`01:00` UTC the next day) for a turno the following morning. Comparing the raw UTC stamp against the local agenda column shifts the appointment by the offset and lets a window through that does not fit. Assert the guard uses `a_local()` on the stamp before the comparison — i.e. that the answer matches the local-time reasoning, not the UTC one. Run it under a non-UTC `TIMEZONE`; a test under UTC proves nothing here.
- [ ] 6.7 Write a failing test: the guard's answer is stable across time — evaluated with two different "now" values it returns the same result, because it depends only on `recordatorio_enviado_en`. This is what prevents a turno being warned and then never cancelled (design § D4).
- [ ] 6.8 Implement `backend/app/services/escalado_service.py` with `paso_de_escalado` and `escalado_encaja_antes_del_turno` as pure functions over values (design § D9). Durations stay on the UTC clock and never convert; `a_local()` appears exactly once, wrapping `recordatorio_enviado_en` before it meets the agenda column.
- [ ] 6.9 Run group 6 to green and refactor. Confirm by inspection that no function in this module takes a session, a settings object or a turno ORM instance — values only.

## 7. Sending the final warning

> Requires C-27 archived (task 1.1): this touches the reminder's Telegram path.

- [ ] 7.1 Write a failing test: the final warning's text repeats the appointment and states that the turno will be cancelled if the patient does not answer within the grace period.
- [ ] 7.2 Write a failing test: the final warning carries the same inline keyboard as the first reminder, so its confirm / cancel / reschedule buttons work through the `cmd:*` routing C-27 already wired. No new n8n node is needed (design § D9) — assert the keyboard is the one `format_recordatorio_keyboard` produces.
- [ ] 7.3 Add `format_segundo_aviso_mensaje` to `telegram_service.py`, next to `format_recordatorio_mensaje`. Respect the 4096-character Telegram limit and use valid markdown.
- [ ] 7.4 Write a failing test: a successful send stamps `segundo_aviso_enviado_en`; a failed send stamps nothing, so the next run retries (design § D6).
- [ ] 7.5 Write a failing test: a turno whose `segundo_aviso_enviado_en` is already set receives no second warning, and the existing stamp is preserved.
- [ ] 7.6 Implement the send-then-stamp step in `escalado_service`, taking the row with `SELECT FOR UPDATE`, honouring Patrón A (no commit in the service), and resolving the recipient from `turno.destinatarios` on channel `TELEGRAM` — never from the patient.
- [ ] 7.7 Write a failing test for the recipient gap: a turno with no `TELEGRAM` recipient is skipped with a logged warning and is **not** escalated further, since a patient who cannot be warned must not be cancelled for not answering. Then implement it.
- [ ] 7.8 Run group 7 to green.

## 8. Automatic cancellation and slot release

> Highest-blast-radius group in the change. Implement it only with groups 4–7 green.

- [ ] 8.1 Write a failing test: cancelling through the escalation sets `estado = 'CANCELADO'` and does **not** call `evaluar_lista_espera` (design § D5 — the product decision explicitly keeps the waiting list out of this change). Assert the absence, do not assume it.
- [ ] 8.2 Write a failing test: after the automatic cancellation, the slot's `HH:MM` appears again in `calcular_disponibilidad` for that date, and a fresh booking of the same slot succeeds without tripping `uq_turno_active_slot`. This is what "returns to the pool" means in this codebase — availability is computed, not stored.
- [ ] 8.3 Write a failing test: the cancelled row keeps `paciente_id`, its `TurnoDestinatario` rows, `recordatorio_enviado_en` and `segundo_aviso_enviado_en`, with `asistencia_confirmada_en` still `NULL` — the audit trail of why it was cancelled (design § D6, recovery).
- [ ] 8.4 Write a failing test: a turno already `CANCELADO` is a no-op on a second pass, and no second notification is sent.
- [ ] 8.5 Write a failing test: a turno whose start time has already passed is not cancelled by the escalation, even when both windows have elapsed (design § D4, second guard).
- [ ] 8.6 Extract `_cancelar_turno_core` from `cancelar_turno` in `turno_service.py`: lock `FOR UPDATE`, validate `CONFIRMADO`, set `CANCELADO`, delete the Google Calendar event best-effort. Re-express `cancelar_turno` as core + `evaluar_lista_espera` so its behaviour is byte-for-byte unchanged for every existing caller.
- [ ] 8.7 Write a regression test proving 8.6 changed nothing for the manual path: a manual cancellation still evaluates the waiting list and still deletes the Calendar event.
- [ ] 8.8 Add `cancelar_turno_por_falta_de_confirmacion` = core + the escalation guards, without the waiting-list call. Patrón A: no commit.
- [ ] 8.9 Write a failing test: after cancelling, the patient's Telegram recipient receives a message saying the turno was cancelled for lack of an answer and how to book again; and a failed send leaves the turno `CANCELADO` with the failure logged at `ERROR` (design § D6 — commit first, notify second).
- [ ] 8.10 Implement the cancellation notice and run group 8 to green.

## 9. The scheduler job

- [ ] 9.1 Write a failing test: with `ASISTENCIA_ESCALADO_HABILITADO` false, the job reads no turno, sends nothing and cancels nothing (design § D8).
- [ ] 9.2 Write a failing test: with the flag on, the job iterates active professionals, commits per professional, and a failure on one professional is logged and rolled back without aborting the others — the shape the four existing jobs already use.
- [ ] 9.3 Write a failing test: a failure on one turno does not abort the remaining turnos of the same professional, and the job never propagates an exception into the scheduler.
- [ ] 9.4 Implement `_escalar_confirmaciones_job` in `backend/app/scheduler/jobs.py`, matching its siblings: optional injected `session` for testing, `Settings()` read at the top, `logger.exception` per failure, commit per professional. It must be `async` and must not block the event loop (`AsyncIOScheduler`).
- [ ] 9.5 Register the job in `init_scheduler` with `asistencia_job_interval_minutos`, `replace_existing=True`, and a log line naming the interval — matching the four existing registrations.
- [ ] 9.6 Run group 9 to green.

## 10. Regression and documentation

- [ ] 10.1 Run the full backend suite and diff against the 1.2 baseline: no new failures, nothing newly skipped.
- [ ] 10.2 Confirm by inspection that `obtener_turnos_para_recordar`, `run_recordatorios_para_todos`, `confirmar_turno` and `reservar_turno` were not modified — this change relies on them as they are.
- [ ] 10.3 Document the four new variables with their defaults and units in `.env.example`, `docker-compose.yml` (next to `COMPLETADO_JOB_INTERVAL_MINUTOS`), `backend/README.md` and `knowledge-base/08_arquitectura_propuesta.md` — the four places the existing optional variables already live.
- [ ] 10.4 Document the escalation walk where the reminder is already documented (`n8n-workflows/README.md`, "Dos motores de recordatorio"), including that the buttons on the final warning are the same `cmd:*` ones and that **no n8n change was required**, so nobody goes looking for a node that does not exist.
- [ ] 10.5 Record OQ-2 (the `marcar_turnos_completados` timezone bug, `turno_service.py:380-384`) where the next person will find it — as a follow-up change entry, not as a comment buried in a service.

## 11. Live verification, then enable

> Nothing here is a code change. The flag flips only after somebody has watched the
> escalation cancel a turno created for the purpose.

- [ ] 11.1 Deploy the migration and the backend with the flag **off**. Confirm the job logs its registration and takes no action.
- [ ] 11.2 Wait one reminder cycle and confirm `recordatorio_enviado_en` is being stamped on newly reminded turnos, and that pre-existing reminded turnos still carry `NULL`.
- [ ] 11.3 With the intervals temporarily shortened, run the full walk against a test turno on a real chat: reminder → no answer → final warning arrives with working buttons → no answer → turno cancelled → patient notified → slot reappears in availability and can be re-booked.
- [ ] 11.4 Run the two negative paths against real turnos: (a) a patient who confirms is never warned and never cancelled; (b) a turno whose window does not fit before its start time is never warned and never cancelled. (b) is the change's main safety rail — verify it explicitly, not by inference.
- [ ] 11.5 Restore the real intervals and set `ASISTENCIA_ESCALADO_HABILITADO=true`. Record the date, the values in effect, and the evidence from 11.3–11.4 in this file.
- [ ] 11.6 Watch the first real cycle and confirm the count of automatic cancellations is plausible against the count of unanswered reminders. If it is not, unset the flag and restart — that is the whole rollback (design § D8).
