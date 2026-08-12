# Tasks — c-28-sender-email-recordatorios

> **Precondition: C-27 must be archived before group 1 starts.** It is not, as of writing:
> tasks 8.2–8.7, 9.1–9.3 and 10.2 are still open there. This change edits the confirmation
> message C-27's spec constrains and the workflow file C-27 is still verifying end-to-end.
> Planning is complete now; implementation waits. Group 0.1 is the gate.
>
> Strict TDD is active for backend work: RED before GREEN, triangulate, refactor green.
> Groups 1–7 are backend; group 8 is n8n; groups 9–10 are verification and docs.
>
> **Order is the proposal's own constraint**: the sender ships before the choice. Offering
> a channel that delivers nothing is the defect this change exists to remove, so groups 3–5
> (delivery) precede group 6 and group 8 (choice).
>
> Backend ships before the workflow (design § Migration Plan): the workflow calls an endpoint
> that must already exist, on the confirmation path of every booking.

## 0. Preconditions and baseline

- [ ] 0.1 Confirm C-27 is archived (`openspec list --json` no longer shows it as active, and `openspec/specs/telegram-turno-confirmation-flow/spec.md` exists). If it is not, STOP — this change's delta spec modifies a requirement that C-27 introduces, and both would be editing the same workflow nodes.
- [ ] 0.2 Resolve **OQ-1** (design § Open Questions): decide the SMTP relay for development/tests and for production, and record the decision in `design.md`. This is implementation-blocking for group 9, not for groups 1–8, which mock the transport.
- [ ] 0.3 Capture the backend test baseline (`cd backend && pytest --tb=no -q`) and record pass/fail counts and the exact IDs of any pre-existing failures, so group 7 has something to diff against. Do NOT fix pre-existing failures — report them.

## 1. Migration — `turno_destinatario` gains its notification ledger

- [ ] 1.1 Write a failing test asserting a `TurnoDestinatario` created without an explicit flag has `notificar` true and `enviado_en` `None` (spec: "Un destinatario nuevo notifica por defecto", "Filas existentes arrancan sin entregar").
- [ ] 1.2 Add `notificar` (`BOOLEAN NOT NULL DEFAULT TRUE`) and `enviado_en` (`TIMESTAMP NULL`) to `app/models/turno_destinatario.py`, and generate the Alembic migration (design § D2, § D3).
- [ ] 1.3 Write a failing test asserting the migration is a no-op for existing behaviour: a destinatario row created before the flags existed (i.e. inserted without them) still delivers — `notificar` backfills to `TRUE` through the server default.
- [ ] 1.4 Run the migration up and down against the test database and confirm both directions are clean; `downgrade` drops both columns and leaves the table usable.
- [ ] 1.5 Run the existing `turno_destinatario` and `captura_service` tests to green — this table is on the read path of `obtener_captura_pendiente` and `obtener_turnos_activos` (`captura_service.py:85`, `:165`).

## 2. SMTP configuration

- [ ] 2.1 Write a failing test: `Settings()` starts with no `SMTP_*` variables present, `smtp_host` is `""`, and the documented defaults hold for port, TLS mode and timeout (spec: "Startup without SMTP variables"; `configuration-management`'s optional-variable contract).
- [ ] 2.2 Add `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_from`, `smtp_use_tls`, `smtp_timeout` to `app/config.py` with those defaults (design § D9). No value is hardcoded anywhere else.
- [ ] 2.3 Add the `SMTP_*` names to `.env.example` with empty values and a one-line comment each. Verify by inspection that no real credential is committed and that `.env` is still git-ignored.

## 3. Email sender — the transport

- [ ] 3.1 Write a failing test: with the SMTP transport mocked, a successful send returns `True` and the message carries the configured `smtp_from`, the recipient address, a subject and a plain-text body.
- [ ] 3.2 Write a failing test: an exception from the transport (connection refused / auth rejected / relay error) returns `False` and logs the failure. Triangulate with at least two distinct exception types.
- [ ] 3.3 Write a failing test: the failure log contains no SMTP password (spec: "The failure log does not disclose the credentials"). Assert on the captured log text, not on the code.
- [ ] 3.4 Write a failing test: the blocking send is executed off the event loop — assert the sender goes through `run_in_threadpool` (or that the blocking function is a plain `def`, never `async def`), per the project hard rules and design § D1.
- [ ] 3.5 Create `app/services/email_service.py`: a synchronous `def` performing the `smtplib` send with an explicit timeout, plus an async wrapper that calls it via `run_in_threadpool` and returns `True`/`False`. No new runtime dependency (stdlib only).
- [ ] 3.6 Write a failing test for the body formatter: it states the patient name, the date, the start time and the professional, and tells the patient to use the bot to cancel or reschedule (spec: "Body content"). Triangulate with a turno whose professional is missing — the reminder must still be sendable, matching how `enviar_recordatorio_telegram` degrades (`notificacion_service.py:88-96`).
- [ ] 3.7 Add `format_recordatorio_email` next to the transport, returning subject and plain-text body. No Telegram markup, no HTML (design § D6).
- [ ] 3.8 Run group 3 to green.

## 4. Fan-out — `enviar_recordatorio` over every recipient

- [ ] 4.1 Write a failing test: a turno with a `TELEGRAM` and an `EMAIL` recipient, both eligible, sends on both channels (spec: "A turno with two channels is delivered on both"). This is the test the current `break` at `notificacion_service.py:71` cannot pass.
- [ ] 4.2 Write a failing test: a turno with only an `EMAIL` recipient sends the email and attempts no Telegram delivery.
- [ ] 4.3 Write a failing test: a recipient with `notificar = FALSE` is not delivered to.
- [ ] 4.4 Write a failing test: a turno with no eligible recipient on any channel logs a warning naming the turno and returns `True` — the branch that moves up out of `enviar_recordatorio_telegram` (`notificacion_service.py:72-78`), now stated over all channels rather than over Telegram.
- [ ] 4.5 Write a failing test: on success, each delivered recipient gets `enviado_en` stamped, and a recipient that already carries one is skipped entirely (no second send).
- [ ] 4.6 Write the **spam-pump regression test**, the one that justifies design § D3: Telegram succeeds and email fails; assert `enviado_en` is set on `TELEGRAM` only and the fan-out returns `False`; then run the fan-out a second time and assert the email is retried and **exactly one** Telegram message was ever sent.
- [ ] 4.7 Write a failing test: the fan-out returns `False` when every attempted delivery fails, leaving the turno retryable.
- [ ] 4.8 Implement `enviar_recordatorio` in `notificacion_service.py` (design § D4): select recipients with `notificar = TRUE AND enviado_en IS NULL`, dispatch per channel, stamp on success, return `True` only when nothing eligible remains undelivered. Patrón A — flush, never commit.
- [ ] 4.9 Implement `enviar_recordatorio_email(turno, destinatario)` in `notificacion_service.py`, mirroring `enviar_recordatorio_telegram`'s `True`/`False` contract and delegating to `email_service`.
- [ ] 4.10 Remove the "no `TELEGRAM` recipient → warn and return `True`" branch from `enviar_recordatorio_telegram`, leaving its signature and its success contract untouched. Confirm the existing Telegram tests still pass or are updated to the new ownership of that branch.
- [ ] 4.11 Write a failing test for the unconfigured relay (spec: "No SMTP host configured"): with `smtp_host` empty, a turno with an `EMAIL` recipient logs a warning naming the turno, stamps the recipient as delivered without attempting a send, and does NOT cause a retry. Triangulate with the same turno also holding a `TELEGRAM` recipient — the Telegram reminder is sent and the turno is marked as reminded.
- [ ] 4.12 Implement the skip branch (design § D5) and run group 4 to green.

## 5. Both engines go through the fan-out

- [ ] 5.1 Write a failing test: a professional with **no** `telegram_bot_token` and a turno with an `EMAIL` recipient still gets the email sent through `recordatorio_service` — the early return at `recordatorio_service.py:60-65` currently skips them entirely.
- [ ] 5.2 Swap `recordatorio_service._procesar_profesional` to call `enviar_recordatorio`, turning the missing-token early return into a per-channel skip. Keep the `RecordatorioError` accounting and the per-professional commit intact.
- [ ] 5.3 Swap `scheduler/jobs.py::_ejecutar_enviar_recordatorios` (`jobs.py:156`) to call `enviar_recordatorio`, preserving its per-professional commit and its per-turno try/except.
- [ ] 5.4 Write a failing test asserting both engines apply the same channel selection for the same turno (spec: "Both engines use the same fan-out"). Grep the repo afterwards and confirm no caller outside `notificacion_service` still calls a channel sender directly.
- [ ] 5.5 Run groups 4 and 5 to green together.

## 6. The channel-choice endpoint

- [ ] 6.1 Write a failing test: `PUT /turnos/{id}/canales-recordatorio` with `{"canales": ["TELEGRAM", "EMAIL"]}` on a `CONFIRMADO` turno marks both recipients for notification and returns the resulting recipient set through a declared `response_model`.
- [ ] 6.2 Write a failing test: `{"canales": ["EMAIL"]}` marks the `EMAIL` recipient and unmarks the `TELEGRAM` one — and the turno still appears in `GET /turnos/activos` for that chat (spec: "Muting Telegram does not remove the turno from the bot"). This is the test that proves design § D2's reason for existing.
- [ ] 6.3 Write a failing test: calling twice with the same body produces identical flags (idempotence).
- [ ] 6.4 Write a failing test: an empty `canales` list returns `422` and modifies nothing.
- [ ] 6.5 Write a failing test: a turno that is not `CONFIRMADO` is refused and nothing is modified.
- [ ] 6.6 Write a failing test: a valid `X-API-Key` with no JWT is accepted (`FlexibleProfesionalDep`), and a turno belonging to a different professional is not reachable.
- [ ] 6.7 Add the request/response schemas to `app/schemas/turno.py` and the service function that flips `notificar` per channel, scoped by `profesional_id` (design § D8). Patrón A — the router commits.
- [ ] 6.8 Add the endpoint to `app/routers/turnos.py` with an explicit `response_model` and full type hints. Run group 6 to green.

## 7. Backend regression

- [ ] 7.1 Run the full backend suite and diff against the 0.3 baseline — no new failures, nothing newly skipped.
- [ ] 7.2 Confirm by inspection (`git diff --stat`) that `turno_service.confirmar_turno`, `_upsert_destinatarios_confirmacion` and `ConfirmarTurnoRequest` were not modified. This change reads the rows they already write (design § Non-Goals).
- [ ] 7.3 Verify the endpoint end-to-end against the running stack with a real `X-API-Key`: set both channels, then email only, and read the `turno_destinatario` rows back from the database to confirm the flags. Note the dev backend is reachable on host port `18000`, not `8000` (recorded in C-27 task 5.3).

## 8. n8n — the corrected message and the channel choice

- [ ] 8.1 Rewrite `Telegram - Turno Confirmado` in `sub-flujo-crear-turno.json`: it currently ends with "Te vamos a recordar por Telegram antes del turno", which was true only because no other channel delivered. It must name every channel that will actually carry the reminder, and say Telegram only when no email was captured (spec: the two announcement scenarios).
- [ ] 8.2 Attach the channel keyboard to that message **only when an email was captured** — `Code - Evaluar Confirmacion` already knows whether `email` was supplied. Callbacks follow the existing `cmd:*` vocabulary: `cmd:canal:<turno_id>:telegram|email|ambos` (design § D7, `n8n-workflows/README.md` § "Vocabulario de callbacks").
- [ ] 8.3 Add the `cmd:canal:*` route to `orquestador.json`'s `Normalizar Comando` and `Switch Comando`, dispatching to a handler that calls `PUT /turnos/{id}/canales-recordatorio` and answers a short confirmation to the patient.
- [ ] 8.4 Every new HTTP node sets `authentication: "genericCredentialType"` + `genericAuthType: "httpHeaderAuth"` as sibling string props, `neverError: true` + `fullResponse: true`, and every expression parameter starts with `=`. Telegram nodes use the `telegramApi` credential named `Telegram account`; HTTP nodes use `Profesional API Key`. All four of these have already broken this repo (`n8n-workflows/README.md` §§ 2–3, C-27 task 7.11).
- [ ] 8.5 Re-verify the untouched routing paths after the `Switch Comando` change: `HH:MM`, `1–20` and `DD/MM/AAAA` must behave exactly as before. C-27 task 6.4's lesson — a new output on the busiest switch is where regressions hide.
- [ ] 8.6 Validate both JSON files: parse validity, full node-graph reachability, switch/IF output-array counts matching rule counts, and `node -e` syntax checks on every new jsCode node. Structural validation proves well-formedness, never behaviour (C-27 design § D3) — group 9 is what proves behaviour.

## 9. Live verification

- [ ] 9.1 Smoke-test the SMTP sender once against the relay chosen in 0.2: a real reminder email arrives, with the right subject and body. This is the only task that touches a live relay — the suite mocks it (design § OQ-2).
- [ ] 9.2 Push the updated workflows to the live instance and confirm the credentials resolved by name rather than landing orphaned. The n8n public API rejects the repo's full workflow shape; reduce the payload to `name`/`nodes`/`connections`/`settings` and keep the repo files' full shape (C-27 task 8.1).
- [ ] 9.3 Book end-to-end supplying an email: the confirmation message names both channels and shows the keyboard.
- [ ] 9.4 Book end-to-end without an email: the message names Telegram only and shows no keyboard.
- [ ] 9.5 Press "email only" and confirm the database flags, then confirm `/cancelar` still lists that turno for the chat — the design's load-bearing claim, verified against a real bot rather than a test double.
- [ ] 9.6 Force the reminder for a turno with both channels and confirm both arrive, exactly once each, and that `turno.recordatorio_enviado` flips only after both.
- [ ] 9.7 Force the reminder with a deliberately broken SMTP password and confirm the Telegram reminder arrives once and is **not** repeated on the next job run — the spam-pump check, live.

## 10. Documentation

- [ ] 10.1 Correct `n8n-workflows/README.md:203`: the warning "Email: almacenado pero no enviado" is now false. Replace it with what is true — both channels deliver, the patient chooses on the confirmation message, and email requires `SMTP_*` in the backend environment or it is skipped with a warning.
- [ ] 10.2 Document the `cmd:canal:*` callbacks in the README's callback vocabulary table, next to the cancel ones.
- [ ] 10.3 Record in the README's "Dos motores de recordatorio" section that per-recipient `enviado_en` now de-duplicates delivery per channel, not only per turno — the two engines' overlap is narrower than the section currently describes.
- [ ] 10.4 Note in C-27's `tasks.md` 10.3 that the email limitation it recorded is discharged by this change, so the two documents do not contradict each other.
