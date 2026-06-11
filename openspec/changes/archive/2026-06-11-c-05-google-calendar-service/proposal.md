## Why

El sistema necesita sincronizar los turnos confirmados con una agenda externa robusta para que el profesional visualice su horario en una herramienta familiar. Delegar la gestión del calendario a Google Calendar (DD-02) elimina la necesidad de desarrollar un calendario propio y mejora la adopción. Sin embargo, el acceso a la API de Google Calendar requiere un wrapper controlado que maneje autenticación, reintentos y errores de forma resiliente, cumpliendo la regla de negocio RN-GL-01 (servicios externos con reintentos configurables).

## What Changes

- Crear `backend/app/services/calendar_service.py`: wrapper síncrono sobre Google Calendar API v3.
- Implementar métodos: `create_event(turno)`, `update_event(turno)`, `delete_event(event_id)`.
- Agregar retries con backoff exponencial ante errores transitorios (HTTP 5xx, timeouts).
- Implementar autenticación OAuth 2.0 con cuenta de servicio usando `GOOGLE_CALENDAR_CREDENTIALS` (JSON) y `GOOGLE_CALENDAR_ID`.
- Extender `backend/app/config.py` con Pydantic Settings para variables de calendario.
- Crear suite de tests: mock de Google Calendar API, reintentos ante 5xx, idempotencia de creación.
- **BREAKING**: `requirements.txt` debe incluir `google-api-python-client` y `google-auth` (ya presentes desde C-01, pero este change las activa).

## Capabilities

### New Capabilities
- `google-calendar-sync`: Wrapper de Google Calendar API con autenticación, CRUD de eventos y reintentos configurables.

### Modified Capabilities
- Ninguno: este change no modifica specs existentes; introduce una nueva capacidad de integración.

## Impact

- **Backend**: nuevo servicio `calendar_service.py`, nuevos settings en `config.py`.
- **Dependencias**: `google-api-python-client`, `google-auth`, `google-auth-oauthlib` (ya en `requirements.txt` desde C-01).
- **Configuración**: nuevas variables de entorno obligatorias: `GOOGLE_CALENDAR_CREDENTIALS`, `GOOGLE_CALENDAR_ID`.
- **Tests**: tests unitarios con mocks de la API de Google (no requiere conexión real en CI).
- **Futuros changes**: C-06 (turno-reservation), C-07 (turno-cancel-reschedule) y C-11 (lista-espera) dependerán de este servicio para sincronizar eventos.
