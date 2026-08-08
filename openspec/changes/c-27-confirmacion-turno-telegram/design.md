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

### D3 — Two `staticData` stores, one owner each: the sub-flujo holds the conversation, the orquestador holds only a routing gate

The flow already keeps `ctx_<chatId>`, `contador_<chatId>` and `fecha_<chatId>` in `$getWorkflowStaticData('global')`, and commit `cf18717` made that mechanism work correctly, including a `freshStart` that clears the keys when a new `cmd:crear` begins. The capture steps extend the same convention with a pending-step key and a partial-answers key, both scoped by chat id.

Rejected: `Telegram - Send and Wait for Response`. It is attractive — its default 10-minute timeout coincides with `reserva_temporal_minutos`, and it holds state inside the live execution, eliminating the problem entirely. It is rejected because its free-text mode responds through a hosted form URL rather than an in-chat reply, which would break the conversational feel of the bot. **This is now CONFIRMED (OQ-1 resolved, see below) rather than merely believed** — this decision stands.

**Revision — `staticData` is per-workflow, so "one store" was never available.** The original wording said "the capture steps extend the same convention" as if there were a single store. There is not. `orquestador.json` and `sub-flujo-crear-turno.json` each call `$getWorkflowStaticData('global')` on their **own** store; both already use the key `ctx_<chatId>` — same name, two different boxes, holding different shapes (`{fecha, rango}` in the parent, `{fecha, rango, slots}` in the child). A pending-capture flag written by the sub-flujo is therefore **invisible** to the orquestador's `Switch Comando`. Any design that assumed otherwise is unimplementable.

The resolution is not to pick one store but to give each store a **different job**, so nothing is duplicated:

| Store | Key | Content | Role |
|---|---|---|---|
| `sub-flujo-crear-turno` | `captura_<chatId>` | `{ turno_id, paso, datos: { dni, nombre, apellido, telefono, email }, expira_en }` | **Owner of the conversation.** The only place the answers live. |
| `orquestador` | `gate_captura_<chatId>` | `{ pendiente: true, expira_en }` | **Routing gate only.** One bit plus a deadline. Never holds an answer. |

The keys are deliberately named differently. The `ctx_<chatId>` collision above is a trap this repo already fell into once; identical names across two stores invite the next reader to assume they are one thing.

**Synchronisation is one-way, child → parent, over the return channel that already exists.** `Execute Crear Turno` has `waitForSubWorkflow: true` but is a terminal node with no outgoing connection: it waits for the sub-workflow's response and throws it away. That discarded value is the wire. The sub-flujo gains a single fan-in node, `Code - Retorno Estado`, which every terminal branch connects into; it reads `captura_<chatId>` from its own store and returns `{ chat_id, captura_pendiente, expira_en, mostrar_ayuda }`. In the orquestador, `Execute Crear Turno` becomes non-terminal and feeds `Code - Sync Captura`, which writes or deletes `gate_captura_<chatId>` from that return value.

The gate is thus **set and cleared by the same mechanism**, on every dispatch, which is what makes it trustworthy.

Rejected: **inferring the gate locally from the `cmd:crear:slot:` dispatch**, with no return value at all. This is the cheapest option on paper — zero new nodes in the orquestador — and it was seriously considered, because the orquestador does know that a slot selection is exactly what makes the sub-flujo reserve a turno and ask for a DNI. It fails on the two events it cannot observe:
- **`POST /turnos` failed** (slot taken in the meantime, backend down). No question was asked, but the gate is set, so the user's next message is swallowed.
- **The capture completed successfully.** Nothing tells the orquestador the conversation ended, so after a confirmation the user types "gracias" and it is routed as a DNI.

The second is fatal and cannot be patched locally: clearing the gate requires knowing what the sub-flujo did. Since the return channel is needed for clearing regardless, using it for setting too is free and strictly more accurate. One mechanism, both directions.

Rejected: **letting the sub-flujo own everything and routing all unrecognised text to it**, with no gate in the orquestador at all. Same node count as the chosen design (a return-value reader plus an IF, to bounce non-answers back to the help message) and zero duplicated state, which is genuinely more elegant. It loses on the escape hatch — see D4. `/cancelar` is dispatched to `sub-flujo-cancelar-turno`, a *third* store; from there nothing can clear a pending capture living in `sub-flujo-crear-turno`. The user stays trapped until the TTL expires, which is precisely the failure task 6.3 exists to prevent. The gate wins because it lives in the one workflow that sees every message.

Rejected: storing the pending step in the backend. That is what `telegram_service.py` does for the direct-webhook path, and adopting it here would mean two systems owning the same conversation. The n8n path deliberately bypasses that service.

**Both keys carry `expira_en`, and a key read past its deadline is treated as absent.** The deadline is the reservation's own expiry — taken from the `POST /turnos` response when it exposes one, otherwise `$env.RESERVA_TEMPORAL_MINUTOS` (default 10) plus a one-minute grace. This is a **UX nicety, not a correctness mechanism**: the real backstop is `PUT /turnos/{id}/confirmar` answering `409 TurnoExpiradoError`, which D6 surfaces. A wrong TTL costs one confusing message, not a wrong booking. It also resolves OQ-2 without inventing a sweeper.

**Cleanup, and the pre-existing leak.** The sub-flujo's `ctx_<chatId>` is never cleared after a successful turno creation today — it survives until the next bare `cmd:crear` triggers `freshStart`. This change **fixes that leak** rather than leaving it: every terminal outcome of the capture (confirmed, expired, rejected) deletes `captura_<chatId>`, `ctx_<chatId>`, `contador_<chatId>` and `fecha_<chatId>` together. The moment a booking ends is the correct clearing point for all four, the fix is one extra `delete` line in a node this change is writing anyway, and leaving the store half-clean guarantees the next person rediscovers it. The following `Code - Retorno Estado` then reports `captura_pendiente: false`, so the orquestador's gate is cleared on the same round trip — cleanup is one mechanism, not two.

The orquestador's gate does **not** need clearing by the sub-flujo's cleanup path beyond this, and the sub-flujo's payload does **not** need clearing by the escape hatch: see D4.

**OQ-1 resolution — hosted form, confirmed both structurally and by source inspection.** A throwaway workflow (`Webhook` → `Telegram` node, `resource: "message"`, `operation: "sendAndWait"`, `responseType: "freeText"`) was created on the live instance and triggered three times against a real chat (the maintainer's own Telegram, chat id `5150361036`, via `@TeleOdontobot`); each run reached a genuine `waiting` execution state (`waitTill: 3000-01-01`, confirmed via `n8n-cli executions get <id>`), so a real message was sent. Ground truth for what that message *contains* was pulled directly from the installed `n8n-nodes-base` source inside the running container (`/usr/local/lib/node_modules/n8n/.../n8n-nodes-base/dist/utils/sendAndWait/utils.js`):
- The `responseType: "freeText"` option's own catalog description reads `"User can submit a response via a form"`.
- `getSendAndWaitConfig()` builds the message's only interactive element as a **button** whose `url` is a signed resume URL (`context.getSignedResumeUrl(...)`) — there is no code path that parses a plain chat reply for this response type.
- `sendAndWaitWebhook()` handles that resume URL: on `GET` it renders `form-trigger` — an n8n-hosted page with a textarea field labelled "Response" — and only resumes the workflow on the form's `POST`.

So the free-text flow is: bot sends a message with a "Respond" button → button opens a hosted n8n web form in the browser → user types into the form, not the chat → form submission resumes the execution. This is not an in-chat reply under any configuration of `responseType: "freeText"`, confirming the design's original wariness. The throwaway workflow was deactivated and deleted after the spike; the live instance's workflow count and content are unchanged (still the 6 pre-existing workflows). D3 (`staticData` convention) is confirmed as the approach for groups 6–7; no revision needed, and task 1.2's revisit condition does not trigger.

Rejected: storing the pending step in the backend. That is what `telegram_service.py` does for the direct-webhook path, and adopting it here would mean two systems owning the same conversation. The n8n path deliberately bypasses that service.

### D4 — Precedence inside `Normalizar Comando`: recognised command, then gate, then today's shape rules

This is the least obvious requirement of the change. Today the orquestador switches on a parsed command; a bare `30111222` matches nothing and falls through to the unknown-command branch. Once the bot asks open questions, arbitrary text becomes meaningful.

**Revision — the orquestador routes free text by the SHAPE of the string, not by state.** Verified by reading the `Normalizar Comando` jsCode. In order: `^\d{1,2}:\d{2}$` → `crear` + `slot`; `^\d+$` **with value 1–20** → `crear` + `slot_numero`; `^\d{2}/\d{2}/\d{4}$` → `crear` + `fecha_raw`; the `cmd:*` callbacks; then the slash / natural-language commands; anything else → `desconocido` → `Telegram - Mensaje de Ayuda`.

All three replies the capture needs fall through to the help branch: a DNI (`30123456`) is `\d+` but outside 1–20, a phone likewise, and "Juan Pérez" matches nothing. So the original wording — "checks whether a capture step is pending" — named the right problem but sat at the wrong layer. The check does not belong beside the switch; it belongs **inside the shape cascade, above it**.

**Precedence, evaluated in `Normalizar Comando` before anything else:**

1. **Recognised command wins.** Any `cmd:*` callback, or any slash / natural-language command (`/reservar`, `/cancelar`, `/reprogramar`, "quiero un turno", …) → **delete `gate_captura_<chatId>`**, then fall into the existing branch bodies unchanged.
2. **Otherwise, if the gate is set and not expired** → `comando = 'crear'`, `payload.respuesta_captura = textRaw`. The message is dispatched to `sub-flujo-crear-turno` through the *existing* `crear` output; no new `Switch Comando` output is needed.
3. **Otherwise** → the existing shape cascade (`HH:MM`, `1–20`, `DD/MM/AAAA`) and its `desconocido` → help fallback, byte-for-byte as today.

Two things about this ordering are load-bearing.

**Step 1 above step 2 is the escape hatch.** A user who abandons a booking mid-question is otherwise trapped: every subsequent message is swallowed as an answer to a question they have forgotten.

**Step 2 above step 3 suspends shape matching entirely while a capture is pending.** This matters beyond the three answers that happen not to collide today: when the bot has asked for a DNI, a reply of `15` must be "that is not a valid DNI, try again", not a slot-number selection, and `10:30` must not re-enter the booking flow. Placing the gate below the cascade would work for a well-formed DNI and fail for a typo — the exact case the user is most likely to produce.

**Step 3 is why task 6.4 holds.** When the gate is empty, step 2 is a no-op and the cascade is reached with today's semantics; the `desconocido` → help wire is not touched at all. The existing branch *bodies* are not rewritten either — the restructure hoists a `comandoReconocido` predicate (the `cmd:` prefix test plus the existing `textLower` tests) above the chain and guards it, leaving each body as it stands.

**The gate is the only thing the escape hatch clears.** Task 6.3 asks for the pending capture to be cleared "in both stores if state is duplicated". Under D3 it is not duplicated: the gate is a routing bit, the payload is the conversation. Clearing the gate is sufficient, because the payload is unreachable without it — no free text will ever be routed to the sub-flujo as an answer again. The orphaned payload is then disposed of three ways over: a bare `cmd:crear` hits the existing `freshStart`, a new slot selection overwrites the key with a fresh `turno_id`, and the TTL expires it regardless. This is the tradeoff being accepted: a stale key may sit in the child store for up to the reservation window, inert. Paying two Execute-Workflow dispatches per `/cancelar` to scrub it is more machinery than the problem is worth.

**Wiring in the orquestador — two new nodes.** `Execute Crear Turno` stops being terminal:

```
Execute Crear Turno → Code - Sync Captura → IF - Mostrar Ayuda ──true──▶ Telegram - Mensaje de Ayuda
```

- `Code - Sync Captura` reads `chat_id` via `$('Normalizar Comando').first().json.chat_id` — **not** from the Execute Workflow output, per the `chat_id` propagation rule that already forced this pattern on `Code - Verificar Slots` and `Code - Extraer Turno ID`. It writes or deletes `gate_captura_<chatId>` from the sub-workflow's `captura_pendiente` / `expira_en`, and passes `{ chat_id, mostrar_ayuda }` on.
- `IF - Mostrar Ayuda` reuses the *existing* help node rather than duplicating the inline keyboard in a second workflow. It covers the self-healing case where the gate says pending but the payload is gone (TTL skew, a lost write, an n8n restart): the sub-flujo returns `captura_pendiente: false, mostrar_ayuda: true`, the gate is cleared and the user gets the menu instead of silence. Cost of that case is one lost message, once.
- `Execute Crear Turno` already carries `onError: "continueRegularOutput"`. A sub-workflow failure therefore yields no return value, `mostrar_ayuda` defaults to **true**, and the user gets the help menu — the failure mode is fail-safe, not silent.

**Implementation constraint for the new HTTP nodes.** The capture chain branches on `404` (`GET /pacientes/buscar`) and `409` (`PUT /turnos/{id}/confirmar`). An n8n HTTP Request node **throws** on those by default, which would abort the branch before D6's messages can be chosen. Both new nodes set `options.response.response.neverError: true` and `fullResponse: true`, and the following Code node branches on `statusCode`. Note this also exposes dead code: `Code - Extraer Turno ID` already tests `input.statusCode >= 400`, but `HTTP - POST Crear Turno` is not configured this way, so that test can never fire — the create node needs the same treatment for its own error path to work at all.

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

**The orquestador's routing becomes stateful.** → This is the most likely source of new bugs, since it changes behaviour for *every* message, not only booking ones. Mitigated by the D4 escape hatch, by the gate being a single bit that step 3 never consults when empty, and by covering the abandon-mid-conversation path explicitly in testing.

**The gate and the payload can disagree.** → Two stores mean two truths. The disagreement is bounded to one direction (gate set, payload gone) because the gate is only ever set by a return value the payload produced, and it self-heals inside a single round trip: the sub-flujo reports `captura_pendiente: false`, the gate is cleared, the user gets the help menu. The cost is one message. The reverse (payload present, gate gone) is not a fault — that is the escape hatch working, and the payload is inert.

**`Execute Crear Turno` becomes non-terminal, which changes a node every booking message already passes through.** → The rewire touches the busiest path in the orquestador. `onError: "continueRegularOutput"` is already set on it, so a sub-workflow failure degrades to the help menu rather than to silence; task 6.4's "behaves exactly as today" check must therefore be run against the `HH:MM`, `1–20` and `DD/MM/AAAA` paths specifically, not only against the help path.

**Fixing the pre-existing `ctx_<chatId>` leak widens this change's blast radius.** → Clearing `ctx_`, `contador_` and `fecha_` on a terminal outcome is correct but touches the day-retry loop's keys, which the weekend-retry bug already burned once. Accepted because the clearing happens strictly *after* a booking terminates, where the retry loop is no longer running; the alternative is knowingly shipping a store that leaks on the happy path.

**An `EMAIL` recipient row that nothing delivers.** → Accepted deliberately, so the data accrues before the sender exists. The bot must not mention email reminders in its confirmation message; the spec makes that a scenario so it cannot be quietly dropped.

**Two `Paciente` rows for one person who mistypes their DNI.** → Out of scope, and pre-existing: `crear_o_obtener_paciente` already keys strictly on DNI equality. Worth noting that the lookup makes this *more* visible, because a typo now silently sends the user down the new-patient path.

## Migration Plan

No data migration. The backend changes are additive: one new endpoint and a dependency swap that widens accepted credentials without removing the existing one, so current JWT callers are unaffected.

The n8n workflow ships as a single import to the live instance. Rollback is `n8n-cli`'s automatic backup version, or reverting the workflow JSON in the repo and re-pushing. Reverting the backend is an independent step — a reverted workflow simply stops calling the new endpoint.

Order matters: backend first, workflow second. A workflow that calls a lookup which does not yet exist fails on every new-patient booking.

## Open Questions

- ~~**OQ-1 — Does `Telegram - Send and Wait for Response` accept a free-text reply in-chat, or does it send the user to a hosted form?**~~ **RESOLVED — hosted form.** See D3 for the spike and source-level evidence. D3's `staticData` approach stands; groups 6–7 proceed unchanged.
- ~~**OQ-2 — Should an abandoned capture expire on its own?**~~ **RESOLVED — yes, by a TTL carried in both keys.** `expira_en` is the reservation's own deadline; a key read past it is treated as absent, in the gate and in the payload alike. See D3. No sweeper, no scheduled job. The TTL is a UX nicety — the correctness backstop is the `409` from `PUT /confirmar`.
- ~~**OQ-3 — Is a bare DNI a safe routing signal?**~~ **RESOLVED — the question was inverted.** D4 does not route *by* the DNI; while a capture is pending it suspends shape matching altogether, so nothing is shadowed by the answer's content. What must be confirmed during testing is the mirror image: that with the gate empty, the `HH:MM`, `1–20` and `DD/MM/AAAA` shapes still resolve exactly as they do today (task 6.4).
- **OQ-4 — Does `POST /turnos` expose the reservation's expiry in its response?** D3's TTL prefers that value and falls back to `$env.RESERVA_TEMPORAL_MINUTOS` (default 10) plus a grace minute. Cheap to check while implementing group 7; the fallback is safe either way.
