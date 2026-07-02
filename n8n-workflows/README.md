# n8n Workflows — Turnos Telegram Bot

Workflows de n8n para la orquestación conversacional del bot de turnos vía Telegram. Implementado en el change **C-24 (n8n-workflows-orquestador-telegram)**.

## Topología actual

El bot del profesional es atendido por **un orquestador** que dispatch-ea a sub-workflows según el comando. Los flujos viejos (1 webhook por flujo) fueron **eliminados** — ver [§ Workflows eliminados](#workflows-eliminados-hist%C3%B3rico).

```
Bot del Profesional
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│  orquestador.json (Telegram Trigger + Switch × 3)                │
│  - Normaliza message.text / callback_query.data → { comando }    │
│  - Switch: crear | cancelar | reprogramar | desconocido          │
└──────────────────────────────────────────────────────────────────┘
        │
        ├─ "crear"       → sub-flujo-crear-turno.json
        ├─ "cancelar"    → sub-flujo-cancelar-turno.json
        └─ "reprogramar" → sub-flujo-reprogramar-turno.json

Workflows independientes (no dispatch-ados por el orquestador):
  - flujo-recordatorio.json  (Schedule Trigger diario → POST /api/v1/recordatorios/run)
  - flujo-lista-espera.json  (placeholder, deuda C-11)
```

## Workflows

| Archivo | Propósito | Trigger | Estado |
|---------|-----------|---------|--------|
| `orquestador.json` | Single entry point del bot; switch por comando | `Telegram Trigger` | ✅ Completo |
| `sub-flujo-crear-turno.json` | Wizard de crear turno (fecha → hora → CSV → confirmar) | `Execute Workflow Trigger` (invocado por orquestador) | ✅ Completo |
| `sub-flujo-cancelar-turno.json` | Cancelar turno por ID | `Execute Workflow Trigger` (invocado por orquestador) | ✅ Completo |
| `sub-flujo-reprogramar-turno.json` | Wizard de reprogramación (nueva fecha → nueva hora) | `Execute Workflow Trigger` (invocado por orquestador) | ✅ Completo |
| `flujo-recordatorio.json` | Cron diario → `POST /api/v1/recordatorios/run` | `Schedule Trigger` (cron `0 10 * * *`) | ✅ Completo |
| `flujo-lista-espera.json` | Notificación de lista de espera (placeholder C-11) | `Webhook Trigger` | ⏳ Placeholder (C-11) |

## Workflows eliminados (histórico)

> 🗑️ Eliminados en C-24 porque quedaron **absorbidos** por el orquestador + sub-workflows. Mantenerlos generaría doble routing (un mismo update Telegram llegaría al orquestador Y al webhook del flujo viejo configurado en `@BotFather`).

- `flujo-reserva.json` → reemplazado por `sub-flujo-crear-turno.json` (con `Header Auth` y sin `paciente_id` en el body, consistente con C-23).
- `flujo-cancelacion.json` → reemplazado por `sub-flujo-cancelar-turno.json` (con `Header Auth`).

Si los necesitás para rollback, están en el historial de git: `git log -- n8n-workflows/flujo-reserva.json`.

## Prerrequisitos

1. **n8n ≥ 1.20** (soporte de `telegramTrigger` v1.2 + `executeWorkflow` v1.3 + `Telegram - Send and Wait for Response`).
2. **Bot de Telegram** creado vía [@BotFather](https://t.me/BotFather).
3. **Backend FastAPI** corriendo con `X-API-Key` configurada (endpoints de C-06 a C-08, más `POST /api/v1/recordatorios/run` de C-24 Decisión 8).

## Patrón de credenciales (MULTI-TENANT — clave del change)

Cada profesional con bot requiere **2 credenciales** configuradas en n8n (Settings → Credentials → New):

| Credencial | Tipo n8n | Header / Campo | Valor | Dónde se usa |
|------------|----------|----------------|-------|--------------|
| `Telegram Bot` | `telegramApi` | (token interno de n8n) | `<profesional.telegram_bot_token>` | `Telegram Trigger` (orquestador) + todos los `Telegram` nodes de los sub-workflows |
| `Profesional API Key` | `httpHeaderAuth` | Header `X-API-Key` | `<profesional.api_key>` | Todos los `HTTP Request` nodes de los 3 sub-workflows + `flujo-recordatorio` + `flujo-lista-espera` |

Los `HTTP Request` nodes referencian la credencial `Profesional API Key` vía:

```
Authentication → Generic Credential Type → httpHeaderAuth
```

Más el bloque `credentials.httpHeaderAuth: { id, name }` que apunta a la credencial en el JSON del nodo.

**NO** se hardcodea `X-API-Key` en ningún campo de expresión. La credencial se configura **una vez** al importar el workflow por profesional y se reusa en todos los nodos HTTP.

> 🔁 **Rotación de `api_key`**: tocar solo la credencial en n8n (un cambio, todos los nodos actualizados). No requiere redeploy del workflow.

## Variables de entorno en n8n

Configurá estas variables en tu instancia de n8n (Settings → External Secrets o via `.env`):

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `BACKEND_URL` | URL base del backend FastAPI (usado en workflows nuevos) | `http://localhost:8000` o `https://api.tuapp.com` |
| `FASTAPI_BASE_URL` | URL base legacy (solo lo usa `flujo-lista-espera.json`, placeholder C-11) | `http://localhost:8000` |

> ⚠️ **Nunca hardcodees** tokens ni URLs en los workflows. Usá siempre `{{ $env.BACKEND_URL }}` o `{{ $env.FASTAPI_BASE_URL }}`.

## Cómo importar workflows (UNA VEZ POR PROFESIONAL)

> El orquestador es **por bot** (Decisión 1 del design.md). Cada profesional importa su propia copia del orquestador y sub-workflows en n8n, con sus 2 credenciales dedicadas.

1. Abrí tu instancia de n8n en el navegador.
2. **Settings → Credentials → New** y crear las 2 credenciales (`Telegram Bot` y `Header Auth` con `X-API-Key`).
3. **Workflows → Import from file** e importar en este orden:
   1. `sub-flujo-crear-turno.json`
   2. `sub-flujo-cancelar-turno.json`
   3. `sub-flujo-reprogramar-turno.json`
   4. `orquestador.json`
   5. `flujo-recordatorio.json`
   6. `flujo-lista-espera.json` (placeholder, opcional)
4. En cada sub-workflow y workflow independiente, abrir cada nodo `HTTP Request` y asignar la credencial `Header Auth` recién creada.
5. En el `orquestador.json`, abrir el `Telegram Trigger` y asignar la credencial `Telegram Bot`. Abrir los 3 `executeWorkflow` y referenciar los sub-workflows (si quedaron `disabled: true` por la import, re-asignar el workflow por nombre desde el dropdown).
6. Activar el **orquestador** (toggle ON). **NO** activar los sub-workflows individualmente: los `executeWorkflow` los invocan sin necesidad de activarlos, pero deben existir en el workspace.

## Cómo configurar `@BotFather` (UNA VEZ POR PROFESIONAL)

> Decisión OQ-1 resuelta: n8n es el entry point principal. El webhook del backend (`POST /webhooks/telegram`) queda como alternativa documentada — ver [§ Coexistencia con el webhook del backend](#coexistencia-con-el-webhook-del-backend).

1. Abrí [@BotFather](https://t.me/BotFather) en Telegram.
2. Escribí `/setwebhook` y seleccioná tu bot.
3. Ingresá la URL del webhook que n8n registra al activar el `Telegram Trigger` del orquestador (la URL la muestra n8n en el panel del workflow activo, formato `https://<tu-n8n>/webhook/<webhookId>`).
4. **No** configures webhooks adicionales para sub-workflows: n8n enruta todos los updates al orquestador y el `Switch` interno los dispatch-ea.

## Mapeo de workflows ↔ endpoints FastAPI

| Workflow | Endpoint | Método | Auth | Descripción |
|----------|----------|--------|------|-------------|
| `orquestador.json` | (ninguno) | — | — | Solo dispatch-ea a sub-workflows; no consume REST |
| `sub-flujo-crear-turno.json` | `/turnos/disponibles` | GET | Header Auth | Lista horarios disponibles para la fecha |
| `sub-flujo-crear-turno.json` | `/turnos` | POST | Header Auth | Crea reserva temporal (sin `paciente_id`, el backend resuelve en confirmación) |
| `sub-flujo-crear-turno.json` | `/turnos/{id}/confirmar` | PUT | Header Auth | Confirma turno reservado + datos paciente (CSV) |
| `sub-flujo-cancelar-turno.json` | `/turnos/{id}/cancelar` | PUT | Header Auth | Cancela turno confirmado |
| `sub-flujo-reprogramar-turno.json` | `/turnos/disponibles` | GET | Header Auth | Lista horarios disponibles para la nueva fecha |
| `sub-flujo-reprogramar-turno.json` | `/turnos/{id}/reprogramar` | PUT | Header Auth | Reprograma turno preservando al paciente |
| `flujo-recordatorio.json` | `/api/v1/recordatorios/run?fecha=YYYY-MM-DD` | POST | Header Auth | Dispara envío de recordatorios del día siguiente (endpoint nuevo de C-24) |
| `flujo-lista-espera.json` | `/lista-espera/siguiente` | GET | Header Auth | ⏳ Placeholder C-11 (deuda) |

## Coexistencia con el webhook del backend

El backend expone `POST /api/v1/webhooks/telegram` (C-08) que procesa updates de Telegram directamente con la lógica conversacional completa (`telegram_service.procesar_mensaje`). El orquestador n8n es una **alternativa** que delega a los mismos endpoints REST saltándose la lógica conversacional del backend.

**Decisión de configuración (OQ-1 resuelta)**: `@BotFather` apunta al `Telegram Trigger` del orquestador n8n. El webhook del backend queda ocioso para este profesional, pero disponible como fallback (si n8n se cae, cambiar `@BotFather` al webhook del backend).

Telegram solo enruta updates al **último** webhook configurado, así que no hay duplicación si se configura solo el orquestador.

## Dos motores de recordatorio (n8n + APScheduler)

El sistema de recordatorios tiene **dos motores** que conviven:

1. **n8n primario** (`flujo-recordatorio.json`): corre via `Schedule Trigger` con cron `0 10 * * *` (default 10:00 hora local). Llama a `POST /api/v1/recordatorios/run?fecha=mañana` y el backend itera por profesionales activos, busca turnos a recordar y los envía.
2. **APScheduler fallback** (`scheduler.jobs._enviar_recordatorios_job` en el backend, C-08): corre en el backend, también diario. Útil si n8n está caído o si el profesional no configuró n8n.

Ambos motores llaman a la **misma lógica** de `notificacion_service` (`obtener_turnos_para_recordar` + `enviar_recordatorio_telegram` + `marcar_recordatorio_enviado`). El campo `turno.recordatorio_enviado` en la DB evita **doble dispatch**: el primer motor que envíe el recordatorio lo marca como enviado, y el segundo lo skipea.

> ℹ️ En v1.0 se recomienda activar **solo uno** de los dos motores por profesional. Si ambos están activos, el de n8n gana por horario (10:00) y el de APScheduler no hace nada (todos los turnos del día siguiente ya están marcados como enviados).

## Testing

### Tests de parseo estático (TDD para n8n)

```bash
# Todos los JSON parsean
for f in n8n-workflows/*.json; do
  python -c "import json; json.load(open('$f'))" || echo "FAIL: $f"
done

# Estructura: cada HTTP Request usa Generic Credential Type → httpHeaderAuth
for f in n8n-workflows/sub-flujo-*.json n8n-workflows/flujo-lista-espera.json n8n-workflows/flujo-recordatorio.json; do
  echo "=== $f ==="
  python -c "import json,sys; d=json.load(open('$f')); nodes=[n for n in d['nodes'] if n['type']=='n8n-nodes-base.httpRequest']; [print(n['name'], '→', n['parameters'].get('authentication',{}).get('type','MISSING')) for n in nodes]"
done

# Orquestador referencia los 3 sub-workflows
python -c "import json; d=json.load(open('n8n-workflows/orquestador.json')); nodes=[n for n in d['nodes'] if n['type']=='n8n-nodes-base.executeWorkflow']; [print(n['name'], '→', n['parameters'].get('workflowId',{}).get('value','MISSING')) for n in nodes]"
```

### Tests manuales (E2E con backend + bot real)

> Requiere n8n local + bot de Telegram real + backend levantado. Documentado en tasks.md §10.6.

1. Levantar backend: `cd backend && uvicorn app.main:app --reload`.
2. Importar los 6 workflows en n8n. Configurar las 2 credenciales.
3. Activar el orquestador.
4. Enviar `/reservar` al bot en Telegram.
5. Verificar en n8n Executions que el orquestador dispatch-ea a `Crear_turno` y los HTTP Request retornan 200.
6. Verificar en backend logs que el turno se crea con el `profesional_id` correcto del profesional dueño del bot.
7. Repetir con `/cancelar` y `/reprogramar` para los otros 2 sub-workflows.
8. **Probar el recordatorio**: trigger manual del cron (o esperar a la hora) y verificar que el endpoint `POST /api/v1/recordatorios/run` itera y envía los mensajes del día siguiente. Confirmar que el turno queda con `recordatorio_enviado=True`.

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| Bot no responde a `/reservar` | Orquestador no activo o `Telegram Trigger` sin credencial | Verificá que el toggle del orquestador esté ON y que el `Telegram Trigger` tenga asignada la credencial `Telegram Bot` |
| HTTP Request retorna 401 | Falta `X-API-Key` o credencial `Header Auth` mal asignada | Asigná la credencial `Header Auth` a cada nodo `HTTP Request` |
| HTTP Request retorna 403 | `X-API-Key` inválida o no coincide con el `profesional_id` esperado | Verificá que el valor de la credencial coincida con `profesional.api_key` en la DB |
| Sub-workflow no se dispara desde el orquestador | `executeWorkflow` con `workflowId` mal referenciado | En el orquestador, abrí cada `executeWorkflow` y re-asigná el workflow por nombre desde el dropdown |
| Recordatorio no llega a los pacientes | Cron mal configurado o endpoint no disponible | Verificá la expresión cron del `Schedule Trigger` y que el endpoint `POST /api/v1/recordatorios/run` exista en el backend (C-24 Decisión 8) |
| Doble mensaje de recordatorio | Ambos motores (n8n + APScheduler) activos para el mismo profesional | Desactivá uno. El campo `recordatorio_enviado` en la DB evita doble dispatch, pero se recomienda dejar uno solo activo |
| Lista de espera retorna 404 | Endpoint `/lista-espera/siguiente` aún no existe (deuda C-11) | Esperá a C-11. El workflow es placeholder; no se ejecuta realmente |

## Notas

- Los workflows usan **botones inline** de Telegram para la navegación (fechas, horarios, reprogramación).
- El `Send and Wait for Response` tiene timeout default de 10 min, alineado con `RESERVA_TEMPORAL_MINUTOS=10` del backend.
- Los 3 sub-workflows son **stateless** entre ejecuciones (convención n8n); el state conversacional multi-step vive en el backend (C-08) o se resuelve en una sola ejecución con `sendAndWait`.
- No se modificó ningún archivo del backend en este change (excepto el endpoint nuevo `POST /api/v1/recordatorios/run`, que lo hace el sub-agente A en paralelo).

---

*Actualizado en el change C-24 (n8n-workflows-orquestador-telegram). Previamente generado en C-09.*

