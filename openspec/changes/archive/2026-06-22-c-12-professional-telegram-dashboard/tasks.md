## 1. Backend Endpoints — Turnos Hoy

- [x] 1.1 Write failing test: `GET /profesional/turnos-hoy` returns confirmed appointments for today with patient data (TDD red)
- [x] 1.2 Create/update Pydantic schema `ProfesionalTurnoHoyResponse` in `app/schemas/profesional.py` with nested `Paciente` info
- [x] 1.3 Implement `GET /profesional/turnos-hoy` in `app/routers/profesional.py` with `response_model`, strict type hints, query filtered by `fecha=today` and `estado=CONFIRMADO`
- [x] 1.4 Run test → green; refactor if needed
- [x] 1.5 Write edge-case test: no appointments today returns empty array (TDD red → green)
- [x] 1.6 Write edge-case test: non-CONFIRMADO states are excluded (TDD red → green)

## 2. Backend Endpoints — Métricas

- [x] 2.1 Write failing test: `GET /profesional/metricas` returns calculated metrics (turnos_hoy, tasa_confirmacion_30d, tasa_cancelacion_30d) (TDD red)
- [x] 2.2 Create Pydantic schema `ProfesionalMetricasResponse` in `app/schemas/profesional.py`
- [x] 2.3 Implement `GET /profesional/metricas` in `app/routers/profesional.py` with `response_model`, strict type hints, SQL aggregation queries
- [x] 2.4 Run test → green; refactor if needed
- [x] 2.5 Write edge-case test: zero data returns all zeros (TDD red → green)
- [x] 2.6 Write edge-case test: verify type safety and response_model filtering (TDD red → green)

## 3. Telegram Formatting Utilities

- [x] 3.1 Write failing test: `format_turnos_hoy` produces MarkdownV2 string with escaped patient names (TDD red)
- [x] 3.2 Implement `format_turnos_hoy(turnos: list[dict]) -> str` in `app/services/telegram_service.py`
- [x] 3.3 Write failing test: `format_metricas` produces MarkdownV2 summary with rates (TDD red)
- [x] 3.4 Implement `format_metricas(metricas: dict) -> str` in `app/services/telegram_service.py`
- [x] 3.5 Write failing test: `format_config_summary` displays pending config changes (TDD red)
- [x] 3.6 Implement `format_config_summary(config: dict) -> str` in `app/services/telegram_service.py`
- [x] 3.7 Run tests → green; refactor if needed
- [x] 3.8 Write test: message splitting for >4096 chars (reuse existing `split_message` util, verify behavior with mock long list)

## 4. Telegram Wizard — /configurar States and Keyboards

- [x] 4.1 Write failing test: `_get_state` initializes new professional config keys (`config_paso`, `config_data`) (TDD red)
- [x] 4.2 Extend `_get_state` to include `config_paso` and `config_data` keys
- [x] 4.3 Write failing test: `format_dias_keyboard` returns inline keyboard with 7 day toggles + confirm button (TDD red)
- [x] 4.4 Implement `format_dias_keyboard(dias_seleccionados: list[str]) -> InlineKeyboardMarkup`
- [x] 4.5 Write failing test: `format_config_confirm_keyboard` returns confirm/cancel buttons (TDD red)
- [x] 4.6 Implement `format_config_confirm_keyboard() -> InlineKeyboardMarkup`
- [x] 4.7 Run tests → green; refactor if needed

## 5. Telegram Router — Professional Commands

- [x] 5.1 Write failing test: text `/turnos_hoy` routes to action and sends formatted message (TDD red)
- [x] 5.2 Implement routing for `/turnos_hoy` in `procesar_mensaje`: query DB, format response, send message
- [x] 5.3 Write failing test: text `/metricas` routes to action and sends formatted metrics (TDD red)
- [x] 5.4 Implement routing for `/metricas` in `procesar_mensaje`
- [x] 5.5 Write failing test: text `/configurar` starts wizard and prompts for start time (TDD red)
- [x] 5.6 Implement routing for `/configurar` in `procesar_mensaje`: set state, send prompt
- [x] 5.7 Run tests → green; refactor if needed

## 6. Telegram Wizard — Step Handlers

- [x] 6.1 Write failing test: state `config_esperando_hora_inicio` parses valid HH:MM and transitions (TDD red)
- [x] 6.2 Implement handler for `config_esperando_hora_inicio` with validation and transition to `config_esperando_hora_fin`
- [x] 6.3 Write failing test: invalid time in `config_esperando_hora_inicio` replies error and stays in state (TDD red)
- [x] 6.4 Implement invalid-time handling
- [x] 6.5 Write failing test: state `config_esperando_hora_fin` validates end > start and transitions (TDD red)
- [x] 6.6 Implement handler for `config_esperando_hora_fin` with validation and transition to `config_esperando_dias`
- [x] 6.7 Write failing test: end <= start replies error and stays (TDD red)
- [x] 6.8 Implement end-time validation error
- [x] 6.9 Write failing test: `config_esperando_dias` toggles day selection via callback and updates keyboard (TDD red)
- [x] 6.10 Implement day toggle handler with `edit_message_reply_markup`
- [x] 6.11 Write failing test: pressing "Confirmar días" transitions to `config_esperando_duracion` (TDD red)
- [x] 6.12 Implement day confirmation handler
- [x] 6.13 Write failing test: `config_esperando_duracion` parses positive int and transitions to `config_confirmar` (TDD red)
- [x] 6.14 Implement duration handler with validation
- [x] 6.15 Write failing test: `config_confirmar` persists changes via existing config service and resets state (TDD red)
- [x] 6.16 Implement confirmation handler calling `update_configuracion` logic (or service layer)
- [x] 6.17 Write failing test: "Cancelar" at any step resets state and discards changes (TDD red)
- [x] 6.18 Implement cancel handler for all wizard states
- [x] 6.19 Run all wizard tests → green; refactor if needed

## 7. Integration and Verification

- [x] 7.1 Run full backend test suite (`pytest backend/`) and ensure no regressions
- [x] 7.2 Verify OpenAPI docs show new endpoints with correct `response_model` schemas
- [x] 7.3 Manual smoke test: send `/turnos_hoy`, `/metricas`, `/configurar` to local bot (if feasible)
- [x] 7.4 Verify Telegram message lengths stay under 4096 chars in realistic data scenarios
- [x] 7.5 Verify no hardcoded config values; all env vars use Pydantic Settings
- [x] 7.6 Verify no blocking sync code in async Telegram handlers (use `run_in_threadpool` if calling sync libs)

## 8. Documentation and Closure

- [x] 8.1 Update `CHANGES.md` to mark C-12 as `[x] propuesto` (or equivalent state)
- [x] 8.2 Verify all spec scenarios have at least one corresponding test
- [x] 8.3 Verify all design decisions are reflected in implementation or documented as deferred
- [x] 8.4 Run `openspec verify` (if available) or manual checklist against specs
