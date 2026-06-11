## Context

C-02 (`core-models`) completó los modelos SQLAlchemy base (`Paciente`, `Profesional`, `Turno`, `ReservaTemporal`, `ListaDeEspera`) junto con la migración inicial y seed data. El modelo `Paciente` ya existe en `backend/app/models/paciente.py` pero no tiene endpoints ni lógica de servicio asociada. Este change construye la capa de aplicación (schemas, servicios, routers) sobre ese modelo existente para habilitar los flujos de reserva y recordatorio que dependen de pacientes identificados.

## Goals / Non-Goals

**Goals:**
- Exponer endpoints REST para crear, consultar y listar pacientes.
- Implementar auto-identificación por DNI (crear si no existe, retornar si existe).
- Proveer historial de turnos del paciente en la consulta (`GET /pacientes/{id}`).
- Validar datos mínimos (nombre, apellido, DNI, teléfono) y unicidad de DNI.
- Cubrir con tests TDD (creación, unicidad, auto-identificación, historial).

**Non-Goals:**
- No se agrega autenticación ni autorización de usuarios (out-of-scope para v1).
- No se modifica el modelo `Paciente` ni se agregan columnas nuevas (ya definido en C-02).
- No se implementa el endpoint de edición/actualización de paciente (se puede agregar en change posterior si surge necesidad).
- No se integra Telegram en este change (lo hace n8n + futuro change de bot).

## Decisions

1. **Pydantic v2 para schemas**  
   - *Rationale*: El proyecto ya usa FastAPI con Pydantic v2. Definimos `PacienteCreate`, `PacienteRead` y `PacienteConHistorial` para separar input/output y aprovechar validación automática.  
   - *Alternativa considerada*: Usar dicts crudos — rechazado por falta de type safety y validación.

2. **Service pattern (`paciente_service.py`)**  
   - *Rationale*: Desacopla lógica de negocio (auto-identificación, validaciones de unicidad) del router y facilita testing unitario sin tocar HTTP.  
   - *Alternativa considerada*: Lógica directa en el router — rechazado por acoplamiento y dificultad de testeo.

3. **Transacción con `SELECT FOR UPDATE` para auto-identificación**  
   - *Rationale*: Previene race conditions cuando dos requests simultáneos intentan crear el mismo DNI. Se hace `SELECT ... FOR UPDATE` sobre DNI antes del `INSERT`.  
   - *Alternativa considerada*: Único constraint de base de datos + manejo de `IntegrityError` — aceptado como fallback, pero el `SELECT FOR UPDATE` da mejor UX controlada antes de explotar.

4. **Historial de turnos como joinedload en el endpoint GET**  
   - *Rationale*: SQLAlchemy 2.0 `selectinload` o `joinedload` evita N+1 al traer turnos del paciente.  
   - *Alternativa considerada*: Endpoint separado exclusivo para historial — rechazado porque el requerimiento pide retornar historial en `GET /pacientes/{id}`; `GET /pacientes/{id}/turnos` existe como alternativa liviana.

5. **Status HTTP estrictos**  
   - *Rationale*: FastAPI exige `response_model` y tipos de retorno. Usamos `201 Created` para `POST`, `200 OK` para `GET`, `404 Not Found` cuando el paciente no existe, `409 Conflict` cuando hay conflicto de DNI (si aplica).  

## Risks / Trade-offs

- **[Risk]** Race condition en creación de paciente con mismo DNI concurrente.  
  → **Mitigación**: Transacción con `SELECT FOR UPDATE` + constraint UNIQUE en DB. Si la transacción falla, manejar `IntegrityError` y retornar el existente.

- **[Risk]** El endpoint `GET /pacientes/{id}` con joinedload de turnos puede ser pesado si un paciente tiene muchos turnos.  
  → **Mitigación**: Por ahora es aceptable dado el volumen esperado de un consultorio odontológico. Si escala, se paginará o se moverá a endpoint separado.

- **[Trade-off]** No se implementa edición/PUT de paciente.  
  → Se prioriza lectura y creación por ser el camino crítico para reservas. Edición se puede agregar como change de mantenimiento.

