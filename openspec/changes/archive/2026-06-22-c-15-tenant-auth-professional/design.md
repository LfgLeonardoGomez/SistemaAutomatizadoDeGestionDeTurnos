## Context

v1.0 del backend (FastAPI + SQLAlchemy 2.0 async + PostgreSQL) opera sin autenticación: no existe JWT, password hashing ni un mecanismo para identificar al profesional que realiza un request. C-14 (prerequisito) agrega las columnas `email`, `password_hash`, `api_key`, `is_active` al modelo `Profesional`. Este change construye la capa de autenticación y autorización sobre esas columnas, desbloqueando C-16 donde todos los endpoints existentes se scoperarán por `profesional_id`.

Stack actual:
- FastAPI con `Depends()` para inyección de dependencias.
- SQLAlchemy 2.0 async (`AsyncSession`).
- Pydantic v2 para validación y serialización.
- pytest para testing.
- Sin OAuth2 ni JWT previos.

## Goals / Non-Goals

**Goals:**
1. Proveer endpoints `POST /auth/register` y `POST /auth/login` que emitan JWT access tokens.
2. Proveer dependencia reusable `get_current_profesional` que valide JWT, cargue el profesional desde DB y rechace tokens inválidos/inactivos.
3. Proveer mecanismo de API Key para integraciones n8n/webhooks (`get_profesional_by_api_key`).
4. Hashear contraseñas con bcrypt y nunca exponer `password_hash`.
5. Cubrir con tests unitarios + integración el flujo completo de auth.

**Non-Goals:**
- No proteger los endpoints existentes en este change (eso es C-16).
- No implementar refresh tokens ni logout server-side (v2.0 pragmático; JWT corto + regeneración es suficiente).
- No implementar roles ni RBAC granular (solo autenticación de profesional).
- No enviar emails de verificación (el profesional se registra directamente).

## Decisions

### 1. JWT con `python-jose` + `cryptography` (HS256)
**Elección**: Usar `python-jose[cryptography]` con algoritmo HS256 y secreto único (`SECRET_KEY`).
**Razón**: HS256 es stateless, simple y suficiente para un backend monolítico. No requiere infraestructura de claves públicas/privadas. `python-jose` es estándar en FastAPI.
**Alternativa descartada**: RS256 con par de claves — overkill para v2.0; agrega complejidad de rotación de claves sin beneficio tangible.

### 2. `passlib[bcrypt]` para hashing de passwords
**Elección**: `passlib[bcrypt]` con `CryptContext(schemes=["bcrypt"], deprecated="auto")`.
**Razón**: `passlib` es el estándar de facto en Python, abstrae el algoritmo y facilita migraciones futuras. `bcrypt` es robusto y soportado por defecto.
**Alternativa descartada**: `argon2` — mejor en teoría pero requiere dependencias nativas extras; `bcrypt` es suficiente.

### 3. Service layer dedicado (`services/auth_service.py`)
**Elección**: Extraer toda la lógica de negocio de auth en `auth_service.py` (registro, login, generación de JWT, generación de API key).
**Razón**: Mantiene los routers delgados (solo HTTP parsing + `response_model`), facilita testing unitario sin levantar el ASGI app, y permite reuso si n8n u otro cliente necesitan llamar a la lógica directamente.
**Alternativa descartada**: Lógica inline en router — más simple a corto plazo pero imposible de testear unitariamente y viola separación de responsabilidades.

### 4. API Key: almacenamiento plaintext (con justificación)
**Elección**: Almacenar la API key en plaintext en `Profesional.api_key` (columna UNIQUE, nullable).
**Razón**: Las API keys son credenciales de máquina-a-máquina. Hashearlas implicaría no poder mostrarla al profesional después de generarla (forzando regeneración en cada consulta). Como el acceso a la DB es controlado y la key se transmite solo por HTTPS, el riesgo es aceptable. Se permite regeneración (POST /auth/api-key sobrescribe la anterior).
**Mitigación**: La columna `api_key` nunca se incluye en ningún `response_model` de lectura; solo se retorna una vez en el response de generación.

### 5. Dependencias de auth en `dependencies.py`
**Elección**: Extender `app/dependencies.py` con `get_current_profesional` y `get_profesional_by_api_key`.
**Razón**: `dependencies.py` ya centraliza `get_db` y `get_settings`; es el lugar natural para dependencias de FastAPI reutilizables. Mantiene consistencia con el codebase existente.

### 6. Config de JWT en `Settings` (Pydantic)
**Elección**: Agregar `secret_key`, `algorithm` (default "HS256"), `access_token_expire_minutes` (default 1440) a `app/config.py`.
**Razón**: Cumple la regla dura "NUNCA hardcodear config". `secret_key` se carga desde env var; en desarrollo puede usarse un valor dummy pero en producción DEBE ser generado con `secrets.token_hex(32)`.

### 7. Token payload mínimo
**Elección**: Payload con claims `sub` (profesional_id como string), `email`, `exp` (timestamp), `iat` (timestamp).
**Razón**: `sub` es el estándar OIDC para identidad. `email` facilita debugging/logging sin query adicional. `exp` e `iat` son requeridos por `python-jose`. No incluir datos mutables (nombre, horarios) para evitar desincronización.

### 8. Router `/auth` con prefix y tags
**Elección**: `APIRouter(prefix="/auth", tags=["auth"])` registrado en `main.py`.
**Razón**: Consistente con el resto de routers (`/profesional`, `/turnos`, etc.).

## Risks / Trade-offs

| Risk | Mitigación |
|------|-----------|
| [Riesgo] `SECRET_KEY` débil o comprometido → cualquiera puede forjar tokens. | Documentar en `.env.example` que debe ser generado con `secrets.token_hex(32)`; nunca commitear a repo. |
| [Riesgo] API key en plaintext en DB → leak de backup de DB expone integraciones. | Restringir acceso a backups; rotar keys periódicamente; en v2.1 evaluar hashear con hash fixo (HMAC) y comparar. |
| [Riesgo] Token JWT largo (24h) sin refresh → si se roba, válido por un día. | Aceptable para v2.0 (profesional independiente, no datos sensibles de salud). En v2.1 evaluar refresh tokens o shorter expiry. |
| [Riesgo] Race condition en registro con email duplicado (validación Python + INSERT no atómica). | Usar `UNIQUE` constraint en DB (C-14) + manejar `IntegrityError` en servicio retornando 409. |
| [Riesgo] Test fixtures de C-14 no incluyen email/password_hash → tests de C-15 fallan. | Documentar en tasks.md que C-14 debe extender el fixture `profesional` con esos campos. |

## Migration Plan

1. Asegurar que C-14 esté aplicado (columnas de auth en `Profesional` + migración Alembic + fixture actualizado).
2. Instalar dependencias: `pip install python-jose[cryptography] passlib[bcrypt]` y agregar a `requirements.txt`.
3. Implementar auth (este change).
4. Seed de v1.0 crea un profesional sin `email` ni `password_hash`; al aplicar C-14 se debe migrar el seed o dejar el profesional legacy inactivo. **Decisión**: el seed de C-14 debe pedir email/password o dejar `is_active=False` hasta que el profesional se registre.

## Open Questions

1. ¿El seed inicial debería crear un profesional pre-registrado con email/password por defecto, o forzar al usuario a registrarse vía `/auth/register`? → **Recomendación**: forzar registro para evitar credenciales por defecto; ajustar seed en C-14 para no crear profesional sin credenciales.
2. ¿Se necesita rate limiting en `/auth/login`? → Fuera de scope de C-15; se puede agregar con middleware externo (nginx/cloudflare) o en C-17 hardening.
