## Context

**Dominio CRÍTICO** (identidad + modelo de datos). El diseño es conservador y explícito, y marca los puntos que requieren confirmación humana antes de aplicar.

### Realidad verificada en el código

- Toda la superficie `/turnos/*` exige auth de PROFESIONAL (`CurrentProfesionalDep`, `backend/app/dependencies.py:62-95`). n8n actúa en nombre del profesional vía `X-API-Key` (`get_profesional_by_api_key`). El paciente **nunca** se autentica: se **identifica**.
- `Paciente` ya se identifica por DNI scoped por profesional: `UniqueConstraint("profesional_id", "dni")` (`paciente.py:39-42`). `crear_o_obtener_paciente` (`paciente_service.py:12`) resuelve al beneficiario por DNI con `SELECT FOR UPDATE` + savepoint. Este es el camino de resolución de beneficiario a reutilizar.
- `paciente.telegram_chat_id` (`paciente.py:18-20`) es una **columna muerta**: no hay ninguna asignación en `backend/app/` (los únicos `telegram_chat_id=` son sobre `ListaDeEspera`, `lista_espera_service.py:54` y `routers/lista_espera.py:28`). El job `enviar_recordatorio_telegram` (`notificacion_service.py:58`) lee `paciente.telegram_chat_id`, que siempre es `NULL`, y en consecuencia marca `recordatorio_enviado=True` **sin enviar nada** (`notificacion_service.py:59-64`). El canal de recordatorios está roto hoy.
- **Precedente de diseño**: `ListaDeEspera` ya modela `telegram_chat_id` **por registro** (por notificación), no por paciente (`04_modelo_de_datos.md:96`). Poner el destinatario en el turno sigue el mismo criterio ya presente en el dominio.
- `ConfirmarTurnoRequest` ya declara un `email: Optional[str]` **sin usar** (`schemas/turno.py:24`). Es el gancho natural para el canal `EMAIL`.
- Concurrencia ya endurecida: índice parcial `uq_turno_active_slot` (`turno.py:81-88`) y `SELECT FOR UPDATE` en reserva/confirmación. **No se toca.**

### Stack y constraints

- FastAPI + SQLAlchemy 2.0 async + PostgreSQL; Alembic para migraciones (head actual: `ch23a7b9c8d2`).
- pytest + pytest-asyncio + testcontainers[postgres] (PostgreSQL real). TDD estricto (RED→GREEN→REFACTOR).
- Patrón A: los servicios no commitean; el router/scheduler commitea.
- Pydantic v2; `response_model`/tipos de retorno siempre; una operación HTTP por función; sin hardcodear config.

## Goals / Non-Goals

**Goals:**
1. Separar **beneficiario** (paciente/DNI) de **destinatario de confirmación** (contacto de ESTE turno).
2. Modelar destinatario+canal en el turno de forma **extensible** (Telegram hoy, email después, uno o ambos).
3. Que reserva y confirmación fijen el destinatario+canal; que confirmaciones y recordatorios apunten a ese destinatario.
4. Arreglar el bug del recordatorio muerto (dejar de leer `paciente.telegram_chat_id`).
5. Soportar el caso multi-chat para un mismo paciente sin sobrescritura.

**Non-Goals:**
- Implementar el envío real por email (solo el modelo lo soporta; el sender queda para un change futuro).
- Optimización UX "recordar qué chat reservó para qué paciente" (M:N chat↔paciente persistente).
- Reescritura de workflows n8n (el contrato REST cambia; n8n se adapta en su propio change).
- Cambiar la lógica de slots, concurrencia, cancelación o Google Calendar.

## Decisions

### Decisión 1 (CLAVE): tabla hija `turno_destinatario` en vez de columnas en `turno`

**Elegido**: entidad hija `turno_destinatario(id, turno_id FK CASCADE, canal ENUM, destinatario VARCHAR(255), creado_en)` con `UNIQUE(turno_id, canal)`. Un turno tiene 0..N destinatarios, uno por canal.

**Alternativas consideradas:**
- **A) Columnas simples en `turno`** (`canal` + `destinatario`): un solo canal por turno. **Rechazada** porque el requisito de negocio es explícito: "uno o **ambos** canales". Con columnas escalares, soportar Telegram + email a la vez exige una migración rompedora en cuanto aparezca el segundo canal. La tabla hija hace la extensibilidad **real, no teórica**.
- **B) JSON/array de destinatarios en `turno`**: **rechazada**. Pierde la `UNIQUE(turno_id, canal)`, no valida el ENUM a nivel DB, y complica el query del sender.
- **C) Entidad de "preferencia de notificación" a nivel Paciente**: **rechazada**. Reintroduce el acoplamiento paciente↔chat que este cambio elimina; no soporta multi-chat por turno.

**Rationale**: es la forma normalizada mínima que cumple "uno o ambos canales" y multi-chat, sin over-engineering. Sigue el precedente de `ListaDeEspera` (contacto por registro). Es turno-scoped: no necesita `profesional_id` propio (el tenant se alcanza vía `turno.profesional_id`); la constraint tenant-first no aplica a esta tabla porque su scope es el turno, no el profesional.

**Modelo (SQLAlchemy):**
```python
class TurnoDestinatario(Base):
    __tablename__ = "turno_destinatario"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    turno_id: Mapped[int] = mapped_column(
        ForeignKey("turno.id", ondelete="CASCADE"), nullable=False
    )
    canal: Mapped[str] = mapped_column(
        SAEnum("TELEGRAM", "EMAIL", name="canal_notificacion_enum",
               create_type=False, native_enum=True),
        nullable=False,
    )
    destinatario: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(), default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    __table_args__ = (
        UniqueConstraint("turno_id", "canal", name="uq_turno_destinatario_canal"),
        Index("ix_turno_destinatario_turno_id", "turno_id"),
    )
```
En `Turno`: `destinatarios: Mapped[list["TurnoDestinatario"]] = relationship(back_populates="turno", lazy="selectin", cascade="all, delete-orphan")`.

### Decisión 2 (requiere confirmación humana — CRÍTICO): DROP de `paciente.telegram_chat_id`

**Elegido (recomendado)**: eliminar la columna. Es código muerto (nunca se escribe) y su único lector se refactoriza en este cambio.

**Alternativa**: conservarla nullable como "contacto preferido por defecto". **Rechazada** porque un chat por defecto a nivel paciente **reintroduce exactamente la ambigüedad** que el cambio elimina (chat↔paciente es M:N). Mantener una columna muerta y contradictoria es deuda que engaña al próximo lector.

**Naturaleza**: cambio **BREAKING** de esquema. Bajo gobernanza CRÍTICA, se marca como **decisión a confirmar por el usuario antes de aplicar**. `downgrade` re-agrega la columna nullable (sin datos, porque nunca los hubo).

### Decisión 3: dónde se fija el destinatario en el flujo

- **Reserva** (`reservar_turno`): parámetro opcional `telegram_chat_id`. El bot conoce el `chat_id` de origen (`telegram_service.accion_reservar_temporal`, `telegram_service.py:471`), así que se registra un destinatario `TELEGRAM` en la creación. Si no viene, el turno queda sin destinatario y se difiere a la confirmación.
- **Confirmación** (`confirmar_turno`): `ConfirmarTurnoRequest` gana `telegram_chat_id: Optional[str]` (y ya tiene `email`). El servicio hace **upsert** de destinatarios por `(turno_id, canal)`: si viene `telegram_chat_id` → fila/actualiza `TELEGRAM`; si viene `email` → fila/actualiza `EMAIL`. Esto cubre el caso n8n, que conoce el `chat_id` del update de Telegram y lo pasa en el confirm.
- **Helper**: `notificacion_target_service.upsert_destinatario(db, turno_id, canal, destinatario)` (o función en `turno_service`) que centraliza el upsert respetando `UNIQUE(turno_id, canal)` (SELECT existente → update, si no INSERT). Patrón A (sin commit).

### Decisión 4: el envío apunta al destinatario del turno

- `enviar_recordatorio_telegram` (`notificacion_service.py:47`) deja de leer `paciente.telegram_chat_id` y lee el destinatario `TELEGRAM` del turno (`turno.destinatarios` filtrado por canal). Si no hay destinatario `TELEGRAM`, mantiene el comportamiento actual de "marcar enviado y loguear warning" (evita reintentos infinitos), pero ahora por ausencia de destinatario, no por columna muerta.
- El sender de `EMAIL` **no se implementa**: si un turno tiene destinatario `EMAIL`, el modelo lo persiste pero el envío queda fuera de alcance (log informativo). Esto mantiene la extensibilidad real sin trabajo de integración de email.

### Decisión 5: migración Alembic explícita

Nueva revisión con `down_revision="ch23a7b9c8d2"` (head actual verificado). Apply DEBE confirmar el head con `alembic heads` antes de fijar `down_revision`.

## Risks / Trade-offs

- **R1 (CRÍTICO): DROP de columna es destructivo.** Mitigación: la columna es provablemente muerta (0 escrituras, 1 lector refactorizado). Confirmación humana requerida antes de aplicar. `downgrade` la recrea.
- **R2: cambio de contrato REST** (`ReservaTurnoRequest`/`ConfirmarTurnoRequest` ganan campos opcionales). Mitigación: los campos son **opcionales** → retrocompatibles; n8n sigue funcionando y se actualiza para enviar `chat_id` en su propio change.
- **R3: no romper concurrencia.** La migración NO toca `uq_turno_active_slot` ni `uq_paciente_profesional_dni`. `turno_destinatario` es tabla nueva e independiente.
- **R4: turnos históricos sin destinatario.** Los turnos existentes quedan sin `turno_destinatario` (antes tampoco enviaban nada útil, la columna era muerta). El recordatorio los tratará como "sin destinatario Telegram" → marca enviado + warning. Comportamiento aceptable y no peor que hoy.
- **R5: enum en PostgreSQL.** Igual que `turno_estado_enum`, el enum se crea explícitamente en la migración (`create_type=False` en el modelo). Hay que crear el tipo con `sa.Enum(...).create(bind)` o `op.execute("CREATE TYPE ...")` en `upgrade` y `DROP TYPE` en `downgrade`.

## Migration Plan

### Fase 0: confirmación (gobernanza CRÍTICA)
- Confirmar con el usuario el **DROP de `paciente.telegram_chat_id`** (Decisión 2) antes de escribir código.

### Fase 1: modelo + migración
1. Nuevo `backend/app/models/turno_destinatario.py` + relación `destinatarios` en `turno.py`; importar el modelo donde se registran los mappers.
2. Quitar `telegram_chat_id` de `paciente.py`.
3. Migración Alembic (`down_revision="ch23a7b9c8d2"`):
   - `upgrade`: `CREATE TYPE canal_notificacion_enum AS ENUM ('TELEGRAM','EMAIL')`; `create_table("turno_destinatario", …)` con FK CASCADE, `UNIQUE(turno_id, canal)`, índice `ix_turno_destinatario_turno_id`; `op.drop_column("paciente", "telegram_chat_id")`.
   - `downgrade`: `add_column("paciente", telegram_chat_id VARCHAR(50) NULL)`; `drop_table("turno_destinatario")`; `DROP TYPE canal_notificacion_enum`.
4. Verificar `alembic upgrade head` y `alembic downgrade -1` en DB limpia.

### Fase 2: schemas (TDD)
- `ReservaTurnoRequest.telegram_chat_id: Optional[str]`; `ConfirmarTurnoRequest.telegram_chat_id: Optional[str]` (email ya existe); `TurnoResponse` opcionalmente expone `destinatarios` (o un schema `TurnoDestinatarioRead`).

### Fase 3: servicio de upsert + reserva/confirmación (TDD)
- Helper de upsert por `(turno_id, canal)`.
- `reservar_turno(..., telegram_chat_id=None)` registra destinatario `TELEGRAM` si viene.
- `confirmar_turno` hace upsert de `TELEGRAM`/`EMAIL` según lo provisto.
- Propagar `chat_id` desde `telegram_service.accion_reservar_temporal`/`accion_confirmar_turno` y desde el router.

### Fase 4: sender de recordatorios (TDD)
- `enviar_recordatorio_telegram` lee el destinatario `TELEGRAM` del turno.
- Test del caso multi-chat: dos turnos del mismo DNI con chats distintos reciben recordatorios en chats distintos.

### Fase 5: verificación
- Suite completa (`pytest`), 0 regresiones sobre baseline.
- `openspec validate c-23-turno-destinatario-multicanal --strict`.
- Actualizar KB (`04`, `03`, `05`) vía chronicle tras archivar.

### Rollback
- `alembic downgrade -1` (recrea columna, dropea tabla y tipo). `git revert` del commit si el código tiene bug.

## Open Questions

- **OQ-1**: ¿Confirmás el **DROP** de `paciente.telegram_chat_id` (recomendado) o preferís conservarla nullable? (Recomendación: DROP; conservarla reintroduce ambigüedad.)
- **OQ-2**: ¿`TurnoResponse` debe exponer los destinatarios en la API, o el destinatario es interno (solo lo consume el sender)? (Recomendación: interno por defecto; exponer solo si n8n lo necesita para debug.)
- **OQ-3**: cuando la confirmación no trae `telegram_chat_id` ni `email` y la reserva tampoco fijó destinatario, el turno queda sin canal. ¿Se rechaza la confirmación, o se permite y el recordatorio hace no-op? (Recomendación: permitir + no-op con warning, como hoy, para no bloquear flujos administrativos/manuales.)
