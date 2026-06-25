# Tesis-N8N-turnos — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

---

## Stack Tecnológico

| Capa | Tecnología | Versión / Notas |
|------|-----------|-----------------|
| Automatización / Orquestación | n8n | Workflow engine visual, nodos para APIs y webhooks |
| Backend | FastAPI (Python) | Framework moderno, async, auto-documentación OpenAPI |
| Base de datos | PostgreSQL | Relacional, robusto, SQLAlchemy 2.0 ORM (async donde sea posible) |
| Scheduler | APScheduler (Python) | Tareas programadas dentro del backend FastAPI |
| Mensajería (UI) | Telegram Bot API | Bot conversacional como interfaz principal del usuario |
| Calendario | Google Calendar API | Agenda espejo sincronizada, evita desarrollo propio |
| Infraestructura | Docker | Contenerización recomendada para despliegue |

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, ERD, migraciones |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-XX) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura, env vars |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Inconsistencias a resolver ANTES de codear |

> ⚠️ Resolver las preguntas de prioridad **Alta** de `10_preguntas_abiertas.md` antes de arrancar el primer change.
> En particular: **IN-01** (tiempo de expiración de reserva temporal) e **IN-03** (panel del profesional vía Telegram vs web).

---

## Skills Disponibles

<!-- Fuente de verdad: .atl/skill-registry.md (generado por skill-registry). -->

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | FastAPI / SQLAlchemy / PostgreSQL / Alembic / modelos | `fastapi`, `supabase-postgres-best-practices`, `saas-multi-tenant` |
| **Backend Aux** | Integraciones, scheduler, calendario, seguridad, DevOps | `google-calendar`, `devops-engineer` |
| **Bot & n8n** | Telegram, workflows, automatización | `telegram-bot`, `n8n-cli` |
| **Orquestación** | OPSX / SDD / docs / foundation | `openspec-init`, `openspec-propose`, `openspec-apply-change`, `openspec-archive-change`, `openspec-explore`, `openspec-sync-specs`, `herald`, `chronicle`, `roadmap-generator`, `agents-md-generator`, `sdd-orchestrator` |

Cargá la skill correspondiente al contexto **ANTES** de escribir código.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 12 changes en 6 fases.
- **Camino crítico** (7): `C-01 → C-02 → C-03 → C-06 → C-07 → C-08 → C-11`.
- **Primer change**: `C-01` (`foundation-setup`).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras

> Reglas **globales** ya definidas en `~/.config/opencode/AGENTS.md` (personality, lenguaje, tone, behavior, no co-autoría IA, no buildear sin pedido, conventional commits): el proyecto las **hereda**, no se repiten acá.

Acá van las reglas **específicas de este proyecto**, derivadas de su stack (FastAPI + PostgreSQL + n8n + Telegram + Google Calendar + APScheduler) y confirmadas como defaults del foundation flow. Son contrato; romperlas es un defecto. Formato `NUNCA X → hacer Y`:

- **NUNCA** usar `async def` para código bloqueante o sincrónico (librerías sync como Google Calendar SDK) → usar `def` y dejar que FastAPI ejecute en threadpool, o envolver explícitamente con `run_in_threadpool`.
- **NUNCA** dejar un endpoint FastAPI sin tipo de retorno o `response_model` → declarar siempre para filtrar/serializar con Pydantic v2.
- **NUNCA** omitir type hints en funciones públicas del backend → tipado estricto; `Any` solo con justificación documentada.
- **NUNCA** hacer commit de código de negocio sin test que lo respalde → pytest obligatorio; modo TDD estricto (test rojo → verde → refactor).
- **NUNCA** hardcodear configuración (URLs, tokens, tiempos de expiración) → usar Pydantic Settings con variables de entorno (ej. `RESERVA_TEMPORAL_MINUTOS`, `GOOGLE_CALENDAR_CREDENTIALS`).
- **NUNCA** mezclar operaciones HTTP en una misma función → una función por operación (GET, POST, PUT, DELETE).
- **NUNCA** ignorar concurrencia en reservas de turnos → usar transacciones de base de datos (`SELECT FOR UPDATE` o patterns de SQLAlchemy) para evitar race conditions en slots.
- **NUNCA** guardar secrets en código commiteado → usar secret managers o `.env` local (`.env` en `.gitignore`); credenciales de Google Calendar vía JSON externo.
- **NUNCA** asumir que n8n está disponible sin fallback → los endpoints REST del backend deben ser funcionales y testeables de forma aislada; n8n es orquestador, no requisito de ejecución.
- **NUNCA** ignorar límites de Telegram → respetar 4096 caracteres por mensaje, usar markdown válido, implementar splitting si es necesario.
- **NUNCA** bloquear el event loop con APScheduler → usar `AsyncIOScheduler` para jobs async, o delegar trabajo pesado a threads con logging de errores.
- **NUNCA** dejar un modelo SQLAlchemy sin `tenant_id` si la entidad es tenant-scoped → aplicar patterns de `saas-multi-tenant` desde v1 (RLS, índices compuestos con `tenant_id` primero).
- **NUNCA** usar `panic`, `exit` o excepciones no controladas en flujos de negocio → manejar errores con excepciones custom, logging estructurado y respuestas HTTP gracefull.
- **NUNCA** priorizar pureza arquitectónica sobre entregar valor → Clean/Hexagonal es preferido pero pragmático para v1; evitar over-engineering. Conceptos > código, pero sin framework obsession.

---

## Model Assignments para OPSX

> Reglas duras sobre qué modelo ejecuta cada fase del ciclo de vida de un change. El orquestador DEBE respetar esto al delegar.

| Fase OPSX | Modelo obligatorio | Razón |
|-----------|-------------------|-------|
| **Propose** | `kimi` | El mismo modelo que generó la KB y el roadmap; mantiene coherencia conceptual y de estilo. |
| **Apply** | `deepdeek-v4-flash` | Optimizado para implementación, refactoring y generación de código en bloque. |
| **Archive** | `deepdeek-v4-flash` | Operaciones mecánicas de sincronización de specs y cierre de change. |
| **Explore** | `kimi` | Pensamiento arquitectónico y análisis de dominio; mejor con el modelo original. |

**Regla adicional**: si el modelo asignado no está disponible en el entorno, el orquestador DEBE abortar la delegación y notificar al usuario en lugar de hacer fallback silencioso a otro modelo.

---

## Flujo de Trabajo

```
0. Idea / integración nueva → herald               → seed (fact vs proposal)
1. Leer la KB relevante (knowledge-base/)           → entender el dominio
2. Identificar el change en CHANGES.md              → respetar dependencias
3. /sdd-new  o  /opsx:propose C-NN-nombre           → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)          → respetando las reglas duras
5. /sdd-verify-seb  +  /sdd-archive-seb             → validar y cerrar el change
6. chronicle (update KB)                             → mantener la KB al día
```

**Paso 0 — herald**: para ideas no especificadas, features nuevas o integraciones entre sistemas. herald groundea en código real (read-only), separa hecho de propuesta, y entrega un seed listo para SDD. No avanza sin aprobación humana.

**Paso 6 — chronicle**: tras implementar y archivar, actualizá la KB con chronicle (modo update) para que la documentación refleje el cambio real. Los modos reverse y audit sirven para documentar código existente o verificar consistencia.

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
