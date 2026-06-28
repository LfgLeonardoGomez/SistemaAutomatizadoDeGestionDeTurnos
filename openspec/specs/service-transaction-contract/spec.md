# service-transaction-contract Specification

## Purpose
TBD - created by archiving change transaction-hardening. Update Purpose after archive.
## Requirements
### Requirement: Servicios no realizan commit; routers y scheduler son responsables de commit/rollback
El sistema SHALL exigir que los servicios de dominio (capa `app/services/`) **NO** ejecuten `await db.commit()` ni `await db.rollback()`. Los servicios SHALL limitarse a operaciones de modificación de sesión: `db.add()`, `db.delete()`, mutaciones de atributos de entidades (`obj.attr = value`), y `await db.flush()` cuando se requiera un identificador de base de datos. Los routers (`app/routers/`) y el scheduler (`app/scheduler/jobs.py`) SHALL ser los únicos responsables de invocar `await db.commit()` en el happy path y `await db.rollback()` ante excepciones. Este contrato SHALL permitir que operaciones compuestas (que llaman a múltiples servicios) ejecuten atómicamente bajo una única transacción administrada por el caller.

#### Scenario: Servicio no contiene commit ni rollback
- **WHEN** se inspecciona el código de un servicio de dominio en `app/services/`
- **THEN** ninguna función SHALL contener `await db.commit()` ni `await db.rollback()`
- **AND** la única excepción permitida es `await db.flush()` para obtener identificadores antes del commit

#### Scenario: Router realiza commit en happy path
- **WHEN** un endpoint HTTP llama a un servicio y la operación retorna exitosamente
- **THEN** el router SHALL invocar `await db.commit()` antes de retornar la respuesta
- **AND** los cambios SHALL estar persistidos en la base de datos al retornar HTTP 2xx

#### Scenario: Router realiza rollback ante excepción de servicio
- **WHEN** un endpoint HTTP llama a un servicio y el servicio lanza una excepción de negocio (ej. `TurnoNoDisponibleError`, `PacienteConTurnoActivoError`, `TurnoExpiradoError`)
- **THEN** el router SHALL invocar `await db.rollback()` antes de traducir la excepción a HTTPException
- **AND** la base de datos SHALL no contener ningún cambio parcial dejado por la operación fallida

#### Scenario: Scheduler realiza commit al final del job
- **WHEN** un job del scheduler ejecuta una operación de servicio que modifica la sesión
- **THEN** el job SHALL invocar `await db.commit()` al final del bloque de ejecución exitosa
- **AND** el job SHALL envolver la operación en `try/except` que invoca `rollback()` ante excepción y registra el error sin detener el scheduler

#### Scenario: Operación compuesta es atómica
- **WHEN** `reprogramar_turno` llama secuencialmente a `cancelar_turno`, `reservar_turno` y `confirmar_turno` sin que estos commiteen internamente
- **THEN** la transacción controlada por el caller (router) SHALL agrupar las tres operaciones
- **AND** si la tercera operación falla, SHALL haber rollback completo: el turno original permanece en su estado previo (`CONFIRMADO`) y no existe el nuevo turno en la base de datos

### Requirement: Servicios usan savepoint para errores recuperables sin destruir la transacción externa
Los servicios SHALL usar `async with db.begin_nested():` (savepoint) cuando necesiten ejecutar operaciones que pueden fallar con `IntegrityError` u otro error recuperable, de modo que el error no destruya la transacción del caller. Este patrón SHALL aplicarse al upsert de entidades por clave natural (ej. `crear_o_obtener_paciente` por DNI).

#### Scenario: Savepoint contiene IntegrityError sin afectar transacción externa
- **WHEN** `crear_o_obtener_paciente` intenta insertar un paciente cuyo `UNIQUE(dni, profesional_id)` ya existe
- **THEN** el `IntegrityError` SHALL ser capturado dentro de un savepoint
- **AND** la transacción externa SHALL continuar válida
- **AND** el servicio SHALL retornar el paciente existente

