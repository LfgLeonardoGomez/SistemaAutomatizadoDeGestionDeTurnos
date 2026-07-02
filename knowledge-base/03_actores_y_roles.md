# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|-------|-------------|-----------------|
| Paciente | Persona que solicita o gestiona un turno odontológico. **Se identifica, no se autentica** (DNI scoped por profesional) | Vía bot de Telegram: solicita turnos, confirma, cancela, reprograma, responde recordatorios |
| Profesional odontológico | Dentista que atiende en el consultorio y gestiona la agenda. **Sí se autentica** | Vía Telegram con `/turnos_hoy`, `/metricas`, `/configurar` [code · telegram_service.py:835-848] **o** vía REST con `X-API-Key` header en `Authorization: Header Auth` de n8n. También configura credenciales del bot y rotación de `api_key` |
| n8n (orquestador) | **C-24** — Capa de orquestación visual de Telegram. **Es el entry point principal del bot** (no el webhook del backend) | Recibe updates del bot vía `Telegram Trigger`, normaliza comando, dispatch-ea a sub-workflows (crear/cancelar/reprogramar) que llaman al backend con `X-API-Key`. Tiene también un workflow independiente (`flujo-recordatorio.json`) que corre el cron diario de recordatorios [code · n8n-workflows/orquestador.json] |
| Sistema (Scheduler/Bot) | Componentes automatizados que ejecutan tareas programadas | APScheduler en el backend (fallback de recordatorios) **+** n8n `Schedule Trigger` (primario). Envía recordatorios, libera reservas vencidas, notifica lista de espera, sincroniza Google Calendar |
| Administrador (implícito v1.0) | Configurador inicial del sistema | Define horarios, duración de turnos, días de atención del profesional; configura credenciales n8n y `@BotFather` por profesional |

## RBAC — Matriz de permisos

> **Nota v1.0 (actualizada en C-23 / C-24)**: el sistema está orientado a un profesional por instancia con sus bots en n8n. La autenticación del profesional se da por dos canales paralelos:
> - **Telegram**: el profesional opera vía comandos (no hay auth formal — se asume que su `chat_id` está autorizado).
> - **REST / n8n**: header `X-API-Key` mapea a `profesional_id` vía `get_profesional_by_api_key`. Sin él, **401** [code · dependencies.py:98-115].
>
> El paciente **nunca se autentica**: se identifica por DNI, scoped por profesional (`UniqueConstraint(profesional_id, dni)`) [code · paciente.py:36-39].

| Rol | Recurso | Permisos |
|-----|---------|----------|
| Paciente | Turno (propio) | Crear (reservar), Leer (consultar), Actualizar (confirmar/reprogramar), Cancelar |
| Paciente | Paciente (propio) | Crear (registro inicial), Leer (datos propios) |
| Paciente | Lista de espera | Crear (inscribirse), Leer (estado propio) |
| Profesional | Turnos (todos) | Leer (todos), Actualizar (estados), Eliminar (solo lógico) |
| Profesional | Pacientes | Leer (todos) |
| Profesional | Configuración | Leer, Actualizar (horarios, duración) |
| Profesional | Métricas | Leer |
| Profesional | TurnoDestinatario (C-23) | Crear, Actualizar (upsert por turno+canal) — vía backend |
| n8n (C-24) | Endpoints REST del profesional | Acceso en nombre del profesional vía `X-API-Key` del `Header Auth` credential. Dispatch-ea a sub-workflows; cada sub-workflow actúa scoped al `profesional_id` autenticado |
| Sistema | Turnos | Leer, Actualizar (estados automáticos), Crear (eventos en Google Calendar), Crear (TurnoDestinatario) |
| Sistema | Lista de espera | Leer, Actualizar (notificar), Eliminar (asignar turno) |

## Rutas públicas

- **Webhook de Telegram**: `POST /webhooks/telegram` — recibe mensajes del bot (validado por `X-Telegram-Bot-Api-Secret-Token`). **Alternativa** al orquestador n8n; por defecto `@BotFather` apunta al `Telegram Trigger` del orquestador (Decisión OQ-1 de C-24) [code · dependencies.py:118-139].
- **Endpoints de disponibilidad**: `GET /turnos/disponibles` — puede ser público para consulta de horarios.
- **Telegram Trigger del orquestador** (C-24): URL pública que n8n registra al activar `orquestador.json`. Es el **entry point principal** del bot del profesional.

> **Pregunta abierta (legado)**: ¿Se requiere autenticación para el panel del profesional? En v1.0 se asume acceso restringido por URL o red interna para el panel, y `X-API-Key` para integraciones server-to-server (n8n, scripts).
