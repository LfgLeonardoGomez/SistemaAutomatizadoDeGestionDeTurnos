## Context

### Realidad verificada en el código

- `backend/app/dependencies.py:98-115` (`get_profesional_by_api_key`): todo endpoint bajo `CurrentProfesionalDep` exige `X-API-Key` header válido. Sin él, **401**.
- `backend/app/dependencies.py:118-139` (`get_profesional_by_telegram_secret_token`): el webhook `POST /webhooks/telegram` exige `X-Telegram-Bot-Api-Secret-Token` válido. Sin él, **403**.
- `backend/app/routers/turnos.py:48-78` y siguientes: la reserva recibe `paciente_id` opcional; en el flujo del orquestador el bot NO conoce `paciente_id` (lo deriva el backend vía DNI en confirmación, C-23 TAREA 7). El orquestador debe llamar `POST /turnos` sin `paciente_id` y el backend crea el turno en estado `RESERVADO_TEMPORAL` sin beneficiario hasta que se confirma.
- `backend/app/routers/lista_espera.py:14-34`: `POST /lista-espera` requiere `paciente_id`, `fecha_solicitada`, `telegram_chat_id`. **No** existe un endpoint `GET /lista-espera/siguiente` real en el router (verificado: solo `POST` y `DELETE`); el placeholder de `flujo-lista-espera.json` apunta a una ruta que el backend no expone. Esto es deuda del change C-11 que queda **fuera de alcance** de C-24 (es un gap del backend, no de los workflows).
- `backend/app/services/telegram_service.py:471-485` (`accion_reservar_temporal`): ya propaga `telegram_chat_id` al servicio. C-23 deja el contrato listo para que n8n lo use (campo `telegram_chat_id` opcional en `ReservaTurnoRequest`).
- Los 4 workflows actuales en `n8n-workflows/`:
  - `flujo-reserva.json` (15 nodos): webhook `reserva` → HTTP `GET /turnos/disponibles` → format → Telegram send → (loop) → HTTP `POST /turnos` con `paciente_id = $json.message?.chat?.id` → format → Telegram send con botón "Confirmar" → HTTP `PUT /turnos/{id}/confirmar` con `dni=99999999` hardcodeado.
  - `flujo-cancelacion.json` (9 nodos): webhook `cancelar` → regex `/cancelar\s+(\d+)` → HTTP `PUT /turnos/{id}/cancelar` (sin auth) → format → Telegram send.
  - `flujo-recordatorio.json` (4 nodos): schedule cada 1h → HTTP `GET /turnos/pendientes` (placeholder, no existe en backend) → format → Telegram send.
  - `flujo-lista-espera.json` (4 nodos): webhook `lista-espera` → HTTP `GET /lista-espera/siguiente` (placeholder, no existe) → format → Telegram send.
- **Gaps identificados** en los workflows actuales:
  1. **Cero** llevan `X-API-Key`. Todos reciben 401.
  2. `flujo-reserva.json` hardcodea `dni=99999999` en la confirmación — no usa el `paciente_id` real.
  3. `flujo-reserva.json` línea 144: `"paciente_id": "={{ $json.message?.chat?.id }}"` mapea `chat_id` a `paciente_id`, lo cual es semánticamente incorrecto (un chat no es un paciente).
  4. Los 4 placeholders apuntan a endpoints que el backend no expone (`/turnos/pendientes`, `/lista-espera/siguiente`). Eso es scope de C-10/C-11, **no** de C-24.
  5. **No existe `flujo-reprogramar.json`** (a pesar de estar en el switch del orquestador modelo). Hay que crearlo.

### Esqueleto del orquestador (modelo del usuario)

`C:\Users\pocho\Downloads\My workflow (4).json` (584 líneas, 16 nodos):

| # | Nodo | Tipo | Estado actual | Observación |
|---|------|------|---------------|-------------|
| 1 | `Telegram Trigger` | `telegramTrigger` | **inactivo, sin cablear** | Tiene credencial `Telegram account` (`a0p5Lql7MVWCO4tP`). Es el entry point que el usuario quiere activar. |
| 2 | `On form submission` | `formTrigger` | **activo, conectado** | Entry point viejo. El usuario lo quiere reemplazar por Telegram Trigger. |
| 3 | `Edit Fields` | `set` | conectado | Renombra `Mensaje/chat_id/Nombre` a `mensaje/chatId/nombre`. |
| 4 | `Buscar Usuario (Mock DB)` | `code` | conectado | Mock de BD en JS hardcodeado con 10 pacientes. **Reemplazar** por lookup real. |
| 5 | `If` | `if` | conectado | `existe == true` → Form1; `existe == false` → Form (registro). |
| 6 | `Select rows from a table` | `postgres` | **aislado** | Nodo postgres sin conexiones. Reemplazar por HTTP a `GET /pacientes?dni=X` o usar el backend. |
| 7 | `Form` / `Form1` | `form` | conectado | Formularios web. **No aplica** a Telegram. Eliminar. |
| 8 | `Guardar Paciente` | `set` | conectado | Guarda el paciente en una variable. Reemplazar por HTTP al backend. |
| 9 | `Merge` | `merge` | conectado | Combina los 2 paths. **No aplica** en flujo lineal. |
| 10 | `Edit Fields2` | `set` | conectado | Extrae `opcion` del form. Reemplazar por extracción del comando Telegram. |
| 11 | `Switch` | `switch` | conectado, **3 reglas** | `Reprogramar_turno` / `Cancelar_turno` / `Crear_turno`. **REUTILIZABLE** tal cual, adaptando `leftValue` a `$json.message.text` o `$json.callback_query.data`. |
| 12 | `Reprogramar_turno` | `executeWorkflow` | **disabled, sin wf** | Cableado al output 0 del switch. Crear el sub-workflow. |
| 13 | `Cancelar_turno` | `executeWorkflow` | **disabled, sin wf** | Cableado al output 1. Crear el sub-workflow. |
| 14 | `Crear_turno` | `executeWorkflow` | **disabled, sin wf** | Cableado al output 2. Crear el sub-workflow. |
| 15 | `Edit Fields1` | `set` | conectado (path de error) | Mapeo alternativo. Conservar como path de fallback. |
| 16 | `Telegram - Enviar*` | (no existe aún) | — | Agregar al final de cada sub-workflow. |

**Conclusión del análisis del esqueleto**: la estructura de **Switch + 3 executeWorkflow** es exactamente lo que el usuario quiere. Hay que:

1. Cambiar el entry point de `On form submission` a `Telegram Trigger`.
2. Eliminar el path de Forms, el mock DB, y el postgres node.
3. Reemplazar el código de Mock DB por una llamada HTTP al backend (o directamente al `paciente_service` del backend, pero como n8n solo consume REST, va por HTTP).
4. Mantener el `Switch` (3 reglas) tal cual.
5. Crear los 3 sub-workflows.
6. Agregar manejo de **callback_query** además de texto (los botones inline de Telegram generan `callback_query`, no `message`).
7. Agregar `X-API-Key` a TODO HTTP Request.

### Stack y constraints

- n8n (cualquier versión reciente con nodo `telegramTrigger` v1.2 y `executeWorkflow` v1.3, que es lo que usa el esqueleto).
- FastAPI + SQLAlchemy 2.0 async (backend, **no modificado**).
- Sin `tenant_id` (single-tenant por instancia en v1.0; multi-tenant **por profesional** dentro de la instancia, vía `profesional_id` en JWT/`X-API-Key`).
- TDD estricto en el backend (no aplica a workflows JSON; "test" aquí significa validación estática del JSON + verificación E2E contra el backend en entorno de demo).

## Goals / Non-Goals

**Goals:**
1. Lograr E2E funcional `Telegram → n8n → backend` con multi-tenancy (cada request lleva `X-API-Key` correcta, el `profesional_id` se respeta vía el `Header Auth` credential).
2. Un **orquestador** como single entry point del bot del profesional, con `Telegram Trigger` + `Switch` por comando (texto o callback) + `executeWorkflow` por caso.
3. Tres sub-workflows (`Crear_turno`, `Cancelar_turno`, `Reprogramar_turno`) que encapsulan el flujo conversacional completo de su acción.
4. **`flujo-lista-espera`** queda como placeholder con `X-API-Key` agregada (deuda C-11; fuera de alcance C-24).
5. **`flujo-recordatorio`** se implementa: Schedule Trigger diario → HTTP al backend (`POST /api/v1/recordatorios/run?fecha=mañana`) que itera por profesionales activos, busca turnos del día siguiente con `obtener_turnos_para_recordar`, y los envía usando `enviar_recordatorio_telegram` + `marcar_recordatorio_enviado`. La hora del cron es configurable (default 10:00 hora local del profesional).
6. Eliminar los flujos viejos (`flujo-reserva`, `flujo-cancelacion`) para evitar doble routing.
7. Documentar el patrón de credenciales en `n8n-workflows/README.md` y en la KB.

**Non-Goals:**
- Modificar el backend para los flujos `Crear`/`Cancelar`/`Reprogramar`/`Lista-espera` (los endpoints ya están, el auth ya está).
- Crear un único orquestador que atienda múltiples bots (n8n's `Telegram Trigger` autentica con UN token; un orquestador por bot es el modelo natural y más simple).
- Implementar el endpoint faltante `/lista-espera/siguiente` (deuda de C-11, fuera de alcance — `flujo-lista-espera` queda como placeholder).
- Persistir estado conversacional en el orquestador (n8n workflows son stateless entre ejecuciones; el state machine conversacional multi-step vive en `telegram_service.py` del backend, C-08; el orquestador trata cada comando como una operación atómica o delega el wizard completo al sub-workflow, que también es stateless y resuelve el slot en una pasada).
- Soporte de email u otros canales en el orquestador (no aplica al dominio Telegram).
- Reemplazar el router conversacional `telegram_service.procesar_mensaje` del backend (es paralelo al orquestador, no lo reemplaza).
- Reemplazar el scheduler interno de APScheduler del backend (sigue activo; el endpoint nuevo lo usa como helper si el scheduler está corriendo, o lo invoca directo n8n).
- Configurar n8n automáticamente (las credenciales se configuran a mano al importar por profesional — el alcance es entregar los JSON + README claros).

## Decisions

### Decisión 1 (CLAVE): un orquestador por bot (modelo natural de n8n)

**Elegido**: cada profesional con bot tiene **una instancia** del orquestador importada en n8n. Esa instancia tiene **2 credenciales** configuradas: `Telegram Bot` (token del bot) y `Header Auth` (`X-API-Key: <profesional.api_key>`).

**Alternativas consideradas:**
- **A) Un único orquestador para N bots**: el orquestador recibiría updates de todos los bots y tendría que mapear `bot_token → profesional` por algún lado. **Rechazada** porque el nodo `Telegram Trigger` de n8n autentica con UN token por workflow; un orquestador multi-bot exigiría reemplazar el trigger por un `Webhook Trigger` + validación de `X-Telegram-Bot-Api-Secret-Token` + un `IF` por profesional, lo cual rompe el modelo "1 trigger = 1 bot" y dificulta el debugging por profesional. El modelo "1 orquestador por bot" es el patrón canónico de n8n para Telegram y minimiza la superficie de acoplamiento.
- **B) Reemplazar el orquestador n8n por más lógica en el backend**: ya está hecho (C-08 / C-17 con `telegram_service.procesar_mensaje`). **Rechazada** porque el usuario explícitamente pidió el orquestador n8n como **capa de orquestación visible** en la demo de la tesis. El backend procesa Telegram vía su propio webhook, pero el orquestador n8n **demuestra la alternativa** y permite ver los workflows visualmente.

**Rationale**: un orquestador por bot, con credenciales dedicadas, es la solución que minimiza acoplamiento, maximiza aislamiento entre profesionales y se alinea con los patrones canónicos de n8n. El `Header Auth` credential garantiza que el `X-API-Key` se inyecta en **todos** los `HTTP Request` nodes del workflow sin hardcodear.

### Decisión 2: ¿Cómo se mapea el entry point del bot a comandos del orquestador?

**Elegido**: el orquestador maneja **dos fuentes de comandos** dentro del `Telegram Trigger`:
- **`message.text`** para comandos textuales: `/reservar`, `/cancelar`, `/reprogramar`, y también texto libre que el `Switch` matching con palabras clave ("quiero un turno", "cancelar", "reprogramar").
- **`callback_query.data`** para los botones inline (Telegram genera `callback_query` cuando el usuario toca un botón, no `message`).

El `Switch` se reemplaza por un `Code` node que normaliza ambas fuentes a un campo `comando` único (`"crear" | "cancelar" | "reprogramar" | "lista_espera" | "reminder" | "desconocido"`), y luego un `Switch` con 3 reglas (`crear`, `cancelar`, `reprogramar`) que dispatch-ea a los `executeWorkflow`. Los casos `lista_espera` y `reminder` también dispatchean a sub-workflows (Decisión 5).

**Alternativas consideradas:**
- **A) `Switch` directo con 6 reglas (3 comandos + 3 callbacks)**: posible, pero el `leftValue` del Switch de n8n es una expresión por regla, y la lógica de "si es callback y empieza con X, derivar a Y" se vuelve spaghetti de expresiones. Un `Code` node que normaliza + un `Switch` de 3 ramas es **más legible** y testeable.
- **B) Texto libre parseado por LLM**: over-engineering. El switch de palabras clave es suficiente para v1.

**Rationale**: separar normalización (Code) de routing (Switch) es el patrón clásico de pipelines; el Code node es chiquito y obvio, el Switch queda limpio con 3 ramas.

### Decisión 3: El orquestador es stateless; el state conversacional multi-step vive en los sub-workflows o en el backend

**Elegido**: el orquestador y los sub-workflows son **stateless entre ejecuciones** (n8n convention). Para flujos multi-step (crear turno = fecha → hora → datos → confirmar), el sub-workflow `Crear_turno` o bien:
- **Opción C3-i**: hace todo en una sola ejecución usando un nodo `Telegram - Ask` que envía botones y **espera** el callback_query del usuario vía el mismo `Telegram Trigger` (patrón "ask & wait" de n8n, que sí es blocking per execution).
- **Opción C3-ii**: delega al backend vía HTTP (manda la fecha al backend, este responde con slots, etc.) y el backend persiste el estado de la conversación.

**Elegido C3-i** para v1: el sub-workflow `Crear_turno` usa `Telegram - Send and Wait for Response` (nodo nativo de n8n) para cada paso del wizard. Esto mantiene la lógica del flujo visible en n8n (mejor para la demo) y evita acoplar el sub-workflow a la API interna de state del backend.

**Alternativas consideradas:**
- **A) Persistir state en Redis desde n8n**: factible pero añade infra. **Rechazada** para v1; queda como mejora futura.
- **B) Persistir state en n8n `staticData`**: factible por profesional pero rompe entre reinicios de n8n. **Rechazada**.
- **C) Confiar en el backend como state machine**: lo que ya hace C-08. **Rechazada** para C-24 porque el orquestador n8n es la **capa visible**; usar el backend como state machine escondería la lógica en n8n.

**Rationale**: `Telegram - Send and Wait for Response` es el patrón canónico de n8n para wizards conversacionales, está documentado, y el timeout default (10 min) coincide con `RESERVA_TEMPORAL_MINUTOS=10` del backend, lo que da una simetría natural.

### Decisión 4: `X-API-Key` se inyecta vía `Header Auth` credential a nivel de workflow

**Elegido**: cada sub-workflow y los workflows viejos modificados declaran una credencial `Header Auth` (nombre sugerido: `Profesional API Key`) con header name `X-API-Key` y valor `<profesional.api_key>`. Los `HTTP Request` nodes referencian esa credencial en `Authentication → Generic Credential Type → Header Auth`. La credencial se configura **una vez** al importar el workflow por profesional.

**Alternativas consideradas:**
- **A) Hardcodear `X-API-Key: {{ $env.FASTAPI_API_KEY }}` en cada HTTP Request node**: funciona pero requiere una env var global en n8n. **Rechazada** porque multi-tenancy exige una `api_key` por profesional; una env var global fuerza a usar la misma key para todos los bots, lo que rompe el aislamiento C-16.
- **B) Pasar `X-API-Key` por el body / query string**: **rechazada** por seguridad (la key podría quedar en logs de n8n y de proxies).
- **C) Usar JWT del profesional en lugar de `api_key`**: factible pero más complejo (exige login + refresh). La `api_key` es exactamente para integraciones server-to-server como n8n (C-15 la diseñó así). **Rechazada** porque añade fricción sin ganancia.

**Rationale**: `Header Auth` credential es el patrón nativo de n8n para autenticación por header; el `X-API-Key` queda fuera de logs del workflow (n8n enmascara credentials en exec logs) y se puede rotar tocando solo la credencial.

### Decisión 5: `flujo-lista-espera` y `flujo-recordatorio` son independientes del orquestador

**Elegido**:
- `flujo-lista-espera.json`: **placeholder** independiente (deuda C-11, fuera de alcance C-24). Solo se le agrega `X-API-Key`. Su endpoint `/lista-espera/siguiente` no existe en el backend, así que el workflow queda con un `notes: "PLACEHOLDER: ..."` y no se ejecuta realmente.
- `flujo-recordatorio.json`: **se reescribe** como workflow funcional que corre **una vez al día** (cron configurable, default 10:00 hora local). El workflow es el **orquestador del recordatorio**: hace `Schedule Trigger` → `Code` (calcula fecha = "mañana") → `HTTP Request` al backend (`POST /api/v1/recordatorios/run?fecha=mañana` con `X-API-Key`) → el backend itera por profesionales activos, busca turnos a recordar y los envía. Ver Decisión 8 (endpoint nuevo del backend).

**Alternativa considerada (rechazada)**: que n8n lea Google Calendar directo para encontrar los eventos del día siguiente. **Rechazada** porque duplica la lógica de OAuth2 multi-tenant que el backend ya tiene (C-15, `CalendarService` per-profesional con refresh_token). El backend ya sincroniza los turnos confirmados con Google Calendar en `confirmar_turno`; el endpoint `POST /api/v1/recordatorios/run` es la única fuente de verdad para "qué turnos recordar". Además, C-23 ya dejó `TurnoDestinatario` con el `chat_id` del paciente, lo que evita que n8n tenga que resolverlo.

**Alternativa considerada (rechazada)**: que el workflow `flujo-recordatorio` se integre al orquestador como un sub-workflow. **Rechazada** porque el orquestador es el **router conversacional** (comandos del paciente); los recordatorios son **notificaciones push del sistema** que no derivan de un comando. Mantenerlos separados respeta la separación de responsabilidades y simplifica el orquestador.

**Rationale**: el backend es la fuente de verdad (tiene la lógica de `obtener_turnos_para_recordar` + `enviar_recordatorio_telegram` + `TurnoDestinatario`); n8n es el **trigger** (cron) y el **transport** (HTTP). Cada uno hace lo que sabe hacer mejor.

### Decisión 6: Tipos de auth n8n usados en cada nodo HTTP Request al backend

**Elegido** (matriz):

| Workflow | Nodo HTTP | Auth | Header adicional |
|----------|-----------|------|------------------|
| `orquestador.json` | (no hace HTTP directo, solo dispatch a sub-workflows) | — | — |
| `sub-flujo-crear-turno.json` | todos los HTTP Request al backend | `Header Auth` (credencial `Profesional API Key`) | `X-API-Key` |
| `sub-flujo-cancelar-turno.json` | idem | idem | idem |
| `sub-flujo-reprogramar-turno.json` | idem | idem | idem |
| `flujo-lista-espera.json` (modificado) | idem | idem | idem |
| `flujo-recordatorio.json` (modificado) | idem | idem | idem |
| `Telegram Trigger` (en orquestador) | — | `Telegram Bot` (credencial `Telegram account`) | n/a |
| `Telegram - Send Message` (en cada sub-workflow) | — | `Telegram Bot` (misma credencial que el trigger) | n/a |

**No** se usa `X-Telegram-Bot-Api-Secret-Token` en los workflows porque ese header lo valida **solo** el webhook `POST /webhooks/telegram` del backend, no los endpoints REST. Los workflows consumen los endpoints REST (`/turnos/*`, `/lista-espera/*`), que validan `X-API-Key`.

### Decisión 7: Reemplazo del `Buscar Usuario (Mock DB)` por lookup real

**Elegido**: el `Code` node que mockea la BD de pacientes se elimina. En su lugar, cada sub-workflow (especialmente `Crear_turno` y `Reprogramar_turno`) llama **directamente** a los endpoints del backend (`GET /turnos/disponibles`, `POST /turnos`, `PUT /turnos/{id}/confirmar`) y el backend maneja la resolución de beneficiario por DNI (`paciente_service.crear_o_obtener_paciente`, C-04 / C-23 TAREA 7).

**Rationale**: el orquestador n8n no debe conocer la lógica de dominio (resolución de paciente). La unicidad `UNIQUE(profesional_id, dni)` y la función `crear_o_obtener_paciente` ya están en el backend y son la fuente de verdad.

### Decisión 8 (NUEVA — introducida tras OQ-3 con implementación del recordatorio): nuevo endpoint del backend `POST /api/v1/recordatorios/run`

**Elegido**: C-24 introduce **un nuevo endpoint en el backend** que n8n consume para el flujo de recordatorios:

- **Path**: `POST /api/v1/recordatorios/run`
- **Query params**: `?fecha=YYYY-MM-DD` (default: mañana en zona horaria del servidor)
- **Auth**: `X-API-Key` header (mismo `Header Auth` credential que usan los sub-workflows)
- **Comportamiento**:
  1. Itera por `Profesional` activos (`is_active=True`).
  2. Para cada uno, llama a `obtener_turnos_para_recordar(db, profesional_id, horas_antes)` con `horas_antes` calculado a partir del `fecha` param (≈ 24h).
  3. Para cada turno candidato, llama a `enviar_recordatorio_telegram(turno, bot_token=profesional.telegram_bot_token)`. Si el profesional no tiene `telegram_bot_token`, se loguea warning y se salta.
  4. Si el envío retorna `True` (éxito o no-hay-destinatario), llama a `marcar_recordatorio_enviado(db, turno.id, profesional.id)`.
  5. Commit por profesional (Patrón A).
- **Response (200)**: `RecordatorioRunResponse { total_candidatos: int, total_enviados: int, total_fallidos: int, errores: list[RecordatorioError] }`.
- **Errores**: si un profesional falla, no rompe el batch — se loguea y se continúa con el siguiente.

**Archivos del backend**:
- `backend/app/routers/recordatorios.py` (nuevo, monta el router con prefix `/recordatorios` y auth `get_profesional_by_api_key`).
- `backend/app/services/recordatorio_service.py` (nuevo, encapsula la lógica de iterar + llamar las funciones existentes de `notificacion_service`).
- `backend/app/schemas/recordatorio.py` (nuevo, `RecordatorioRunResponse`, `RecordatorioError`).
- `backend/tests/test_recordatorio_router.py` (nuevo, tests del endpoint con testcontainers[postgres]).
- `backend/app/main.py` (modificado, incluye el nuevo router).

**Alternativas consideradas**:
- **A) n8n itera por profesional y llama a un endpoint por profesional**: el endpoint sería `GET /api/v1/profesionales/activos` + por cada uno `GET /api/v1/turnos/recordatorios?profesional_id=X&fecha=Y`. **Rechazada** porque multiplica las requests (1 + N) y duplica la lógica de iteración en n8n. Mejor: un solo endpoint batch que itera server-side.
- **B) Reemplazar el scheduler APScheduler interno del backend**: **fuera de alcance** C-24. El endpoint nuevo es **complementario**: cuando n8n no está disponible, el APScheduler sigue funcionando (con su propia lógica que ya existe en `notificacion_service.obtener_turnos_para_recordar` + `enviar_recordatorio_telegram`). C-24 agrega la opción n8n-driven; no rompe la opción backend-driven.
- **C) Reusar directamente `obtener_turnos_para_recordar` y `enviar_recordatorio_telegram` en un solo nodo Code de n8n**: **rechazada** porque n8n no debería tener lógica de dominio ni acceso directo a la DB.

**Rationale**: el backend tiene la lógica y la DB; n8n tiene el cron y el HTTP. Esta división es la que mejor respeta el principio de "single source of truth" (el backend) y "single trigger orchestration" (n8n).

## Risks / Trade-offs

- **R1 (CRÍTICO): el esqueleto del orquestador es solo eso, un esqueleto.** No es production-ready: tiene Forms, mock DB, postgres node aislado, y los 3 sub-workflows referenciados no existen. Mitigación: el apply phase va a **reescribir el esqueleto desde cero**, manteniendo solo el patrón `Telegram Trigger → Code (normalizar) → Switch → executeWorkflow × 3`. El esqueleto sirve de inspiration, no de base.
- **R2 (ALTO): cambio del entry point de `On form submission` a `Telegram Trigger` requiere entender el payload de updates de Telegram.** El esqueleto mapeaba `Mensaje/chat_id/Nombre` (form fields); el payload real de Telegram es `{ message: { text, chat: { id }, from: { first_name, last_name } }, callback_query: {...} }`. Mitigación: el `Code` node de normalización documenta explícitamente las dos formas (`message` y `callback_query`) y devuelve `{ comando, chat_id, profesional_api_key, payload }`.
- **R3 (ALTO): la auth multi-tenant requiere que cada workflow sepa QUÉ profesional atiende el chat.** La respuesta es: el orquestador **es por bot** (Decisión 1), por lo que la `api_key` se configura a nivel de workflow instance y es **constante** para todas las ejecuciones. n8n credentials se configuran una vez y se reutilizan en todos los nodos. No hace falta pasar `profesional_id` por el payload.
- **R4 (MEDIO): el orquestador n8n y el webhook del backend (`POST /webhooks/telegram`) son entry points redundantes.** Telegram solo entrega updates al **último** webhook configurado en `@BotFather`, así que no hay duplicación si se configura solo el orquestador. Mitigación: el README documenta explícitamente que `@BotFather` se configura **una vez**, apuntando al orquestador n8n (recomendado, OQ-1). El webhook del backend queda como alternativa documentada.
- **R5 (MEDIO): el placeholder `flujo-lista-espera` apunta a un endpoint que el backend no expone** (`/lista-espera/siguiente`). Deuda de C-11. C-24 no lo implementa. Mitigación: el `Header Auth` se agrega igual; el `notes: "PLACEHOLDER: ..."` se mantiene.
- **R6 (BAJO): el sub-workflow `Crear_turno` con `Send and Wait for Response` puede tener timeouts** si el usuario no responde. Mitigación: configurar el timeout del nodo en 10 min (= `RESERVA_TEMPORAL_MINUTOS`); en timeout, enviar mensaje "Tu reserva expiró, iniciá de nuevo con /reservar".
- **R7 (BAJO): la rotación de `api_key` requiere reconfigurar el `Header Auth` credential en n8n.** No se puede hacer en caliente desde el orquestador. Mitigación: documentar el procedimiento en el README.
- **R8 (NUEVO, BAJO): si n8n está caído cuando corre el cron de recordatorios, no se mandan.** Mitigación: el APScheduler interno del backend (C-08) sigue activo como fallback; documentar en el README que el sistema de recordatorios tiene **dos motores** (n8n como primario, APScheduler como fallback) y que ambos llaman a la misma lógica de `notificacion_service` — no se duplican envíos porque el campo `recordatorio_enviado` evita doble dispatch.

## Migration Plan

### Fase 0: gate de gobernanza (BAJA — propuesta, no necesita confirmación humana explícita)

- [x] 0.1 Confirmar OQ-1 (¿n8n orquestador es **el** entry point, o es **un** entry point paralelo al webhook del backend?) → **RESUELTA**: n8n orquestador es EL entry point (`@BotFather` apunta a n8n). El webhook del backend queda como alternativa documentada.
- [x] 0.2 Confirmar OQ-2 (¿`flujo-lista-espera` y `flujo-recordatorio` quedan independientes del orquestador?) → **RESUELTA**: sí, ambos independientes. `flujo-lista-espera` como placeholder (deuda C-11). `flujo-recordatorio` reimplementado con cron + endpoint nuevo del backend.
- [x] 0.3 Confirmar OQ-3 (¿se implementan los endpoints placeholder `/turnos/pendientes` y `/lista-espera/siguiente` en este change?) → **RESUELTA**: solo se implementa el endpoint del recordatorio (`POST /api/v1/recordatorios/run`) que C-24 introduce. `/lista-espera/siguiente` queda como placeholder.

### Fase 1: workflow del orquestador (rewrite del esqueleto)

1. Crear `n8n-workflows/orquestador.json` desde cero, basado en el patrón:
   ```
   Telegram Trigger (con credencial Telegram Bot)
     → Code (normalizar message.text / callback_query.data → { comando, chat_id, payload })
       → Switch (3 reglas: crear / cancelar / reprogramar)
         → executeWorkflow "Crear_turno" (rama 0)
         → executeWorkflow "Cancelar_turno" (rama 1)
         → executeWorkflow "Reprogramar_turno" (rama 2)
   ```
2. Eliminar los nodos del esqueleto que no aplican: `On form submission`, `Edit Fields` (form), `Buscar Usuario (Mock DB)`, `Select rows from a table`, `Form`, `Form1`, `Edit Fields1`, `Guardar Paciente`, `Merge`, `Edit Fields2`.
3. Mantener el nodo `Switch` (3 reglas) tal cual, ajustando solo el `leftValue` para que matchee el campo `comando` normalizado.

### Fase 2: sub-workflows

1. Crear `sub-flujo-crear-turno.json` (similar a `flujo-reserva.json` viejo, pero con `Header Auth` credential, sin `paciente_id` en el body, usando `Send and Wait for Response` para el wizard).
2. Crear `sub-flujo-cancelar-turno.json` (similar a `flujo-cancelacion.json` viejo, con `Header Auth`).
3. Crear `sub-flujo-reprogramar-turno.json` (basado en `accion_iniciar_reprogramacion` y `accion_reprogramar_turno` del backend; usa `Send and Wait for Response`).
4. Cada sub-workflow recibe del orquestador: `{ chat_id, comando, payload }`. Si necesita más state (turno_id, fecha seleccionada), lo maneja internamente con `Send and Wait for Response` + variables del execution context.

### Fase 3: actualizar workflows viejos + implementar recordatorio

1. `flujo-lista-espera.json`: agregar `Header Auth` credential al nodo `HTTP Request - Placeholder Lista Espera`. Dejar el `notes: "PLACEHOLDER..."` intacto.
2. `flujo-recordatorio.json`: **reescribir** desde cero como workflow funcional:
   - `Schedule Trigger` (cron configurable, default 10:00 hora local)
   - `Code` node: calcula `fecha = mañana` (YYYY-MM-DD) en zona horaria del servidor
   - `HTTP Request`: `POST {BACKEND_URL}/api/v1/recordatorios/run?fecha={fecha}` con `X-API-Key` (Header Auth credential)
   - Manejo de respuesta: si `total_enviados > 0`, loguear; si error, loguear pero no romper.
3. **Eliminar** `flujo-reserva.json` y `flujo-cancelacion.json` (absorbidos por los sub-workflows).
4. Actualizar `n8n-workflows/README.md` con la nueva topología, el procedimiento de import (1 orquestador + 3 sub-workflows + 2 independientes por profesional), la matriz de credenciales, y la nota sobre los dos motores de recordatorio (n8n primario, APScheduler fallback).

### Fase 4: configuración en n8n (procedimiento operativo, no testeable en CI)

1. Por cada profesional, en n8n: **Settings → Credentials → New**:
   - `Telegram Bot`: pegar el `telegram_bot_token` del profesional.
   - `Header Auth`: header name `X-API-Key`, valor `<profesional.api_key>`.
2. **Workflows → Import from file**: importar `orquestador.json`, `sub-flujo-crear-turno.json`, `sub-flujo-cancelar-turno.json`, `sub-flujo-reprogramar-turno.json`.
3. En cada sub-workflow, abrir los nodos `HTTP Request` y asignar la credencial `Header Auth` recién creada.
4. En el orquestador, abrir el `Telegram Trigger` y asignar la credencial `Telegram Bot`. Abrir los `executeWorkflow` y referenciar los sub-workflows por nombre (ya importados).
5. Activar el orquestador (toggle ON). **No** activar los sub-workflows individualmente (los `executeWorkflow` los invocan sin necesidad de activarlos, pero en n8n deben existir en el workspace).
6. **NO** configurar webhooks manualmente en `@BotFather` para los sub-workflows: n8n registra el webhook del `Telegram Trigger` al activar el orquestador. Telegram enruta todos los updates al orquestador; el orquestador dispatch-ea.

### Fase 5: verificación E2E

1. Tests unitarios del JSON: `jq` + `python -c "import json; json.load(open('orquestador.json'))"` para validar que cada JSON parsea.
2. Test de estructura: cada workflow tiene los nodos esperados (al menos `Trigger` + nodos de `HTTP Request` con `Authentication: Generic Credential Type → Header Auth`).
3. **Test E2E manual** (fuera de CI, documentado en README):
   - Levantar backend (`uvicorn app.main:app`) con seed de un profesional + paciente.
   - Importar los 4 workflows en n8n local, configurar credenciales.
   - Activar el orquestador.
   - Enviar `/reservar` al bot en Telegram.
   - Verificar en n8n Executions que el orquestador dispatch-ea a `Crear_turno` y los HTTP Request al backend retornan 200.
4. **Test de regresión**: `pytest` del backend (suite completa, 0 regresiones) — confirma que el orquestador n8n no rompió nada del backend.

### Rollback

- `git revert` del commit. `flujo-reserva.json` y `flujo-cancelacion.json` reaparecen (si se los borró con `git rm`).
- En n8n: desactivar el orquestador, re-configurar `@BotFather` con el webhook del backend.
- **No** hay cambios en el backend, así que no hay migración que revertir.

## Open Questions

**Estado al cierre del propose (2026-07-01)**: las 3 OQ del diseño original están RESUELTAS. Las decisiones se documentaron arriba y se aplican en `Migration Plan → Fase 0`.

- [x] **OQ-1** (CRÍTICO): ¿`@BotFather` apunta al orquestador n8n o al webhook del backend? → **n8n como entry point principal**. El webhook del backend queda como alternativa documentada. Razonamiento en Decisión 1.
- [x] **OQ-2** (MEDIO): el sub-workflow `Crear_turno` pide datos del paciente como un único mensaje CSV ("Nombre, Apellido, DNI, Teléfono") parseado por coma, consistente con C-08. Documentado en Decisión 3 como C3-i.
- [x] **OQ-3** (BAJO): el `Send and Wait for Response` usa el timeout default de 10 min (= `RESERVA_TEMPORAL_MINUTOS`); no se implementa timeout custom. Documentado en R6.
