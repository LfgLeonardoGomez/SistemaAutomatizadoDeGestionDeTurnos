# Knowledge Base Changelog

Registro de cambios entre regeneraciones / updates de la KB. Cada entrada lleva el motivo, los archivos tocados y el origen del cambio (change de OpenSpec, decisión de usuario, etc.).

## 2026-07-02 — Chronicle update post C-23 + C-24

- **Origen**: archive de los changes `c-23-turno-destinatario-multicanal` y `c-24-n8n-workflows-orquestador-telegram` (ambos archivados el 2026-07-02).
- **Modo**: Update no-destructivo (merge incremental sobre la KB existente). No se regenera desde cero.

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | **(C-23)** Agregada entidad `turno_destinatario` con ENUM `canal_notificacion_enum` y `UNIQUE(turno_id, canal)`. **Eliminada** columna `telegram_chat_id` de `paciente` (código muerto). **Eliminada** mención de `telefono` "vinculado a Telegram" como destino único. **Agregada** columna `profesional_id` en `paciente` y constraint `UNIQUE(profesional_id, dni)`. **Actualizado** ERD con la nueva tabla. **Agregados** campos `telegram_bot_token`, `api_key`, `is_active` en `profesional`. |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | **(C-23)** Agregadas `RN-RE-03` (destinatario por turno) y `RN-RE-04` (recordatorio lee del turno, no del paciente). **(C-24)** Agregadas `RN-RE-05` (turno sin destinatario se omite) y `RN-RE-06` (dos motores de recordatorio). |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | **(C-24)** Reescrita sección "Integración n8n" con topología de orquestador + 3 sub-workflows. **Agregada** sección "Dos motores de recordatorio (n8n + APScheduler)" con `POST /api/v1/recordatorios/run`. **Actualizado** árbol de directorios con `orquestador.json`, `sub-flujo-*.json`, `turno_destinatario.py`, `destinatario_service.py`, `recordatorio_service.py`, `routers/recordatorios.py`, `schemas/recordatorio.py`. **Actualizada** tabla de patrones con `Orquestador (Router)` y `Upsert por clave natural`. **Actualizada** sección de Seguridad con multi-tenant `X-API-Key` y secretos n8n. |
| [03_actores_y_roles.md](03_actores_y_roles.md) | **(C-23/C-24)** Agregado actor "n8n (orquestador)" como entry point principal del bot. **Actualizada** matriz RBAC con permisos de n8n y profesional sobre `TurnoDestinatario`. **Aclarado** que el paciente se identifica, no se autentica. |
| [02_descripcion_general.md](02_descripcion_general.md) | **(C-24)** Actualizado diagrama de arquitectura con orquestador n8n como single entry point. **Agregada** fila "n8n (orquestador)" en integraciones externas. **Agregado** endpoint `POST /api/v1/recordatorios/run` en API REST. |
| [07_flujos_principales.md](07_flujos_principales.md) | **(C-24)** Flujo 1 (Reserva) reescrito con el camino `orquestador → sub-flujo-crear-turno → backend con X-API-Key → upsert TurnoDestinatario → Google Calendar → Telegram`. Flujo 4 (Recordatorio) reescrito con los dos motores (n8n primario + APScheduler fallback) y el endpoint `POST /api/v1/recordatorios/run`. |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | **Agregada** `DD-09` (destinatario por turno, C-23). **Agregada** `DD-10` (orquestador n8n single entry point, C-24). **Agregada** `DD-11` (dos motores de recordatorio, C-24). |
| [06_funcionalidades.md](06_funcionalidades.md) | **Actualizada** US-001 con criterios de aceptación de C-23 (destinatario por turno, DNI scoped) y C-24 (orquestador). **Actualizada** US-006 con los dos motores de recordatorio y la omisión con warning (RN-RE-05). |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | **Actualizada** pregunta multi-tenancy: ya implementada por profesional, pendiente por instancia. **Agregadas** 2 preguntas: endpoint `/lista-espera/siguiente` (deuda C-11) y sender de `EMAIL` (modelo listo, integración fuera de alcance). |

### Decisiones de gobernanza

- **Decisiones DD-09, DD-10, DD-11** se citan como `[user]` (origen: el usuario aprobó las Decisiones 1, 2, 4, 5, 8 del design.md de C-23/C-24 en sus respectivas Fases 0).
- **Eliminación de la columna `paciente.telegram_chat_id`** se documenta como `BREAKING` de esquema (Decisión 2 de C-23, aprobada por el usuario antes de aplicar el change).
- **Multi-tenancy por profesional** (C-14..C-22) y **multi-tenancy por instancia** (`tenant_id` global + RLS) son dos cambios distintos: el primero ya está en producción; el segundo queda en `NEXT_SESSION.md` para v2.0.

### Inconsistencias detectadas durante el update (cerradas)

- **Pre-C-23**: la KB decía que el recordatorio leía `paciente.telegram_chat_id` → en realidad esa columna nunca se escribía (era código muerto). **Corregido**: el recordatorio lee del `turno_destinatario` (RN-RE-04).
- **Pre-C-24**: la KB describía 4 workflows n8n (`flujo-reserva`, `flujo-cancelacion`, `flujo-recordatorio`, `flujo-lista-espera`) sin `X-API-Key`. **Corregido**: la topología real es `orquestador.json` + 3 sub-workflows + 2 independientes; los flujos viejos se eliminaron (los re-crea git si se necesita rollback).
- **Pre-C-24**: la KB no mencionaba que el paciente **no se autentica** (se identifica). **Aclarado** en `03_actores_y_roles.md` y `02_descripcion_general.md`.

### Próximos updates a considerar

- Cuando se implemente el sender de `EMAIL` → actualizar `notificacion_service.enviar_recordatorio_email` y RN-RE-*.
- Cuando se implemente `GET /lista-espera/siguiente` (deuda C-11) → actualizar flujo de lista de espera y eliminar pregunta de `10_preguntas_abiertas.md`.
- Cuando se decida v2.0 multi-tenant por instancia (`tenant_id` + RLS) → revisar todos los modelos de `04_modelo_de_datos.md` y RN-PA-* / RN-TU-*.
