## Why

Los workflows de n8n en `n8n-workflows/flujo-*.json` quedaron **desactualizados** respecto del modelo multi-tenant aplicado en C-14 a C-22. Hoy el backend rechaza cualquier request a `/turnos/*`, `/lista-espera/*` y `/webhooks/telegram` que no presente `X-API-Key` o `X-Telegram-Bot-Api-Secret-Token` (`backend/app/dependencies.py:98-139`), pero los workflows:

- Envían el payload al backend como si fueran un único bot global (sin header `X-API-Key`).
- Toman el `profesional_id` del propio body, lo que viola el scoping por tenant aplicado en C-16.
- Tienen un `Webhook Trigger` por flujo (4 webhooks a configurar en `@BotFather` por cada profesional), sin orquestador: el routing "qué comando pidió el usuario" se hace por convención de webhook, no por switch sobre el contenido del update.

Resultado: **E2E Telegram → n8n → backend no funciona en v2.0.** El backend responde 401/403 a los 4 workflows y la tesis queda con un componente crítico sin demostrar.

Adicionalmente, el usuario diseñó un esqueleto de **orquestador** (single entry point que switch-ea a sub-workflows según comando). Ese esqueleto existe en `C:\Users\pocho\Downloads\My workflow (4).json` y debe ser el punto de partida.

## What Changes

- **Nuevo** `orquestador.json`: workflow único con `Telegram Trigger` que recibe updates del bot del profesional, identifica el comando (texto o `callback_data`) y dispatch-ea vía `executeWorkflow` a uno de 3 sub-workflows (`Crear_turno`, `Cancelar_turno`, `Reprogramar_turno`). Es **state-less**: cada sub-workflow resuelve su slot/datos en una sola ejecución.
- **Nuevos** 3 sub-workflows (`sub-flujo-crear-turno.json`, `sub-flujo-cancelar-turno.json`, `sub-flujo-reprogramar-turno.json`): encapsulan el flujo conversacional completo de su acción (fechas → horarios → reserva → confirmación para crear; wizard de reprogramación; etc.). Cada nodo `HTTP Request` al backend lleva `X-API-Key` configurado vía `Header Auth` credential a nivel de workflow.
- **Nuevo** `sub-flujo-lista-espera-respuesta.json` (opcional, ver Decisión 5 en design.md): workflow que responde a los `callback_data` `lista_espera:aceptar:{id}` y `lista_espera:rechazar:{id}` que el orquestador delega cuando el `tipo` del callback es `lista_espera`.
- **Modificados** `flujo-lista-espera.json` y `flujo-recordatorio.json`: se les agrega el header `X-API-Key` (mismo patrón `Header Auth` credential) para que el backend deje de rechazar. Su forma general (webhook / schedule trigger) **no cambia**.
- **Eliminados** `flujo-reserva.json` y `flujo-cancelacion.json`: quedaron absorbidos por el orquestador + sub-workflows. Mantenerlos activos generaría doble routing (un mismo update llegaría al orquestador Y al webhook del flujo viejo, configurado en `@BotFather`).
- **Modificado** `n8n-workflows/README.md`: refleja la nueva topología, documenta el patrón de credenciales (`Header Auth` para `X-API-Key`, `Telegram Bot` para el token del bot), y el procedimiento de importación **una vez por profesional** (no por bot).
- **NO** se introduce `tenant_id`, **NO** se modifica el backend, **NO** se reemplazan los routers FastAPI existentes ni la lógica de `python-telegram-bot` del backend (C-08 / C-17). En v2.0, **n8n es la capa de orquestación** paralela al webhook conversacional del backend; el orquestador apunta a los mismos endpoints REST.

> **Nota de coexistencia**: el backend ya expone `POST /webhooks/telegram` (C-08) que procesa updates de Telegram directamente con la lógica conversacional completa (`telegram_service.procesar_mensaje`). El orquestador n8n es una **alternativa** que delega a los mismos endpoints REST (`/turnos`, `/turnos/{id}/cancelar`, etc.) saltándose la lógica conversacional. **Decisión a confirmar por el usuario** si en producción se usa solo el webhook del backend, solo el orquestador n8n, o ambos (con `@BotFather` apuntando a uno u otro). Por defecto, el orquestador **asume** que se configura `@BotFather` para apuntar al `Telegram Trigger` de n8n, dejando el webhook del backend ocioso para este profesional.

## Capabilities

### New Capabilities
- `n8n-workflow-orquestador-telegram`: nuevo patrón de orquestador de n8n. Single entry point por bot, switch por comando (texto o callback), dispatch a sub-workflows vía `executeWorkflow`, X-API-Key en cada llamada al backend.

### Modified Capabilities
- (vacío) — los endpoints REST del backend no cambian; los specs existentes de `n8n-workflow-reserva` / `n8n-workflow-cancelacion` / `n8n-workflow-lista-espera` / `n8n-workflow-recordatorio` describen comportamiento v1.0 y serán **archivados conceptualmente** al cumplirse este change (los flujos viejos se eliminan, el resto se reemplaza). El comportamiento nuevo (orquestador + multi-tenant auth) está capturado por la nueva capability.

## Impact

- **Workflows JSON** (afectados, en `n8n-workflows/`):
  - Nuevos: `orquestador.json`, `sub-flujo-crear-turno.json`, `sub-flujo-cancelar-turno.json`, `sub-flujo-reprogramar-turno.json`, `sub-flujo-lista-espera-respuesta.json` (opcional).
  - Modificados: `flujo-lista-espera.json`, `flujo-recordatorio.json`, `README.md`.
  - Eliminados: `flujo-reserva.json`, `flujo-cancelacion.json`.
- **Backend**: **sin cambios**. Los endpoints `GET /turnos/disponibles`, `POST /turnos`, `PUT /turnos/{id}/confirmar`, `PUT /turnos/{id}/cancelar`, `PUT /turnos/{id}/reprogramar` y `GET /lista-espera/siguiente` ya aceptan `X-API-Key` (`backend/app/dependencies.py:98-115`) y están scoped por `profesional_id` (C-16).
- **Configuración en n8n** (procedimiento de despliegue):
  - Por cada profesional con bot, **una instancia** del orquestador + sub-workflows importados en n8n.
  - Por instancia, **2 credenciales** configuradas: `Telegram Bot` (token del bot) y `Header Auth` (`X-API-Key: <profesional.api_key>`).
  - **No** se configuran webhooks en `@BotFather` por sub-workflow: el único webhook es el del `Telegram Trigger` del orquestador, registrado por n8n al activar el workflow.
- **KB**: actualizar `knowledge-base/08_arquitectura_propuesta.md` §Integración n8n (topología de workflows y patrón de credenciales) tras el archive.
- **Fuera de alcance**: capa visual web (no aplica a n8n), reemplazo del router conversacional de `telegram_service.py` (C-08 / C-17), integración de envío por email (futuro, modelo soporta vía C-23), soporte de UN solo orquestador para N bots (decisión: un orquestador por bot).
- **Gobernanza**: BAJO. No toca modelo de datos ni contratos REST. El cambio es de configuración y orquestación.
