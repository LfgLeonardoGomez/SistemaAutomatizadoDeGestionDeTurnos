# C-30 — Reescritura del sub-flujo de reprogramar

## Why

`sub-flujo-reprogramar-turno` figuraba como "✅ Completo" en el README y **nunca
funcionó**. Es el gemelo del sub-flujo de cancelar, que apareció roto apenas se
lo ejercitó en runtime (C-27 task 9.1): mismo autor, mismos patrones, mismos
defectos. La task 9.2 de C-27 lo anticipaba textualmente — "expect defects".

Un análisis estático contra el backend encontró **ocho**, verificados uno por
uno. Tres son la familia exacta que ya se reparó en cancelar (`bfa8610`); cinco
son propios y encadenan en algo peor que un flujo que no anda: un flujo que
**miente**.

### La familia heredada de cancelar

1. **`chat_id` leído del item equivocado, dos veces.** `Code - Formatear Slots`
   y `Code - Formatear Resultado` leen `$input.all()[0].json` inmediatamente
   después de un nodo HTTP. La respuesta HTTP **reemplaza el item**: `chat_id`,
   `turno_id` y `nueva_fecha` llegan `undefined` y Telegram no sabe a dónde
   responder. El grafo es lineal, sin merge, así que no hay forma de que esos
   campos sobrevivan.
2. **`turno_id` leído de la raíz.** `TurnoResponse` expone `id`
   (`backend/app/schemas/turno.py:104`). El mensaje dice
   "Turno #undefined reprogramado".
3. **El bloque de errores es código muerto.** `Code - Formatear Resultado`
   evalúa `input.statusCode >= 400`, pero `HTTP - PUT Reprogramar` no declara
   `fullResponse` ni `neverError`. `statusCode` no existe nunca, `errorStatus`
   es siempre falso, las ramas 404 y 409 son inalcanzables y **todo fallo se
   reporta como éxito**.

### Los propios

4. **El selector de horarios no puede mostrar un horario.**
   `GET /turnos/disponibles` devuelve `list[SlotResponse]`, un array JSON pelado
   (`backend/app/routers/turnos.py:48`), y n8n parte un array de respuesta en N
   items. `Code - Formatear Slots` busca `Array.isArray(input)` o `input.slots`
   sobre el **primer objeto slot**: ninguna condición da true, `slots = []`
   siempre. El paciente ve "No hay horarios" aunque la agenda esté vacía.
5. **Ese botón vacío dispara un PUT corrupto.** El fallback emite
   `callback_data: '...:slot:none'`, que vuelve al parser, produce
   `nuevoSlot = 'none'` y `accion = 'ejecutar'`, y sale un `PUT` con
   `nueva_hora_inicio: "none"` → 422 de Pydantic. Que por el defecto 3 se le
   informa al paciente **como turno reprogramado**. Este es el peor del
   conjunto: el sistema le dice a alguien que su turno se movió cuando no se
   movió.
6. **El bucle del ID tipeado, calcado de cancelar.** `Telegram - Pedir ID`
   indica `/reprogramar <ID>` con espacio; el parser solo acepta
   `cmd:reprogramar:turno_id:N` o `reprogramar:N`. Seguir la instrucción del
   propio bot no matchea nada.
7. **Las etiquetas de fecha están corridas un día.** El loop de fechas arranca
   en `i = 1` (mañana) pero `nombresCorto` mapea el índice `0` a "Hoy": el
   primer botón dice **"Hoy"** y es **mañana**.
8. **Timezone en la generación de fechas.** `new Date()` + `toISOString()`
   resuelve en UTC. El contenedor corre UTC y la agenda es local (UTC-3), así
   que entre las 21:00 y medianoche las siete fechas ofrecidas salen corridas.
   Misma clase de bug que `863c778` y que `marcar_turnos_completados`.

## What Changes

**El defecto 6 no se arregla eligiendo un formato de texto.** Pedirle a un
paciente el ID de su turno es pedirle un dato que no tiene — la misma conclusión
a la que se llegó en cancelar, donde se eliminó el parseo tipeado entero en vez
de elegir un formato. `GET /turnos/activos` ya existe (`2a781bb`), devuelve
exactamente lo que hace falta y este flujo no lo usa.

Por eso esto es una **reescritura**, no una serie de parches:

1. **Selección por lista, no por ID.** El paso inicial consulta
   `GET /turnos/activos`, muestra fecha y hora en botones con el `turno_id`
   escondido en el `callback_data`, y elimina toda entrada tipeada. Mismo
   vocabulario de callbacks que cancelar.
2. **Lectura de estado por nodo nombrado.** Todo Code que corra después de un
   nodo HTTP lee `chat_id` y `turno_id` vía `$('Code - Decidir Paso')`, nunca de
   `$json`.
3. **`neverError` + `fullResponse` en los tres nodos HTTP**, con el body bajo
   `input.body` y el status bajo `input.statusCode`, para que las ramas de error
   dejen de ser inalcanzables.
4. **El selector de slots lee el array de items**, no un campo inexistente, y
   cuando no hay horarios ofrece cambiar de fecha en vez de emitir un
   `callback_data` que el propio flujo no puede honrar.
5. **Fechas calculadas en hora local del profesional**, con las etiquetas
   alineadas al día que realmente representan.
6. **Confirmación antes de ejecutar**, releyendo la lista para detectar turnos
   que cambiaron entre que se mostró el botón y se tocó — como ya hace cancelar.

## Non-Goals

- **No se toca el endpoint `PUT /turnos/{id}/reprogramar`.** Su contrato es
  correcto y sus tests pasan; el defecto está del lado de n8n.
- **No se agregan endpoints nuevos.** `GET /turnos/activos` y
  `GET /turnos/disponibles` alcanzan.
- **No se resuelve la deuda del token single-tenant.** El patrón de teclados
  inline usa `$env.TELEGRAM_BOT_TOKEN`, que es un token por instancia; eso entra
  con el bot por profesional de v2.0, no acá.

## Depende de

- **C-27 archivado.** Este change cierra su task 9.2 y hereda su vocabulario de
  callbacks.
- El fix de teclados inline (`ad49cb9`) ya está aplicado y **es prerrequisito**:
  sin él ningún botón de este flujo se renderiza. No forma parte del alcance de
  este change, solo se apoya en él.

## Governance

**MEDIUM.** Es lógica de negocio sobre agendas reales: reprogramar cancela un
turno y reserva otro en una sola transacción. No toca auth ni datos de terceros,
pero un defecto acá mueve el turno de una persona real. Implementación con
checkpoints y verificación E2E contra la instancia viva antes de cerrar.
