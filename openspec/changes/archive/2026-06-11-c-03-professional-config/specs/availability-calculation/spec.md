## ADDED Requirements

### Requirement: Servicio de disponibilidad calcula slots libres
El sistema SHALL proveer un servicio `availability_service.py` que, dada una fecha y un profesional, retorne la lista de horarios de inicio disponibles.

#### Scenario: Cálculo sin turnos existentes
- **WHEN** el servicio recibe una fecha laborable sin turnos ocupados
- **THEN** genera slots desde horario_inicio hasta horario_fin con paso duracion_turno

#### Scenario: Cálculo con turnos ocupados
- **WHEN** el servicio recibe una fecha con turnos CONFIRMADOS o RESERVADO_TEMPORAL
- **THEN** excluye los slots que se solapen con cualquier turno ocupado

#### Scenario: Cálculo en día no laborable
- **WHEN** el servicio recibe una fecha que no pertenece a dias_atencion
- **THEN** retorna lista vacía

### Requirement: No se ofrecen horarios ya ocupados
El sistema SHALL garantizar que un slot nunca se incluya en la disponibilidad si existe un turno en estado CONFIRMADO o RESERVADO_TEMPORAL cuyo intervalo [hora_inicio, hora_fin) se intersecte con el intervalo del slot.

#### Scenario: Solapamiento exacto
- **WHEN** existe un turno 09:00-09:30 y se calcula un slot de 09:00 con duración 30 minutos
- **THEN** el slot 09:00 no aparece en la disponibilidad

#### Scenario: Solapamiento parcial
- **WHEN** existe un turno 09:00-09:30 y se calcula un slot de 09:00 con duración 45 minutos
- **THEN** el slot 09:00 no aparece en la disponibilidad

#### Scenario: Turno adyacente sin solapamiento
- **WHEN** existe un turno 09:00-09:30 y se calcula un slot de 09:30 con duración 30 minutos
- **THEN** el slot 09:30 SÍ aparece en la disponibilidad

### Requirement: Recálculo de slots al cambiar configuración
El sistema SHALL recalcular los slots disponibles usando la configuración más reciente del profesional.

#### Scenario: Cambio de duración de turno
- **WHEN** el profesional cambia duracion_turno de 30 a 60 minutos
- **THEN** las consultas de disponibilidad futuras retornan slots con paso de 60 minutos

#### Scenario: Cambio de días de atención
- **WHEN** el profesional elimina un día de dias_atencion
- **THEN** las consultas de disponibilidad para ese día retornan lista vacía

#### Scenario: Cambio de horario de atención
- **WHEN** el profesional cambia horario_inicio a 10:00
- **THEN** las consultas de disponibilidad futuras no retornan slots antes de las 10:00
