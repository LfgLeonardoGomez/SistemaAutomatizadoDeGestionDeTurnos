## Why

C-14 (tenant-data-model) agregó `profesional_id` a `Paciente` y `ListaDeEspera`, y C-15 (tenant-auth-professional) implementó autenticación JWT y API Key por profesional. Sin embargo, **todas las operaciones del backend siguen asumiendo un único profesional global**: los servicios usan `_get_profesional_default()`, los routers no exigen autenticación, los jobs del scheduler operan sobre datos de todos los profesionales, y los tests no verifican aislamiento. Este change cierra la brecha de seguridad y arquitectura haciendo que **cada query, mutación y regla de negocio esté scopeada explícitamente por `profesional_id`**, sentando las bases para el modelo SaaS multi-tenant de v2.0.

## What Changes

- **BREAKING**: Eliminar `_get_profesional_default()` de todos los servicios. Todo método de servicio que hoy la usa debe recibir `profesional_id: int` como parámetro explícito.
- **BREAKING**: Todos los routers REST (`/turnos`, `/pacientes`, `/profesional`, `/lista-espera`) requieren autenticación vía `Depends(get_current_profesional)` y filtran resultados por `profesional.id`.
- **BREAKING**: El router `/webhooks/telegram` deja de usar un `telegram_webhook_secret` global y rutea por `X-Telegram-Bot-Api-Secret-Token` → búsqueda de `Profesional` por `telegram_secret_token`.
- **BREAKING**: `CalendarService` deja de ser singleton con credenciales globales y construye clientes OAuth2 por profesional usando `profesional.google_refresh_token`.
- **BREAKING**: `TelegramService` deja de usar un `_bot` global con un único token y opera con el token del profesional correspondiente.
- **BREAKING**: Todos los jobs de scheduler (`liberar_reservas_vencidas`, `marcar_turnos_completados`, `enviar_recordatorios`, `procesar_timeouts_lista_espera`) iteran por profesional activo o reciben `profesional_id` para filtrar.
- **BREAKING**: Regla de negocio RN-TU-01 se ajusta: un paciente puede tener turno activo con **diferentes** profesionales; el scopeo es por `(profesional_id, paciente_id)`.
- **BREAKING**: Todos los tests existentes (~35 archivos) se actualizan para usar el fixture `profesional` y el `authenticated_client`. Se agregan tests de aislamiento obligatorios.
- Los servicios de negocio (`TurnoService`, `PacienteService`, `ListaEsperaService`, `AvailabilityService`, `NotificacionService`) reciben `profesional_id` y filtran queries SQL en consecuencia.

## Capabilities

### New Capabilities
- `tenant-backend-scoping`: Scoping obligatorio de todas las operaciones del backend por `profesional_id`, incluyendo servicios, routers, scheduler y tests de aislamiento.

### Modified Capabilities
- `turno-reservation`: Requiere `profesional_id` en creación y lectura; RN-TU-01 ahora scopa por profesional.
- `turno-cancel`: Cancelación solo de turnos del profesional autenticado.
- `turno-reschedule`: Reprogramación solo dentro del scope del profesional.
- `turno-completado-transition`: Job scopado por profesional.
- `turno-google-event-persistence`: CalendarService opera con token del profesional.
- `patient-management`: CRUD de pacientes scopado por `profesional_id`; DNI único por profesional.
- `lista-espera-registration`: Registro scopado por profesional.
- `lista-espera-fifo-assignment`: Asignación FIFO scopada por profesional.
- `lista-espera-timeout`: Timeout scopado por profesional.
- `lista-espera-telegram-notification`: Notificación usa bot token del profesional.
- `recordatorio-automatico`: Job de recordatorios filtra por `profesional_id`.
- `professional-turnos-hoy-endpoint`: Endpoint requiere autenticación y retorna solo turnos del profesional.
- `professional-metrics-endpoint`: Métricas calculadas solo con datos del profesional autenticado.
- `configuration-management`: Configuración lee/escribe solo el profesional autenticado.
- `telegram-webhook-reception`: Ruteo por `secret_token` del profesional.
- `telegram-conversation-router`: Procesamiento scopado por profesional.
- `telegram-service-integration`: Servicio Telegram scopado por profesional.
- `google-calendar-sync`: Sync por profesional con refresh token individual.
- `scheduler-skeleton`: Jobs iteran por profesional o filtran por `profesional_id`.

## Impact

- **Código**: Todos los archivos en `app/services/*`, `app/routers/*`, `app/scheduler/jobs.py`, `app/dependencies.py`.
- **Tests**: ~35 archivos de test deben actualizarse; nuevos tests de aislamiento obligatorios.
- **API REST**: Todos los endpoints de negocio ahora requieren header `Authorization: Bearer <JWT>` (excepto `/auth/*` y `/webhooks/telegram` que usa `X-Telegram-Bot-Api-Secret-Token`).
- **Configuración**: Nuevas variables de entorno para Google Calendar OAuth2 por profesional (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) en lugar de service account JSON global.
- **Seguridad**: Cierre de brecha crítica donde cualquier cliente podía leer/escribir datos de cualquier profesional.
