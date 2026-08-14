# Design — c-30-reprogramar-turno-reescritura

## Context

`sub-flujo-reprogramar-turno` tiene 12 nodos y ocho defectos verificados
(enumerados en `proposal.md`). Cinco de ellos encadenan: el selector de horarios
no puede mostrar un horario → ofrece un botón `slot:none` → ese botón produce un
`PUT` con `nueva_hora_inicio: "none"` → el backend responde 422 → el formatter no
puede ver el status → el paciente recibe "Turno #undefined reprogramado".

El flujo no falla: **miente**. Esa es la diferencia con cancelar, que fallaba de
forma visible. Un flujo que reporta éxito sobre una operación que no ocurrió es
peor que uno caído, porque el paciente se va tranquilo y aparece el día viejo.

### Lo que ya está resuelto y no se rediscute

- **El endpoint.** `PUT /turnos/{id}/reprogramar` implementa el Patrón A
  (cancelar + reservar + confirmar sin commitear, con el router a cargo del
  commit/rollback). Es atómico y está testeado. El defecto es del lado de n8n.
- **Los teclados inline.** El fix de `ad49cb9` convirtió los tres nodos de este
  flujo al patrón `httpRequest` → `sendMessage`. Sin eso ningún botón se
  renderiza. Es prerrequisito, no alcance.
- **El vocabulario de selección por lista.** `sub-flujo-cancelar-turno` ya
  resolvió el mismo problema de UX: el paciente no conoce el ID de su turno.
  Este change copia esa solución, no inventa otra.

### La referencia normativa

`sub-flujo-cancelar-turno` (16 nodos, post-`6e34f73`) es el modelo. Donde este
diseño diga "como cancelar", significa literalmente el mismo patrón de nodos, no
uno equivalente. Dos flujos gemelos que resuelven el mismo problema de dos formas
distintas son la razón por la que este change existe.

## Goals / Non-Goals

**Goals**

- Que reprogramar funcione de punta a punta, verificado en runtime y no por
  lectura de JSON.
- Que un fallo del backend llegue al paciente como un fallo.
- Que reprogramar y cancelar sean legibles como el mismo flujo con distinto
  verbo.

**Non-Goals**

- Tocar `PUT /turnos/{id}/reprogramar` o cualquier endpoint.
- Agregar endpoints. `GET /turnos/activos` y `GET /turnos/disponibles` alcanzan.
- Resolver el token single-tenant (`$env.TELEGRAM_BOT_TOKEN`). Es de v2.0.
- Rediseñar el orquestador. Este sub-flujo se invoca igual que hoy.
- Reprogramar turnos de otro chat. La lista se acota al `telegram_chat_id`, que
  es lo que `GET /turnos/activos` ya garantiza.

## Decisions

### D1 — La selección es por lista; no existe ninguna entrada tipeada

El paso inicial consulta `GET /turnos/activos?telegram_chat_id=<chat>` y muestra
un botón por turno con fecha y hora legibles, con el `turno_id` escondido en el
`callback_data`. Se elimina `Telegram - Pedir ID` y las cuatro expresiones
regulares de `Code - Decidir Paso` que parsean IDs tipeados.

**Por qué no elegir un formato de texto y arreglar el mensaje:** ya se probó en
cancelar y se descartó. El ID de un turno es un detalle de implementación de la
base de datos; un paciente no lo tiene, no lo puede averiguar y no debería
necesitarlo. Mantener una entrada tipeada obliga a mantener un parser, y ese
parser es exactamente lo que produjo el bucle infinito del defecto 6.

### D2 — El estado viaja en el `callback_data`; no hay `staticData`

Cada botón lleva todo lo necesario para el paso siguiente. No se usa
`$getWorkflowStaticData` ni el mecanismo de captura del backend.

**Por qué:** es lo que ya hacen cancelar y el picker de horarios de crear-turno
(`cmd:crear:slot:HH:MM:f:YYYY-MM-DD`, con el comentario "la seleccion es
STATELESS"). Un flujo stateless sobrevive a un reinicio de n8n y a dos pacientes
reprogramando en paralelo desde el mismo bot, y no deja estado colgado cuando
alguien abandona a mitad de camino.

### D3 — El vocabulario de callbacks se acorta para entrar en 64 bytes

Telegram limita `callback_data` a **64 bytes**. El vocabulario actual
(`cmd:reprogramar:turno_id:7:fecha:2026-08-14:slot:10:00`) mide 52 con un id de
un dígito, y crece con el id.

Vocabulario nuevo:

| `callback_data` | Significado | Peor caso |
|---|---|---|
| `cmd:reprogramar` | Listar los turnos activos del chat | 15 |
| `cmd:reprogramar:t:<id>` | Mostrar fechas para ese turno | 26 |
| `cmd:reprogramar:t:<id>:f:<fecha>` | Mostrar horarios de esa fecha | 39 |
| `cmd:reprogramar:t:<id>:f:<fecha>:h:<hora>` | Pedir confirmación | 49 |
| `cmd:reprogramar:ok:<id>:<fecha>:<hora>` | Ejecutar la reprogramación | 47 |

Peor caso calculado con `id` de 8 dígitos. El margen contra 64 se verifica con un
test estático, no a ojo: el defecto es silencioso —Telegram rechaza el botón
entero— y no se nota hasta que un id crece.

**Consecuencia:** el orquestador debe seguir ruteando `cmd:reprogramar*` a este
sub-flujo. Se verifica que su switch matchea por prefijo y no por la forma vieja.

### D3b — `cmd:reprogramar:turno_id:<id>` se sigue aceptando: lo emite el backend

El botón "Reprogramar" del recordatorio **no lo arma n8n**: lo genera el backend
en `telegram_service.format_recordatorio_keyboard`
(`backend/app/services/telegram_service.py:615`) con la forma
`cmd:reprogramar:turno_id:{turno_id}`.

`Code - Decidir Paso` SHALL aceptar esa forma como sinónimo exacto de
`cmd:reprogramar:t:<id>`. No es retrocompatibilidad opcional con botones viejos
del historial: es el camino por el que hoy entra la mayoría de las
reprogramaciones, y romperlo dejaría el recordatorio con un botón muerto sin que
nada falle visiblemente.

**Por qué no cambiar el backend para que emita la forma corta:** se puede, pero
es otro change. Tocar el formatter obliga a mover sus tests y toca el mismo
archivo que c-28 y c-29 van a modificar. La forma larga entra en 64 bytes
(`cmd:reprogramar:turno_id:12345678` = 33), así que no hay razón técnica para
forzarlo ahora. Queda anotado como deuda de unificación.

### D4 — Todo Code posterior a un HTTP lee por nodo nombrado

Cualquier nodo `Code` que corra después de un `httpRequest` obtiene `chat_id`,
`turno_id`, `fecha` y `hora` vía `$('Code - Decidir Paso').first().json`, nunca
de `$json`.

**Por qué:** la respuesta HTTP reemplaza el item. Es la causa de los defectos 1 y
2, la misma que se reparó en cancelar (`bfa8610`), y la misma que el comentario de
`Code - Formatear Respuesta` en cancelar ya documenta. No es una preferencia de
estilo: leer `$json.chat_id` después de un HTTP **siempre** da `undefined`.

### D5 — `neverError` + `fullResponse` en los tres nodos HTTP

Los tres (`GET /turnos/activos`, `GET /turnos/disponibles`,
`PUT /turnos/{id}/reprogramar`) declaran ambos flags. El body pasa a estar bajo
`input.body` y el status bajo `input.statusCode`.

**Por qué los dos y no uno:** sin `fullResponse` no hay `statusCode` y las ramas
de error son inalcanzables (defecto 3). Sin `neverError` un 404 o un 409 lanza
excepción, el Code node nunca corre y el paciente recibe **silencio**, que es el
modo de falla que cancelar tenía antes de `bfa8610`.

**Contrapartida asumida:** `neverError` también silencia errores de red y 5xx,
que quedan indistinguibles de una respuesta válida hasta que el Code node mira el
status. Por eso el formatter trata explícitamente el caso "status ausente o
inesperado" como fallo, en vez de asumir éxito cuando no reconoce el código. Este
es exactamente el bug que produjo la ambigüedad de "No tenés turnos" en cancelar.

### D6 — Los slots se leen de los items, no de un campo

`GET /turnos/disponibles` devuelve `list[SlotResponse]` — un array JSON pelado — y
n8n lo parte en N items. Con `fullResponse: true` el array queda bajo
`input.body` del primer item.

El formatter lee `$input.all()[0].json.body` y valida que sea un array. **No**
busca `input.slots` ni `Array.isArray(input)`, que son las dos condiciones que
nunca dan true y producen el defecto 4.

### D7 — Sin horarios se ofrece cambiar de fecha, no un botón imposible

Cuando la fecha elegida no tiene slots libres, el flujo responde con un botón que
vuelve al paso de fechas (`cmd:reprogramar:t:<id>`). Se elimina el
`callback_data` con `slot:none`.

**Por qué:** un botón cuyo callback el propio flujo no puede honrar es peor que
no ofrecer botón. El `slot:none` actual llega al parser como un slot válido,
produce `accion = 'ejecutar'` y dispara el PUT corrupto del defecto 5. La regla
general: **ningún botón emite un `callback_data` que el flujo no sepa procesar.**

### D8 — Las fechas se calculan en hora local del profesional

La ventana de fechas ofrecidas se construye con la fecha local, no con
`new Date().toISOString()`, que resuelve en UTC y corre el día entre las 21:00 y
medianoche en UTC-3 (defecto 8). Las etiquetas ("Hoy", "Mañana") se alinean al
día que efectivamente representan (defecto 7).

**Regla que aplica y no reinventa:** `backend/app/tiempo.py` ya define la
separación entre hora de agenda (local) y hora de auditoría (UTC), establecida en
`863c778`. Este flujo muestra horas de agenda: son locales, y no se convierten.
El formatter de cancelar ya lo hace bien —arma la fecha con `Date.UTC` y la lee
con `getUTCDay()` para que el día de la semana no dependa del server— y ese es el
patrón a copiar.

### D9 — Confirmación antes de ejecutar, releyendo la lista

Antes del `PUT`, el flujo pide confirmación mostrando el turno viejo y el nuevo
horario, y al confirmar **vuelve a consultar** `GET /turnos/activos` para detectar
turnos cancelados o vencidos entre que se mostró el botón y se tocó.

**Por qué confirmar si reprogramar no es irreversible como cancelar:** porque sí
mueve el turno de una persona, el botón viejo puede quedar vivo en el historial
del chat indefinidamente, y el slot elegido puede haberlo tomado otro paciente en
el medio. La relectura es la misma defensa que cancelar ya implementa.

## Risks / Trade-offs

- **`neverError` oculta fallos de infraestructura.** Mitigado por D5: el
  formatter falla explícitamente ante un status ausente o no reconocido, en vez
  de asumir éxito. Es la contrapartida aceptada a que un 404 llegue como mensaje
  y no como silencio.
- **El flujo crece de 12 a ~18 nodos.** Es el costo de la paridad con cancelar
  (16). Un flujo más grande pero legible como su gemelo es preferible a uno
  chico que nadie puede razonar por comparación.
- **La reescritura no puede apoyarse en tests automáticos de runtime.** n8n no
  tiene suite propia acá; la verificación es estática (parseo, forma de nodos,
  presupuesto de callbacks, ejecución de expresiones con datos simulados) más
  E2E manual contra la instancia. Por eso el grupo de verificación E2E es
  bloqueante para cerrar el change, no opcional.
- **El vocabulario de callbacks cambia.** Un botón viejo que siga vivo en el
  chat de un paciente emitirá la forma antigua. `Code - Decidir Paso` degrada
  cualquier callback no reconocido a "listar", que es la degradación que cancelar
  ya aplica; el paciente ve su lista en vez de un error.

## Migration Plan

No hay migración de datos: el change es enteramente de workflow n8n.

1. Reescribir `n8n-workflows/sub-flujo-reprogramar-turno.json` en el repo.
2. Verificación estática (parseo, credenciales por nombre, presupuesto de
   callbacks, expresiones ejecutadas con datos simulados).
3. Backup de la versión viva vía `n8n-cli workflows get --json`.
4. Push con `n8n-cli workflows update --file --skip-validation` y payload
   reducido a `name`/`nodes`/`connections`/`settings` — la Public API rechaza la
   forma completa del repo.
5. E2E manual contra el bot real.
6. Rollback: reimportar el backup del paso 3.

## Open Questions — RESUELTAS (2026-08-14)

- **OQ-1 — ¿Cuántas fechas se ofrecen y desde cuándo?** → **7 días fijos.**
  Verificado que es seguro: `calcular_disponibilidad`
  (`backend/app/services/availability_service.py:53-55`) devuelve `[]` para un
  día que no está en `dias_atencion`, así que un día sin agenda produce una lista
  vacía y el flujo lo trata con la rama de D7 (ofrecer cambiar de fecha). No
  hace falta filtrar las fechas antes de ofrecerlas.

- **OQ-2 — ¿Se permite reprogramar a un horario del mismo día?** → **Sí, debería
  poderse — pero NO entra en este change.** Habilitarlo hoy ofrecería turnos en
  el pasado: `calcular_disponibilidad` **no filtra por hora actual**, solo resta
  turnos `CONFIRMADO`/`RESERVADO_TEMPORAL`. Pedir disponibilidad de hoy a las
  18:00 devuelve los slots de las 09:00 en adelante, y el paciente puede
  reservarlos.

  El filtro correspondiente es backend, tiene que comparar contra la hora local
  del profesional (no contra el reloj del proceso, que corre en UTC), y lo
  necesitan **los dos** flujos — reprogramar y crear, cuyo rango "lo antes
  posible" también arranca mañana (`sub-flujo-crear-turno`,
  `Code - Decidir Paso:118`). Por eso vive en su propio change y no acá, donde
  "no se toca el backend" es un Non-Goal declarado.

  **Este change mantiene la ventana arrancando en mañana**, con el generador de
  fechas escrito de forma que mover el arranque sea un parámetro y no una
  reescritura.
