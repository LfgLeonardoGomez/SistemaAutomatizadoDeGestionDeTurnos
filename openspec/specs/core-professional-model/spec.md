## ADDED Requirements

### Requirement: Profesional tiene configuración de agenda por defecto
El sistema SHALL crear un registro `Profesional` con valores por defecto al iniciar la aplicación si no existe ninguno.

#### Scenario: Seed idempotente en arranque
- **WHEN** la aplicación inicia y no hay registros en `Profesional`
- **THEN** se crea un `Profesional` con nombre="Dr. Por Defecto", especialidad="Odontología general", duracion_turno=30, horario_inicio="08:00", horario_fin="18:00", dias_atencion=["Lunes","Martes","Miércoles","Jueves","Viernes"]

#### Scenario: Seed no duplica registros
- **WHEN** la aplicación inicia y ya existe un `Profesional`
- **THEN** no se crea un segundo registro; el seed es idempotente

### Requirement: Profesional define duración de turnos
El sistema SHALL almacenar `duracion_turno` en minutos para el profesional.

#### Scenario: Duración por defecto
- **WHEN** se consulta el `Profesional` creado por seed
- **THEN** `duracion_turno` es 30 minutos

### Requirement: Profesional tiene horarios de atención
El sistema SHALL almacenar `horario_inicio`, `horario_fin` y `dias_atencion` para el profesional.

#### Scenario: Horarios configurados
- **WHEN** se consulta el `Profesional` creado por seed
- **THEN** `horario_inicio` es "08:00", `horario_fin` es "18:00" y `dias_atencion` incluye los días laborables

#### Scenario: Profesional tiene múltiples turnos
- **WHEN** un `Profesional` tiene 5 turnos asignados
- **THEN** la consulta `profesional.turnos` retorna los 5 turnos
