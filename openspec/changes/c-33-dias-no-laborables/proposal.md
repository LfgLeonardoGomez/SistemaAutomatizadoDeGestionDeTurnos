# C-33 — Días no laborables y feriados

> **Estado: idea registrada, sin planificar.** Solo `proposal.md`. No tiene
> design, specs ni tasks, y no está listo para implementar.

## Why

La disponibilidad se calcula únicamente contra `profesional.dias_atencion`, que
es una lista de días de la semana (`availability_service.py:53-55`). El modelo no
tiene ninguna forma de decir *"este día en particular no atiendo"*.

Consecuencia concreta, observada el 2026-08-14: el lunes siguiente es **feriado
nacional**, el profesional atiende de lunes a viernes, y el bot ofrece turnos ese
día con normalidad. Un paciente puede reservar un turno al que nadie va a
atenderlo.

El caso no se limita a feriados nacionales: vacaciones, un congreso, una
enfermedad, media jornada por un motivo puntual. Hoy la única forma de bloquear
un día es sacarlo de `dias_atencion`, que lo bloquea **todas las semanas**.

## What Changes (esbozo)

Sin decidir todavía. Las piezas que se ven:

1. **Un modelo de excepciones de agenda** por profesional: una fecha concreta
   marcada como no laborable, con un motivo opcional.
2. **`calcular_disponibilidad` las respeta**, devolviendo lista vacía para esas
   fechas — igual que hace hoy con un día fuera de `dias_atencion`.
3. **Una forma de cargarlas.** Manual por el profesional, y/o importadas.

## La opción de Google Calendar

El proyecto ya integra Google Calendar (`calendar_service`, C-08) como agenda
espejo. Importar de ahí los días bloqueados es tentador porque el profesional ya
gestiona su tiempo en un calendario que conoce.

**Pero no es gratis y hay que decidirlo, no asumirlo:**

- Un feriado nacional en Google es un evento de calendario público, no una marca
  de "no trabajo". Que exista no implica que el profesional no atienda — de
  hecho, muchos atienden los feriados.
- Requiere distinguir un evento que bloquea la agenda de uno que no
  (`transparency`, todo-el-día vs con horario), y esa heurística va a fallar en
  algún caso.
- La integración actual es de **escritura** (el backend crea eventos). Leer para
  decidir disponibilidad invierte la dirección y agrega un fallo externo en el
  camino crítico de la reserva.

Una carga manual resuelve el caso real —el profesional sabe cuándo no atiende—
sin depender de un servicio externo para poder reservar. La importación puede
venir después, encima de un modelo que ya funcione.

## Preguntas a resolver antes de planificar

- ¿Un día no laborable es todo el día, o hay medias jornadas?
- ¿Qué pasa con los turnos **ya confirmados** en un día que se marca como no
  laborable? ¿Se cancelan, se avisan, se dejan?
- ¿La carga es por fecha suelta o por rango (vacaciones)?
- ¿Se importa de Google, se carga a mano, o ambas?
- ¿Dónde se cargan, si el profesional no tiene panel web todavía? (IN-03 de
  `knowledge-base/10_preguntas_abiertas.md` sigue abierta.)

## Governance

**MEDIUM** en principio; sube a **ALTO** si el alcance incluye cancelar turnos ya
confirmados al marcar un día, porque eso toca agendas de pacientes reales.
