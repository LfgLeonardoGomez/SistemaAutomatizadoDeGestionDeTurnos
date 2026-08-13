# Tasks — c-30-reprogramar-turno-reescritura

> **Sobre TDD en este change.** El proyecto está en modo TDD estricto, pero n8n
> no tiene runner de tests y este change no toca código de backend. La
> adaptación honesta —y la única que da evidencia real— es escribir **primero**
> el chequeo estático que falla contra el JSON actual, después modificar el
> workflow hasta que pase. El grupo 2 construye ese harness antes de tocar un
> solo nodo. Lo que el harness NO puede probar (que Telegram renderice, que el
> backend responda, que el paciente entienda) va al grupo 11, que es
> **bloqueante** para cerrar el change: este flujo ya estuvo marcado "✅
> Completo" sin haber corrido nunca, y no se repite el error.

## 1. Baseline

- [ ] 1.1 Confirmar que `openspec validate --changes --strict` pasa c-30 antes de empezar, para que un fallo posterior sea atribuible a este trabajo.
- [ ] 1.2 Guardar backup de la versión viva: `n8n-cli workflows get NKLiszZeopCTc7iNBx9XY --json`. Es el único rollback que existe.
- [ ] 1.3 Registrar el estado de partida: 12 nodos, 8 defectos verificados (ver `proposal.md`), teclados ya convertidos a `sendMessage` por `ad49cb9`.
- [ ] 1.4 Resolver **OQ-1** y **OQ-2** de `design.md` con el usuario. OQ-1 (cuántas fechas y si se filtran por días con agenda) condiciona el grupo 5; OQ-2 (si se puede reprogramar al mismo día) condiciona el rango. No arrancar el grupo 5 sin respuesta.

## 2. Harness de verificación estática — RED primero

- [ ] 2.1 Escribir el chequeo de **presupuesto de callbacks**: para cada botón que el workflow emite, calcular el `callback_data` con un `turno_id` de 8 dígitos y afirmar ≤ 64 bytes. Debe correr contra el JSON actual y **pasar** (el vocabulario viejo también entra), así que su valor es de regresión: protege el vocabulario nuevo del grupo 3.
- [ ] 2.2 Escribir el chequeo de **lectura por nodo nombrado**: ningún `jsCode` que corra después de un `httpRequest` puede leer `chat_id`, `turno_id`, `fecha` ni `hora` desde `$json`/`$input.all()[0].json` sin pasar por `$('Code - Decidir Paso')`. Debe **FALLAR** contra el JSON actual (defectos 1 y 2).
- [ ] 2.3 Escribir el chequeo de **flags HTTP**: los tres nodos `httpRequest` que hablan con el backend declaran `neverError: true` y `fullResponse: true`. Debe **FALLAR** contra el JSON actual (defecto 3).
- [ ] 2.4 Escribir el chequeo de **callbacks honrables**: todo `callback_data` que el workflow emite tiene que ser reconocido por el parser de `Code - Decidir Paso`. Debe **FALLAR** contra el JSON actual por `slot:none` (defecto 5).
- [ ] 2.5 Escribir el **ejecutor de expresiones**: correr cada `jsonBody` de los nodos `sendMessage` con datos simulados, parsear el resultado y validar forma de teclado, `chat_id` presente y texto no vacío — ejercitando **las dos ramas** de cada ternario. Reusar el patrón del harness de `ad49cb9`.
- [ ] 2.6 Dejar el harness corriendo con un solo comando y documentar cómo se invoca. Si vive en `n8n-workflows/`, que no rompa el parseo de `*.json` del README.

## 3. `Code - Decidir Paso` — vocabulario y parser

- [ ] 3.1 RED: chequeo que afirma que el parser reconoce las cinco formas de D3 (`cmd:reprogramar`, `:t:<id>`, `:t:<id>:f:<fecha>`, `:t:<id>:f:<fecha>:h:<hora>`, `ok:<id>:<fecha>:<hora>`). Falla contra el parser actual.
- [ ] 3.2 RED: chequeo que afirma que `cmd:reprogramar:turno_id:<id>` —el que emite el backend en `telegram_service.py:615`— se interpreta como selección de turno (D3b). Falla contra el parser actual, que lo trata como forma distinta.
- [ ] 3.3 GREEN: reescribir el parser con las cinco formas más la legacy. Eliminar las cuatro regex de IDs tipeados y la rama `pedir_id`.
- [ ] 3.4 RED + GREEN: un callback no reconocido degrada a `listar` sin emitir requests derivados de él.
- [ ] 3.5 Eliminar el nodo `Telegram - Pedir ID` y su salida del switch. Verificar que no queda ninguna conexión colgada.

## 4. Paso de listado — `GET /turnos/activos`

- [ ] 4.1 Agregar el nodo HTTP con `telegram_chat_id` por `sendQuery`, credencial `Profesional API Key` por nombre, y ambos flags de D5.
- [ ] 4.2 Formatter que lee `input.body`, valida que sea array, y arma un botón por turno con fecha y hora legibles y `cmd:reprogramar:t:<id>` en el callback. Copiar el formateo de fecha de `Code - Formatear Lista` de cancelar (arma con `Date.UTC`, lee con `getUTCDay()`).
- [ ] 4.3 Rama de lista vacía: mensaje propio más botón para reservar. **No** reusar el texto de "no hay turnos" para el caso de error.
- [ ] 4.4 Distinguir lista vacía legítima de error del backend: con `neverError` un 422 produce body no-array. Ese caso debe decir que algo falló, **no** "no tenés turnos" — es la ambigüedad que hizo dar por bueno un smoke test en cancelar.

## 5. Paso de fechas

> Bloqueado por 1.4 (OQ-1 y OQ-2).

- [ ] 5.1 RED: chequeo de que las fechas se calculan en local y no con `toISOString()` (defecto 8).
- [ ] 5.2 RED: chequeo de que cada etiqueta relativa coincide con la fecha que el botón envía (defecto 7).
- [ ] 5.3 GREEN: generador de fechas en hora local del profesional, con el rango que resuelva OQ-1/OQ-2.
- [ ] 5.4 Botones con `cmd:reprogramar:t:<id>:f:<fecha>`.

## 6. Paso de horarios

- [ ] 6.1 RED: chequeo de que el formatter lee el array de `input.body` y no `input.slots` ni `Array.isArray(input)` (defecto 4).
- [ ] 6.2 GREEN: formatter corregido, filtrando `disponible !== false`.
- [ ] 6.3 Botones con `cmd:reprogramar:t:<id>:f:<fecha>:h:<hora>`.
- [ ] 6.4 Rama sin horarios: mensaje más botón que vuelve al paso de fechas (`cmd:reprogramar:t:<id>`). Eliminar `slot:none` (defecto 5). El chequeo 2.4 tiene que pasar acá.

## 7. Paso de confirmación

- [ ] 7.1 Mensaje que muestra el turno actual y el horario nuevo, con botones confirmar (`cmd:reprogramar:ok:...`) y volver.
- [ ] 7.2 Al confirmar, releer `GET /turnos/activos` y verificar que el turno sigue vigente antes del PUT (D9).
- [ ] 7.3 Rama "el turno ya no está": mensaje más botón para volver a pedir la lista.

## 8. Ejecución y resultado

- [ ] 8.1 RED: chequeo de que el formatter de resultado deriva éxito del `statusCode` y trata status ausente/no reconocido como fallo (D5).
- [ ] 8.2 GREEN: `HTTP - PUT Reprogramar` con ambos flags; formatter que lee `input.statusCode` y `input.body`.
- [ ] 8.3 RED + GREEN: el mensaje de éxito toma el id de `body.id`, no de `body.turno_id` (defecto 2). Verificar contra `TurnoResponse` en `backend/app/schemas/turno.py:104`.
- [ ] 8.4 Ramas 404 y 409 con los mensajes de la spec, alcanzables (defecto 3).
- [ ] 8.5 Rama de fallo genérico que no promete que el turno se movió.

## 9. Verificación estática completa

- [ ] 9.1 Los cinco chequeos del grupo 2 pasan sobre el JSON final.
- [ ] 9.2 El JSON parsea; todo nodo es alcanzable desde el trigger; ninguna conexión apunta a un nodo inexistente; los outputs del switch coinciden con la cantidad de reglas.
- [ ] 9.3 Credenciales por **nombre**, no por id, en todo nodo que use `Profesional API Key` (`n8n-workflows/README.md` §credenciales).
- [ ] 9.4 Toda expresión empieza con `=`; ningún `{{ }}` suelto (§3 del README — ya rompió el repo dos veces).
- [ ] 9.5 El test estático de `reply_markup` del README sigue dando 0.
- [ ] 9.6 Sintaxis de todo `jsCode` validada con `node -e`.

## 10. Push a la instancia viva

- [ ] 10.1 Reducir el payload a `name`/`nodes`/`connections`/`settings` — la Public API rechaza la forma completa del repo (`additional properties`).
- [ ] 10.2 `n8n-cli workflows update NKLiszZeopCTc7iNBx9XY --file <reducido> --skip-validation --force`. `--skip-validation` es necesario por el falso `UNKNOWN_NODE_TYPE` del validador local con `n8n-nodes-base.telegram`.
- [ ] 10.3 Verificar en vivo: `active: true`, cantidad de nodos esperada, cero credenciales huérfanas.

## 11. Verificación E2E — BLOQUEANTE

> Nada de este grupo se puede tildar por lectura de JSON. Cada ítem exige haber
> visto el mensaje en el chat.

- [ ] 11.1 `/reprogramar` sin turnos activos → mensaje propio y botón de reservar. Confirmar que **no** es el mensaje de error.
- [ ] 11.2 Con al menos dos turnos activos → aparece un botón por turno, con fecha y hora correctas, y sin ningún id visible.
- [ ] 11.3 Elegir un turno → aparecen las fechas, y la etiqueta relativa coincide con la fecha real.
- [ ] 11.4 Elegir una fecha con disponibilidad → aparecen los horarios libres.
- [ ] 11.5 Elegir una fecha sin disponibilidad → mensaje y botón que vuelve a fechas. Tocarlo y confirmar que vuelve.
- [ ] 11.6 Confirmar → el turno se movió en la base, el slot viejo quedó libre y el nuevo ocupado.
- [ ] 11.7 Camino 409: dos chats tomando el mismo slot, o tomar el slot por otra vía entre el botón y la confirmación. El paciente recibe el mensaje de horario ocupado y **no** un falso éxito.
- [ ] 11.8 Camino 404: cancelar el turno entre que se muestra el botón y se confirma. Verificar que 7.2 lo detecta antes del PUT.
- [ ] 11.9 Entrar desde el botón "Reprogramar" del recordatorio (`cmd:reprogramar:turno_id:<id>`, emitido por el backend) y confirmar que cae en el paso de fechas (D3b).
- [ ] 11.10 Escribir `/reprogramar 42` y confirmar que muestra la lista en vez de entrar en un bucle (defecto 6).
- [ ] 11.11 Correr el flujo entre las 21:00 y medianoche hora local, o con el reloj movido, y confirmar que las fechas ofrecidas no se corren un día (defecto 8).

## 12. Documentación y cierre

- [ ] 12.1 Agregar el vocabulario de callbacks de reprogramar al README, al lado del de cancelar, incluyendo la forma legacy que emite el backend y por qué se acepta.
- [ ] 12.2 Actualizar la tabla de workflows: `sub-flujo-reprogramar-turno` sale de "❌ No funcional" al estado que corresponda **según el grupo 11**, no según el 9.
- [ ] 12.3 Tildar la task **9.2 de c-27** con la evidencia de este change, y anotar en c-27 que el follow-up quedó descargado.
- [ ] 12.4 Anotar la deuda de D3b: unificar el `callback_data` del recordatorio del backend con el vocabulario corto.
- [ ] 12.5 Registrar en engram los defectos que aparezcan en el grupo 11 y no estén en los ocho de `proposal.md`.
