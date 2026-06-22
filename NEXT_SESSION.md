# Contexto para Próxima Sesión — Migración Multi-Tenant

> **Fecha**: 2026-06-22
> **Sesión anterior**: Implementación C-12 + Auditoría KB vs Código
> **Decisión clave**: Pivotear de single-tenant por instancia a **multi-tenant por profesional en una sola instancia**.

---

## Estado Actual del Proyecto (al cierre de sesión)

- **v1.0 COMPLETA**: Todos los changes C-01 a C-13 implementados, testeados (318 tests passing) y archivados.
- **Arquitectura actual**: Single-tenant por instancia. Cada profesional corre su propio backend + PostgreSQL + bot de Telegram.
- **Documentación**: KB auditada y sincronizada con el código. AGENTS.md actualizado.

---

## Decisión de Arquitectura: Multi-Tenant por Profesional

### ¿Por qué el cambio?

El modelo de negocio es vender el SaaS a **muchos profesionales independientes** (B2C profesional), no a clínicas. En este escenario, una sola instancia multi-tenant es superior:

| Ventaja | Descripción |
|---------|-------------|
| **Costo marginal ≈ 0** | Un profesional más no cuesta infra extra significativa. |
| **Onboarding instantáneo** | "Registrate y empezá" vs. "esperá que te deploye una instancia". |
| **Deploy único** | Update de código una vez, todos los profesionales lo reciben. |
| **Trial gratuito viable** | Podés ofrecer 14 días gratis sin costo de infra por usuario. |

### ¿Qué significa "multi-tenant por profesional"?

- Cada **Profesional** es un tenant.
- Todos los profesionales comparten el **mismo backend** y la **misma base de datos PostgreSQL**.
- Los datos de cada profesional están **aislados** mediante `profesional_id` (FK) en todas las entidades tenant-scoped.
- Cada profesional tiene **su propio bot de Telegram** (distinto `TELEGRAM_BOT_TOKEN`).
- Cada profesional tiene **su propio calendario de Google** (distintas credenciales `GOOGLE_CALENDAR_CREDENTIALS`).

---

## Trabajo Pendiente — Migración a Multi-Tenant

### Fase 1: Diseño y Planificación (antes de tocar código)

1. **Revisar modelo de datos**
   - Agregar `profesional_id` como FK en: `Turno`, `Paciente`, `ReservaTemporal`, `ListaDeEspera`, `Configuracion`.
   - `Profesional` ya existe; hay que agregarle campos de auth (email, password_hash, api_key).
   - Considerar índices compuestos: `(profesional_id, fecha)`, `(profesional_id, estado)`, etc.

2. **Definir estrategia de aislamiento**
   - **Opción A**: Scoping en application layer (cada query filtra por `profesional_id`).
   - **Opción B**: Row-Level Security (RLS) de PostgreSQL + scoping en app layer como defensa en profundidad.
   - **Recomendación**: Opción A para v2.0 (más simple), Opción B para v3.0 (más seguro).

3. **Autenticación y autorización**
   - Auth básica para profesionales: email + password (bcrypt), JWT token.
   - Middleware que extrae `profesional_id` del token y lo inyecta en el request state.
   - Endpoints de registro y login para profesionales.
   - Opcional: API key para integraciones (n8n).

4. **Telegram: múltiples bots**
   - Un solo webhook `/webhooks/telegram` que recibe updates de múltiples bots.
   - Routing: el webhook debe identificar qué bot recibió el update (`bot_token` o `bot_username`) y rutear al `Profesional` correspondiente.
   - Tabla nueva: `ProfesionalBotConfig` (`profesional_id`, `telegram_bot_token`, `webhook_url`, `webhook_secret`).
   - El `telegram_service.py` actual asume un solo bot global. Hay que refactorizar para que reciba `bot_token` y `profesional_id` en cada llamada.

5. **Google Calendar: múltiples cuentas**
   - Cada `Profesional` tiene sus propias credenciales OAuth2.
   - Tabla nueva: `ProfesionalCalendarConfig` (`profesional_id`, `credentials_json`, `calendar_id`).
   - El `calendar_service.py` actual lee credenciales de env var. Hay que refactorizar para recibir `credentials` por parámetro.

6. **Super-admin**
   - Rol nuevo: `SUPER_ADMIN` (no es un profesional, es el operador del SaaS).
   - Panel mínimo para: listar profesionales, activar/desactivar, ver métricas globales.
   - Opcional para v2.0: puede ser un CLI o un endpoint protegido por env var (`SUPER_ADMIN_API_KEY`).

### Fase 2: Implementación (orden sugerido)

1. **C-14: Multi-tenant Core**
   - Migración Alembic: agregar `profesional_id` a todas las tablas.
   - Auth: registro/login de profesionales, JWT middleware.
   - Refactorizar todos los services y routers para scopar por `profesional_id`.
   - Tests: verificar que un profesional A no ve datos del profesional B.

2. **C-15: Multi-bot Telegram**
   - Refactorizar webhook para soportar múltiples bots.
   - Migración: tabla `ProfesionalBotConfig`.
   - Tests: dos bots simulados, verificar aislamiento de conversaciones.

3. **C-16: Multi-calendar Google**
   - Refactorizar `calendar_service.py`.
   - Migración: tabla `ProfesionalCalendarConfig`.
   - Tests: mock de múltiples cuentas de Google Calendar.

4. **C-17: Super-admin y onboarding**
   - Endpoint de registro de profesionales (self-service o por invitación).
   - Panel super-admin mínimo.
   - Tests: flujo de registro completo.

### Fase 3: Data Migration (si hay datos existentes)

- Si ya hay datos en producción (v1.0 single-tenant), necesitamos un script de migración:
  - Crear un `Profesional` "default".
  - Asignar `profesional_id = 1` a todos los registros existentes.
  - Migrar `TELEGRAM_BOT_TOKEN` y `GOOGLE_CALENDAR_CREDENTIALS` de env vars a tablas de config.

---

## Riesgos Identificados

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| **Bug de scoping** (profesional A ve datos de B) | **CRÍTICO** | Tests exhaustivos de aislamiento. Audit middleware. |
| **Refactor grande de Telegram** | Alto | Hacerlo en change aparte (C-15). Mantener compatibilidad temporal. |
| **Complejidad de múltiples bots** | Alto | Diseñar bien el routing del webhook antes de codear. |
| **Performance con muchos profesionales** | Medio | Índices compuestos con `profesional_id` primero. Monitorear queries. |
| **Auth: password reset, etc.** | Medio | Empezar con auth básica, iterar. No over-engineerar. |

---

## Archivos Clave a Revisar en Próxima Sesión

- `backend/app/models/*.py` — para agregar `profesional_id`.
- `backend/app/routers/profesional.py` — auth y scoping.
- `backend/app/services/telegram_service.py` — refactor multi-bot.
- `backend/app/services/calendar_service.py` — refactor multi-calendar.
- `backend/app/dependencies.py` — inyección de `profesional_id` en requests.
- `knowledge-base/04_modelo_de_datos.md` — actualizar ERD.
- `AGENTS.md` — actualizar reglas duras (multi-tenant desde v2.0).

---

## Notas para el Orquestador

- **Modelo para propose**: `kimi` (decisiones arquitectónicas).
- **Modelo para apply**: `deepdeek-v4-flash` (implementación en bloque).
- **Skills a cargar**: `fastapi`, `supabase-postgres-best-practices`, `saas-multi-tenant` (FINALMENTE la vamos a usar 😄).
- **Strict TDD**: test rojo → verde → refactor, SIEMPRE.

---

> **Contexto completo de esta sesión**: Implementación de C-12 (professional-telegram-dashboard), auditoría KB vs código (318 tests verdes), decisión de pivotear a multi-tenant.
