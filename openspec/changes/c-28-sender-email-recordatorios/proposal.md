# C-28 — Sender de email y elección de canal para el recordatorio

## Why

`turno_destinatario` modela `(turno, canal, destinatario)` y acepta `TELEGRAM`
y `EMAIL` desde C-23. El flujo de captura de C-27 ya **guarda** el email cuando
el paciente lo carga, y queda una fila con `canal='EMAIL'`.

Nadie la lee. No existe ningún sender de email en el backend: el único envío
implementado es Telegram, en `notificacion_service.enviar_recordatorio_telegram`.
Un paciente que da su email hoy no recibe absolutamente nada por ese canal, y
el mensaje de confirmación tiene prohibido prometérselo (spec de C-27, "Email
delivery is not promised").

De ahí el segundo problema, que es el que el usuario planteó: **hoy el paciente
no elige el canal**. `TELEGRAM` se escribe siempre y automáticamente con el
`chat_id` desde el que habla; el teléfono que el paciente escribe durante la
captura no se usa para notificar nada — es solo un dato de la ficha. Ofrecer una
elección de canal sin un sender detrás sería prometer un plato que la cocina no
prepara, así que el sender es prerrequisito de la elección, no al revés.

## What Changes

- Sender de email en el backend (SMTP configurable por Pydantic Settings), con
  el mismo contrato que el sender de Telegram: devuelve `True`/`False` para que
  el job decida reintento.
- `enviar_recordatorio` pasa a iterar **todos** los destinatarios del turno en
  lugar de quedarse con el primero `TELEGRAM`.
- Elección de canal por parte del paciente durante la captura de C-27, una vez
  que ambos canales entregan de verdad.
- Corregir el texto del mensaje de confirmación, que hoy anuncia solo el
  recordatorio por Telegram porque el email no existía.
- Actualizar `n8n-workflows/README.md`, que documenta la limitación como
  conocida.

## Impact

- Affected specs: `telegram-turno-confirmation-flow` (mensaje de confirmación),
  capability nueva para notificaciones multicanal.
- Affected code: `app/services/notificacion_service.py`, `app/config.py`,
  `app/scheduler/jobs.py`, `n8n-workflows/sub-flujo-crear-turno.json`.
- Depende de: C-27 archivado.
- Riesgo: credenciales SMTP son secretos — aplica la regla dura de no
  commitearlas; van por variable de entorno.
