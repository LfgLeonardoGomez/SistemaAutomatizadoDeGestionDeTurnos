## Why

v1.0 del sistema no tiene autenticación ni autorización formal: cualquier request al backend opera sobre datos del único profesional sin verificar identidad. Para evolucionar a un modelo multi-profesional (SaaS para profesionales independientes) y scoperar todas las operaciones por `profesional_id`, necesitamos una capa de autenticación JWT que identifique al profesional en cada request. Este change desbloquea C-16 (backend scoping) y es prerequisito para cualquier funcionalidad de panel profesional seguro.

## What Changes

- **Nuevo router `/auth`** con endpoints de registro, login y gestión de API keys.
- **JWT middleware** (`get_current_profesional`) extraíble como `Depends(...)` en cualquier router; valida token, carga profesional activo desde DB.
- **API Key auth** (`get_profesional_by_api_key`) para integraciones n8n/webhooks que no manejan OAuth2 password flow.
- **Hashing de contraseñas** con bcrypt + validaciones de seguridad (mínimo 8 caracteres).
- **Nuevas variables de entorno** en `config.py`: `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
- **Tests** unitarios e integración para hashing, JWT encode/decode, flujo register→login→protected endpoint, y rechazo de tokens inválidos/inexistentes.
- **BREAKING**: Ninguno en v1.0 porque no existen endpoints protegidos aún. C-16 aplicará `Depends(get_current_profesional)` a los routers existentes.

## Capabilities

### New Capabilities
- `professional-jwt-auth`: Registro, login y validación de tokens JWT para profesionales.
- `professional-api-key`: Generación y validación de API keys para integraciones externas (n8n).

### Modified Capabilities
- *(Ninguno: este change solo agrega infraestructura de auth sin modificar requisitos de capabilities existentes.)*

## Impact

- **Código**: Nuevos archivos `routers/auth.py`, `services/auth_service.py`, `schemas/auth.py`, `dependencies.py` (extensión con deps de auth).
- **Config**: `config.py` suma settings de JWT.
- **DB**: Asume columnas `email`, `password_hash`, `api_key`, `is_active` en `Profesional` (aplicadas por C-14).
- **Tests**: Nuevos tests en `tests/` para auth.
- **Dependencias**: python-jose, passlib[bcrypt] (agregar a `requirements.txt`).
