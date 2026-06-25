# C-16 Breaking Changes

## Summary

C-16 elimina el modo single-professional y hace que **toda operación del backend esté scopeada por `profesional_id`**. Esto es un breaking change para todas las integraciones externas.

---

## 1. API REST — Autenticación obligatoria

### Antes
- Todos los endpoints de negocio (`/turnos`, `/pacientes`, `/lista-espera`, `/profesional`) eran públicos.
- No se requería header de autenticación.

### Ahora
- Todos los endpoints de negocio requieren autenticación:
  - **`Authorization: Bearer <jwt>`** (para sesiones web/Telegram)
  - **`X-API-Key: <api_key>`** (para n8n y bots)
- El único router público es `/auth/*` (register, login, api-key).

### Migración para n8n
Actualizar todos los nodos HTTP Request de n8n para incluir:
```
X-API-Key: {{ $env.API_KEY_DEL_PROFESIONAL }}
```
Cada profesional tiene su propia `api_key` generada en `/auth/api-key`.

---

## 2. Telegram Webhooks — Secret Token por profesional

### Antes
- Un solo webhook `/webhooks/telegram` sin validación de origen.
- Un único bot token global (`TELEGRAM_BOT_TOKEN` en `.env`).

### Ahora
- El webhook requiere el header **`X-Telegram-Bot-Api-Secret-Token`**.
- Cada profesional tiene:
  - `telegram_bot_token` (token del bot propio)
  - `telegram_secret_token` (para validar webhooks)
- El backend busca el profesional por `telegram_secret_token` y rechaza 403 si no coincide.

### Migración
1. Cada profesional debe crear su propio bot en @BotFather.
2. Guardar `telegram_bot_token` y `telegram_secret_token` en la configuración del profesional.
3. Configurar el webhook de Telegram apuntando al backend con el `secret_token` correspondiente.

---

## 3. Google Calendar — OAuth2 por profesional

### Antes
- Un único service account global (`GOOGLE_CALENDAR_CREDENTIALS` en `.env`).
- Todos los turnos se sincronizaban en un calendario compartido.

### Ahora
- `CalendarService` recibe `profesional: Profesional` y construye credenciales OAuth2 usando:
  - `profesional.google_refresh_token`
  - `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` (globales)
- Si `google_refresh_token` es NULL, la sincronización se omite con warning (best-effort).

### Migración
1. Configurar `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` en `.env`.
2. Cada profesional debe completar el flujo OAuth2 para obtener su `refresh_token`.
3. Guardar el `refresh_token` en el campo `google_refresh_token` del profesional.

---

## 4. Eliminación de `_get_profesional_default()`

### Antes
- Los servicios usaban `_get_profesional_default()` que hacía `SELECT first()` y asumía un único profesional.

### Ahora
- La función fue eliminada. Todos los métodos de servicio reciben `profesional_id: int` explícitamente.
- No hay fallback implícito. Cualquier llamada sin `profesional_id` falla.

---

## 5. Scheduler — Jobs multi-profesional

### Antes
- Los jobs del scheduler operaban sobre datos globales (asumiendo un solo profesional).

### Ahora
- Cada job itera sobre `Profesional.is_active == True` y procesa datos por profesional.
- Las sesiones de DB se crean/reutilizan por iteración.

---

## Checklist de migración para Ops

- [ ] Actualizar variables de entorno: eliminar `GOOGLE_CALENDAR_CREDENTIALS`, agregar `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`.
- [ ] Actualizar workflows n8n: agregar header `X-API-Key` en todas las llamadas al backend.
- [ ] Configurar bots de Telegram por profesional y setear `telegram_secret_token`.
- [ ] Obtener `google_refresh_token` para cada profesional que use Calendar.
- [ ] Verificar que todos los profesionales tengan `is_active = True` para que el scheduler los procese.
