# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **Tesis-N8N-turnos**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 foundation-setup
  └── C-02 core-models
        ├── C-03 professional-config
        ├── C-04 patient-management
        └── C-05 google-calendar-service
              └── C-06 turno-reservation
                    ├── C-07 turno-cancel-reschedule
                    │     └── C-13 turno-hardening
                    │           └── C-11 lista-espera
                    └── C-08 telegram-bot-webhook
                          └── C-13 turno-hardening
                                ├── C-09 n8n-workflows
                                ├── C-10 recordatorios
                                └── C-12 professional-telegram-dashboard
```

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes dentro de un grupo pueden ejecutarse en paralelo.

```
GATE 0: ninguna
  → C-01 foundation-setup              [Agente A]

GATE 1: C-01 ✓
  → C-02 core-models                     [Agente A]

GATE 2: C-02 ✓                         ← PRIMER FORK (3 paralelos)
  → C-03 professional-config             [Agente A]
  → C-04 patient-management              [Agente B]
  → C-05 google-calendar-service         [Agente B]

GATE 3: C-03 + C-04 + C-05 ✓
  → C-06 turno-reservation               [Agente A]

GATE 4: C-06 ✓                         ← FORK (2 paralelos)
  → C-07 turno-cancel-reschedule         [Agente A]
  → C-08 telegram-bot-webhook            [Agente C]

GATE 5: C-07 + C-08 ✓                  ← FORK (2 paralelos)
  → C-09 n8n-workflows                   [Agente C]
  → C-13 turno-hardening                 [Agente A]

GATE 6: C-13 ✓                         ← MAYOR FORK (3 paralelos)
  → C-10 recordatorios                   [Agente B]
  → C-11 lista-espera                    [Agente B]
  → C-12 professional-telegram-dashboard [Agente C]
```

### Camino crítico (8 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-06 → C-07 → C-08 → C-13 → C-11
```

> Nota: C-04 y C-05 son prerequisitos paralelos de C-06. El camino crítico asume el orden de finalización más largo entre los tres.

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Backend Core)    │ Agente B (Backend Aux)       │ Agente C (Bot / n8n / Prof)
─────┼────────────────────────────┼──────────────────────────────┼─────────────────────────────
  1  │ C-01 foundation-setup      │ —                            │ —
  2  │ C-02 core-models           │ —                            │ —
  3  │ C-03 professional-config   │ C-04 patient-management      │ —
  4  │ —                          │ C-05 google-calendar-service │ —
  5  │ C-06 turno-reservation     │ —                            │ —
  6  │ C-07 turno-cancel-         │ —                            │ C-08 telegram-bot-webhook
      │    reschedule              │                              │
  7  │ C-13 turno-hardening       │ —                            │ C-09 n8n-workflows
  8  │ —                          │ C-10 recordatorios           │ C-12 professional-telegram-
      │                            │ C-11 lista-espera            │    dashboard
```

---

## FASE 0 — Cimientos

### [C-01] `foundation-setup`
- **Estado**: `[x] completado
- **Scope**: Scaffolding completo del monorepo + infraestructura base
  - Estructura de directorios: `backend/`, `n8n-workflows/`, `docs/`, `knowledge-base/`
  - `backend/`: FastAPI app mínima con health check `/health`, Alembic inicializado, `app/config.py` con Pydantic Settings
  - `backend/app/dependencies.py`: inyección de dependencias (session de DB, settings)
  - `backend/app/scheduler/jobs.py`: esqueleto de APScheduler (sin jobs aún)
  - `docker-compose.yml`: PostgreSQL + backend + (n8n opcional)
  - `.env.example` con todas las variables del KB §Variables de entorno
  - `requirements.txt` con FastAPI, SQLAlchemy, Alembic, APScheduler, python-telegram-bot, google-api-python-client
  - Gitignore, README técnico mínimo
  - Tests: smoke test del health check
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-04, §DD-05

---

## FASE 1 — Dominio Core

> Los changes C-03, C-04 y C-05 pueden proponerse en paralelo tras C-02.

### [C-02] `core-models`
- **Estado**: `[x] completado`
- **Scope**: Modelos SQLAlchemy + migración inicial + seed mínimo
  - Modelos: `Paciente`, `Profesional`, `Turno`, `ReservaTemporal`, `ListaDeEspera`
  - `Turno.estado`: ENUM (`DISPONIBLE`, `RESERVADO_TEMPORAL`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`)
  - Relaciones: Paciente 1:N Turno, Profesional 1:N Turno, Turno 1:1 ReservaTemporal, Paciente 1:N ListaDeEspera
  - Constraints: `CHECK(hora_fin > hora_inicio)`, `UNIQUE(dni)`, índices en `(fecha, hora_inicio)`, `(estado)`, `(paciente_id, estado)`
  - Migración 001: creación de todas las tablas
  - Seed: un registro `Profesional` con horarios y duración por defecto
  - Tests: validación de constraints, integridad referencial, seed idempotente
- **Dependencias**: C-01
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` (completo — ERD y entidades)
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Turnos (RN-TU-01 a RN-TU-03)
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones (Repository, State Machine)

---

### [C-03] `professional-config`
- **Estado**: `[x]` archivado
- **Scope**: Configuración del profesional + cálculo de disponibilidad
  - Endpoints: `GET /profesional/configuracion`, `PUT /profesional/configuracion`
  - Campos editables: `horario_inicio`, `horario_fin`, `dias_atencion`, `duracion_turno`
  - Servicio `availability_service.py`: calcula slots libres dado una fecha
  - Fórmula: horarios posibles (según config) MINUS turnos en estado `CONFIRMADO` o `RESERVADO_TEMPORAL`
  - Tests: cambio de duración recalcula slots, filtrado por día no laborable, solapamiento
- **Dependencias**: C-02
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Profesional
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU-06
  - `knowledge-base/06_funcionalidades.md` §US-010

---

### [C-04] `patient-management`
- **Estado**: `[x] completado`
- **Scope**: Registro e identificación de pacientes
  - Endpoints: `POST /pacientes`, `GET /pacientes/{id}`, `GET /pacientes/{id}/turnos`
  - Validación: DNI único, teléfono requerido, datos mínimos (nombre, apellido, DNI, teléfono)
  - Servicio: auto-identificación por DNI (si ya existe, retorna existente)
  - Tests: CRUD, unicidad de DNI, auto-identificación, historial de turnos
- **Dependencias**: C-02
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Paciente
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PA-01, §RN-PA-02
  - `knowledge-base/06_funcionalidades.md` §US-011

---

### [C-05] `google-calendar-service`
- **Estado**: `[x] completado`
- **Scope**: Cliente de Google Calendar API para sincronización de eventos
  - Servicio `calendar_service.py`: wrapper con retries y backoff exponencial
  - Métodos: `create_event(turno)`, `update_event(turno)`, `delete_event(event_id)`
  - Autenticación: cuenta de servicio OAuth 2.0 vía JSON de credenciales (`GOOGLE_CALENDAR_CREDENTIALS`)
  - Manejo de errores: logging + reintentos configurables (RN-GL-01)
  - Tests: mock de Google Calendar API, reintentos ante 5xx, idempotencia de creación
- **Dependencias**: C-02
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §Integraciones externas
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-02
  - `knowledge-base/05_reglas_de_negocio.md` §RN-GL-01

---

## FASE 2 — Ciclo de Turnos

### [C-06] `turno-reservation`
- **Estado**: `[x] completado
- **Scope**: Reserva temporal, confirmación y creación de evento en calendario
  - Endpoints:
    - `GET /turnos/disponibles?fecha=YYYY-MM-DD` — lista slots libres
    - `POST /turnos` — crea turno en estado `RESERVADO_TEMPORAL` + `ReservaTemporal` con expiración
    - `PUT /turnos/{id}/confirmar` — valida paciente, pasa a `CONFIRMADO`, elimina `ReservaTemporal`, crea evento en Google Calendar
  - Reglas aplicadas: RN-TU-01 (un turno activo por paciente), RN-TU-03 (expiración), RN-TU-06 (disponibilidad), RN-TU-07 (calendar sync)
  - Scheduler APScheduler: job periódico que libera reservas temporales vencidas (`expiracion < NOW()`)
  - Tests: reserva temporal, expiración automática, doble reserva bloqueada, confirmación con calendar mock
- **Dependencias**: C-03, C-04, C-05
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 1: Reserva de turno
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU-01, §RN-TU-03, §RN-TU-06, §RN-TU-07
  - `knowledge-base/06_funcionalidades.md` §US-001, §US-002

---

### [C-07] `turno-cancel-reschedule`
- **Estado**: `[x] completado`
- **Scope**: Cancelación y reprogramación con sincronización de calendario
  - Endpoints:
    - `PUT /turnos/{id}/cancelar` — estado `CANCELADO`, elimina evento de Google Calendar, libera slot
    - `PUT /turnos/{id}/reprogramar` — cancela turno anterior (lógica de C-06 cancelar) + crea nuevo `CONFIRMADO` + nuevo evento calendar
  - Dispara notificación a lista de espera (delega a C-11 cuando exista; por ahora solo libera el slot)
  - Reglas: RN-TU-04, RN-TU-05, RN-TU-08, RN-TU-09
  - Tests: cancelación con calendar delete, reprogramación con calendar update, no-show handling
- **Dependencias**: C-06
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 2, §Flujo 3
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU-04, §RN-TU-05, §RN-TU-08, §RN-TU-09
  - `knowledge-base/06_funcionalidades.md` §US-003, §US-004

---

## FASE 3 — Integraciones Externas

> C-07 y C-08 pueden ejecutarse en paralelo.

### [C-08] `telegram-bot-webhook`
- **Estado**: `[x] completado`
- **Scope**: Webhook de Telegram + enrutador de mensajes + respuestas básicas
  - Endpoint: `POST /webhooks/telegram` — recibe updates del Bot API, valida `X-Telegram-Bot-Api-Secret-Token`
  - Router conversacional: parsea texto y botones inline, enruta a acciones
  - Estado conversacional en memoria (`dict` por `chat_id`) con `asyncio.Lock` por chat
  - Acciones básicas:
    - "Quiero un turno" / `/start` → muestra fechas disponibles con `InlineKeyboardMarkup`
    - Selección de fecha → muestra horarios disponibles
    - Selección de hora → llama `reservar_turno` (reserva temporal)
    - Ingreso de datos paciente → CSV simple: Nombre, Apellido, DNI, Teléfono
    - Confirmación → llama `confirmar_turno` y limpia estado
    - "Cancelar" / "Reprogramar" → resetea estado o placeholder
  - Formato de mensajes: MarkdownV2 con `escape_markdown`, splitting > 4096 chars
  - Bot: `python-telegram-bot` `Bot` + `run_in_threadpool` para no bloquear event loop
  - Tests: webhook validation (7 tests), routing table (10 tests), service integration (9 tests), message formatting (9 tests), E2E flow (5 tests), bot sending (2 tests)
- **Dependencias**: C-06
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §API REST §Webhooks
  - `knowledge-base/07_flujos_principales.md` §Flujo 1 (interacción Telegram)
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-03

---

### [C-09] `n8n-workflows`
- **Estado**: `[x]` completado
- **Scope**: Workflows exportables de n8n para orquestar flujos conversacionales
  - Archivos JSON exportables: `flujo-reserva.json`, `flujo-cancelacion.json`, `flujo-recordatorio.json`, `flujo-lista-espera.json`
  - Cada workflow: Webhook Trigger → HTTP Request a FastAPI → Format Response → Telegram Send Message
  - Documentación de variables de entorno necesarias en n8n (`N8N_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`)
  - Tests manuales: importar en n8n local y verificar que los webhooks de Telegram llegan a FastAPI
- **Dependencias**: C-08
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §Arquitectura general
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-01

---

## FASE 4 — Hardening del Núcleo

> C-13 corrige deudas técnicas del núcleo de turnos antes de construir automatizaciones y panel profesional.

### [C-13] `turno-hardening`
- **Estado**: `[x] completado`
- **Scope**: Completar y corregir el núcleo de turnos que quedó incompleto o roto en changes anteriores
  - Persistir `google_event_id` en modelo `Turno`: nueva columna SQLAlchemy + migración Alembic + integración en confirmación/cancelación/reprogramación
  - Transición a estado `COMPLETADO`: endpoint `PUT /turnos/{id}/completar` + scheduler job `marcar_turnos_completados`
  - Flujo de reprogramación en Telegram: reemplazar placeholder "próximamente" con wizard conversacional completo (fecha → hora → confirmación)
- **Reglas**: RN-TU-02, RN-TU-05, RN-TU-07, RN-TU-08, RN-TU-09
- **Tests**: migración, persistencia de `google_event_id`, transición a `COMPLETADO`, flujo Telegram reprogramación
- **Dependencias**: C-06, C-07, C-08
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Turno
  - `knowledge-base/05_reglas_de_negocio.md` §RN-TU-02, §RN-TU-05, §RN-TU-07 a RN-TU-09
  - `knowledge-base/07_flujos_principales.md` §Flujo 3: Reprogramación

---

## FASE 5 — Automatizaciones

> C-10, C-11 y C-12 pueden proponerse en paralelo tras C-13. C-09 puede ejecutarse en paralelo con C-13.

### [C-10] `recordatorios`
- **Estado**: `[ ]` pendiente
- **Scope**: Recordatorios automáticos 24h antes del turno
  - Scheduler APScheduler: job que corre cada hora (o configurado por `RECORDATORIO_HORAS_ANTES`)
  - Query: turnos `CONFIRMADO` con `fecha/hora` dentro de las próximas 24h y sin `recordatorio_enviado`
  - Servicio `notificacion_service.py`: envía mensaje Telegram con fecha, hora y botones inline (Confirmar, Cancelar, Reprogramar)
  - Al interactuar desde el recordatorio, enruta a los endpoints de C-06/C-07
  - Reglas: RN-RE-01, RN-RE-02
  - Tests: job de scheduler, detección correcta de ventana 24h, envío mock Telegram
- **Dependencias**: C-13
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 4: Recordatorio automático
  - `knowledge-base/05_reglas_de_negocio.md` §RN-RE-01, §RN-RE-02
  - `knowledge-base/06_funcionalidades.md` §US-006

---

### [C-11] `lista-espera`
- **Estado**: `[x] completado`
- **Scope**: Registro, notificación y asignación automática de turnos liberados
  - Endpoints: `POST /lista-espera`, `DELETE /lista-espera/{id}`
  - Hook post-cancelación (desde C-07): al liberar un slot, consulta `ListaDeEspera` ordenada por `creado_en`
  - Servicio: notifica al primer paciente vía Telegram con botones Aceptar / Rechazar
  - Si acepta: confirma turno (reutiliza lógica C-06), elimina de lista, crea evento calendar
  - Si rechaza o timeout: pasa al siguiente paciente (configurable por `LISTA_ESPERA_MINUTOS`)
  - Reglas: RN-LE-01, RN-LE-02
  - Tests: orden FIFO, timeout, condición de carrera (atomicidad en DB), aceptación/rechazo
- **Dependencias**: C-13
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 5: Lista de espera
  - `knowledge-base/05_reglas_de_negocio.md` §RN-LE-01, §RN-LE-02
  - `knowledge-base/06_funcionalidades.md` §US-007, §US-008

---

## FASE 6 — Panel del Profesional

### [C-12] `professional-telegram-dashboard`
- **Estado**: `[ ]` pendiente
- **Scope**: Comandos de Telegram para el profesional + métricas básicas
  - Comandos Telegram:
    - `/turnos_hoy` — lista turnos `CONFIRMADO` del día con hora y paciente
    - `/metricas` — resumen: turnos del día, tasa confirmación, tasa cancelación/inasistencia
    - `/configurar` — wizard para modificar horarios, duración y días de atención
  - Endpoints backend (si no existen aún):
    - `GET /profesional/turnos-hoy`
    - `GET /profesional/metricas`
  - Tests: comandos con mock de datos, métricas calculadas correctamente
- **Dependencias**: C-03, C-13
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-005, §US-009, §US-010
  - `knowledge-base/03_actores_y_roles.md` (matriz de permisos del profesional)
  - `knowledge-base/10_preguntas_abiertas.md` §IN-03 (panel del profesional)

---

## Resumen

| Change | Fase | Estado | Governance | Depende de |
|--------|------|--------|------------|------------|
| C-01 | 0 — Cimientos | `[x]` | BAJO | — |
| C-02 | 1 — Dominio Core | `[x]` | CRITICO | C-01 |
| C-03 | 1 — Dominio Core | `[x]` | MEDIO | C-02 |
| C-04 | 1 — Dominio Core | `[x]` | BAJO | C-02 |
| C-05 | 1 — Dominio Core | `[x]` | ALTO | C-02 |
| C-06 | 2 — Ciclo de Turnos | `[x]` | CRITICO | C-03, C-04, C-05 |
| C-07 | 2 — Ciclo de Turnos | `[x]` | ALTO | C-06 |
| C-08 | 3 — Integraciones | `[x]` | MEDIO | C-06 |
| C-09 | 3 — Integraciones | `[x]` | BAJO | C-08 |
| C-13 | 4 — Hardening | `[x]` | ALTO | C-06, C-07, C-08 |
| C-10 | 5 — Automatizaciones | `[ ]` | MEDIO | C-13 |
| C-11 | 5 — Automatizaciones | `[x]` | ALTO | C-13 |
| C-12 | 6 — Panel Profesional | `[ ]` | BAJO | C-03, C-13 |

**Primer change recomendado**: `C-13` (`turno-hardening`)

Para arrancar: `/opsx:propose C-13-turno-hardening`
