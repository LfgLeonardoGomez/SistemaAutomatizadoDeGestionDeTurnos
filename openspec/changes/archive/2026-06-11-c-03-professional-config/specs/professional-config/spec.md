## ADDED Requirements

### Requirement: Profesional puede consultar su configuración
El sistema SHALL permitir al profesional obtener su configuración actual de horarios, días de atención y duración de turno.

#### Scenario: Consulta exitosa
- **WHEN** el sistema recibe una petición GET a /profesional/configuracion
- **THEN** retorna un JSON con los campos horario_inicio, horario_fin, dias_atencion, duracion_turno y especialidad

### Requirement: Profesional puede actualizar su configuración
El sistema SHALL permitir al profesional modificar los campos editables de su configuración: horario_inicio, horario_fin, dias_atencion y duracion_turno.

#### Scenario: Actualización exitosa
- **WHEN** el sistema recibe una petición PUT a /profesional/configuracion con los campos editables válidos
- **THEN** actualiza el registro del profesional y retorna la configuración actualizada

#### Scenario: Validación de horarios
- **WHEN** el sistema recibe una petición PUT con horario_inicio >= horario_fin
- **THEN** retorna un error 422 Unprocessable Entity indicando que horario_inicio debe ser menor a horario_fin

#### Scenario: Validación de duración de turno
- **WHEN** el sistema recibe una petición PUT con duracion_turno <= 0
- **THEN** retorna un error 422 Unprocessable Entity indicando que duracion_turno debe ser positiva

#### Scenario: Validación de días de atención
- **WHEN** el sistema recibe una petición PUT con dias_atencion vacío o con valores no válidos
- **THEN** retorna un error 422 Unprocessable Entity indicando que dias_atencion debe contener al menos un día válido

### Requirement: Sistema calcula slots disponibles para una fecha
El sistema SHALL calcular los horarios de inicio disponibles para una fecha dada, considerando la configuración del profesional y los turnos existentes.

#### Scenario: Día laborable con turnos disponibles
- **WHEN** el sistema calcula disponibilidad para un día laborable sin turnos ocupados
- **THEN** retorna todos los slots posibles desde horario_inicio hasta horario_fin con paso igual a duracion_turno

#### Scenario: Día no laborable
- **WHEN** el sistema calcula disponibilidad para un día no incluido en dias_atencion
- **THEN** retorna una lista vacía de slots

#### Scenario: Slots ocupados por turnos confirmados
- **WHEN** el sistema calcula disponibilidad para un día con turnos en estado CONFIRMADO
- **THEN** excluye de la lista los slots cuyo horario_inicio se solape con el rango [hora_inicio, hora_fin) de esos turnos

#### Scenario: Slots ocupados por reservas temporales
- **WHEN** el sistema calcula disponibilidad para un día con turnos en estado RESERVADO_TEMPORAL
- **THEN** excluye de la lista los slots cuyo horario_inicio se solape con el rango [hora_inicio, hora_fin) de esas reservas

#### Scenario: Recálculo al cambiar duración de turno
- **WHEN** el profesional actualiza duracion_turno de 30 a 60 minutos
- **THEN** los slots calculados para fechas futuras usan el nuevo paso de 60 minutos

#### Scenario: Evitar solapamientos parciales
- **WHEN** existe un turno de 09:00 a 09:30 y la duración de turno es 45 minutos
- **THEN** el slot de 09:00 no está disponible, aunque el turno termine antes de que el slot hipotético termine
