## 1. Modelo y Migración

- [x] 1.1 Agregar columna `recordatorio_enviado` (Boolean, default `False`, nullable=False) al modelo `Turno` en `backend/app/models/turno.py`
- [x] 1.2 Generar migración Alembic `add_recordatorio_enviado_to_turnos` con upgrade/downgrade
- [x] 1.3 Ejecutar migración en entorno de desarrollo y verificar schema
- [x] 1.4 Escribir test unitario del modelo: instanciar `Turno` y verificar `recordatorio_enviado` default `False`

## 2. Configuración

- [x] 2.1 Agregar `recordatorio_horas_antes: int = 24` a `backend/app/config.py` (Pydantic Settings, variable `RECORDATORIO_HORAS_ANTES`)
- [x] 2.2 Agregar `recordatorio_job_interval_minutos: int = 60` a `backend/app/config.py` (variable `RECORDATORIO_JOB_INTERVAL_MINUTOS`)
- [x] 2.3 Actualizar `.env.example` con las nuevas variables
- [x] 2.4 Escribir test: instanciar `Settings` y verificar defaults de recordatorio

## 3. Servicio de Notificación

- [x] 3.1 Crear `backend/app/services/notificacion_service.py` con función `obtener_turnos_para_recordar(db, horas_antes: int) -> list[Turno]`
  - Query: turnos `CONFIRMADO`, `recordatorio_enviado = False`, fecha/hora dentro de ventana
  - Usar `datetime.now()` local y combinar con `fecha` + `hora_inicio`
- [x] 3.2 Crear función `enviar_recordatorio_telegram(turno: Turno) -> bool` en `notificacion_service.py`
  - Formatear mensaje con fecha, hora, nombre del paciente
  - Construir `InlineKeyboardMarkup` con botones: "Confirmar asistencia", "Cancelar", "Reprogramar"
  - Usar `run_in_threadpool` para envío no bloqueante
  - Retornar `True` si el envío fue exitoso, `False` si falló
- [x] 3.3 Crear función `marcar_recordatorio_enviado(db, turno_id: int) -> None` en `notificacion_service.py`
- [x] 3.4 Escribir tests unitarios (TDD red → green):
  - Query correcta dentro/fuera de ventana
  - Envío exitoso mock de Telegram
  - Falla de Telegram no marca flag
  - Paciente sin `chat_id` marca flag y no envía

## 4. Scheduler Job

- [x] 4.1 Crear función `_enviar_recordatorios_job(session: Optional[AsyncSession] = None) -> None` en `backend/app/scheduler/jobs.py`
  - Obtener session si no se provee
  - Llamar `obtener_turnos_para_recordar`
  - Para cada turno: enviar recordatorio; si éxito, marcar flag; si falla, loguear y continuar
  - Usar `SELECT FOR UPDATE` al obtener turnos para prevenir race conditions
- [x] 4.2 Registrar el job en `init_scheduler` con `AsyncIOScheduler.add_job`, intervalo desde `settings.recordatorio_job_interval_minutos`
- [x] 4.3 Escribir tests de integración del job:
  - Job encuentra 2 turnos candidatos y envía 2 mensajes
  - Job no encuentra turnos y no envía nada
  - Job maneja excepción de Telegram sin detenerse

## 5. Integración Telegram (Callback Handlers)

- [x] 5.1 Completar handler de callback `reminder:` en `backend/app/services/telegram_service.py`
  - `reminder:confirmar:<turno_id>` → llamar endpoint `PUT /turnos/{id}/confirmar-asistencia` y responder mensaje de agradecimiento
  - `reminder:cancelar:<turno_id>` → reutilizar `cancelar_turno` y responder confirmación
  - `reminder:reprogramar:<turno_id>` → reutilizar `accion_iniciar_reprogramacion`
- [x] 5.2 Crear función `format_recordatorio_mensaje(turno: dict, paciente: dict) -> str` en `telegram_service.py`
  - Formato MarkdownV2 con escape correcto
  - Incluir fecha, hora, nombre del paciente
- [x] 5.3 Crear función `format_recordatorio_keyboard(turno_id: int) -> InlineKeyboardMarkup` en `telegram_service.py`
- [x] 5.4 Escribir tests de routing de callbacks:
  - Callback `reminder:confirmar:5` enruta correctamente
  - Callback `reminder:cancelar:5` ejecuta cancelación
  - Callback `reminder:reprogramar:5` inicia wizard

## 6. Endpoint REST

- [x] 6.1 Crear endpoint `PUT /turnos/{turno_id}/confirmar-asistencia` en `backend/app/routers/turnos.py` (o router existente)
  - `response_model` definido (ej. `TurnoResponse` o esquema simple)
  - Buscar turno por ID, validar estado `CONFIRMADO`
  - No modificar estado (permanece `CONFIRMADO`); opcionalmente agregar campo `asistencia_confirmada_en` timestamp si se decide
  - Retornar turno actualizado
- [x] 6.2 Escribir tests del endpoint (TDD):
  - Confirmar asistencia de turno CONFIRMADO → 200
  - Confirmar asistencia de turno CANCELADO → 400/422
  - Confirmar asistencia de turno inexistente → 404

## 7. Tests de Integración y Verificación

- [x] 7.1 Test E2E: crear turno CONFIRMADO dentro de 24h → ejecutar job → verificar que se envió mensaje de Telegram mock → verificar `recordatorio_enviado = True`
- [x] 7.2 Test E2E: paciente presiona "Confirmar asistencia" desde recordatorio → verificar endpoint responde 200 → verificar mensaje de agradecimiento enviado
- [x] 7.3 Test E2E: paciente presiona "Cancelar" desde recordatorio → verificar turno pasa a CANCELADO y google_event_id se elimina (mock)
- [x] 7.4 Verificar cobertura de tests > 80% para archivos nuevos/modificados
- [x] 7.5 Ejecutar `pytest` completo y confirmar que ningún test existente se rompe (regresión)

## 8. Documentación y Cierre

- [x] 8.1 Actualizar `README.md` del backend (o docs correspondiente) con las nuevas variables de entorno
- [x] 8.2 Verificar que `AGENTS.md` no requiere actualización (no cambia reglas duras)
- [x] 8.3 Ejecutar `openspec verify` si está disponible, o revisión manual contra specs
- [x] 8.4 Ejecutar `openspec archive c-10-recordatorios` para cerrar el change
