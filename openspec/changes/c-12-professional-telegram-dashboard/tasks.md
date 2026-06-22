## 1. Backend Endpoints — Turnos Hoy

- [ ] 1.1 Write failing test: `GET /profesional/turnos-hoy` returns confirmed appointments for today with patient data (TDD red)
- [ ] 1.2 Create/update Pydantic schema `ProfesionalTurnoHoyResponse` in `app/schemas/profesional.py` with nested `Paciente` info
- [ ] 1.3 Implement `GET /profesional/turnos-hoy` in `app/routers/profesional.py` with `response_model`, strict type hints, query filtered by `fecha=today` and `estado=CONFIRMADO`
- [ ] 1.4 Run test → green; refactor if needed
- [ ] 1.5 Write edge-case test: no appointments today returns empty array (TDD red → green)
- [ ] 1.6 Write edge-case test: non-CONFIRMADO states are excluded (TDD red → green)

## 2. Backend Endpoints — Métricas

- [ ] 2.1 Write failing test: `GET /profesional/metricas` returns calculated metrics (turnos_hoy, tasa_confirmacion_30d, tasa_cancelacion_30d) (TDD red)
- [ ] 2.2 Create Pydantic schema `ProfesionalMetricasResponse` in `app/schemas/profesional.py`
- [ ] 2.3 Implement `GET /profesional/metricas` in `app/routers/profesional.py` with `response_model`, strict type hints, SQL aggregation queries
- [ ] 2.4 Run test → green; refactor if needed
- [ ] 2.5 Write edge-case test: zero data returns all zeros (TDD red → green)
- [ ] 2.6 Write edge-case test: verify type safety and response_model filtering (TDD red → green)

## 3. Telegram Formatting Utilities

- [ ] 3.1 Write failing test: `format_turnos_hoy` produces MarkdownV2 string with escaped patient names (TDD red)
- [ ] 3.2 Implement `format_turnos_hoy(turnos: list[dict]) -> str` in `app/services/telegram_service.py`
- [ ] 3.3 Write failing test: `format_metricas` produces MarkdownV2 summary with rates (TDD red)
- [ ] 3.4 Implement `format_metricas(metricas: dict) -> str` in `app/services/telegram_service.py`
- [ ] 3.5 Write failing test: `format_config_summary` displays pending config changes (TDD red)
- [ ] 3.6 Implement `format_config_summary(config: dict) -> str` in `app/services/telegram_service.py`
- [ ] 3.7 Run tests → green; refactor if needed
- [ ] 3.8 Write test: message splitting for >4096 chars (reuse existing `split_message` util, verify behavior with mock long list)

## 4. Telegram Wizard — /configurar States and Keyboards

- [ ] 4.1 Write failing test: `_get_state` initializes new professional config keys (`config_paso`, `config_data`) (TDD red)
- [ ] 4.2 Extend `_get_state` to include `config_paso` and `config_data` keys
- [ ] 4.3 Write failing test: `format_dias_keyboard` returns inline keyboard with 7 day toggles + confirm button (TDD red)
- [ ] 4.4 Implement `format_dias_keyboard(dias_seleccionados: list[str]) -> InlineKeyboardMarkup`
- [ ] 4.5 Write failing test: `format_config_confirm_keyboard` returns confirm/cancel buttons (TDD red)
- [ ] 4.6 Implement `format_config_confirm_keyboard() -> InlineKeyboardMarkup`
- [ ] 4.7 Run tests → green; refactor if needed

## 5. Telegram Router — Professional Commands

- [ ] 5.1 Write failing test: text `/turnos_hoy` routes to action and sends formatted message (TDD red)
- [ ] 5.2 Implement routing for `/turnos_hoy` in `procesar_mensaje`: query DB, format response, send message
- [ ] 5.3 Write failing test: text `/metricas` routes to action and sends formatted metrics (TDD red)
- [ ] 5.4 Implement routing for `/metricas` in `procesar_mensaje`
- [ ] 5.5 Write failing test: text `/configurar` starts wizard and prompts for start time (TDD red)
- [ ] 5.6 Implement routing for `/configurar` in `procesar_mensaje`: set state, send prompt
- [ ] 5.7 Run tests → green; refactor if needed

## 6. Telegram Wizard — Step Handlers

- [ ] 6.1 Write failing test: state `config_esperando_hora_inicio` parses valid HH:MM and transitions (TDD red)
- [ ] 6.2 Implement handler for `config_esperando_hora_inicio` with validation and transition to `config_esperando_hora_fin`
- [ ] 6.3 Write failing test: invalid time in `config_esperando_hora_inicio` replies error and stays in state (TDD red)
- [ ] 6.4 Implement invalid-time handling
- [ ] 6.5 Write failing test: state `config_esperando_hora_fin` validates end > start and transitions (TDD red)
- [ ] 6.6 Implement handler for `config_esperando_hora_fin` with validation and transition to `config_esperando_dias`
- [ ] 6.7 Write failing test: end <= start replies error and stays (TDD red)
- [ ] 6.8 Implement end-time validation error
- [ ] 6.9 Write failing test: `config_esperando_dias` toggles day selection via callback and updates keyboard (TDD red)
- [ ] 6.10 Implement day toggle handler with `edit_message_reply_markup`
- [ ] 6.11 Write failing test: pressing "Confirmar días" transitions to `config_esperando_duracion` (TDD red)
- [ ] 6.12 Implement day confirmation handler
- [ ] 6.13 Write failing test: `config_esperando_duracion` parses positive int and transitions to `config_confirmar` (TDD red)
- [ ] 6.14 Implement duration handler with validation
- [ ] 6.15 Write failing test: `config_confirmar` persists changes via existing config service and resets state (TDD red)
- [ ] 6.16 Implement confirmation handler calling `update_configuracion` logic (or service layer)
- [ ] 6.17 Write failing test: "Cancelar" at any step resets state and discards changes (TDD red)
- [ ] 6.18 Implement cancel handler for all wizard states
- [ ] 6.19 Run all wizard tests → green; refactor if needed

## 7. Integration and Verification

- [ ] 7.1 Run full backend test suite (`pytest backend/`) and ensure no regressions
- [ ] 7.2 Verify OpenAPI docs show new endpoints with correct `response_model` schemas
- [ ] 7.3 Manual smoke test: send `/turnos_hoy`, `/metricas`, `/configurar` to local bot (if feasible)
- [ ] 7.4 Verify Telegram message lengths stay under 4096 chars in realistic data scenarios
- [ ] 7.5 Verify no hardcoded config values; all env vars use Pydantic Settings
- [ ] 7.6 Verify no blocking sync code in async Telegram handlers (use `run_in_threadpool` if calling sync libs)

## 8. Documentation and Closure

- [ ] 8.1 Update `CHANGES.md` to mark C-12 as `[x] propuesto` (or equivalent state)
- [ ] 8.2 Verify all spec scenarios have at least one corresponding test
- [ ] 8.3 Verify all design decisions are reflected in implementation or documented as deferred
- [ ] 8.4 Run `openspec verify` (if available) or manual checklist against specs
