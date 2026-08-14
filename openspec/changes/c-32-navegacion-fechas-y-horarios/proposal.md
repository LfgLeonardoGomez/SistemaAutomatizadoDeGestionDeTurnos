# C-32 — Navegación de fechas y horarios

## Why

Tres huecos que comparten una sola causa: **el flujo de reserva asume que el
paciente va a aceptar lo que se le ofrece.**

### 1. El selector de horarios no tiene salida

Cuando `sub-flujo-crear-turno` muestra los horarios libres de una fecha, los
únicos botones son los horarios. Si ninguno le sirve al paciente, no tiene forma
de pedir otro día: la única salida es abandonar la conversación y empezar de
cero, perdiendo los datos que ya cargó.

Es el mismo defecto que se corrigió en la lista de turnos de reprogramar y
cancelar (`28e319a`): **un paso sin salida obliga al paciente a elegir algo que
no quiere para poder salir.** Acá duele más, porque llegar al selector de
horarios cuesta varios pasos.

`sub-flujo-reprogramar-turno` ya lo resuelve (C-30, botón "Elegir otra fecha").
Crear no.

### 2. No se ofrecen turnos para hoy, ni siquiera pidiendo "lo antes posible"

`Code - Decidir Paso` de crear-turno hace `if (rango === 'inmediato') daysToAdd = 1`:
la ventana arranca **mañana**. Un paciente que pide lo antes posible no ve los
horarios libres de hoy aunque existan. Reprogramar tiene la misma restricción
(C-30, `DIA_INICIO = 1`).

### 3. Y por eso mismo no se puede simplemente habilitarlo

`calcular_disponibilidad` (`backend/app/services/availability_service.py:40`)
**no filtra por hora actual**: solo resta los turnos `CONFIRMADO` y
`RESERVADO_TEMPORAL` y valida `dias_atencion`. Pedir disponibilidad de hoy a las
18:00 devuelve los slots desde las 09:00, y el paciente los puede reservar.

Habilitar "hoy" sin ese filtro no es una mejora: es ofrecer turnos en el pasado.

## What Changes

1. **Filtro de slots pasados en el backend.** Cuando la fecha consultada es hoy,
   `calcular_disponibilidad` descarta los slots cuya hora de inicio ya pasó. La
   comparación va contra la **hora local del profesional**, no contra el reloj
   del proceso: el contenedor corre en UTC y la agenda es local, que es la
   trampa de `863c778` y de `marcar_turnos_completados`.
2. **Navegación en el selector de horarios de crear-turno.** Botones para ir a
   otra fecha sin perder la conversación. Queda por definir la forma exacta
   (OQ-1).
3. **La ventana arranca hoy en los dos flujos.** En reprogramar es mover
   `DIA_INICIO` de 1 a 0 — se dejó como constante nombrada en C-30 exactamente
   para esto. En crear, es el `daysToAdd` del rango `inmediato`.

## Non-Goals

- **Días no laborables / feriados.** Es C-33.
- **Rediseñar el wizard de reserva.** Se agrega navegación, no se reordenan los
  pasos.
- **Tocar reprogramar más allá de `DIA_INICIO`.** C-30 lo dejó funcionando.

## Depende de

- **C-30 verificado E2E.** Este change mueve `DIA_INICIO` en un flujo que
  todavía no se probó contra el bot real.

## Governance

**MEDIUM.** El filtro de slots pasados toca el cálculo de disponibilidad, que es
el corazón de la reserva: un error de borde deja de ofrecer un slot legítimo, o
peor, sigue ofreciendo uno pasado. Requiere tests de borde explícitos sobre el
slot que empieza *justo ahora*.

## Open Questions

- **OQ-1 — ¿Qué forma toma la navegación?** Un botón "día siguiente" avanza de a
  uno y es predecible, pero necesita también "día anterior" para no dejar al
  paciente en un callejón, y no ayuda a quien busca dentro de dos semanas.
  Volver al selector de fechas reusa lo que ya existe y no agrega vocabulario.
  Definir con el usuario.
- **OQ-2 — ¿El filtro de slots pasados necesita un margen?** Ofrecer un turno que
  empieza en tres minutos es técnicamente válido y prácticamente inútil: el
  paciente no llega. Un margen (30 min, configurable por Pydantic Settings)
  puede ser más correcto que comparar contra la hora exacta.
