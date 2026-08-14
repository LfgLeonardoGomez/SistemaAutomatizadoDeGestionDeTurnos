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
| `sub-flujo-crear-turno.json` | Crea reserva temporal (fecha → hora); captura y confirmación en progreso | `Execute Workflow Trigger` (invocado por orquestador) | 🔄 Parcial (C-27) |
| `sub-flujo-cancelar-turno.json` | Lista los turnos activos del chat, el paciente elige y confirma | `Execute Workflow Trigger` (invocado por orquestador) | ✅ Completo |
| `sub-flujo-reprogramar-turno.json` | Lista los turnos activos, el paciente elige turno, fecha y horario, y confirma | `Execute Workflow Trigger` (invocado por orquestador) | 🔄 Reescrito (C-30) — falta E2E |
| `flujo-recordatorio.json` | Cron diario → `POST /api/v1/recordatorios/run` | `Schedule Trigger` (cron `0 10 * * *`) | ✅ Completo |
| `flujo-lista-espera.json` | Notificación de lista de espera (placeholder C-11) | `Webhook Trigger` | ⏳ Placeholder (C-11) |

## Workflows eliminados (histórico)

> 🗑️ Eliminados en C-24 porque quedaron **absorbidos** por el orquestador + sub-workflows. Mantenerlos generaría doble routing (un mismo update Telegram llegaría al orquestador Y al webhook del flujo viejo configurado en `@BotFather`).

- `flujo-reserva.json` → reemplazado por `sub-flujo-crear-turno.json` (con `Header Auth` y sin `paciente_id` en el body, consistente con C-23).
- `flujo-cancelacion.json` → reemplazado por `sub-flujo-cancelar-turno.json` (con `Header Auth`).

### Vocabulario de callbacks de cancelar

El flujo NO acepta ningún ID tipeado. Un formato de texto libre ya causó un
bucle infinito: el bot indicaba `/cancelar <ID>` (con espacio) y el parser solo
aceptaba `cancelar:<id>` (con dos puntos), así que el usuario seguía la
instrucción del propio bot y el sistema la rechazaba. Se eliminó el parseo
tipeado entero en vez de elegir un formato: el paciente no tiene por qué
conocer el ID de su turno.

| `callback_data` | Significado |
|---|---|
| `cmd:cancelar` | Listar los turnos activos del chat |
| `cmd:cancelar:turno_id:<id>` | Mostrar el paso de confirmación de ese turno |
| `cmd:cancelar:confirmado:<id>` | Ejecutar la cancelación |
| `cmd:menu` | Volver al menú principal y abandonar cualquier captura pendiente |

El botón de cancelar del recordatorio (que arma el **backend**, en
`telegram_service.format_recordatorio_keyboard`) emite
`cmd:cancelar:turno_id:<id>`, así que también pasa por la confirmación: un
toque accidental no debe costarle el turno al paciente.

### Vocabulario de callbacks de reprogramar

Mismo criterio que cancelar: **ninguna entrada tipeada**. Las claves son cortas
porque Telegram corta el `callback_data` en **64 bytes** y rechaza el botón
entero, en silencio.

| `callback_data` | Significado |
|---|---|
| `cmd:reprogramar` | Listar los turnos activos del chat |
| `cmd:reprogramar:t:<id>` | Ofrecer las fechas para ese turno |
| `cmd:reprogramar:t:<id>:f:<fecha>` | Ofrecer los horarios de esa fecha |
| `cmd:reprogramar:t:<id>:f:<fecha>:h:<hora>` | Pedir confirmación |
| `cmd:reprogramar:ok:<id>:<fecha>:<hora>` | Ejecutar la reprogramación |
| `cmd:reprogramar:turno_id:<id>` | **Forma larga.** La emite el BACKEND |

Esa última no es retrocompatibilidad opcional: el botón "Reprogramar" del
recordatorio lo arma `telegram_service.format_recordatorio_keyboard`, y por ahí
entra la mayoría de las reprogramaciones. Si el sub-flujo deja de aceptarla, ese
botón queda muerto **sin que nada falle visiblemente**.

> Regla que este flujo aprendió por las malas: **ningún botón emite un
> `callback_data` que el propio flujo no sepa procesar.** La versión anterior
> ofrecía `...:slot:none` cuando no había horarios; el parser lo leía como un
> horario elegido y terminaba en un `PUT` con `nueva_hora_inicio: "none"`, que el
> backend rechazaba con 422 y que —por no tener `fullResponse`— se le informaba
> al paciente como turno reprogramado.

### El escape hatch: `fresh_start`

`Normalizar Comando` marca `payload.fresh_start = true` en **todo** comando
reconocido, y `Code - Decidir Paso` de crear-turno lo usa para abandonar una
captura pendiente. Sin eso, quien deja una reserva a mitad de pregunta queda
atrapado hasta que la reserva expire: cualquier mensaje suyo se leería como
respuesta a una pregunta que ya olvidó.

**Un callback que no está en la lista de reconocidos no marca `fresh_start`**, y
peor: cae en la rama de texto libre, que lo despacha a crear-turno como
`respuesta_captura`. Es decir, se manda como si fuera el DNI que el bot estaba
esperando. Así estuvo `cmd:menu` —emitido por tres botones de cancelar y
reconocido por nadie— hasta que se lo agregó a la lista.

`cmd:menu` es el único comando reconocido que **no** asigna `comando`: se queda
en `'desconocido'` a propósito y cae en el fallback del Switch, que es
`Telegram - Mensaje de Ayuda`. No le agregues una rama — la ausencia ES el
ruteo.

> Al agregar un `callback_data` nuevo: si es un comando (algo que interrumpe lo
> que el paciente estaba haciendo), va en `esCallbackReconocido`. Si es un paso
> dentro de un flujo, no. Un botón cuyo callback no cae en ninguna de las dos
> categorías es un botón que rompe la conversación en silencio.

Si los necesitás para rollback, están en el historial de git: `git log -- n8n-workflows/flujo-reserva.json`.

### ⚠️ Teclados inline: el nodo Telegram no puede emitir listas dinámicas

El nodo `n8n-nodes-base.telegram` arma su teclado con una **fixedCollection**
(`replyMarkup: "inlineKeyboard"` + `inlineKeyboard.rows[].row.buttons[]`), o sea
filas **literales** escritas a mano. Sirve para menús fijos —el mensaje de ayuda
del orquestador, el "Pedir Rango" de crear-turno— y no sirve cuando la cantidad
de botones depende de los datos: N turnos activos, N slots libres, N fechas.

**El atajo que parece funcionar y no funciona:** meter la forma cruda de la API
de Telegram dentro de `options`:

```jsonc
// ❌ NO: `reply_markup` no es un parámetro del nodo Telegram.
//        Lo descarta en silencio. El texto llega, los botones no existen.
"options": { "reply_markup": { "inline_keyboard": "={{ $json.inline_keyboard }}" } }
```

No hay error, no hay warning, y la ejecución figura en verde en n8n. El síntoma
es un mensaje con el texto correcto y sin un solo botón. Así estuvieron rotos
`sub-flujo-cancelar-turno`, `sub-flujo-reprogramar-turno` y `flujo-lista-espera`.

**El patrón correcto** es bajar a la API con un nodo `httpRequest`:

```jsonc
{
  "method": "POST",
  "url": "=https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage",
  "sendBody": true,
  "specifyBody": "json",
  "jsonBody": "={{ JSON.stringify({ chat_id: ($json.chat_id), text: ($json.mensaje), reply_markup: { inline_keyboard: ($json.inline_keyboard) } }) }}"
}
```

Requiere `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` en el servicio n8n (ya está en
`docker-compose.yml`), porque la imagen bloquea `$env` en expresiones por
default. Al escribir la expresión, cuidado con que el payload no contenga la
secuencia `}}`: cierra el bloque antes de tiempo y trunca el mensaje. Separá las
llaves con un espacio (`} }`).

> Deuda conocida: este patrón usa `$env.TELEGRAM_BOT_TOKEN`, que es **un token
> por instancia**, mientras que la credencial `Telegram account` apunta al mismo
> bot único. Los dos son single-tenant hoy; cuando entre un bot por profesional
> (v2.0) hay que resolver ambos, no solo este.

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

### ⚠️ El `id` de una credencial es local a cada instancia — referenciala por `name`

**Leé esto antes de "corregir" un id de credencial en el repo.**

Los ids de credenciales los genera cada instancia de n8n cuando la credencial se
crea. Son locales a esa instancia y **nunca coinciden entre dos máquinas**:

| Credencial | Instancia de Leonardo | Otra instancia |
|---|---|---|
| Telegram | `TZgUFY41hdHCU9fu` | `telegram-bot-credentials` |
| API Key del profesional | `T9DkbhELoxyryvzg` | (otro) |

Si commiteás el id de tu instancia, al otro se le queda el nodo con una credencial
colgada. Y no falla al importar: falla **en runtime**. Como los nodos de Telegram
suelen estar al final del flujo, el error aparece lejos de la causa.

Ya nos pasó tres veces — con `profesional-api-key`, y con Telegram en `943fdb7`.

**La regla:** lo único portable entre instancias es el `name`. Cuando n8n importa un
workflow cuyo id de credencial no existe localmente, **resuelve por nombre** y
reescribe el id con el suyo. Entonces:

- El `name` es el contrato. Tiene que ser **exacto**, mayúsculas incluidas.
- El `id` del repo es irrelevante. No hace falta tocarlo ni "arreglarlo".

**Nombres canónicos** (los nodos llevan además un campo `notes` que repite esto):

| Tipo de credencial | `name` que va en el repo |
|---|---|
| `telegramApi` | `Telegram account` |
| `httpHeaderAuth` (X-API-Key) | `Profesional API Key` |

Si tu instancia tiene la credencial con otro nombre, **renombrala en tu n8n** para
que coincida con el repo. No cambies el repo para que coincida con tu instancia:
eso le rompe el entorno al otro.

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
| `sub-flujo-cancelar-turno.json` | `/turnos/activos` | GET | Header Auth | Turnos CONFIRMADOS y futuros del chat |
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

> ⚠️ **Email: almacenado pero no enviado**: Cuando un paciente proporciona un email en la confirmación del turno, se crea un registro de destinatario en la base de datos (canal `EMAIL`), pero **no existe un motor de envío de emails en el backend**. Los recordatorios se envían solo por Telegram en v1.0.

## Testing

### Harness de chequeos (`n8n-workflows/tests/`)

```bash
# Reglas estaticas sobre todos los workflows. Cada una existe porque el defecto
# que detecta YA se rompio en produccion, y n8n reporta ejecucion verde en todos.
node n8n-workflows/tests/check-workflows.js
node n8n-workflows/tests/check-workflows.js reprogramar   # filtro por substring

# Comportamiento: ejecuta los Code nodes de reprogramar con datos simulados,
# incluyendo el round trip -- todo callback_data que el flujo emite se le
# devuelve a su propio parser y tiene que resolver al paso que pretendia.
node n8n-workflows/tests/check-reprogramar-behavior.js
```

> `check-workflows.js` falla hoy en `sub-flujo-crear-turno :: HTTP - GET
> Disponibilidad`, que no declara `neverError`: un 500 del backend tira excepción
> y el paciente recibe silencio. Es un defecto real y **no es un one-liner**:
> agregar el flag sin distinguir error de lista vacía haría que un 500 se lea
> como "no hay horarios disponibles". Pendiente de su propio change.

### Tests de parseo estático (TDD para n8n)

```bash
# Todos los JSON parsean
for f in n8n-workflows/*.json; do
  python -c "import json; json.load(open('$f', encoding='utf-8'))" || echo "FAIL: $f"
done

# Estructura: cada HTTP Request usa Generic Credential Type → httpHeaderAuth
#
# `authentication` es un STRING, no un objeto. HttpRequestV3 lo compara contra
# 'genericCredentialType' | 'predefinedCredentialType' | 'none'. Una forma anidada
# ({"type": "generic", "properties": {...}}) no matchea ninguno, cae a "sin auth",
# y el request sale SIN el header → 401. Es silencioso: n8n no se queja al importar.
for f in n8n-workflows/sub-flujo-*.json n8n-workflows/flujo-lista-espera.json n8n-workflows/flujo-recordatorio.json; do
  echo "=== $f ==="
  python -c "import json; d=json.load(open('$f', encoding='utf-8')); nodes=[n for n in d['nodes'] if n['type']=='n8n-nodes-base.httpRequest']; [print(n['name'], '→', n['parameters'].get('authentication','MISSING'), '/', n['parameters'].get('genericAuthType','MISSING')) for n in nodes]"
done

# Lo mismo para el body de un POST/PUT: sendBody + specifyBody:"json" + jsonBody.
# Un campo `body` suelto no es schema válido y el request sale con el body vacío.

# Ningún nodo declara `options.reply_markup`: no es un parámetro del nodo Telegram,
# se descarta en silencio y el mensaje sale sin botones. Ver la sección de teclados
# inline más arriba. Debe imprimir 0.
python -c "
import json, glob
malos = [(f, n['name']) for f in glob.glob('n8n-workflows/*.json')
         for n in json.load(open(f, encoding='utf-8'))['nodes']
         if 'reply_markup' in (n.get('parameters') or {}).get('options', {})]
print(len(malos), 'nodos con reply_markup en options')
[print('  FAIL:', f, '::', name) for f, name in malos]
"

# Orquestador referencia los 3 sub-workflows
python -c "import json; d=json.load(open('n8n-workflows/orquestador.json', encoding='utf-8')); nodes=[n for n in d['nodes'] if n['type']=='n8n-nodes-base.executeWorkflow']; [print(n['name'], '→', n['parameters'].get('workflowId',{}).get('value','MISSING')) for n in nodes]"
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

