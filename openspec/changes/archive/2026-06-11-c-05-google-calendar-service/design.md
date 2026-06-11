## Context

El proyecto adopta Google Calendar como agenda espejo (DD-02). La integración con la API de Google Calendar v3 es una operación I/O bloqueante (sincrónica). El backend usa FastAPI con SQLAlchemy 2.0 async. Esto genera un punto de fricción: el SDK de Google es síncrono y no debe ser invocado con `async def` (regla dura del proyecto). Además, el sistema debe ser resiliente ante caídas momentáneas de Google (RN-GL-01), requiriendo reintentos con backoff exponencial.

## Goals / Non-Goals

**Goals:**
- Proporcionar un wrapper de Google Calendar API que exponga `create_event`, `update_event` y `delete_event`.
- Garantizar que la autenticación con cuenta de servicio OAuth 2.0 funcione vía JSON de credenciales (`GOOGLE_CALENDAR_CREDENTIALS`).
- Implementar retries con backoff exponencial ante errores transitorios (5xx, timeouts, conexión fallida).
- Todos los parámetros de conexión y reintentos deben ser configurables vía Pydantic Settings (no hardcode).
- Cubrir el servicio con tests unitarios (mock de API, reintentos, idempotencia).

**Non-Goals:**
- No se expone un endpoint REST directo para el calendario; este servicio es interno y consumido por los routers de turnos (C-06, C-07).
- No se maneja múltiples calendarios (un solo `GOOGLE_CALENDAR_ID` por instancia).
- No se implementa sincronización bidireccional (solo push: sistema → Google Calendar).

## Decisions

### DEC-01: Servicio síncrono con `def` (no `async def`)
**Decisión**: El `calendar_service.py` usará funciones síncronas (`def`) y será invocado desde endpoints async vía `run_in_threadpool` de FastAPI.
**Razonamiento**: El SDK de Google (`google-api-python-client`) es bloqueante. Forzar `async def` sin un executor real bloquearía el event loop. FastAPI ya ejecuta `def` en un threadpool por defecto cuando se usan como dependencias o en endpoints.
**Alternativas consideradas**: Wrappear todo el servicio con `run_in_threadpool` internamente. Descartado porque oculta el contrato de sincronía y puede llevar a nested threadpool problems.

### DEC-02: Backoff exponencial con `tenacity`
**Decisión**: Usar `tenacity` para retries con backoff exponencial y jitter.
**Razonamiento**: Es la biblioteca estándar en Python para reintentos, más robusta que implementar manualmente. Permite configurar `max_retries`, `base_delay`, `max_delay` y `retryable_exceptions` (HTTP 5xx, `socket.timeout`, `ConnectionError`).
**Alternativas consideradas**: Implementar loop manual con `time.sleep`. Descartado por falta de jitter y dificultad de testing.

### DEC-03: Autenticación con cuenta de servicio (Service Account)
**Decisión**: Usar `google.oauth2.service_account.Credentials` desde un JSON de credenciales.
**Razonamiento**: No requiere interacción humana (consentimiento OAuth), es ideal para servidores backend. El JSON se inyecta vía variable de entorno `GOOGLE_CALENDAR_CREDENTIALS`.
**Alternativas consideradas**: OAuth 2.0 de flujo de autorización (authorization code). Descartado porque requiere intervención del profesional y no es apto para un backend desatendido.

### DEC-04: Mapping de `Turno` a evento de Google Calendar
**Decisión**: El evento se titula con el nombre del paciente y la descripción incluye DNI y teléfono. Las fechas/horas se serializan en formato ISO 8601 con timezone local.
**Razonamiento**: El profesional debe identificar rápidamente al paciente en su calendario. Se incluye DNI para trazabilidad interna. El formato ISO 8601 es el requerido por la API de Google.

### DEC-05: Logging estructurado de errores
**Decisión**: Todos los errores de Google Calendar API se loguean con `logging.getLogger(__name__)` incluyendo `event_id`, `turno_id` y código de error HTTP.
**Razonamiento**: Facilita el debugging operativo sin exponer información sensible en las respuestas HTTP al cliente.

## Risks / Trade-offs

- [Riesgo] Google Calendar API no está disponible en el entorno de CI → usar mocks estrictos en tests. No ejecutar tests de integración reales en CI.
- [Riesgo] El calendario destino (`GOOGLE_CALENDAR_ID`) no existe o las credenciales expiran → el servicio fallará en runtime. Mitigación: validar la existencia del calendario al iniciar la aplicación (health check extendido en C-06 o futuro change).
- [Riesgo] Race condition si se crean dos eventos para el mismo turno. Mitigación: usar `google_event_id` único (UUID o hash determinístico) para garantizar idempotencia en `create_event`.
- [Riesgo] Limite de rate de Google Calendar API (cerca de 1 req/segundo). Mitigación: este sistema no tendrá alta frecuencia de writes en v1.0 (un consultorio). Si se escala, evaluar batching o caché.

## Migration Plan

- No aplica migración de datos: este change no modifica la base de datos.
- Requiere que el usuario configure `GOOGLE_CALENDAR_CREDENTIALS` y `GOOGLE_CALENDAR_ID` en `.env` antes de desplegar.
- Si las credenciales no están presentes, la aplicación debe levantar igual (no bloquear startup) pero el servicio fallará grácilmente al ser invocado. Esto permite tests locales sin credenciales reales.
