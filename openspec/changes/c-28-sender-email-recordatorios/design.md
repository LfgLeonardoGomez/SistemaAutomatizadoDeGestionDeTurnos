# Design — c-28-sender-email-recordatorios

## Context

`turno_destinatario` has accepted `EMAIL` since C-23 (`models/turno_destinatario.py:29-38`), and C-27's capture flow already writes a row on that channel whenever the patient types an email. Nothing reads it. The only sender in the backend is `notificacion_service.enviar_recordatorio_telegram`, and it does not iterate recipients at all: it walks `turno.destinatarios`, takes the **first** row whose `canal == 'TELEGRAM'`, and `break`s (`notificacion_service.py:66-71`). An `EMAIL` row is invisible to it by construction.

That is why C-27's spec forbids the confirmation message from promising an email reminder ("Email delivery is not promised"), why `n8n-workflows/README.md:203` documents the gap as known, and why the patient is never asked which channel they want: offering a choice whose second option delivers nothing would be worse than not offering it. **The sender is the prerequisite; the choice follows it.** This change does both, in that order.

Four facts about the current code shape the design.

**The reminder has two engines, and both call the same function.** `scheduler/jobs.py:156` (APScheduler fallback) and `services/recordatorio_service.py:80` (the n8n-driven `POST /api/v1/recordatorios/run`) each call `enviar_recordatorio_telegram` directly and each interpret its `True`/`False` as "mark sent" / "retry later". Any fan-out has to happen **below** both call sites, or the two engines will drift.

**`recordatorio_service` skips a professional entirely when there is no bot token** (`recordatorio_service.py:60-65`). Today that is correct — no token, no Telegram, nothing to send. Once email exists it is a silent bug: a professional without a bot would stop sending email reminders they never knew they had.

**The `TELEGRAM` recipient row is load-bearing for routing, not only for delivery.** `captura_service.obtener_captura_pendiente` (`captura_service.py:85-91`) and `obtener_turnos_activos` (`captura_service.py:165-170`) both resolve *chat → turno* by joining `turno_destinatario` on `canal='TELEGRAM'`. That row is how `/cancelar` knows which turnos this chat may cancel. Deleting it to express "no Telegram reminder, please" would silently take `/cancelar` and `/reprogramar` away from the patient — a punishment they did not ask for.

**`turno.recordatorio_enviado` is a single boolean** covering what is about to become two independent deliveries.

## Goals / Non-Goals

**Goals:**

- A reminder actually arrives by email when the patient has an `EMAIL` recipient, through a sender with the same `True`/`False` retry contract as the Telegram one.
- `enviar_recordatorio` fans out over **every** recipient of the turno instead of the first `TELEGRAM` one, and both reminder engines go through it.
- The patient chooses which channel carries their reminder, and the choice survives to reminder time.
- The confirmation message stops describing a Telegram-only world, and `n8n-workflows/README.md` stops documenting a limitation that no longer exists.

**Non-Goals:**

- Email for anything other than the turno reminder. Lista de espera, cancellation and reschedule notices stay Telegram-only; this change adds one sender, not a notification platform.
- Action buttons in the email. Email has no inline keyboard, and building a signed-link confirm/cancel surface is its own change with its own auth story.
- HTML email, templating engines, per-professional branding, bounce handling, or an outbound queue.
- Changing `ConfirmarTurnoRequest`, `confirmar_turno`, the reservation window, or `_upsert_destinatarios_confirmacion` (`turno_service.py:256`) — this change reads the rows it already writes.
- Retrofitting the channel choice onto turnos confirmed before this change. They keep today's behaviour, which the migration defaults preserve exactly.

## Decisions

### D1 — `smtplib` in a threadpool, not a new async SMTP dependency

The email transport is stdlib `smtplib.SMTP` inside a **synchronous** `def`, called from the async layer through `fastapi.concurrency.run_in_threadpool`.

Two project hard rules point the same way: blocking libraries must not be declared `async def`, and APScheduler jobs must not block the event loop. The reminder sender runs inside `AsyncIOScheduler`, so a blocking `SMTP.send_message` on the loop would stall every other job for the duration of the SMTP handshake — which, against a slow or unreachable relay, is the socket timeout.

Rejected: `aiosmtplib`. It is natively async and would avoid the threadpool hop, but it adds a runtime dependency for a call the system makes a handful of times a day. The repo already has the precedent for the other side of the trade: `turno_service` wraps the blocking Google Calendar SDK with `run_in_threadpool` (`turno_service.py:247`) rather than hunting for an async client. Following the precedent keeps one pattern in the codebase instead of two.

An explicit `smtp_timeout` is passed to `smtplib.SMTP`; without it the default is the OS socket timeout, which can hold a threadpool worker for minutes.

### D2 — The channel choice is a flag on the recipient, not the presence of the recipient

`turno_destinatario` gains `notificar BOOLEAN NOT NULL DEFAULT TRUE`. The sender delivers only to rows where `notificar` is true.

The obvious cheaper design — express "I don't want Telegram reminders" by deleting the `TELEGRAM` row — is wrong for the reason recorded in Context: that row is also the chat-to-turno index behind `/cancelar` and `/reprogramar`. Conflating *"this is the chat that owns this turno"* with *"deliver reminders here"* is the actual defect; the flag separates them. A patient who mutes Telegram reminders keeps their booking manageable from the bot.

Rejected: a `canal_recordatorio` column on `turno`. It stores the same fact one table further from where it is used, cannot express "both" without an enum of combinations, and would have to be kept consistent with which recipient rows actually exist.

`DEFAULT TRUE` makes the migration a no-op for existing rows: every current turno keeps delivering exactly where it delivers today.

### D3 — Per-recipient delivery marking, so a failing channel cannot re-send a succeeding one

The same migration adds `enviado_en TIMESTAMP NULL`. `enviar_recordatorio` skips any recipient that already carries a timestamp, and stamps each one as it succeeds. `turno.recordatorio_enviado` stays the aggregate gate and is set only when every selected recipient has been delivered.

This is not gold-plating; it is what makes "iterate all recipients" safe against a single boolean. Without it, the fan-out has to answer partial failure with one bit, and every available answer is bad:

- *All-or-nothing* (`True` only if every channel succeeded) re-sends the succeeded channel on the next run. With a misconfigured SMTP relay and a 60-minute job interval, every turno in the 24-hour window gets a **fresh Telegram reminder every hour until the appointment**. A broken email config becomes a Telegram spam pump.
- *Any-success* (`True` if at least one channel worked) marks the turno done and drops the failed channel forever.

With `enviado_en`, a retry retries exactly the channel that failed. The cost is one nullable column on a table this change is already migrating.

Note this also hardens the two-engine overlap documented in `n8n-workflows/README.md:192-201`: today the engines de-duplicate on `turno.recordatorio_enviado` alone.

### D4 — One fan-out function, below both engines

```
enviar_recordatorio(db, turno, bot_token, settings) -> bool
```

It selects the turno's recipients with `notificar = TRUE AND enviado_en IS NULL`, dispatches each to its channel sender (`TELEGRAM` → the existing `enviar_recordatorio_telegram`, `EMAIL` → the new `enviar_recordatorio_email`), stamps `enviado_en` on each success, and returns `True` only when nothing remains undelivered.

`enviar_recordatorio_telegram` keeps its signature and its `True`/`False` meaning, minus one thing: the *"no `TELEGRAM` recipient → log a warning and return `True`"* branch (`notificacion_service.py:72-78`) moves up into `enviar_recordatorio`, generalised to *"no eligible recipient on any channel"*. That branch is a statement about the turno, not about Telegram, and leaving it in the channel sender would make an email-only turno report a missing Telegram recipient every run.

Both call sites — `jobs.py:156` and `recordatorio_service.py:80` — switch to `enviar_recordatorio`. `_procesar_profesional`'s early return on a missing `telegram_bot_token` (`recordatorio_service.py:60-65`) becomes a per-channel skip: no token means the Telegram channel fails closed for that professional, not that the professional is skipped.

Patrón A holds throughout: the fan-out flushes but never commits; the callers already commit per professional.

### D5 — An unconfigured SMTP relay is a permanent skip, never a retry

When `smtp_host` is empty, `enviar_recordatorio_email` logs a warning once per turno and reports the recipient as **skipped**: `enviado_en` is stamped, no delivery is attempted, and the turno's other channels are unaffected.

The alternative — returning `False` — turns an unset environment variable into an infinite retry across every turno in the window, which is exactly the failure mode D3 exists to prevent. Absent configuration is not a transient error; retrying it cannot fix it. A genuine SMTP failure (connection refused, auth rejected, relay 4xx/5xx) still returns `False` and is still retried, because that one might.

The trade-off is that a deployment which forgets `SMTP_HOST` delivers no email and says so only in the logs — the same failure class the C-23 reminder bug belonged to. The mitigation is that the log line is a warning naming the turno and the missing variable, and that `.env.example` carries the variable with a comment.

### D6 — Plain-text email, no action links

Subject and body are built by a formatting helper next to the transport, mirroring how `telegram_service` owns both `enviar_mensaje` and `format_recordatorio_mensaje`. The body carries the same facts as the Telegram reminder — patient name, date, time, professional and specialty — in plain text.

No HTML: it doubles the surface (multipart, client quirks, inlined CSS) for a five-line message. No confirm/cancel/reschedule links: the Telegram reminder gets those from an inline keyboard, and the email equivalent would need signed one-time URLs and a public endpoint to receive them. The email instead tells the patient to message the bot to cancel or reschedule — which stays available to them precisely because D2 keeps the `TELEGRAM` recipient row.

Telegram's `MarkdownV2` escaping and its 4096-character limit are Telegram's problem, not the email's; the two formatters share facts, not code.

### D7 — The choice is offered on the confirmation message, not as a fourth capture question

The confirmation message — which this change has to rewrite anyway — carries an inline keyboard with the channel options, and pressing one calls the backend. It is not a new question inside the capture flow.

C-27's D5 treats every extra question as a cost paid inside a 10-minute reservation window that is expiring while the user types, and its risk register already names "the reservation window now contains a conversation". Adding a fourth question would make a new patient answer four times before the slot is secured, and would need a new step in `captura_service.derivar_paso`, a new key in `datos_captura`, and a new branch in `Code - Procesar Captura`.

After confirmation none of that is true. The reservation is consumed, the turno is `CONFIRMADO`, the reminder is roughly 24 hours away, and the patient can answer at leisure or not at all. The keyboard is stateless in the C-27 sense: `cmd:canal:<turno_id>:<opcion>` carries everything the handler needs, following the `cmd:*` vocabulary the orquestador already routes (`n8n-workflows/README.md:46-60`) and the same lesson that produced `cmd:crear:slot:HH:MM:f:YYYY-MM-DD`.

**The keyboard appears only when the turno has an `EMAIL` recipient.** Offering "reminder by email" to a patient who never gave an email is an option that cannot be honoured. With no email, the confirmation message says the reminder comes by Telegram — true, and no longer a limitation being hidden.

**Default when the patient never presses anything: every recipient the turno has.** A patient who typed an email during a booking has asked to be reachable there; `notificar` defaults to `TRUE` and the buttons narrow that, they do not enable it. The alternative default (Telegram only until email is explicitly requested) is more conservative about unsolicited mail but leaves the common case — "I gave you my email so you'd write to me" — silently unserved.

### D8 — `PUT /turnos/{turno_id}/canales-recordatorio`, professional-scoped like its neighbours

Body `{"canales": ["TELEGRAM", "EMAIL"]}`. The endpoint sets `notificar = TRUE` on the turno's recipients whose channel is listed and `FALSE` on the rest, and returns the resulting recipient set through a declared `response_model` (hard rule: no endpoint without a return type). It is idempotent — pressing the same button twice is a no-op — and rejects an empty list with `422`, because "no reminder at all" is not one of the offered options and is more likely a bug in the caller than an intention.

Auth is `FlexibleProfesionalDep`: n8n holds an `X-API-Key` and no JWT, and C-27's D2 already widened this dependency's reach. This is **not** a new auth surface — `/turnos/*` has accepted the key since C-26 — so it does not trip the CRITICAL governance gate that C-27's group 4 did.

Scope is `profesional_id` only, matching `cancelar_turno` (`turno_service.py:397-411`), which likewise does not verify that the requesting chat owns the turno. A stricter contract here would be inconsistent with its neighbours while leaving the actual gap open next door; see OQ-4.

Only a `CONFIRMADO` turno may be targeted — a reminder preference on a turno that will never be reminded is meaningless, and refusing it surfaces caller bugs early.

### D9 — SMTP settings are Pydantic Settings, and the password never enters the repo

`Settings` gains `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_from`, `smtp_use_tls` and `smtp_timeout`, all with defaults that keep the application startable when email is not configured — the `configuration-management` spec's "optional variables use their documented default" contract. `smtp_host` defaulting to `""` is what D5's skip branch tests.

`SMTP_PASSWORD` goes in `.env` (git-ignored) and is documented by **name only** in `.env.example`, exactly as `GOOGLE_CLIENT_SECRET` and `SECRET_KEY` are. No credential, sample or otherwise, is committed, and none is logged: the failure log names the host and the turno, never the user or the password.

## Risks / Trade-offs

**A migration on `turno_destinatario`, a table on the read path of the capture flow and `/turnos/activos`.** → Both columns are additive with defaults that reproduce current behaviour (`notificar` `TRUE`, `enviado_en` `NULL`), so in-flight reservations and pending reminders are unaffected. No column is dropped or renamed; rollback is a `DROP COLUMN` and the sender's absence.

**A misconfigured relay could have become a Telegram spam pump.** → D3 and D5 are the mitigation, and they must be tested as such: a test where the email channel fails and the Telegram channel succeeds must assert the Telegram message is sent **once** across two job runs.

**`recordatorio_service` currently skips professionals without a bot token.** → Fixed in D4 as part of the fan-out, and guarded by a test with an email-only turno under a professional with no `telegram_bot_token`. Left unfixed, the email sender would work everywhere except the deployments most likely to need it.

**SMTP credentials are secrets in a repo whose hard rules say so.** → `.env` only, names documented in `.env.example`, nothing logged. Worth stating plainly because the natural way to test an SMTP sender is to paste a real password into a test file.

**Email deliverability is not something the backend controls.** → A reminder that lands in spam is indistinguishable from one that was never sent, and the sender reports `True` either way. Out of scope (no bounce handling, no SPF/DKIM work), but it means the Telegram channel stays the reliable one and the default in D7 keeps it on.

**The confirmation message and the reminder keyboard both change, on the busiest path in the workflow.** → C-27's task 6.4 lesson applies: the `HH:MM`, `1–20` and `DD/MM/AAAA` paths must be re-verified after the orquestador gains the `cmd:canal:*` route, not only the new path.

**C-27 is not archived, and this change declares it a dependency.** → Stated as a precondition rather than resolved: planning proceeds now, implementation waits. See "Migration Plan".

**Two more nullable-ish concepts on a row that already carries `creado_en`.** → Accepted. `turno_destinatario` is becoming the notification ledger rather than a contact list, which is what a per-channel delivery contract needs it to be.

## Migration Plan

**Precondition — C-27 must be archived first.** It is not, as of this writing: tasks 8.2–8.7 (the end-to-end n8n verification), 9.1–9.3 (the c-26 cancel/reschedule follow-up) and 10.2 remain open. This change edits the confirmation message that C-27's spec constrains and the workflow file C-27 is still validating, so implementing it against an unarchived C-27 would put two changes in the same nodes at once. Planning is complete now; implementation starts when C-27 archives.

Deployment order, and it matters:

1. **Migration** — `turno_destinatario.notificar` and `turno_destinatario.enviado_en`. Safe with reminders in flight: the defaults reproduce today's behaviour exactly.
2. **Backend** — the email sender, the fan-out, the two call-site swaps, the settings, the new endpoint. Additive: the endpoint is new and the fan-out preserves the existing `True`/`False` contract, so nothing outside `notificacion_service` changes meaning.
3. **Environment** — `SMTP_*` set in the target environment. Until then, D5 keeps the system in exactly its current state: Telegram delivers, email is skipped with a warning.
4. **n8n workflow** — the corrected confirmation message, the channel keyboard, the `cmd:canal:*` route. A workflow calling `PUT /turnos/{id}/canales-recordatorio` before step 2 fails on every confirmation that offers the choice, so the order is not negotiable.
5. **Documentation** — `n8n-workflows/README.md` and `.env.example`, once the behaviour they describe is live.

Rollback is per-step and independent: reverting the workflow stops the endpoint being called; reverting the backend leaves two unread columns; unsetting `SMTP_HOST` disables email without a deploy, which is also the kill switch if delivery misbehaves in production.

## Open Questions

- **OQ-1 — Which SMTP relay, in development and in production? IMPLEMENTATION-BLOCKING.** The sender cannot be verified end-to-end without a real account, and the choice has consequences the design cannot make alone: a Gmail app password is fastest but rate-limited and tied to a personal account; a transactional provider (Brevo, Resend, SES) gives deliverability and a sending domain but needs DNS records; a dev-only catcher (Mailtrap, MailHog) proves the sender works without proving anything about deliverability. **Recommended default:** MailHog or Mailtrap for development and the automated tests, and a transactional provider for production, decided before task group 8. Unit tests must not depend on any of them — they mock the transport (see OQ-2).
- **OQ-2 — Is a live SMTP round trip part of the test suite?** **Recommended default: no.** The transport is mocked in unit tests, exactly as `telegram_service.enviar_mensaje` is, and a single manual smoke test against the real relay is recorded in the task list. A test suite that needs a network mail server is a test suite that fails on someone else's laptop.
- **OQ-3 — What happens to the reminder state when the turno is rescheduled?** `reprogramar_turno` preserves the patient and the turno row, so the recipients and their flags survive. It does **not** reset `recordatorio_enviado` — `grep` finds that column written in exactly one place, `notificacion_service.marcar_recordatorio_enviado`. So a turno rescheduled after its reminder went out never gets a second one, today, for the old reason: this is a pre-existing defect that `enviado_en` inherits rather than causes. **Recommended default:** do not fix it here — it is a reschedule bug, not a fan-out bug, and fixing it means deciding whether a reschedule re-arms the reminder at all. File it against `turno-reschedule` and keep this change's scope to the four items in the proposal.
- **OQ-4 — Should the endpoint verify that the requesting chat owns the turno?** Today it will not, matching `cancelar_turno`. The residual exposure is that a caller holding the professional's API key can mute any of that professional's reminders — the same caller who can already cancel any of those turnos, so the endpoint adds no new capability to the key. **Recommended default:** leave it consistent, and treat chat-ownership scoping as its own change covering `cancelar`, `reprogramar` and this endpoint together.
- **OQ-5 — Should the email reminder eventually carry action links?** Deferred. It needs signed one-time URLs and a public endpoint, which is a security surface, not a formatting decision. Recorded here so the plain-text choice in D6 reads as a decision rather than an omission.
