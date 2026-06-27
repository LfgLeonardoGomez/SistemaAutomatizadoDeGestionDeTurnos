## Context

La configuración del backend está fragmentada y contiene inconsistencias detectadas en la auditoría:

- Existen dos `.env.example` (raíz y `backend/`) des-sincronizados: variables como `LISTA_ESPERA_MINUTOS` y `GOOGLE_CALENDAR_MAX_RETRIES` viven solo en uno de ellos.
- `backend/app/config.py` declara `n8n_webhook_url` y `telegram_webhook_secret`, pero ningún módulo del backend las consume. `telegram_webhook_secret` fue reemplazado por tokens por-profesional en C-16.
- `docker-compose.yml` inyecta solo 5 variables al servicio `backend`, omitiendo `SECRET_KEY` (obligatoria), credenciales de Google, intervalos de jobs, y otras opcionales. Esto provoca que el backend arranque con defaults inesperados o falle.
- `backend/app/seed.py` espera `super_admin_password_hash` pre-hasheado. Si el operador pone texto plano, el login falla porque `verify_password` trata el valor como un hash bcrypt.
- Un archivo SQLite binario (`backend/test_migrate.db`) está comiteado en el repositorio.

Este change es puro hardening de infraestructura: corrige la superficie de configuración sin modificar comportamiento de negocio.

## Goals / Non-Goals

**Goals:**
- Unificar la documentación de variables de entorno en un único `.env.example` canónico en la raíz.
- Eliminar variables muertas de `config.py` y de los archivos de ejemplo.
- Completar el bloque `environment` del servicio `backend` en `docker-compose.yml`.
- Cambiar el seed de super-admin para aceptar contraseña en texto plano y hashearla internamente.
- Eliminar el artefacto SQLite comiteado y prevenir futuros commits de `.db`.

**Non-Goals:**
- No agregar, remover ni modificar endpoints de la API.
- No cambiar la lógica de negocio de turnos, recordatorios, lista de espera o calendario.
- No modificar workflows de n8n ni la integración con Telegram más allá de limpiar config muerta.
- No introducir multi-tenancy ni cambios de esquema de base de datos.

## Decisions

1. **Un solo `.env.example` en la raíz**
   - *Rationale*: Una sola fuente de verdad evita la des-sincronización. El backend lee `.env` de su propio directorio en runtime gracias a `SettingsConfigDict`, pero el archivo de ejemplo es documentación pura. Mantenerlo en raíz es la convención estándar para repos monorepo.
   - *Alternative considered*: Mantener ambos sincronizados con un script de CI. Rechazado por sobrecarga innecesaria.

2. **Remover `N8N_WEBHOOK_URL` y `TELEGRAM_WEBHOOK_SECRET` de Settings**
   - *Rationale*: `n8n_webhook_url` nunca fue consumida por código propio. `telegram_webhook_secret` fue desplazada por `profesional.telegram_secret_token` (C-16). Retenerlas genera confusión operativa.
   - *Alternative considered*: Dejarlas con comentarios de deprecación. Rechazado porque no hay consumidor legacy que justifique la compatibilidad.

3. **Cambiar `SUPER_ADMIN_PASSWORD_HASH` → `SUPER_ADMIN_PASSWORD`**
   - *Rationale*: Exigir un hash bcrypt manual al operador es fricción innecesaria y propensa a error (texto plano guardado como "hash"). El seed ya importa `CryptContext`; hashear en el seed es una línea de código y elimina toda la clase de error.
   - *Alternative considered*: Documentar con un comentario grande en `.env.example` que debe ser bcrypt. Rechazado porque la fricción permanece y el error humano sigue siendo probable.

4. **Inyectar todas las variables en `docker-compose.yml`**
   - *Rationale*: Explicitar la configuración en el compose evita el "funciona en mi máquina" cuando el host tiene `.env` pero CI o un compañero no. Se usa `${VAR:-default}` para las opcionales.
   - *Alternative considered*: Documentar que el operador debe montar un `.env` externo. Rechazado porque el compose de desarrollo debe ser auto-contenido.

## Risks / Trade-offs

- **[Breaking]** Entornos existentes que usen `SUPER_ADMIN_PASSWORD_HASH` o `N8N_WEBHOOK_URL` fallarán al arrancar tras el cambio.
  - *Mitigation*: Los operadores deben renombrar la variable en su `.env` local. El change se documenta como breaking en el proposal.
- **[Risk]** El `docker-compose.yml` crece en tamaño.
  - *Mitigation*: Es un trade-off aceptable; la claridad operativa supera la brevedad.
- **[Risk]** Al eliminar `backend/.env.example`, algún script o documentación externa puede referenciarlo.
  - *Mitigation*: El repo es el source of truth; se actualizará `.env.example` raíz y se eliminará el otro en el mismo commit.

## Migration Plan

1. **Pre-merge (local)**:
   - Renombrar `SUPER_ADMIN_PASSWORD_HASH` a `SUPER_ADMIN_PASSWORD` en `.env` local.
   - Eliminar `N8N_WEBHOOK_URL` y `TELEGRAM_WEBHOOK_SECRET` de `.env` local si existen.
2. **Merge**:
   - Se aplican todos los cambios en un único commit (o un work-unit por área si el usuario prefiere).
3. **Post-merge**:
   - Verificar que `docker compose up backend` arranca sin errores de `ValidationError`.
   - Ejecutar `pytest` para confirmar que `Settings()` se instancia correctamente en los tests de config.

## Open Questions

- Ninguna. Todas las decisiones están resueltas en el contexto de la auditoría.
