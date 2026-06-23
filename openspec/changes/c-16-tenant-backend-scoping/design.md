## Context

Tras C-14 (tenant-data-model) y C-15 (tenant-auth-professional), el schema de PostgreSQL ya tiene `profesional_id` en `Paciente`, `ListaDeEspera` y `Turno`, y el modelo `Profesional` cuenta con campos de autenticación (`email`, `password_hash`, `api_key`). Los routers de auth (`/auth/register`, `/auth/login`, `/auth/api-key`) y las dependencias `get_current_profesional` / `get_profesional_by_api_key` están implementados.

Sin embargo, **ningún endpoint de negocio exige autenticación**, y los servicios siguen usando `_get_profesional_default()` — una función que hace `select(Profesional).first()` y asume un único profesional global. Esto representa una brecha de seguridad crítica: cualquier request puede acceder o modificar datos de cualquier profesional.

Este change es el más grande de la migración v2.0 porque toca **cada capa** del backend: servicios, routers, scheduler, integraciones externas (Google Calendar, Telegram) y la suite completa de tests.

## Goals / Non-Goals

**Goals:**
1. Hacer que **toda operación de lectura y escritura** en el backend esté scopeada por `profesional_id`.
2. Eliminar completamente `_get_profesional_default()` y todas las asunciones de single-professional.
3. Proteger todos los routers REST con autenticación (`JWT` o `API Key`) y filtrar resultados por el profesional autenticado.
4. Hacer que Google Calendar y Telegram operen **por profesional**, usando tokens individuales.
5. Actualizar todos los tests existentes para funcionar en el nuevo modelo autenticado.
6. Agregar tests de aislamiento que verifiquen que un profesional no puede ver ni modificar datos de otro.

**Non-Goals:**
- No se implementa multi-tenancy a nivel de base de datos (row-level security de PostgreSQL). El scoping se hace en la capa de aplicación.
- No se modifica el schema de la base de datos (ya fue hecho en C-14).
- No se agrega autorización basada en roles (RBAC); todos los profesionales tienen el mismo nivel de permisos.
- No se rediseña la arquitectura de n8n workflows en este change (se asume que n8n usará la API Key del profesional).
- No se implementa frontend web para gestión profesional (la UI sigue siendo Telegram).

## Decisions

### DEC-01: Service layer scoping via parámetro explícito

**Decision**: Cada método público de servicio recibirá `profesional_id: int` como parámetro posicional obligatorio (o al menos no-optional) y filtrará todas las queries SQL por ese valor.

**Rationale**: 
- **Parameter passing** es explícito, trazable y testeable. Cualquier llamada sin `profesional_id` fallará en tiempo de chequeo de tipos.
- **Context variable** (ej. `contextvars`) fue descartado porque es implícito, difícil de rastrear en tests async, y puede causar fugas entre tareas concurrentes en el mismo event loop.

**Pattern**:
```python
async def listar_turnos(
    db: AsyncSession,
    profesional_id: int,
    # ... otros params
) -> list[Turno]:
    result = await db.execute(
        select(Turno).where(Turno.profesional_id == profesional_id)
    )
    return result.scalars().all()
```

### DEC-02: Router protection con dos dependencias

**Decision**: Se usan dos dependencias de FastAPI según el router:
- `CurrentProfesionalDep` (`get_current_profesional`) para todos los routers REST de negocio (`/turnos`, `/pacientes`, `/profesional`, `/lista-espera`). Extrae JWT del header `Authorization: Bearer <token>`.
- `get_profesional_by_api_key` para el webhook de Telegram (`/webhooks/telegram`), validando el header `X-API-Key`.

**Rationale**: Los webhooks de Telegram vienen de la infraestructura del bot y no portan JWT; portan `X-Telegram-Bot-Api-Secret-Token` para validación de origen, y para operaciones del backend necesitamos identificar al profesional. n8n usará `X-API-Key`.

**Exception**: El router `/auth/*` no requiere autenticación (es donde se obtienen las credenciales).

### DEC-03: Telegram webhook routing por `telegram_secret_token`

**Decision**: El webhook `/webhooks/telegram` recibe `X-Telegram-Bot-Api-Secret-Token`, busca el `Profesional` cuyo `telegram_secret_token` coincida, y pasa ese `profesional` al servicio de Telegram.

**Rationale**: 
- Cada profesional tiene su propio bot de Telegram (token propio en `telegram_bot_token`).
- El `secret_token` es la forma que Telegram ofrece para validar que el webhook viene realmente de Telegram.
- Si no hay `secret_token` configurado para el profesional, se rechaza el webhook.

**Pattern**:
```python
@router.post("/telegram")
async def recibir_webhook_telegram(
    request: Request,
    secret_token: Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None,
):
    if not secret_token:
        raise HTTPException(403, ...)
    profesional = await lookup_profesional_by_telegram_secret(secret_token)
    if not profesional:
        raise HTTPException(403, ...)
    await procesar_update_async(body, profesional_id=profesional.id)
```

### DEC-04: Google Calendar per-professional con OAuth2 refresh token

**Decision**: `CalendarService` ya no inicializa un cliente global con service account JSON. En su lugar, recibe `profesional: Profesional` y construye credenciales OAuth2 usando `profesional.google_refresh_token`.

**Rationale**:
- En v1.0 se usaba una service account con un calendario compartido. En v2.0 multi-profesional, cada profesional debe sincronizar con su propia cuenta de Google.
- El flujo OAuth2 (obtención del `refresh_token`) es responsabilidad del frontend/profesional; el backend solo lo consume.
- Si `google_refresh_token` es NULL o vacío, las operaciones de Calendar se omiten con un warning log (best-effort, no bloquea operaciones de negocio).

**Pattern**:
```python
class CalendarService:
    def __init__(self, profesional: Profesional, settings: Optional[Settings] = None):
        self.profesional = profesional
        self.settings = settings or Settings()
        if not profesional.google_refresh_token:
            raise ValueError("Profesional sin google_refresh_token")
        credentials = Credentials(
            token=None,
            refresh_token=profesional.google_refresh_token,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        self._service = build("calendar", "v3", credentials=credentials)
```

### DEC-05: Scheduler jobs iteran por profesional activo

**Decision**: Los jobs del scheduler que necesitan scopeo ejecutan un `SELECT id FROM profesional WHERE is_active = TRUE` y luego iteran, creando una sesión de DB por profesional (o reutilizando la sesión pasando `profesional_id` a los servicios).

**Rationale**:
- El scheduler no tiene un "usuario autenticado" en ejecución; opera como sistema.
- Iterar por profesional activo garantiza que no se procesan datos de profesionales desactivados.
- Es más simple y predecible que usar context variables o threads con scopes implícitos.

**Pattern**:
```python
async def _enviar_recordatorios_job() -> None:
    settings = Settings()
    async_session = _get_sessionmaker()
    async with async_session() as db:
        result = await db.execute(select(Profesional.id).where(Profesional.is_active == True))
        profesional_ids = result.scalars().all()

    for pid in profesional_ids:
        async with async_session() as db:
            turnos = await obtener_turnos_para_recordar(db, profesional_id=pid, ...)
            for turno in turnos:
                ...
```

### DEC-06: RN-TU-01 scoping ajustado a por-profesional

**Decision**: La regla RN-TU-01 ("un paciente solo puede tener un turno activo a la vez") se redefin como: "un paciente solo puede tener un turno activo **por profesional**". Es decir, un paciente puede tener turnos activos con diferentes profesionales simultáneamente.

**Rationale**:
- En un modelo SaaS multi-tenant, los pacientes de un profesional no deberían impedir que otro profesional les dé turnos.
- El DNI ya es único por `profesional_id` (`uq_paciente_profesional_dni`), lo que naturalmente soporta esto.
- La query `_paciente_tiene_turno_activo` debe agregar `Turno.profesional_id == profesional_id` a su filtro.

### DEC-07: Test migration: authenticated_client obligatorio

**Decision**: Todos los tests de routers usan `authenticated_client` en lugar de `api_client`. Los tests de servicios reciben el fixture `profesional` y pasan `profesional.id`.

**Rationale**:
- Los routers ahora requieren autenticación; cualquier test que use `api_client` recibirá 401.
- El fixture `profesional` ya existe en `conftest.py` con hash bcrypt real.
- Para tests de servicios que no requieren autenticación (tests unitarios puros), se inyecta `profesional_id` directamente.

### DEC-08: PacienteService también requiere profesional_id

**Decision**: `crear_o_obtener_paciente` recibe `profesional_id` y la búsqueda por DNI se hace con `where(Paciente.dni == data.dni, Paciente.profesional_id == profesional_id)`.

**Rationale**:
- El constraint `uq_paciente_profesional_dni` ya existe en la base de datos.
- Un paciente con el mismo DNI puede existir para otro profesional; no debe ser "reutilizado" automáticamente entre profesionales.
- Esto implica que el flujo de Telegram también debe identificar al profesional antes de crear/obtener paciente.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Riesgo de regresión masiva**: al tocar ~35 archivos de tests y todos los servicios, es muy probable introducir bugs. | Ejecutar la suite completa de tests tras cada grupo de cambios. Dividir la implementación en tareas atómicas (servicio por servicio). |
| **Riesgo de deadlock en scheduler**: si un job itera por profesional creando sesiones anidadas, podría haber problemas de conexiones. | Usar un solo `async with session()` por iteración, cerrando explícitamente. No anidar sesiones. |
| **Riesgo de performance**: agregar `profesional_id` a todas las queries podría degradar performance si faltan índices. | Verificar que existan índices en `turno.profesional_id`, `paciente.profesional_id`, `lista_de_espera.profesional_id`. Ya fueron creados en C-14. |
| **Riesgo de breaking change en API para n8n**: n8n workflows existentes no envían `Authorization` ni `X-API-Key`. | Documentar el breaking change. Los workflows deben actualizarse para incluir `X-API-Key` en las llamadas al backend. |
| **Riesgo de complejidad en Telegram**: un mismo número de teléfono podría interactuar con bots de diferentes profesionales. | Cada profesional tiene su propio bot (token propio). El routing por `secret_token` garantiza que el update llegue al profesional correcto. El estado de conversación (`_conversation_states`) debe incluir `profesional_id` como parte de la clave o del state. |
| **Riesgo de Google Calendar: profesionales sin refresh_token** | Operación best-effort: si no hay `refresh_token`, se loguea warning y se omite la sincronización. El turno sigue confirmado en DB. |

## Migration Plan

1. **Preparación**: Verificar que C-14 y C-15 estén completamente aplicados y archivados. ✅ (El usuario confirmó que sí.)
2. **Implementación secuencial** (ver `tasks.md`):
   - Fase 1: Servicios core (Turno, Paciente, ListaEspera)
   - Fase 2: Servicios de integración (Calendar, Telegram, Notificacion)
   - Fase 3: Routers + Dependencias
   - Fase 4: Scheduler
   - Fase 5: Tests existentes (migración masiva)
   - Fase 6: Tests de aislamiento (nuevos)
3. **Validación**: Ejecutar `pytest` completo. Si falla >10% de tests, detener y fix antes de continuar.
4. **Despliegue**: Este change es breaking para cualquier integración externa (n8n, bots de Telegram). Requiere coordinación con el equipo de ops.

## Open Questions

1. **¿Cómo se obtiene el `google_refresh_token` para cada profesional?** Este change asume que el campo ya existe (C-14) y tiene valor. El flujo OAuth2 para obtenerlo es un change separado (C-17 probablemente).
2. **¿El estado de conversación de Telegram (`_conversation_states`) debe ser global o por-profesional?** Dado que cada profesional tiene su propio bot, en teoría no debería haber colisión de chat_id. Sin embargo, para robustez futura, se recomienda que la clave del state sea `(profesional_id, chat_id)`. Esto se deja como mejora post-C-16.
3. **¿Los endpoints de auth (`/auth/register`) deben seguir disponibles públicamente o requerir algún token de administrador?** Por ahora se mantiene público para permitir onboarding de nuevos profesionales. En v2.1 se puede agregar invitación por admin.
