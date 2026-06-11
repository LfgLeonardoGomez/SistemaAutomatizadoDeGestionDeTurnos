## 1. Configuración y Dependencias

- [x] 1.1 Verificar que `google-api-python-client`, `google-auth`, `tenacity` están en `backend/requirements.txt`; agregar si faltan.
- [x] 1.2 Extender `backend/app/config.py` con Pydantic Settings para `GOOGLE_CALENDAR_CREDENTIALS`, `GOOGLE_CALENDAR_ID`, `GOOGLE_CALENDAR_MAX_RETRIES`, `GOOGLE_CALENDAR_BASE_DELAY`, `GOOGLE_CALENDAR_MAX_DELAY`.
- [x] 1.3 Actualizar `backend/.env.example` con las nuevas variables de entorno y valores por defecto.

## 2. Implementación del Servicio

- [x] 2.1 Crear `backend/app/services/calendar_service.py` con clase `CalendarService`.
- [x] 2.2 Implementar autenticación con `google.oauth2.service_account.Credentials` desde `GOOGLE_CALENDAR_CREDENTIALS`.
- [x] 2.3 Implementar `create_event(turno: Turno) -> str` que cree un evento en Google Calendar y retorne el `event_id`.
- [x] 2.4 Implementar `update_event(turno: Turno) -> str` que actualice un evento existente por su `google_event_id`.
- [x] 2.5 Implementar `delete_event(event_id: str) -> None` que elimine un evento de Google Calendar.
- [x] 2.6 Implementar retry con `tenacity` (backoff exponencial + jitter) para errores transitorios (5xx, timeout, connection).
- [x] 2.7 Implementar idempotencia en `create_event`: si el turno ya tiene `google_event_id`, delegar a `update_event` en lugar de crear duplicado.
- [x] 2.8 Agregar logging estructurado en cada operación (event_id, turno_id, excepción).

## 3. Tests (TDD Estricto)

- [x] 3.1 Crear `backend/tests/test_calendar_service.py`.
- [x] 3.2 Escribir test de mock exitoso para `create_event` (verificar payload enviado a Google API).
- [x] 3.3 Escribir test de mock exitoso para `update_event`.
- [x] 3.4 Escribir test de mock exitoso para `delete_event`.
- [x] 3.5 Escribir test de reintentos: simular HTTP 500 y verificar que `tenacity` reintenta N veces antes de fallar.
- [x] 3.6 Escribir test de no-reintento ante HTTP 404 (falla inmediata).
- [x] 3.7 Escribir test de idempotencia: doble `create_event` con mismo turno debe llamar a `update` en la segunda vez.
- [x] 3.8 Escribir test de error de autenticación: credenciales inválidas deben fallar grácilmente con mensaje claro.
- [x] 3.9 Escribir test de configuración: verificar que `Settings` lee correctamente las variables de entorno de calendario.
- [x] 3.10 Ejecutar `pytest` y asegurar que todos los tests pasan.

## 4. Documentación y Cierre

- [x] 4.1 Actualizar `backend/app/services/__init__.py` para exportar `CalendarService` si aplica.
- [x] 4.2 Verificar que `openspec status` marca `c-05-google-calendar-service` como completo.
- [ ] 4.3 Archivar el change con `/opsx:archive c-05-google-calendar-service`.
