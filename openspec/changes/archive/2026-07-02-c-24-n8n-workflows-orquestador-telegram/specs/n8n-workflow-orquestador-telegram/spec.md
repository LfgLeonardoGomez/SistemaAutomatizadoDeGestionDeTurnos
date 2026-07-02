## ADDED Requirements

### Requirement: Orquestador es el single entry point por bot
El sistema SHALL desplegar **un workflow orquestador por bot de profesional** en n8n, identificado por el nombre `orquestador`. El orquestador SHALL usar el nodo `Telegram Trigger` como único entry point y SHALL autenticar al bot del profesional vía la credencial `Telegram Bot` configurada a nivel de workflow. El orquestador SHALL reemplazar el patrón previo de N webhooks por flujo (`/reserva`, `/cancelar`, `/lista-espera`) por un único webhook registrado por n8n al activar el orquestador.

#### Scenario: Un profesional importa el orquestador
- **WHEN** un profesional crea su bot en `@BotFather` y se configura `@BotFather` con la URL del webhook que n8n registra al activar el orquestador
- **THEN** todo update de Telegram de ese bot SHALL llegar al orquestador (no a los flujos viejos)
- **AND** SHALL NO requerir webhooks adicionales en `@BotFather` para sub-workflows (los `executeWorkflow` no exponen webhooks)

#### Scenario: Múltiples profesionales conviven
- **WHEN** dos profesionales importan cada uno su orquestador en la misma instancia de n8n
- **THEN** cada orquestador SHALL procesar los updates de su propio bot
- **AND** los orquestadores SHALL NO compartir el `Telegram Trigger` (cada uno tiene su credencial `Telegram Bot` con el token de su bot)

### Requirement: Orquestador dispatch-ea por comando textual o callback
El orquestador SHALL normalizar el contenido del update de Telegram a un campo único `comando` ∈ {`"crear"`, `"cancelar"`, `"reprogramar"`, `"lista_espera"`, `"reminder"`, `"desconocido"`} usando un nodo `Code`. El orquestador SHALL enrutar al sub-workflow correspondiente vía un nodo `Switch` con 3 ramas (`crear`, `cancelar`, `reprogramar`) seguidas de nodos `executeWorkflow`. Los casos `lista_espera` y `reminder` SHALL delegar al flujo independiente correspondiente (no son derivados de un comando del paciente en v1).

#### Scenario: Paciente envía comando textual
- **WHEN** el paciente envía `/reservar` o el texto `"Quiero un turno"`
- **THEN** el orquestador SHALL normalizar el comando a `"crear"`
- **AND** SHALL dispatch-ear al sub-workflow `Crear_turno` vía `executeWorkflow`

#### Scenario: Paciente toca un botón inline
- **WHEN** el paciente toca un botón inline cuyo `callback_data` empieza con `"reservar_lista_"`
- **THEN** el orquestador SHALL detectar que el update trae `callback_query.data` (no `message.text`)
- **AND** SHALL dispatch-ear al sub-workflow o flujo independiente correspondiente según el prefijo del callback_data

#### Scenario: Comando desconocido
- **WHEN** el paciente envía un texto que no matchea ningún comando conocido (ej. "hola")
- **THEN** el orquestador SHALL responder con un mensaje de ayuda: "Comandos disponibles: /reservar, /cancelar, /reprogramar"
- **AND** SHALL NO dispatch-ear a ningún sub-workflow

### Requirement: Sub-workflows envían X-API-Key en cada HTTP Request al backend
Cada sub-workflow (`Crear_turno`, `Cancelar_turno`, `Reprogramar_turno`) y cada workflow independiente modificado (`flujo-lista-espera`, `flujo-recordatorio`) SHALL declarar una credencial `Header Auth` a nivel de workflow con header name `X-API-Key` y valor el `api_key` del profesional. Cada nodo `HTTP Request` que invoque un endpoint REST del backend SHALL usar la autenticación `Generic Credential Type → Header Auth` referenciando esa credencial. El orquestador SHALL NO hardcodear el valor de `X-API-Key` en ningún campo de expresión.

#### Scenario: Sub-workflow llama al backend
- **WHEN** el sub-workflow `Crear_turno` ejecuta un nodo `HTTP Request` con método `POST` y URL `{{$env.FASTAPI_BASE_URL}}/turnos`
- **THEN** el request SHALL incluir el header `X-API-Key: <profesional.api_key>` inyectado por la credencial `Header Auth`
- **AND** SHALL NO requerir env vars globales para el valor del header

#### Scenario: Workflow independiente llama al backend
- **WHEN** `flujo-recordatorio.json` ejecuta su nodo `HTTP Request - Placeholder Recordatorio` con método `GET` y URL `{{$env.FASTAPI_BASE_URL}}/turnos/pendientes`
- **THEN** el request SHALL incluir el header `X-API-Key: <profesional.api_key>` inyectado por la credencial `Header Auth`

### Requirement: Flujos viejos absorbed son eliminados
El sistema SHALL eliminar del repositorio los archivos `n8n-workflows/flujo-reserva.json` y `n8n-workflows/flujo-cancelacion.json`. La funcionalidad de reserva SHALL vivir en el sub-workflow `sub-flujo-crear-turno.json` dispatch-ado por el orquestador. La funcionalidad de cancelación SHALL vivir en el sub-workflow `sub-flujo-cancelar-turno.json` dispatch-ado por el orquestador. Mantener los archivos viejos en el repo generaría doble routing si un usuario los importa accidentalmente y configura webhooks adicionales en `@BotFather`.

#### Scenario: Workflow viejo eliminado
- **WHEN** se importa el orquestador y los 3 sub-workflows en n8n
- **THEN** el repositorio NO SHALL contener los archivos `flujo-reserva.json` y `flujo-cancelacion.json`
- **AND** SHALL NO existir forma de que un update de Telegram llegue a esos webhooks eliminados (no están importados en n8n)

### Requirement: Documentación de la topología actualizada
El archivo `n8n-workflows/README.md` SHALL documentar: (1) la nueva topología (orquestador + 3 sub-workflows + 2 workflows independientes), (2) el patrón de credenciales (`Telegram Bot` y `Header Auth`), (3) el procedimiento de import **una vez por profesional** (no por bot), (4) la matriz de endpoints del backend consumidos por cada workflow, (5) la decisión de coexistencia con el webhook del backend (OQ-1 del design.md).

#### Scenario: Lector del README
- **WHEN** un operador lee `n8n-workflows/README.md`
- **THEN** SHALL poder identificar qué workflow importar para qué caso
- **AND** SHALL poder configurar las credenciales `Telegram Bot` y `Header Auth` siguiendo los pasos
- **AND** SHALL entender la decisión de OQ-1 (cuál es el entry point: orquestador n8n o webhook del backend)
