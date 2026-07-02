## Why

El paciente **no se autentica** en el sistema: se **identifica**. Toda la superficie `/turnos/*` exige auth de PROFESIONAL (`CurrentProfesionalDep`, JWT o API key para n8n); el paciente nunca presenta credenciales. Hoy el único identificador de contacto del paciente es una sola columna nullable `paciente.telegram_chat_id`.

Esto rompe un caso real: una misma persona (ej. una abuela, un solo DNI) puede ser gestionada desde **múltiples chats de Telegram** (el nieto esta semana, la hermana la próxima). Con una única columna `telegram_chat_id`, la segunda reserva **sobrescribe** el chat de la primera: la confirmación y el recordatorio del primer turno se envían al chat equivocado o se pierden. La relación chat ↔ paciente es **muchos-a-muchos**; una columna escalar no puede modelarla.

Descubrimiento que agrava el problema: `paciente.telegram_chat_id` **nunca se escribe** en el backend (verificado: los únicos `telegram_chat_id = …` del código son sobre `ListaDeEspera`, no sobre `Paciente`). El job de recordatorios lee `paciente.telegram_chat_id`, que siempre es `NULL`, por lo que **hoy los recordatorios se marcan como enviados sin enviarse**. La columna es efectivamente código muerto y el canal de notificación está roto.

## What Changes

- **Separar identidad de destinatario.** El **beneficiario** (paciente) se identifica por DNI, scoped por profesional (la constraint `UniqueConstraint(profesional_id, dni)` ya existe). El **destinatario de confirmación** (a quién y por qué canal se notifica ESTE turno) se modela aparte.
- **Mover el destinatario+canal al `Turno`.** Se introduce una entidad hija `turno_destinatario` (`turno_id`, `canal`, `destinatario`) con `UNIQUE(turno_id, canal)`. Un turno puede tener uno o más destinatarios, cada uno en un canal distinto.
- **Canal extensible desde el día uno.** Un ENUM `canal_notificacion_enum` con `TELEGRAM` (único activo hoy) y `EMAIL` (modelado, envío fuera de alcance). El paciente puede elegir uno o ambos canales sin migración adicional.
- **El flujo de reserva/confirmación fija el destinatario.** Al reservar desde Telegram se registra el `chat_id` de origen como destinatario `TELEGRAM`; al confirmar se registran/actualizan los destinatarios (chat de Telegram y/o email). Se reutiliza `crear_o_obtener_paciente` (DNI) para resolver al beneficiario; no se crea un camino paralelo.
- **El envío apunta al destinatario del turno.** Confirmaciones y recordatorios se envían al `destinatario` del turno en su `canal`, no a `paciente.telegram_chat_id`. Esto **arregla el bug del recordatorio muerto**.
- **BREAKING:** se elimina la columna `paciente.telegram_chat_id` (columna muerta; conservarla reintroduce la ambigüedad que el cambio elimina).
- **Migración Alembic** para el ENUM, la tabla `turno_destinatario` y el drop de `paciente.telegram_chat_id`, sin tocar `uq_turno_active_slot` ni `uq_paciente_profesional_dni`.

## Capabilities

### New Capabilities
- `turno-destinatario-model`: entidad `turno_destinatario` + ENUM `canal_notificacion_enum`; desacople de identidad (paciente/DNI) y destinatario (turno/canal); soporte multi-chat para un mismo paciente y multicanal (Telegram ahora, email extensible).

### Modified Capabilities
- `turno-reservation`: la reserva y la confirmación registran/actualizan el destinatario+canal del turno (nuevos requisitos añadidos; no cambia la mecánica de slots ni de concurrencia existente).
- `recordatorio-automatico`: el envío de recordatorio apunta al destinatario `TELEGRAM` del turno en lugar de `paciente.telegram_chat_id`.

## Impact

- **Modelos**: `backend/app/models/turno.py` (relación `destinatarios`), nuevo `backend/app/models/turno_destinatario.py`, `backend/app/models/paciente.py` (quita `telegram_chat_id`).
- **Migración**: nueva revisión Alembic en `backend/alembic/versions/` (crea enum + tabla, dropea columna).
- **Schemas**: `backend/app/schemas/turno.py` (`ReservaTurnoRequest`, `ConfirmarTurnoRequest`, `TurnoResponse`), nuevo schema de destinatario.
- **Servicios**: `turno_service.reservar_turno`/`confirmar_turno` (fijan destinatarios), `notificacion_service.enviar_recordatorio_telegram` (lee destinatario del turno), `telegram_service.accion_reservar_temporal` (propaga `chat_id`).
- **KB**: `04_modelo_de_datos.md` (ERD), `03_actores_y_roles.md` (identificación vs autenticación), `05_reglas_de_negocio.md` (nueva RN de destinatario).
- **Fuera de alcance**: integración real de envío por email (solo el modelo lo soporta); optimización UX de "recordar qué chat reservó para qué paciente" (M:N chat↔paciente); reescritura de workflows n8n.
- **Gobernanza**: dominio CRÍTICO (identidad + modelo de datos). Cambio conservador y explícito; el drop de columna se marca para confirmación humana antes de aplicar.
