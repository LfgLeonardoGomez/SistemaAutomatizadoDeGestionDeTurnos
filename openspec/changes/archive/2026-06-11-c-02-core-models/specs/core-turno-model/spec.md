## ADDED Requirements

### Requirement: Turno tiene máquina de estados bien definida
El sistema SHALL definir el estado de un `Turno` como un ENUM con los valores: `DISPONIBLE`, `RESERVADO_TEMPORAL`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`.

#### Scenario: Estado por defecto
- **WHEN** se crea un `Turno` sin especificar estado
- **THEN** el estado por defecto es `DISPONIBLE`

#### Scenario: Estados válidos
- **WHEN** se intenta asignar a un `Turno` un estado no definido en el ENUM
- **THEN** la base de datos rechaza la operación

### Requirement: Turno tiene horarios válidos
El sistema SHALL garantizar que `hora_fin` sea mayor que `hora_inicio` para todo `Turno`.

#### Scenario: Horario válido
- **WHEN** se crea un `Turno` con `hora_inicio="09:00"` y `hora_fin="09:30"`
- **THEN** la inserción es exitosa

#### Scenario: Horario inválido
- **WHEN** se intenta crear un `Turno` con `hora_inicio="09:30"` y `hora_fin="09:00"`
- **THEN** la base de datos rechaza la inserción por violación de `CHECK(hora_fin > hora_inicio)`

### Requirement: Turno pertenece a un Profesional y opcionalmente a un Paciente
El sistema SHALL exigir `profesional_id` y permitir `paciente_id` nullable en `Turno`.

#### Scenario: Turno disponible sin paciente
- **WHEN** se crea un `Turno` con `profesional_id` válido y `paciente_id=NULL`
- **THEN** el turno se persiste con estado `DISPONIBLE`

#### Scenario: Turno reservado con paciente
- **WHEN** se actualiza un `Turno` con `paciente_id` válido y estado `CONFIRMADO`
- **THEN** el turno se persiste con el paciente asignado

#### Scenario: Turno sin profesional
- **WHEN** se intenta crear un `Turno` sin `profesional_id`
- **THEN** la base de datos rechaza la inserción por violación de `NOT NULL`

### Requirement: Turno tiene índices para consultas eficientes
El sistema SHALL crear índices en `Turno` para las combinaciones `(fecha, hora_inicio)`, `(estado)` y `(paciente_id, estado)`.

#### Scenario: Índices existen
- **WHEN** se inspecciona el esquema de la tabla `turno` en PostgreSQL
- **THEN** los índices `ix_turno_fecha_hora_inicio`, `ix_turno_estado` e `ix_turno_paciente_id_estado` existen

### Requirement: Turno tiene hora_fin calculada según duración del profesional
El sistema SHALL calcular `hora_fin` como `hora_inicio + Profesional.duracion_turno` al momento de la creación del turno.

#### Scenario: Cálculo automático
- **WHEN** se crea un `Turno` con `hora_inicio="09:00"` para un `Profesional` con `duracion_turno=30`
- **THEN** `hora_fin` se calcula como "09:30"
