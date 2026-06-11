## 1. Setup y Modelos SQLAlchemy

- [ ] 1.1 Crear `backend/app/models/base.py` con `DeclarativeBase` y configuración común (si no existe).
- [ ] 1.2 Crear `backend/app/models/paciente.py` con modelo `Paciente`: `id`, `nombre`, `apellido`, `dni` (UNIQUE), `telefono`, `creado_en`, relación 1:N `turnos`.
- [ ] 1.3 Crear `backend/app/models/profesional.py` con modelo `Profesional`: `id`, `nombre`, `especialidad`, `duracion_turno`, `horario_inicio`, `horario_fin`, `dias_atencion`, `creado_en`, relación 1:N `turnos`.
- [ ] 1.4 Crear `backend/app/models/turno.py` con modelo `Turno`: `id`, `fecha`, `hora_inicio`, `hora_fin`, `estado` (ENUM nativo PostgreSQL), `paciente_id` (FK nullable), `profesional_id` (FK), `creado_en`, relaciones `paciente`, `profesional`, `reserva_temporal`. Índices `(fecha, hora_inicio)`, `(estado)`, `(paciente_id, estado)`. Constraint `CHECK(hora_fin > hora_inicio)`.
- [ ] 1.5 Crear `backend/app/models/reserva_temporal.py` con modelo `ReservaTemporal`: `id`, `turno_id` (FK, UNIQUE), `expiracion`, índice `expiracion`, relación `turno`.
- [ ] 1.6 Crear `backend/app/models/lista_de_espera.py` con modelo `ListaDeEspera`: `id`, `paciente_id` (FK), `fecha_solicitada`, `creado_en`, `notificado` (BOOLEAN default FALSE), relación `paciente`.
- [ ] 1.7 Crear `backend/app/models/__init__.py` que exporte todos los modelos.

## 2. Alembic Migration

- [ ] 2.1 Generar migración Alembic `001` (autogenerate o manual) que cree todas las tablas: `paciente`, `profesional`, `turno`, `reserva_temporal`, `lista_de_espera`.
- [ ] 2.2 Verificar que la migración incluya: `UNIQUE(dni)`, `CHECK(hora_fin > hora_inicio)`, `UNIQUE(turno_id)` en `reserva_temporal`, FKs con `ondelete` apropiado, y todos los índices definidos.
- [ ] 2.3 Ejecutar `alembic upgrade head` localmente y confirmar que las tablas se crean sin errores.
- [ ] 2.4 Ejecutar `alembic downgrade -1` y confirmar que las tablas se eliminan correctamente.

## 3. Seed Idempotente

- [ ] 3.1 Crear `backend/app/seed.py` con función `seed_profesional()` que inserte un `Profesional` con valores por defecto si no existe ningún registro.
- [ ] 3.2 Integrar el seed en el evento de startup de FastAPI (`@app.on_event("startup")`) en `main.py` o en un script separado invocado al inicio.
- [ ] 3.3 Verificar idempotencia: ejecutar el seed dos veces y confirmar que no se duplica el registro.

## 4. Tests

- [ ] 4.1 Crear `backend/tests/conftest.py` con fixture de `AsyncSession` (SQLite en memoria o PostgreSQL local) para tests async.
- [ ] 4.2 Escribir test `test_paciente_unique_dni`: intentar insertar dos pacientes con mismo DNI y esperar `IntegrityError`.
- [ ] 4.3 Escribir test `test_turno_check_horario`: intentar crear un `Turno` con `hora_fin <= hora_inicio` y esperar `IntegrityError`.
- [ ] 4.4 Escribir test `test_turno_estado_enum`: intentar asignar un estado inválido y esperar `IntegrityError` (o `ValueError` según el driver).
- [ ] 4.5 Escribir test `test_reserva_temporal_unique_turno`: intentar crear dos `ReservaTemporal` con mismo `turno_id` y esperar `IntegrityError`.
- [ ] 4.6 Escribir test `test_integridad_referencial`: intentar crear un `Turno` con `profesional_id` inexistente y esperar `IntegrityError`.
- [ ] 4.7 Escribir test `test_seed_idempotente`: ejecutar `seed_profesional()` dos veces y verificar que `count(Profesional) == 1`.
- [ ] 4.8 Escribir test `test_profesional_turnos_relation`: crear un `Profesional` con 3 `Turno`s y verificar que `profesional.turnos` retorna 3 objetos.
- [ ] 4.9 Escribir test `test_paciente_turnos_relation`: crear un `Paciente` con 2 `Turno`s y verificar que `paciente.turnos` retorna 2 objetos.
- [ ] 4.10 Escribir test `test_lista_de_espera_notificado_default`: crear un registro en `ListaDeEspera` y verificar que `notificado` es `False`.
- [ ] 4.11 Escribir test `test_turno_hora_fin_calculada`: crear un `Turno` con `hora_inicio="09:00"` para un `Profesional` con `duracion_turno=30` y verificar que `hora_fin` es `datetime.time(9, 30)`.
- [ ] 4.12 Ejecutar `pytest` y asegurar que todos los tests pasan (rojo → verde → refactor).
