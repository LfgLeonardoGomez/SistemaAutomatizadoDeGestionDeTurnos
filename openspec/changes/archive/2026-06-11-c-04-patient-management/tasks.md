## 1. Schemas Pydantic

- [x] 1.1 Crear `backend/app/schemas/paciente.py` con `PacienteCreate`, `PacienteRead`, `PacienteConHistorial`
- [x] 1.2 Agregar tests de validación de schemas (campos requeridos, tipos, formato)

## 2. Service de Pacientes

- [x] 2.1 Crear `backend/app/services/paciente_service.py` con función `crear_o_obtener_paciente`
- [x] 2.2 Implementar validación de DNI único y auto-identificación con transacción `SELECT FOR UPDATE`
- [x] 2.3 Implementar `obtener_paciente_con_historial` con joinedload de turnos
- [x] 2.4 Implementar `listar_turnos_por_paciente`
- [x] 2.5 Agregar tests unitarios para `paciente_service.py` (crear, auto-identificar, DNI duplicado, historial, turnos)

## 3. Router / Endpoints

- [x] 3.1 Crear `backend/app/routers/pacientes.py` con `POST /pacientes`
- [x] 3.2 Implementar `GET /pacientes/{id}` con historial de turnos
- [x] 3.3 Implementar `GET /pacientes/{id}/turnos`
- [x] 3.4 Registrar router en `backend/app/main.py` con prefijo `/pacientes`
- [x] 3.5 Agregar tests de integración para endpoints (CRUD, unicidad DNI, auto-identificación, historial, 404)

## 4. Verificación y Cierre

- [x] 4.1 Ejecutar `pytest` y asegurar que todos los tests pasan (coverage ≥ 90% del nuevo código)
- [x] 4.2 Verificar OpenAPI docs en `/docs` muestran los nuevos endpoints correctamente
- [x] 4.3 Revisar que no se violan reglas duras (type hints, response_model, no hardcoded config)
