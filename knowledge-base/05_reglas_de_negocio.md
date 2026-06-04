# Reglas de Negocio

Cada regla tiene un código único `RN-{DOMINIO}-{NN}` para trazabilidad.

## Dominio: Turnos (RN-TU)

- **RN-TU-01**: Un paciente solo puede tener un turno activo a la vez. Un turno activo es aquel cuyo estado sea `RESERVADO_TEMPORAL` o `CONFIRMADO`.
  - *Justificación*: evita sobre-reservas y garantiza que un mismo paciente no ocupe múltiples franjas horarias.
- **RN-TU-02**: Los turnos completados (`COMPLETADO`) forman el historial del paciente.
  - *Justificación*: permite consultar la última atención y mantener trazabilidad sin redundancia de datos.
- **RN-TU-03**: La reserva temporal expira automáticamente si no se confirma dentro del tiempo definido.
  - *Justificación*: libera el horario para otros pacientes y evita bloqueos innecesarios. El documento fuente menciona "2 minutos" como ejemplo de tiempo límite.
- **RN-TU-04**: La cancelación de un turno confirmado libera el horario para otros pacientes.
  - *Justificación*: optimiza la ocupación de la agenda. El turno cancelado mantiene registro histórico en estado `CANCELADO`.
- **RN-TU-05**: La reprogramación se gestiona como cancelación seguida de nueva reserva.
  - *Justificación*: mantiene trazabilidad del turno original y genera uno nuevo con estado limpio.
- **RN-TU-06**: La disponibilidad de horarios se calcula como: horarios posibles (según configuración del profesional) MINUS turnos en estado `CONFIRMADO` o `RESERVADO_TEMPORAL`.
  - *Justificación*: garantiza que no se ofrezcan horarios ya ocupados.
- **RN-TU-07**: Al confirmar un turno, se crea un evento correspondiente en Google Calendar.
  - *Justificación*: sincroniza la agenda del profesional con una herramienta externa robusta.
- **RN-TU-08**: Al cancelar un turno confirmado, se elimina el evento correspondiente de Google Calendar.
  - *Justificación*: mantiene la consistencia entre el sistema y la agenda externa.
- **RN-TU-09**: Al reprogramar, se elimina el evento anterior de Google Calendar y se crea uno nuevo con el horario actualizado.
  - *Justificación*: refleja el cambio en la agenda sincronizada.

## Dominio: Pacientes (RN-PA)

- **RN-PA-01**: Un paciente se identifica por su DNI. El DNI debe ser único en el sistema.
  - *Justificación*: evita duplicados y permite reconocer usuarios recurrentes automáticamente.
- **RN-PA-02**: Los datos mínimos requeridos para registrar un paciente son: nombre, apellido, DNI y teléfono.
  - *Justificación*: necesarios para la gestión del turno y la comunicación vía Telegram.
- **RN-PA-03**: Se permite la reserva de turnos a nombre de terceros cuando sea necesario.
  - *Justificación*: cubre casos donde un familiar o asistente gestiona el turno.

## Dominio: Recordatorios (RN-RE)

- **RN-RE-01**: El sistema envía recordatorios automáticos 24 horas antes de cada turno confirmado.
  - *Justificación*: reduce la tasa de inasistencias por olvido.
- **RN-RE-02**: El recordatorio debe permitir al paciente confirmar asistencia, cancelar o solicitar reprogramación directamente desde el mensaje recibido.
  - *Justificación*: minimiza la fricción del usuario y agiliza la gestión de la agenda.

## Dominio: Lista de Espera (RN-LE)

- **RN-LE-01**: Cuando se libera un turno (cancelación o expiración de reserva temporal), el sistema notifica al primer paciente en la lista de espera para esa fecha.
  - *Justificación*: maximiza la ocupación de la agenda evitando horarios vacíos.
- **RN-LE-02**: El paciente notificado tiene un tiempo limitado para aceptar el turno liberado antes de pasar al siguiente en la lista.
  - *Justificación*: evita que un único paciente bloquee la reasignación indefinidamente.

## Dominio: Excepciones globales

- **RN-GL-01**: Si un servicio externo (Telegram API o Google Calendar API) no está disponible, el sistema debe registrar el error y reintentar la operación crítica un número configurable de veces antes de notificar al profesional.
  - *Justificación*: evita pérdida de datos ante caídas momentáneas de servicios de terceros.
- **RN-GL-02**: La información de la última atención del paciente se obtiene dinámicamente a partir de los turnos registrados (`COMPLETADO` o `CONFIRMADO` pasados), evitando redundancia de datos.
  - *Justificación*: mantiene la consistencia sin campos adicionales en la entidad Paciente.
