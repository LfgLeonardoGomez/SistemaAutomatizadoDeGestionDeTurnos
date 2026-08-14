# Tasks — c-31-confirmacion-rica-y-escape-conversacional

> **TDD.** A diferencia de c-30, acá **sí hay runner**: el formatter y el schema
> son backend con pytest, y van en RED → GREEN → REFACTOR estricto. La parte n8n
> se verifica con el harness estático (ejecutar el jsCode real con inputs
> simulados, como en `d186408`). El grupo 6 (E2E) es **bloqueante**: el modo de
> falla de D3 es que el mensaje **no llegue**, y eso ningún test unitario lo ve.
>
> Correr la suite: dentro del container, contra la DB de test.
> `docker compose exec -T -e TEST_DATABASE_URL="postgresql+asyncpg://turnos:turnos@db:5432/turnos_test" backend pytest`
> (el venv del root está roto: su `pyvenv.cfg` apunta a un Python que ya no existe).

## 1. Baseline y decisiones

- [ ] 1.1 Safety net: correr la suite completa y registrar el baseline de tests en verde. Un fallo posterior tiene que ser atribuible a este trabajo.
- [x] 1.2 Resolver **OQ-1** (`/start` entra o no como escape) con el usuario. **Resuelta 2026-08-14: SÍ. Son cinco comandos (`/menu`, `/salir`, `/esc`, `/volver`, `/start`). Ver D5b.**
- [x] 1.3 Resolver **OQ-2** (si la confirmación repite nombre y apellido del paciente) con el usuario. **Resuelta 2026-08-14: el mensaje espeja al del recordatorio — paciente Y profesional. Supuesto declarado en el design.**
- [ ] 1.4 Backup de `orquestador.json` y `sub-flujo-crear-turno.json` vivos vía `n8n-cli workflows get --json`.
- [ ] 1.5 Resolver **OQ-3**: qué comando se nombra en el menú y con qué redacción exacta. Es copy que ve todo paciente en cada vuelta al menú. Bloquea 4.8.

## 2. Formatter — `format_confirmacion_mensaje`

> Bloqueado por 1.3.

- [ ] 2.1 RED: test de que el mensaje incluye nombre y especialidad del profesional.
- [ ] 2.2 GREEN: implementar el formatter en `telegram_service.py`, al lado de `format_recordatorio_mensaje`.
- [ ] 2.3 RED + GREEN: fecha y hora del turno presentes.
- [ ] 2.4 RED + GREEN: `profesional=None` produce el mensaje sin esa línea, sin línea vacía ni rótulo huérfano (D4).
- [ ] 2.5 RED + GREEN: profesional con nombre y sin especialidad no deja paréntesis colgado. Es el caso que `format_recordatorio_mensaje` ya contempla — copiar la defensa, no reinventarla.
- [ ] 2.6 RED: test de escapado **exhaustivo** — nombre, apellido y especialidad conteniendo **cada** carácter reservado de MarkdownV2. Afirmar que ninguno queda sin escapar (D3). Este test es el que evita que la confirmación no llegue.
- [ ] 2.7 GREEN: escapar todo con `escape_markdown_v2`.
- [ ] 2.8 REFACTOR: si el formatter y `format_recordatorio_mensaje` comparten la construcción de la línea del profesional, extraerla. Tests verdes después de cada paso.

## 3. Schema y endpoint

- [ ] 3.1 RED: test de que `PUT /turnos/{id}/confirmar` devuelve el turno **y** el mensaje formateado.
- [ ] 3.2 GREEN: schema de respuesta propio que extiende `TurnoResponse` con el mensaje (D2). **No** modificar `TurnoResponse`.
- [ ] 3.3 RED + GREEN: cargar el profesional del turno para pasárselo al formatter. Si no se puede, seguir sin él (D4) — no romper la confirmación.
- [ ] 3.4 Test de regresión: `/cancelar`, `/reprogramar`, `/completar` y `/confirmar-asistencia` mantienen su respuesta sin campos nuevos.
- [ ] 3.5 Verificar que el endpoint sigue declarando `response_model` (regla dura del proyecto) y que el tipo de retorno está anotado.
- [ ] 3.6 Suite completa en verde contra el baseline de 1.1.

## 4. Escapes en el orquestador

> Desbloqueado por 1.2. Son **cinco** comandos: `/menu`, `/salir`, `/esc`, `/volver`, `/start`.

- [ ] 4.1 RED: extender el harness de `d186408` con los cinco comandos, afirmando `comando === 'desconocido'` y `fresh_start === true`. Falla contra el JSON actual.
- [ ] 4.2 RED: afirmar que ninguno de los cinco viaja con `respuesta_captura`. Falla contra el JSON actual. **Incluir `/start` explícitamente: hoy pasa por texto libre y con una captura viva se manda como respuesta.**
- [ ] 4.3 GREEN: agregarlos a `esComandoTexto` con **igualdad exacta** sobre el texto trimmeado y en minúsculas (D5). No asignar `comando` — la ausencia es el ruteo, igual que `cmd:menu`.
- [ ] 4.4 RED + GREEN: una frase larga que contenga un comando de escape **no** escapa.
- [ ] 4.5 RED + GREEN: una palabra sin barra que contenga "salir" o "volver" sigue siendo respuesta de captura. Cubrir el apellido "Volver", que es real.
- [ ] 4.6 Regresión: los 11 casos de ruteo de `d186408` siguen pasando.
- [ ] 4.7 Documentar los cinco comandos en el README, en la sección del escape hatch.
- [ ] 4.8 **Redactar el nuevo texto de `Telegram - Mensaje de Ayuda`** con la línea que enseña la salida (D7). Bloqueado por 1.5. Hoy dice solo `"Hola 👋 ¿Qué querés hacer?"`; pasa a tener dos trabajos y la segunda línea no debe competir con los botones.
- [ ] 4.9 Verificar que el mensaje de ayuda sigue siendo el mismo nodo al que llegan **las dos** entradas (fallback del Switch y `IF - Mostrar Ayuda`), para que el texto nuevo se vea por ambos caminos.

## 5. n8n — transporte del mensaje

- [ ] 5.1 `Telegram - Turno Confirmado` de `sub-flujo-crear-turno` pasa a enviar el texto que devuelve el backend, sin concatenar nada.
- [ ] 5.2 Declarar `parse_mode: "MarkdownV2"` en ese envío (D3). Verificar que es el **único** mensaje del flujo que lo lleva, para no romper los que están en texto plano.
- [ ] 5.3 Ejecutar la expresión con datos simulados y confirmar que el payload contiene texto y parse mode.
- [ ] 5.4 Verificación estática completa: JSON parsea, grafo sin nodos colgados, expresiones con `=`, `reply_markup` sigue en 0, sintaxis de todo `jsCode`.
- [ ] 5.5 Push con backup previo y payload reducido a `name`/`nodes`/`connections`/`settings`, con `--skip-validation`.
- [ ] 5.6 Verificar en vivo: `active: true`, nodos esperados, cero credenciales huérfanas.

## 6. E2E — BLOQUEANTE

> Nada acá se tilda por lectura de código. Cada ítem exige haber visto el chat.

- [ ] 6.1 Reservar un turno de punta a punta y confirmar que el mensaje final **nombra al profesional**.
- [ ] 6.2 Confirmar que el mensaje se ve **formateado**, sin barras de escape visibles. Es el modo de falla de "sin `parse_mode`".
- [ ] 6.3 Reservar con un paciente cuyo apellido tenga un guión o un punto, y confirmar que el mensaje **llega**. Es el modo de falla de "escapado incompleto": Telegram devuelve 400 y no llega nada.
- [ ] 6.4 Los cinco escapes, uno por uno, a mitad de una captura: cada uno devuelve el menú y abandona la captura.
- [ ] 6.4b Abandonar una reserva, cerrar el chat y volver a abrirlo: el /start automático del cliente devuelve el menú y no se registra como respuesta a la pregunta pendiente (D5b).
- [ ] 6.4c Leer el menú como paciente nuevo y confirmar que la línea de escape se entiende sin explicación previa. Después usar el comando que nombra y verificar que funciona (D7).
- [ ] 6.5 Después de escapar, empezar una reserva nueva y confirmar que no arrastra nada de la anterior.
- [ ] 6.6 Responder una frase que contenga "salir" a una pregunta de captura y confirmar que **no** escapa.
- [ ] 6.7 Verificar que el turno confirmado en 6.1 quedó `CONFIRMADO` en la base con su `paciente_id`.

## 7. Cierre

- [ ] 7.1 Actualizar la KB con chronicle si el cambio de mensajería afecta lo documentado del flujo de reserva.
- [ ] 7.2 Registrar en engram los defectos que aparezcan en el grupo 6 y no estén previstos en el design.
- [ ] 7.3 Anotar como deuda: el resto de los mensajes de n8n sigue en texto plano y armado en expresiones. Si esto funciona, es el precedente para migrarlos.
