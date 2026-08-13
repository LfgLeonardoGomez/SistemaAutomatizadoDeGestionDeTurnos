# C-31 — Confirmación de reserva con datos del profesional, y escape conversacional

## Why

Dos huecos que aparecieron probando el bot E2E el 2026-08-13, distintos entre sí
pero que viven en la misma superficie: qué le dice el bot al paciente y cómo
sale el paciente de una conversación.

### 1. La confirmación de reserva no dice con quién es el turno

Al terminar de reservar, `Telegram - Turno Confirmado` de `sub-flujo-crear-turno`
manda:

```
✅ Turno confirmado para {nombre} {apellido}.
📅 Fecha: {fecha}
🕐 Hora: {hora}
Te vamos a recordar por Telegram antes del turno.
```

El recordatorio, en cambio, sí incluye el profesional: `format_recordatorio_mensaje`
(`backend/app/services/telegram_service.py:567`) arma una `linea_profesional` con
nombre y especialidad. Resultado: **el paciente se entera de con quién es su turno
recién el día anterior.** En el momento de reservar —que es cuando decide— no se
lo dice nadie.

### 2. Ningún comando de texto saca al paciente de la conversación

`Normalizar Comando` reconoce cuatro comandos, y cualquiera de ellos marca
`fresh_start`, que abandona una captura pendiente. Ese es el escape hatch y
funciona. Pero **no hay ningún comando cuyo propósito sea salir**: los cuatro
arrancan otro flujo. Un paciente a mitad de una reserva que quiere simplemente
volver al principio no tiene cómo pedirlo por texto.

El botón `cmd:menu` sí existe y ahora funciona (`d186408`, que reparó que se
despachaba como respuesta de captura), pero es un botón: solo está disponible si
el paciente todavía tiene a mano un mensaje que lo trae. Quien está en medio de
una captura está viendo una pregunta, no un menú.

## What Changes

### Confirmación

El mensaje de confirmación lo arma **el backend**, como ya hace con el
recordatorio, y n8n solo lo transporta. Un formatter nuevo
`format_confirmacion_mensaje(turno, paciente, profesional)` en `telegram_service`,
consistente con `format_recordatorio_mensaje`: mismos datos, mismo orden, misma
convención de escapado.

**Consecuencia que el diseño tiene que resolver:** ese formatter produce
**MarkdownV2**, y hoy **ningún** mensaje que manda n8n declara `parse_mode`. Si
el texto viaja sin él, el paciente ve los escapes crudos (`2026\-08\-14`); si
viaja con él y algún carácter quedó sin escapar, Telegram responde 400 y el
mensaje no llega. Ver `design.md` D3.

### Escape

Cuatro comandos de texto —`/menu`, `/salir`, `/esc`, `/volver`— se suman a los
reconocidos por `Normalizar Comando`, con el mismo tratamiento que `cmd:menu`:
marcan `fresh_start` y caen en el fallback del Switch, que es el menú principal.

## Non-Goals

- **No se toca `format_recordatorio_mensaje`.** El mensaje del recordatorio queda
  como está; el nuevo se le parece, no lo reemplaza.
- **No se agrega `/start`.** No estaba en los cuatro comandos pedidos. Queda como
  pregunta abierta (OQ-1) porque hoy funciona por accidente.
- **No se mueven al backend los demás mensajes de n8n.** Solo el de confirmación.
  Migrar el resto es un change propio con su propia discusión.
- **No se toca `sub-flujo-reprogramar-turno`.** Es c-30.
- **No se resuelve la deuda del token single-tenant.**

## Depende de

- `d186408` (fix de `cmd:menu`) ya está aplicado: este change extiende el mismo
  mecanismo a comandos de texto.
- No depende de c-30 ni lo bloquea. Tocan archivos distintos salvo
  `orquestador.json`, que c-30 no modifica.

## Governance

**MEDIUM.** Toca `telegram_service` (mensajería al paciente) y el router
conversacional. No toca auth, dinero ni datos de terceros, pero un escape mal
puesto puede tragarse respuestas de captura legítimas —un paciente cuyo nombre o
apellido colisione con un comando— y un `parse_mode` mal puesto hace que el
mensaje no llegue. Implementación con checkpoints y verificación E2E.
