## Why

La auditoría de configuración del proyecto detectó cinco issues concretos (E-1, E-2, E-3, L-5, H-2) que generan fricción en el setup, riesgo de despliegue incorrecto y confusión operativa. La configuración está fragmentada entre dos `.env.example`, contiene variables muertas, el `docker-compose.yml` no inyecta variables críticas, existe un binario SQLite comiteado por error, y el seed del super-admin exige un hash bcrypt manual sin documentar. Este change de hardening unifica y corrige la infraestructura de configuración para que el proyecto arranque de forma coherente y segura en cualquier entorno.

## What Changes

- **E-1 — Eliminar `N8N_WEBHOOK_URL` y `TELEGRAM_WEBHOOK_SECRET` muertas** de `backend/app/config.py` y de ambos `.env.example`. Estas variables se leen en Settings pero ningún módulo las consume. **BREAKING**: si algún workflow n8n o script externo dependía de la presencia de la key en el entorno, dejará de existir.
- **E-2 — Unificar `.env.example`** en un solo archivo en la raíz del repo, eliminando `backend/.env.example`. Se sincronizan todas las variables declaradas en `config.py` con comentarios y defaults. **BREAKING**: los documentos o scripts que referencien `backend/.env.example` dejarán de funcionar.
- **E-3 — Completar `docker-compose.yml`** inyectando todas las variables de entorno necesarias para que el servicio `backend` arranque sin depender de un `.env` montado implícitamente. Se incluyen `SECRET_KEY`, `SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `LISTA_ESPERA_MINUTOS`, `COMPLETADO_JOB_INTERVAL_MINUTOS`, `RECORDATORIO_JOB_INTERVAL_MINUTOS`, y las vars de retry de Google Calendar.
- **H-2 — Cambiar `super_admin_password_hash` → `super_admin_password`** (texto plano) en `config.py` y `.env.example`, y hashear bcrypt dentro de `seed_super_admin()` en `backend/app/seed.py`. Reduce fricción y evita que un admin ponga texto plano creyendo que es un hash. **BREAKING**: cualquier entorno existente que tuviera `SUPER_ADMIN_PASSWORD_HASH` deberá migrar a `SUPER_ADMIN_PASSWORD`.
- **L-5 — Eliminar `backend/test_migrate.db`** y agregar `*.db` a `.gitignore`.

## Capabilities

### New Capabilities
- *(Ninguno — este change no agrega funcionalidad de negocio)*

### Modified Capabilities
- `configuration-management`: Se amplían los requisitos de limpieza de configuración. Se agregan variables muertas a remover (`N8N_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`), se documenta la unificación de `.env.example`, se agrega validación de que `docker-compose.yml` inyecte todas las variables críticas.
- `super-admin-auth`: Se modifica el requisito de bootstrap del super-admin para usar `SUPER_ADMIN_PASSWORD` (texto plano) en lugar de `SUPER_ADMIN_PASSWORD_HASH`, con hashing bcrypt realizado en el seed.

## Impact

- **Archivos modificados**: `.env.example` (raíz), `backend/app/config.py`, `docker-compose.yml`, `backend/app/seed.py`, `.gitignore`.
- **Archivos eliminados**: `backend/.env.example`, `backend/test_migrate.db`.
- **Sistemas afectados**: Setup local, despliegue con Docker, CI/CD si monta `.env.example` de forma diferenciada, y el seed de base de datos en nuevas instancias.
- **Dependencias**: Ninguna nueva. Requiere que exista la función `verify_password` / `get_password_hash` en el backend (ya presente desde el change de auth).
