## 1. Servicios Core — TurnoService

- [x] 1.1 Eliminar `_get_profesional_default()` de `app/services/turno_service.py`
- [x] 1.2 Ajustar `_paciente_tiene_turno_activo` para recibir `profesional_id` y filtrar por `Turno.profesional_id`
- [x] 1.3 Ajustar `reservar_turno` para requerir `profesional_id: int` (no optional) y eliminar fallback a `_get_profesional_default`
- [x] 1.4 Ajustar `confirmar_turno` para requerir `profesional_id: int` y validar que el turno pertenezca al profesional
- [x] 1.5 Ajustar `cancelar_turno` para requerir `profesional_id: int` y validar ownership del turno
- [x] 1.6 Ajustar `reprogramar_turno` para requerir `profesional_id: int` y propagarlo a las sub-operaciones
- [x] 1.7 Ajustar `confirmar_asistencia_turno` para requerir `profesional_id: int` y validar ownership
- [x] 1.8 Ajustar `consultar_disponibilidad` para requerir `profesional_id: int` y eliminar fallback
- [x] 1.9 Ajustar `liberar_reservas_vencidas` para recibir `profesional_id` o iterar por profesional
- [x] 1.10 Ajustar `marcar_turnos_completados` para recibir `profesional_id` o iterar por profesional
- [x] 1.11 Actualizar tests de `tests/services/test_turno_service.py` para pasar `profesional.id` en todas las llamadas

## 2. Servicios Core — PacienteService

- [x] 2.1 Ajustar `crear_o_obtener_paciente` para recibir `profesional_id: int` y filtrar DNI por `profesional_id`
- [x] 2.2 Ajustar `obtener_paciente_con_historial` para recibir `profesional_id: int` y filtrar por él
- [x] 2.3 Ajustar `listar_turnos_por_paciente` para recibir `profesional_id: int` y filtrar turnos por él
- [x] 2.4 Actualizar tests de `tests/services/test_paciente_service.py` para pasar `profesional.id`

## 3. Servicios Core — ListaEsperaService & AvailabilityService

- [x] 3.1 Ajustar `registrar_en_lista_espera` para recibir `profesional_id: int` y asignarlo al registro
- [x] 3.2 Ajustar `eliminar_de_lista_espera` para validar `profesional_id` ownership
- [x] 3.3 Ajustar `obtener_siguiente_paciente_fifo` para filtrar por `profesional_id`
- [x] 3.4 Ajustar `evaluar_lista_espera` para recibir `profesional_id` y eliminar `_get_profesional_default`
- [x] 3.5 Ajustar `aceptar_turno_lista_espera` para validar `profesional_id` del turno ofrecido
- [x] 3.6 Ajustar `rechazar_turno_lista_espera` para validar `profesional_id`
- [x] 3.7 Ajustar `procesar_timeouts_lista_espera` para recibir `profesional_id` o iterar por profesional
- [x] 3.8 Verificar que `calcular_disponibilidad` ya recibe `profesional_id` y no necesita cambios (ajustar call sites)
- [x] 3.9 Actualizar tests de `tests/services/test_lista_espera_service.py`

## 4. Servicios de Integración — CalendarService

- [x] 4.1 Modificar `CalendarService.__init__` para recibir `profesional: Profesional` en lugar de settings globales
- [x] 4.2 Construir credenciales OAuth2 usando `profesional.google_refresh_token` + `GOOGLE_CLIENT_ID/SECRET`
- [x] 4.3 Agregar validación: si `google_refresh_token` es NULL, lanzar ValueError con mensaje claro
- [x] 4.4 Actualizar todos los call sites de `CalendarService()` en `turno_service.py` para pasar `profesional`
- [x] 4.5 Actualizar tests de `tests/services/test_calendar_service.py` (mockear profesional con refresh_token)

## 5. Servicios de Integración — TelegramService

- [x] 5.1 Modificar `_get_bot` para recibir `telegram_bot_token: str` en lugar de usar settings global
- [x] 5.2 Eliminar singleton global `_bot`; permitir instanciación por token
- [x] 5.3 Modificar `enviar_mensaje` para recibir `bot_token: str` o `bot: Bot`
- [x] 5.4 Modificar `accion_turnos_hoy` para filtrar por `profesional_id`
- [x] 5.5 Modificar `accion_metricas` para calcular métricas solo del `profesional_id`
- [x] 5.6 Modificar `_persist_config` para recibir `profesional_id` y eliminar `select(Profesional).first()`
- [x] 5.7 Modificar `mostrar_disponibilidad` para recibir `profesional_id`
- [x] 5.8 Modificar `accion_reservar_temporal` para recibir `profesional_id`
- [x] 5.9 Modificar `procesar_mensaje` y `procesar_update_async` para recibir `profesional_id`
- [x] 5.10 Actualizar tests de `tests/services/test_telegram_service.py`

## 6. Servicios de Integración — NotificacionService

- [x] 6.1 Modificar `obtener_turnos_para_recordar` para recibir `profesional_id: int` y filtrar por él
- [x] 6.2 Modificar `enviar_recordatorio_telegram` para recibir `bot_token: str` del profesional
- [x] 6.3 Modificar `marcar_recordatorio_enviado` para validar `profesional_id` ownership
- [x] 6.4 Actualizar tests de `tests/services/test_notificacion_service.py`

## 7. Router Protection — Turnos, Pacientes, ListaEspera

- [x] 7.1 Agregar `Depends(get_current_profesional)` a todas las rutas de `app/routers/turnos.py`
- [x] 7.2 Pasar `profesional.id` desde `turnos.py` a todos los métodos de `turno_service`
- [x] 7.3 Agregar `Depends(get_current_profesional)` a todas las rutas de `app/routers/pacientes.py`
- [x] 7.4 Pasar `profesional.id` desde `pacientes.py` a todos los métodos de `paciente_service`
- [x] 7.5 Agregar `Depends(get_current_profesional)` a todas las rutas de `app/routers/lista_espera.py`
- [x] 7.6 Pasar `profesional.id` desde `lista_espera.py` a todos los métodos de `lista_espera_service`
- [x] 7.7 Actualizar tests de routers de turnos para usar `authenticated_client`
- [x] 7.8 Actualizar tests de routers de pacientes para usar `authenticated_client`
- [x] 7.9 Actualizar tests de routers de lista_espera para usar `authenticated_client`

## 8. Router Protection — Profesional (self-only)

- [x] 8.1 Agregar `Depends(get_current_profesional)` a `app/routers/profesional.py`
- [x] 8.2 Modificar `get_configuracion` para retornar solo la configuración del profesional autenticado
- [x] 8.3 Modificar `update_configuracion` para permitir update solo del profesional autenticado
- [x] 8.4 Modificar `get_disponibilidad` para usar `profesional.id` del autenticado
- [x] 8.5 Modificar `get_turnos_hoy` para filtrar por `profesional.id`
- [x] 8.6 Modificar `get_metricas` para calcular solo con datos del `profesional.id`
- [x] 8.7 Eliminar TODO "v1.0 asume single-profesional"
- [x] 8.8 Actualizar tests de `tests/routers/test_profesional.py` para usar `authenticated_client`

## 9. Router Protection — Webhooks (Telegram routing)

- [x] 9.1 Crear función `get_profesional_by_telegram_secret_token` en `dependencies.py`
- [x] 9.2 Modificar `app/routers/webhooks.py` para recibir `X-Telegram-Bot-Api-Secret-Token`
- [x] 9.3 Buscar profesional por `telegram_secret_token` y rechazar 403 si no coincide
- [x] 9.4 Pasar `profesional_id` a `procesar_update_async` en background task
- [x] 9.5 Actualizar tests de `tests/routers/test_webhooks.py`

## 10. Scheduler Jobs

- [x] 10.1 Modificar `_liberar_reservas_vencidas_job` para iterar por profesionales activos
- [x] 10.2 Modificar `_marcar_turnos_completados_job` para iterar por profesionales activos
- [x] 10.3 Modificar `_procesar_timeouts_lista_espera_job` para iterar por profesionales activos
- [x] 10.4 Modificar `_enviar_recordatorios_job` para iterar por profesionales activos
- [x] 10.5 Asegurar que cada iteración usa una sesión de DB separada (o reutiliza con cuidado)
- [x] 10.6 Actualizar tests de `tests/scheduler/test_jobs.py`

## 11. Configuración y Variables de Entorno

- [x] 11.1 Agregar `google_client_id` y `google_client_secret` a `app/config.py`
- [x] 11.2 Verificar que `.env.example` (si existe) incluya las nuevas variables
- [x] 11.3 Validar que `Settings()` funciona con y sin las nuevas variables (defaults vacíos)

## 12. Test Migration — Suite Existente

- [x] 12.1 Actualizar `tests/routers/test_turnos.py` para usar `authenticated_client`
- [x] 12.2 Actualizar `tests/routers/test_pacientes.py` para usar `authenticated_client`
- [x] 12.3 Actualizar `tests/routers/test_lista_espera.py` para usar `authenticated_client`
- [x] 12.4 Actualizar `tests/routers/test_profesional.py` para usar `authenticated_client`
- [x] 12.5 Actualizar `tests/routers/test_webhooks.py` para usar secret_token por profesional
- [x] 12.6 Actualizar `tests/services/test_turno_service.py` para pasar `profesional.id`
- [x] 12.7 Actualizar `tests/services/test_paciente_service.py` para pasar `profesional.id`
- [x] 12.8 Actualizar `tests/services/test_lista_espera_service.py` para pasar `profesional.id`
- [x] 12.9 Actualizar `tests/services/test_availability_service.py` si es necesario
- [x] 12.10 Actualizar `tests/services/test_calendar_service.py`
- [x] 12.11 Actualizar `tests/services/test_telegram_service.py`
- [x] 12.12 Actualizar `tests/services/test_notificacion_service.py`
- [x] 12.13 Actualizar `tests/scheduler/test_jobs.py`
- [x] 12.14 Ejecutar suite completa y fixear tests rotos

## 13. Tests de Aislamiento (Nuevos)

- [x] 13.1 Crear `tests/isolation/test_paciente_isolation.py`: Prof A crea paciente → Prof B no lo ve
- [x] 13.2 Crear `tests/isolation/test_turno_isolation.py`: Prof A crea turno → Prof B no lo ve ni cancela
- [x] 13.3 Crear `tests/isolation/test_api_key_isolation.py`: API Key de Prof A no accede datos de Prof B
- [x] 13.4 Crear `tests/isolation/test_jwt_isolation.py`: Token de Prof A retorna Prof A, no Prof B
- [x] 13.5 Crear `tests/isolation/test_lista_espera_isolation.py`: Prof B no ve lista de espera de Prof A
- [x] 13.6 Crear `tests/isolation/test_disponibilidad_isolation.py`: Disponibilidad de Prof A no incluye turnos de Prof B

## 14. Validación y Cierre

- [x] 14.1 Ejecutar `pytest` completo y asegurar que pasa 100%
- [x] 14.2 Ejecutar `openspec validate` y confirmar que pasa
- [x] 14.3 Verificar con `grep` que no quedan referencias a `_get_profesional_default`
- [x] 14.4 Verificar con `grep` que no quedan queries sin filtro de `profesional_id` en servicios
- [x] 14.5 Revisar código con flake8/mypy si están configurados
- [x] 14.6 Documentar breaking changes para integraciones externas (n8n, bots)
