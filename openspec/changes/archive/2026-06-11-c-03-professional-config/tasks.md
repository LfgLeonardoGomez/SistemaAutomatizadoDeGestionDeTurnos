## 1. Schemas Pydantic para configuración del profesional

- [ ] 1.1 Crear `ProfesionalConfigResponse` schema en `backend/app/schemas/profesional.py` con campos: `horario_inicio`, `horario_fin`, `dias_atencion`, `duracion_turno`, `especialidad`.
- [ ] 1.2 Crear `ProfesionalConfigUpdate` schema en `backend/app/schemas/profesional.py` con campos editables: `horario_inicio`, `horario_fin`, `dias_atencion`, `duracion_turno` (todos opcionales).
- [ ] 1.3 Agregar validaciones en `ProfesionalConfigUpdate`:
  - `horario_inicio` < `horario_fin` (validator Pydantic v2).
  - `duracion_turno` > 0.
  - `dias_atencion` no vacío y valores válidos.
- [ ] 1.4 Crear `DisponibilidadResponse` schema (lista de `time` o strings ISO) para respuesta del cálculo de slots.

## 2. Router REST para configuración del profesional

- [ ] 2.1 Crear `backend/app/routers/profesional.py` con router FastAPI y prefix `/profesional`.
- [ ] 2.2 Implementar `GET /profesional/configuracion` — retorna configuración del profesional (id=1) usando `ProfesionalConfigResponse`.
- [ ] 2.3 Implementar `PUT /profesional/configuracion` — actualiza campos editables usando `ProfesionalConfigUpdate`, valida y retorna configuración actualizada.
- [ ] 2.4 Incluir el router en `backend/app/main.py`.
- [ ] 2.5 Escribir tests de integración para GET /profesional/configuracion (200, retorno de seed data).
- [ ] 2.6 Escribir tests de integración para PUT /profesional/configuracion (200, validación 422 en horarios, duración, días).

## 3. Servicio de cálculo de disponibilidad

- [ ] 3.1 Crear `backend/app/services/availability_service.py`.
- [ ] 3.2 Implementar `get_db` compatible con async session (reutilizar `dependencies.py` si existe).
- [ ] 3.3 Implementar función `calcular_disponibilidad(db, fecha, profesional_id=1)`:
  - Leer config del profesional.
  - Si el día de la semana no está en `dias_atencion`, retornar lista vacía.
  - Generar slots posibles: desde `horario_inicio` hasta `horario_fin` con paso `duracion_turno`.
  - Query turnos de esa fecha con estado `CONFIRMADO` o `RESERVADO_TEMPORAL`.
  - Excluir slots que se solapen con turnos ocupados (intervalo [hora_inicio, hora_fin)).
  - Retornar lista de horarios de inicio disponibles.
- [ ] 3.4 Agregar docstring y type hints estrictas en todas las funciones públicas del servicio.

## 4. Endpoint de disponibilidad

- [ ] 4.1 Implementar `GET /profesional/disponibilidad?fecha=YYYY-MM-DD` en el router de profesional.
- [ ] 4.2 Usar `DisponibilidadResponse` como `response_model`.
- [ ] 4.3 Escribir tests de integración para el endpoint de disponibilidad.

## 5. Tests unitarios e integración del servicio de disponibilidad

- [ ] 5.1 Test: día laborable sin turnos ocupados retorna todos los slots.
- [ ] 5.2 Test: día no laborable retorna lista vacía.
- [ ] 5.3 Test: turnos CONFIRMADOS excluyen slots solapados.
- [ ] 5.4 Test: turnos RESERVADO_TEMPORAL excluyen slots solapados.
- [ ] 5.5 Test: solapamiento parcial (slot de duración mayor que turno) se excluye correctamente.
- [ ] 5.6 Test: turno adyacente sin solapamiento (ej. 09:00-09:30 y slot 09:30) SÍ está disponible.
- [ ] 5.7 Test: cambio de `duracion_turno` recalcula slots con nuevo paso.
- [ ] 5.8 Test: cambio de `dias_atencion` elimina slots del día removido.
- [ ] 5.9 Test: cambio de `horario_inicio` elimina slots antes del nuevo horario.

## 6. Documentación y validación de borde

- [ ] 6.1 Verificar que el modelo `Profesional` en `backend/app/models/profesional.py` tiene los campos esperados (`horario_inicio`, `horario_fin`, `dias_atencion`, `duracion_turno`).
- [ ] 6.2 Confirmar formato de `dias_atencion` (ARRAY PostgreSQL o VARCHAR) y ajustar schema/validación si es necesario.
- [ ] 6.3 Agregar comentario TODO/FIXME en el router indicando que es single-profesional (v1.0).
- [ ] 6.4 Actualizar `CHANGES.md` marcando `[x]` en C-03 si corresponde (lo hace el orquestador al archivar, pero verificar estado).

## 7. Registro de decisiones en engram

- [ ] 7.1 Guardar en engram la decisión de single-profesional simplificado (`topic_key`: `opsx/c-03-professional-config/propose`).
- [ ] 7.2 Guardar en engram la decisión de schema de salida del cálculo de disponibilidad (lista de `time` objects).
