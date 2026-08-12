# C-29 — Confirmación de asistencia con escalado y liberación automática

## Why

El recordatorio pregunta "¿Confirmás tu asistencia?" y ofrece tres botones. Los
callbacks ya llegan al orquestador (arreglado en C-27), pero la respuesta no
tiene consecuencias:

- `confirmar` llama a `turno_service.confirmar_asistencia_turno`, que valida
  ownership y estado y **devuelve el turno sin modificarlo**. No existe ninguna
  columna donde registrar que el paciente respondió.
- Que el paciente ignore el mensaje tampoco tiene consecuencias: el turno queda
  reservado, el profesional pierde el espacio y nadie más puede tomarlo.

El valor del recordatorio no está en avisar; está en **liberar el turno cuando
el paciente no va a venir**. Hoy esa mitad no existe.

## What Changes

Comportamiento definido por el usuario (2026-08-12):

1. **Sin respuesta** → esperar una o dos horas y reenviar el recordatorio,
   ahora advirtiendo que el turno se cancela si no responde en la hora
   siguiente. Si tampoco responde al segundo, el turno se **cancela y el slot
   vuelve a estar disponible**.
2. **Responde cancelar o reprogramar** → se deriva al sub-flujo correspondiente
   y sigue el camino que ya existe.
3. **Responde confirmar** → el turno sigue `CONFIRMADO`; no cambia nada de lo
   que ve el profesional. Solo se le agradece al paciente.

## Design Notes

**El punto 3 no puede ser literalmente "no cambia nada en la base".** El job de
escalado necesita distinguir "el paciente confirmó" de "el paciente ignoró el
mensaje": sin esa marca, el segundo recordatorio le llega igual a quien ya
confirmó y después se le cancela el turno. La marca debe ser un dato propio
—por ejemplo `turno.asistencia_confirmada_en`— y no un estado nuevo: el estado
sigue siendo `CONFIRMADO` y la vista del profesional no cambia, que es lo que
el usuario pidió.

Preguntas abiertas para el design:

- ¿La cancelación automática libera el slot como `DISPONIBLE` u ofrece el turno
  a la lista de espera, que ya existe (`lista_espera_service`)?
- ¿Los intervalos (1-2h y 1h) son configuración o constantes?
- ¿Qué pasa si el segundo recordatorio caería después de la hora del turno?
- ¿El profesional puede ver quién confirmó y quién no?

## Impact

- Affected specs: capability nueva de confirmación de asistencia.
- Affected code: `app/models/turno.py` (+ migración), `app/services/turno_service.py`
  (`confirmar_asistencia_turno`, hoy un no-op), `app/scheduler/jobs.py`,
  `app/services/recordatorio_service.py`, `n8n-workflows/orquestador.json`.
- Depende de: C-27 archivado.
- Governance: MEDIUM — cancela turnos de forma automática, o sea que un error
  acá le borra la agenda a un paciente real.
