# Design — c-27-confirmacion-turno-telegram

## Context

`sub-flujo-crear-turno` ends at `HTTP - POST Crear Turno` followed by `Telegram - Turno Creado`. The turno it announces is in `RESERVADO_TEMPORAL`, and the scheduler releases it 10 minutes later. The message is, in effect, a lie: it tells the user the booking exists while the system is already counting down to discarding it.

Three constraints shape the design.

**The backend already does more than the flow uses.** `crear_o_obtener_paciente` (`paciente_service.py:12`) upserts on `(profesional_id, dni)` under `SELECT FOR UPDATE`, and `_upsert_destinatarios_confirmacion` (`turno_service.py:256`) already registers `TELEGRAM` and `EMAIL` recipients from the confirm payload. Neither needs modification. What is missing is a way to *read* the patient before confirming, and permission for n8n to call it.

**Conversation state is the historical failure mode of this repo.** The date-persistence bug, the stateless slot-button rewrite, and the weekend retry loop were all state problems. Each new question added to the bot is another opportunity to lose state between Telegram messages. This design treats the number of conversational steps as a cost to be minimised, not a UX preference.

**Free-text answers cannot use the stateless trick.** The existing flow encodes state in `callback_data` (`cmd:crear:slot:HH:MM:f:YYYY-MM-DD`) because the user answers by pressing buttons. A DNI, a name and a phone number are typed, so nothing carries context back. State must live somewhere.

## Goals / Non-Goals

**Goals:**

- A turno reaches `CONFIRMADO` through Telegram, consuming its reservation instead of letting it expire.
- A returning patient is confirmed after a single question; a new patient after three.
- `cancelar` and `reprogramar` become testable, which closes the c-26 task 8.3 follow-up.
- The email address is captured and persisted for the day a mail sender exists.

**Non-Goals:**

- Sending email. No mail sender exists in `backend/app/`; an `EMAIL` recipient row is written and nothing delivers it.
- Per-request professional identity. The bot still authenticates as one professional via a static credential — deliberately deferred to the multitenancy change.
- Changing `ConfirmarTurnoRequest`, the reservation window, or `confirmar_turno` itself.
- Touching `cancelar` or `reprogramar` beyond making them reachable.

## Decisions

### D1 — A dedicated lookup endpoint, not a filter on the list

`GET /pacientes/buscar?dni=<dni>` returning `200` with the patient or `404`.

Rejected: adding `?dni=` to `GET /pacientes`. A list endpoint answers `200` with `[]` for "no match", which forces the caller to branch on an empty array rather than a status code. The bot needs a crisp exists / does-not-exist signal, and `404` is that signal. A filtered list also invites future callers to page through patients by DNI prefix, which is not a capability we want to offer.

**Route-ordering gotcha:** `GET /pacientes/{paciente_id}` already exists. FastAPI matches routes in declaration order, so `/pacientes/buscar` MUST be declared *before* `/pacientes/{paciente_id}`; otherwise `buscar` is parsed as a `paciente_id` and the request dies with `422`. This is a silent trap — it fails only at runtime and only for the new route.

### D2 — Reuse `get_current_profesional_flexible` verbatim for `pacientes.py`

The four existing endpoints swap `CurrentProfesionalDep` for `FlexibleProfesionalDep`, and the new lookup uses the same. c-26 built this dependency, tested it across nine scenarios, and shipped it; duplicating the logic for patients would create a second place for the two schemes to drift apart.

This is an **auth-surface change and is treated as CRITICAL governance**: it widens what the n8n credential can reach from `/turnos/*` to `/pacientes/*`. The blast radius stays inside one professional's own data — every patient query is already scoped by `profesional_id` — but the change gets an explicit test per endpoint rather than one test for the dependency.

### D3 — The conversation lives in Postgres, on the reservation it belongs to

**This decision replaces an earlier one that shipped and failed in production. The failure is recorded below rather than deleted, because it is the most useful thing in this document.**

#### What was tried first, and how it broke

The original D3 put the conversation in `$getWorkflowStaticData('global')`: `captura_<chatId>` in the sub-flujo holding `{turno_id, paso, datos, expira_en}`, and `gate_captura_<chatId>` in the orquestador holding a routing bit, synchronised child → parent over the `Execute Workflow` return value. Groups 6–7 were implemented that way, validated by graph reachability and `node -e` simulation of every jsCode node, and pushed to the live instance.

The first end-to-end booking failed at the first question. Evidence from the real executions (chat `5150361036`, n8n **2.4.4**):

- Execution 254 (22:59:15): `Code - Sync Captura` runs without error, receives `{captura_pendiente: true, expira_en: …}` from the sub-flujo and writes `gate_captura_5150361036`. Execution status `success`.
- Execution 256 (22:59:47, **32 seconds later**, no container restart): the user types their DNI. `Normalizar Comando` returns `comando: "desconocido"` and the bot shows the help menu. The gate read returned `null`.

`GET /workflows/<id>` reports `staticData: null` on both workflows, although `ctx_<chatId>` had been written since July. Ruled out before concluding: an unpublished draft (`versionId === activeVersionId` on both), a container restart, a failed execution, and a key-name mismatch.

**`$getWorkflowStaticData` does not persist across executions on this instance.** The official documentation marks static data experimental and warns it "may behave unreliably". This repo had already routed around it once without diagnosing it — the stateless `cmd:crear:slot:HH:MM:f:YYYY-MM-DD` callback exists precisely because the date kept disappearing.

Two lessons worth keeping:

- **The simulation could not have caught this.** A `node -e` harness runs one process and one memory space; cross-execution persistence is exactly the property it cannot observe. Structural validation proves a workflow is well-formed, never that it works.
- Both stores were affected. Fixing only the orquestador's gate would have moved the failure one question later, to the name.

#### The design that replaced it

The conversation's partial answers live in **`reserva_temporal.datos_captura`** (`JSONB NOT NULL DEFAULT '{}'`, migration `c27a1b3d9e40`).

The row is the right home because its lifetime is already exactly right: `turno_service.confirmar_turno` deletes it on confirmation and `liberar_reservas_vencidas` deletes it on expiry. The conversation therefore expires with the slot it belongs to, and needs no TTL, no sweeper and no cleanup of its own — all of which the previous design had to build and get right.

**The chat is resolved to its booking through a row that already existed.** `reservar_turno` writes `TurnoDestinatario(canal='TELEGRAM', destinatario=chat_id)` for every Telegram reservation (C-23, `turno_service.py:150`). The link from a chat to its pending turno has been in Postgres since July; this change only had to read it. No chat-to-turno mapping is introduced.

**The step is derived, never stored.** `captura_service.derivar_paso` computes it from the captured data: no `dni` → ask for the DNI; `dni` without a complete `nombre`/`apellido` pair → ask for the name; no `telefono` → ask for the phone; otherwise confirm. `email` is optional and never blocks. Storing `paso` as its own column would allow it to contradict `datos` — `paso='telefono'` with no DNI captured. Deriving it makes that state unrepresentable rather than merely unlikely.

Two endpoints, both on `FlexibleProfesionalDep` because n8n has no JWT:

| Endpoint | Contract |
|---|---|
| `GET /turnos/captura-pendiente?telegram_chat_id=` | `200 {turno_id, paso, datos}` or `404`. Only a turno of this professional, still `RESERVADO_TEMPORAL`, whose reservation has not expired. |
| `PATCH /turnos/{turno_id}/captura` | Merges `{datos}` into what is stored and returns the new step. |

The `404` is an expected outcome, not an error: it is how the flow learns "this text is not an answer".

`PATCH` is called **only when a question still lies ahead** — after a DNI that matched no patient, and after the name. The last answer goes straight to `PUT /turnos/{id}/confirmar`, because there is no next message that needs to remember anything.

#### Alternatives, reconsidered

**Letting the sub-flujo own everything** was rejected by the original D3 on the escape hatch: `/cancelar` dispatches to a *third* workflow, and from there nothing could clear a capture living in `sub-flujo-crear-turno`'s private store. Moving the state to Postgres dissolves that objection — every workflow sees the same row. The rejected design became the right one, for a reason that had nothing to do with its own merits. **This is now the implemented design.**

**Storing the pending step in the backend** was also rejected, on the grounds that `telegram_service.py` does this for the direct-webhook path and adopting it "would mean two systems owning the same conversation". That reasoning does not survive contact with the facts: a Telegram bot has exactly one webhook and n8n owns it, so `telegram_service`'s handler never runs and its in-memory `_conversation_states` is never populated. There is no second owner to conflict with. The concern was real in principle and empty in practice.

**`Telegram - Send and Wait for Response`** stays rejected, for the reason confirmed by the OQ-1 spike: its free-text mode answers through a hosted web form, not an in-chat reply.

### D4 — The orquestador is a pure parser; the sub-flujo decides against the database

The orquestador reads no state and writes none. It parses a Telegram update and dispatches.

Today it routes free text by the **shape** of the string: `^\d{1,2}:\d{2}$` → slot; `^\d+$` in 1–20 → slot number; `^\d{2}/\d{2}/\d{4}$` → date; the `cmd:*` callbacks; then the slash and natural-language commands; anything else → the help menu. All three capture answers fall through to help: a DNI is `\d+` but outside 1–20, a phone likewise, and "Juan Pérez" matches nothing.

The previous design solved this by making the orquestador stateful — the gate that could not persist. The current one does not need it:

1. **A recognised command wins.** Any `cmd:*` callback or slash/natural-language command sets `payload.fresh_start = true` and falls into its existing branch body unchanged. `fresh_start` is the escape hatch: it tells the sub-flujo to ignore a pending capture, so a user who abandons a booking mid-question is not trapped answering a question they have forgotten.
2. **Everything else is dispatched as a candidate answer.** `comando = 'crear'` and `payload.respuesta_captura = textRaw`, **in addition to** the shape parsing, which runs unchanged. Both travel together.
3. **The sub-flujo breaks the tie**, because it is the one holding the database. `HTTP - GET Captura Pendiente` runs before `Code - Decidir Paso`; a `200` means the text is an answer and the shape is ignored, a `404` means the shape stands.

The load-bearing consequence: a mistyped `15` while the bot waits for a DNI is an invalid DNI, not slot number 15 — and that decision is made against stored state rather than guessed. Sending both interpretations and resolving them where the truth lives is what removes the need for the orquestador to know anything.

**Free text that matches nothing** — no live capture, no date, no slot, no range — resolves to `accion = 'ayuda'`, which matches no `Switch Accion` rule and falls through the fallback output to `Code - Retorno Estado` **without sending a message**. The help menu lives in the orquestador, so the sub-flujo reports `mostrar_ayuda: true` and lets it answer. An earlier revision let this case reach `pedir_rango`, which sent "¿para cuándo necesitás el turno?" *and* the help menu: two replies to one "hola".

**Node changes.** In the orquestador, `Code - Sync Captura` became `Code - Evaluar Retorno`, which no longer touches `staticData` and only carries the `mostrar_ayuda` fail-safe: `Execute Crear Turno` has `onError: "continueRegularOutput"`, so a sub-workflow failure returns nothing, `mostrar_ayuda` defaults to `true`, and the user gets the menu instead of silence. `Telegram - Gracias Confirmacion` and a fourth `Switch Comando` output were added for `cmd:confirmar:turno_id:` — see the reminder-button note below. In the sub-flujo: `HTTP - GET Captura Pendiente`, `HTTP - PATCH Captura`, `Code - Paso Siguiente` and `Switch - Paso Siguiente` are new; `Code - Decidir Paso`, `Code - Procesar Captura`, `Code - Evaluar Paciente`, `Code - Extraer Turno ID`, `Code - Evaluar Confirmacion` and `Code - Retorno Estado` no longer read or write `staticData`.

**The reminder buttons were dead, and this change wired them.** `format_recordatorio_keyboard` emitted `reminder:confirmar|cancelar|reprogramar:{id}`, a vocabulary only `telegram_service`'s own webhook handler understands. Since n8n owns the webhook, all three buttons reached the orquestador, matched nothing and produced the help menu. They now emit `cmd:cancelar:turno_id:{id}` and `cmd:reprogramar:turno_id:{id}`, which the orquestador already routed, plus `cmd:confirmar:turno_id:{id}`, which answers a thank-you without touching the turno — it is already `CONFIRMADO`. Registering the patient's answer, and escalating when there is none, is c-29.

**Implementation constraint for the new HTTP nodes.** The chain branches on `404` (`GET /pacientes/buscar`, `GET /turnos/captura-pendiente`) and `409` (`PUT /turnos/{id}/confirmar`). An n8n HTTP Request node **throws** on those by default, aborting the branch before D6's messages can be chosen. Every new HTTP node sets `options.response.response.neverError: true` and `fullResponse: true`, and the following Code node branches on `statusCode`. This also fixed dead code: `Code - Extraer Turno ID` already tested `statusCode >= 400`, but `HTTP - POST Crear Turno` was not configured this way, so that test could never fire.

### D5 — Group the new-patient questions into two messages

Name and surname are asked together; phone and email are asked together, with the email marked optional. Three questions total including the DNI.

Rejected: one question per field (four questions). Each additional step is another state transition to lose, and the reservation is expiring while the user types.

Rejected: a single CSV message (`Juan,Perez,30111222,1122334455`), which was the original C-24 design. One round-trip and no state at all, but it is unforgiving: a missing comma, a swapped order or a stray space produces either a validation error or — worse — a patient recorded with the surname in the phone field. The DNI-first design achieves a comparable number of round-trips for returning patients, who are the common case, without that fragility.

### D6 — Surface confirmation failures by their business reason

`PUT /turnos/{id}/confirmar` fails in ways the user can act on, and each gets its own message: `409 TurnoExpiradoError` means the reservation lapsed and the booking must restart; `409 PacienteConTurnoActivoError` means the patient already holds an active turno. A generic "something went wrong" would leave the user retyping data into a turno that no longer exists.

The mechanism that makes this reachable is stated at the end of D4: the confirm and lookup nodes must be configured `neverError` + `fullResponse`, or the HTTP node throws on the `409` and no branch runs.

## Risks / Trade-offs

**The reservation window now contains a conversation.** → Three questions maximum, and the returning-patient path needs only one. The `409` is reported clearly so a lapsed reservation is recoverable by restarting rather than confusing. Widening the window is deliberately out of scope; if smoke testing shows real users losing slots, that becomes its own change with a config default to argue about.

**`pacientes.py` becomes reachable by the n8n credential.** → Scope is unchanged and enforced per query by `profesional_id`; each endpoint gets an explicit dual-auth test plus a cross-professional isolation test. Note this risk compounds with the known single-tenant weakness of the n8n path: one leaked credential exposes one professional's patients, not several.

**Every free-text message now reaches `sub-flujo-crear-turno`.** → The orquestador no longer holds state, but it dispatches anything that is not a recognised command, so a plain "hola" costs one sub-workflow execution and one `GET /turnos/captura-pendiente` before resolving to the help menu. Accepted: the round trip is cheap, and the alternative is asking the orquestador to guess what it cannot know. The behaviour of the `HH:MM`, `1-20` and `DD/MM/AAAA` paths is unchanged and must be verified as such (task 6.4).

**One store, one truth.** → The gate/payload split that this risk used to describe is gone: there is a single row in Postgres, read by whoever needs it. What remains is a narrower window — after a `/cancelar` mid-capture, the reservation stays alive until its TTL (~10 minutes) and free text in that window is still read as an answer. `fresh_start` covers the commands themselves; an explicit abandon endpoint was judged more machinery than the problem is worth.

**`Execute Crear Turno` becomes non-terminal, which changes a node every booking message already passes through.** → The rewire touches the busiest path in the orquestador. `onError: "continueRegularOutput"` is already set on it, so a sub-workflow failure degrades to the help menu rather than to silence; task 6.4's "behaves exactly as today" check must therefore be run against the `HH:MM`, `1–20` and `DD/MM/AAAA` paths specifically, not only against the help path.

**`Code - Verificar Slots` still calls `$getWorkflowStaticData`.** → It caches the slot list so a user can pick a slot by number. That cache never persisted either, so numeric selection has been broken since before this change; it is left untouched rather than widening the blast radius, and is the one place where the store survives in the capture path's neighbourhood. Whoever removes it should also decide whether numeric slot selection is worth restoring.

**An `EMAIL` recipient row that nothing delivers.** → Accepted deliberately, so the data accrues before the sender exists. The bot must not mention email reminders in its confirmation message; the spec makes that a scenario so it cannot be quietly dropped.

**Two `Paciente` rows for one person who mistypes their DNI.** → Out of scope, and pre-existing: `crear_o_obtener_paciente` already keys strictly on DNI equality. Worth noting that the lookup makes this *more* visible, because a typo now silently sends the user down the new-patient path.

## Migration Plan

One migration, `c27a1b3d9e40`, adding `reserva_temporal.datos_captura` as `JSONB NOT NULL DEFAULT '{}'`. Existing rows backfill through the server default, so it is safe to apply with reservations in flight: a reservation created before the migration simply looks like a capture with nothing captured yet, which is exactly what it is.

The rest of the backend changes are additive: three new endpoints and a dependency swap that widens accepted credentials without removing the existing one, so current JWT callers are unaffected.

The n8n workflow ships as a single import to the live instance. Rollback is `n8n-cli`'s automatic backup version, or reverting the workflow JSON in the repo and re-pushing. Reverting the backend is an independent step — a reverted workflow simply stops calling the new endpoint.

Order matters: migration, then backend, then workflow. A workflow that calls an endpoint which does not yet exist fails on every booking — and unlike the previous design, the capture endpoints are on the path of *every* free-text message, not only new-patient ones.

## Open Questions

- ~~**OQ-1 — Does `Telegram - Send and Wait for Response` accept a free-text reply in-chat, or does it send the user to a hosted form?**~~ **RESOLVED — hosted form**, confirmed by a live spike and by reading the node's source inside the running container. The node stays rejected. Note that this spike's conclusion at the time — "D3's `staticData` approach stands" — was correct about `Send and Wait` and wrong about `staticData`, which failed for an unrelated reason the spike was never designed to test.
- ~~**OQ-2 — Should an abandoned capture expire on its own?**~~ **RESOLVED — it already did.** The state lives on `reserva_temporal`, which `confirmar_turno` deletes on success and `liberar_reservas_vencidas` deletes on expiry. No TTL was written, because the row's lifetime already is the TTL. The correctness backstop remains the `409` from `PUT /confirmar`.
- ~~**OQ-3 — Is a bare DNI a safe routing signal?**~~ **RESOLVED — the orquestador does not route by it.** It forwards the text as a candidate answer alongside the shape parsing, and the sub-flujo resolves the ambiguity against the database. What must still be confirmed at runtime is the mirror image: with no capture pending, the `HH:MM`, `1-20` and `DD/MM/AAAA` shapes resolve exactly as before (task 6.4).
- ~~**OQ-4 — Does `POST /turnos` expose the reservation's expiry in its response?**~~ **MOOT.** It does not (`TurnoResponse` has no expiry field), but the flow no longer needs it: nothing in n8n tracks a deadline now, and `GET /turnos/captura-pendiente` filters expired reservations server-side.
- **OQ-5 — After a `/cancelar` mid-capture, should the pending reservation be abandoned explicitly?** Today it survives until its TTL and free text in that window is still read as an answer. An explicit abandon endpoint would close it and free the slot sooner. Deferred: bounded, low-frequency, and it adds an HTTP call to every recognised command.
