# Design — c-31-confirmacion-rica-y-escape-conversacional

## Context

Dos trabajos independientes que comparten superficie: el mensaje de confirmación
de reserva y el router conversacional del orquestador. Se agrupan porque los dos
salieron de la misma sesión de prueba E2E y los dos tocan
`orquestador.json` / `telegram_service.py`, no porque sean el mismo problema.

### Lo que ya está resuelto y no se rediscute

- **El escape hatch existe.** `fresh_start` se marca en todo comando reconocido y
  `Code - Decidir Paso` de crear-turno lo usa para abandonar la captura pendiente.
  Este change **agrega comandos a la lista**, no inventa un mecanismo.
- **`cmd:menu` ya funciona** (`d186408`). El patrón que dejó —entrar al bloque de
  reconocidos sin asignar `comando`, para caer en el fallback del Switch— es el
  que reusan los cuatro comandos nuevos.
- **El backend ya sabe armar mensajes para el paciente.** `telegram_service` tiene
  ocho formatters con la convención MarkdownV2 y `escape_markdown_v2`. El nuevo
  se suma a esa familia.

## Goals / Non-Goals

**Goals**

- Que el paciente sepa con quién es su turno en el momento de reservarlo.
- Que el mensaje de confirmación y el del recordatorio se parezcan, porque
  describen el mismo turno.
- Que un paciente atrapado a mitad de una captura pueda salir escribiendo.

**Non-Goals**

- Migrar el resto de los mensajes de n8n al backend.
- Agregar `/start` (ver OQ-1).
- Tocar reprogramar (c-30) o el recordatorio.

## Decisions

### D1 — El mensaje lo arma el backend; n8n lo transporta

`format_confirmacion_mensaje(turno, paciente, profesional)` vive en
`telegram_service`, al lado de `format_recordatorio_mensaje`, y produce el texto
completo. n8n no concatena nada.

**Por qué, habiendo alternativas más baratas:** se evaluó agregar `nombre` a
`ProfesionalConfigResponse` y que n8n armara la línea, o embeber el profesional
en `TurnoResponse`. Las dos dejan la redacción del mensaje repartida entre dos
sistemas, que es la razón por la que hoy el recordatorio y la confirmación dicen
cosas distintas sobre el mismo turno. Con el mensaje en el backend, cambiar qué
dice una confirmación es editar una función con tests, no editar una expresión
dentro de un JSON de workflow.

**Contrapartida asumida:** la presentación al paciente queda en el backend, que
es una responsabilidad discutible para un servicio de dominio. Se acepta porque
ya es el patrón vigente para todo lo que el backend manda (recordatorio, lista de
espera, expiración) y tener dos patrones sería peor que tener uno imperfecto.

### D2 — El texto viaja en la respuesta de `PUT /turnos/{id}/confirmar`

El endpoint pasa a responder un schema propio que extiende `TurnoResponse` con el
mensaje ya formateado. **No** se modifica `TurnoResponse`.

**Por qué no modificar `TurnoResponse`:** lo comparten `/cancelar`,
`/reprogramar`, `/completar` y `/confirmar-asistencia`. Agregarle un campo de
presentación obliga a todos esos endpoints a producirlo o a devolverlo nulo, y
arrastra sus tests a un cambio que no les incumbe. Un schema propio del endpoint
que lo necesita mantiene el radio chico.

**Por qué no un endpoint aparte** (`GET /turnos/{id}/mensaje-confirmacion`): sería
un segundo round-trip para algo que el flujo ya tiene que pedir, y abre la puerta
a que el mensaje se pida sobre un turno en cualquier estado. Viene con la
confirmación o no viene.

### D3 — `parse_mode: MarkdownV2` es parte del contrato, no un detalle de envío

El formatter produce MarkdownV2 con `escape_markdown_v2`, igual que el resto de
la familia. **Hoy ningún mensaje que manda n8n declara `parse_mode`.**

- Si el texto viaja **sin** `parse_mode`, el paciente ve los escapes crudos:
  `Fecha: 2026\-08\-14`, `Turno confirmado\.`.
- Si viaja **con** `parse_mode` y algún carácter quedó sin escapar, Telegram
  responde **400 y el mensaje no llega**. El paciente confirma su turno y no
  recibe nada.

Por eso el nodo que envía la confirmación SHALL declarar
`parse_mode: "MarkdownV2"` explícitamente, y el formatter SHALL escapar **todo**
dato de entrada, incluidos los que "no deberían" tener caracteres especiales: un
apellido con guión, una especialidad con paréntesis o un punto en un nombre
alcanzan para romperlo.

**Verificación asociada:** un test que arme el mensaje con nombre, apellido y
especialidad conteniendo cada carácter reservado de MarkdownV2 y afirme que el
resultado está íntegramente escapado. No alcanza con probar el camino feliz: el
modo de falla es que el mensaje no llegue, y eso no se ve en un test que solo
mira que el texto contenga el nombre.

### D4 — El profesional es opcional; su ausencia no cuesta el mensaje

Si el profesional no se puede cargar, el mensaje sale igual, sin esa línea.

**Por qué:** es exactamente lo que ya decidió `format_recordatorio_mensaje`, y su
docstring lo argumenta: "losing the message is worse than losing a line of it".
Un turno confirmado cuyo profesional no se pudo leer merece su confirmación. La
regla se hereda, no se reinventa.

### D5 — Los cuatro escapes reusan el patrón de `cmd:menu`

`/menu`, `/salir`, `/esc`, `/volver` entran en el bloque de comandos reconocidos
de `Normalizar Comando` **sin asignar `comando`**, con lo que quedan en
`'desconocido'` y caen en el fallback del Switch → `Telegram - Mensaje de Ayuda`.
Marcan `fresh_start = true`, que es lo que abandona la captura pendiente.

Se comparan sobre `textLower` ya trimmeado, con **igualdad exacta**, no con
`startsWith` ni `includes`.

**Por qué igualdad exacta y no `includes`:** los comandos existentes usan
`includes` para frases como "dar de baja" o "cambiar turno", y eso es tolerable
en una intención larga. Un escape corto no: con `includes`, un paciente cuyo
apellido sea "Esclusa" o que escriba "me tengo que ir, /salir mañana" dispara un
escape que no pidió. El costo de la igualdad exacta es que `/salir ` con espacio
al final no matchee — de ahí el trim.

**Por qué no aceptar `menu`, `salir`, `volver` sin barra:** compiten directamente
con la rama de texto libre que alimenta la captura de nombre y apellido. "Volver"
es un apellido real. La barra es lo que separa un comando de un dato.

### D6 — El escape muestra el menú, no un acuse

Al escapar, el paciente recibe el menú principal (`Telegram - Mensaje de Ayuda`),
no un "conversación cancelada". Un acuse sin opciones lo deja donde estaba, sin
saber qué hacer, y obliga a un mensaje más. El menú **es** el acuse: si aparece,
salió.

## Risks / Trade-offs

- **`parse_mode` mal puesto no degrada, corta.** Un escape faltante hace que la
  confirmación no llegue. Mitigado por D3 (test con todos los caracteres
  reservados) y por el E2E, que es bloqueante.
- **Un escape puede tragarse una respuesta legítima.** Mitigado por D5 (igualdad
  exacta y barra obligatoria). El caso residual —un paciente que responda
  literalmente `/salir` a "¿cuál es tu nombre?"— es el comportamiento deseado.
- **El mensaje de confirmación queda acoplado al endpoint.** Cambiar su redacción
  toca un schema de API. Es el costo de D2, y es preferible a que la redacción
  viva en un JSON de workflow sin tests.
- **Dos trabajos en un change.** Si el E2E de uno falla, el otro queda esperando.
  Se acepta porque ambos son chicos y comparten `orquestador.json`; si el apply
  muestra que no es así, se parten.

## Migration Plan

Sin migración de datos. Sin cambios de esquema de base.

1. Backend: formatter + schema de respuesta + tests (TDD estricto, hay runner).
2. n8n: `Telegram - Turno Confirmado` pasa a transportar el texto del backend con
   `parse_mode`.
3. n8n: los cuatro escapes en `Normalizar Comando`.
4. Push a la instancia con backup previo.
5. E2E manual.
6. Rollback: el backend es retrocompatible salvo el `response_model` de
   `/confirmar`, que **agrega** un campo; un cliente viejo lo ignora. Los
   workflows vuelven desde el backup.

## Open Questions

- **OQ-1 — ¿`/start` entra como escape?** No estaba en los cuatro pedidos. Hoy
  cae en texto libre → `comando = 'crear'` → sin captura viva muestra la ayuda,
  o sea **funciona por accidente**. Con una captura viva se manda como respuesta.
  Los clientes de Telegram lo emiten solos al abrir un chat por primera vez, así
  que la primera interacción de un paciente nuevo pasa por ahí. Resolver antes
  del grupo de escapes.
- **OQ-2 — ¿La confirmación repite los datos del paciente?** El recordatorio los
  incluye porque llega un día después, cuando el paciente ya no recuerda qué
  cargó. En la confirmación acaba de tipearlos. Mostrarlos sirve para que detecte
  un error de tipeo; omitirlos acorta el mensaje. Definir antes del grupo del
  formatter, porque cambia sus tests.
