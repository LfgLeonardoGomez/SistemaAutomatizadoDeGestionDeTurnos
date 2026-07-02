# Decisiones y Supuestos

## Decisiones documentadas

### DD-01 — Uso de n8n como orquestador de flujos
**Decisión**: Utilizar n8n como herramienta visual para orquestar la integración entre Telegram, el backend y Google Calendar.
**Contexto**: Se necesita una forma flexible de modelar flujos conversacionales y de integración sin acoplar todo al código del backend.
**Alternativas consideradas**:
- Implementar toda la lógica de flujo directamente en FastAPI con manejo manual de estados de conversación.
- Usar Rasa o similar para bots conversacionales.
**Justificación**: n8n ofrece una interfaz visual para no-programadores, facilita la iteración de flujos y permite conectar servicios sin código adicional. Es adecuado para el alcance académico y operativo del proyecto.
**Trade-offs aceptados**: Mayor dependencia de un servicio externo; posible overhead de mantenimiento si los flujos crecen en complejidad.

### DD-02 — Google Calendar como agenda espejo
**Decisión**: Delegar la gestión del calendario a Google Calendar en lugar de desarrollar un calendario propio.
**Contexto**: El profesional necesita visualizar su agenda de forma familiar y accesible.
**Alternativas consideradas**:
- Calendario propio embebido en una aplicación web.
- iCal / calendarios genéricos.
**Justificación**: Google Calendar es una herramienta robusta, ampliamente utilizada y con API estable. Reduce el scope del proyecto y mejora la adopción por parte del profesional.
**Trade-offs aceptados**: Dependencia de los términos y disponibilidad de Google; requiere OAuth 2.0.

### DD-03 — Telegram como única interfaz de usuario en v1.0
**Decisión**: El bot de Telegram será el único canal de interacción con los pacientes en la versión inicial.
**Contexto**: Los pacientes demandan inmediatez y canales accesibles; Telegram es ampliamente utilizado y no requiere instalar una app propia.
**Alternativas consideradas**:
- WhatsApp Business API (más costosa y compleja de integrar en fase inicial).
- Aplicación web progresiva (PWA) o móvil nativa.
**Justificación**: Telegram ofrece API gratuita, webhooks, y una experiencia conversacional simple que alinea con el MVP.
**Trade-offs aceptados**: Limita el alcance a usuarios con Telegram; posible barrera para usuarios que solo usan WhatsApp.

### DD-04 — PostgreSQL como base de datos relacional
**Decisión**: Utilizar PostgreSQL para persistencia de todos los datos del sistema.
**Contexto**: Se requiere integridad referencial, consistencia y consultas complejas sobre turnos, pacientes y estados.
**Alternativas consideradas**:
- SQLite (insuficiente para concurrencia y escala futura).
- MongoDB (menor ajuste a la naturaleza relacional de los datos).
**Justificación**: PostgreSQL es robusto, open-source, maneja bien la concurrencia y se integra naturalmente con SQLAlchemy en FastAPI.
**Trade-offs aceptados**: Requiere operación y monitoreo de una base de datos servidor.

### DD-05 — FastAPI como framework backend
**Decisión**: Desarrollar el backend con FastAPI (Python).
**Contexto**: Necesidad de alta velocidad de desarrollo, validación automática, documentación OpenAPI integrada y soporte async.
**Alternativas consideradas**:
- Flask (menor soporte nativo para async y validación automática).
- Node.js/Express (ecosistema diferente, menor alineación con el stack de n8n/PostgreSQL del proyecto).
- Django (más pesado para una API pequeña).
**Justificación**: FastAPI ofrece el mejor balance entre rendimiento, productividad y modernidad para APIs REST en Python.
**Trade-offs aceptados**: Curva de aprendizaje inicial para desarrolladores no familiarizados con Pydantic y async/await.

### DD-06 — Estados de turno como VARCHAR con validación Pydantic (no ENUM de PostgreSQL)
**Decisión**: Implementar el campo `Turno.estado` como `String(50)` en SQLAlchemy y validar los valores permitidos (`DISPONIBLE`, `RESERVADO_TEMPORAL`, `CONFIRMADO`, `CANCELADO`, `COMPLETADO`) en el schema Pydantic, en lugar de usar un tipo `Enum` nativo de PostgreSQL.
**Contexto**: Simplifica migraciones y evita dependencia de tipos ENUM específicos de PostgreSQL, manteniendo la base portable.
**Trade-offs aceptados**: Menor enforcement a nivel de base de datos; la validación queda en la capa de aplicación.

### DD-07 — Persistencia de `google_event_id` en la tabla Turno
**Decisión**: Agregar la columna `google_event_id` al modelo `Turno` para persistir el ID del evento creado en Google Calendar.
**Contexto**: Necesario para poder eliminar o actualizar el evento externo cuando el turno se cancela o reprograma, sin depender de búsquedas por fecha/hora en Calendar API.
**Trade-offs aceptados**: Acoplamiento leve con Google Calendar (la columna es NULLable y no bloquea operaciones si Calendar falla).

### DD-08 — Flag `recordatorio_enviado` en Turno para deduplicación de recordatorios
**Decisión**: Usar una columna booleana `recordatorio_enviado` en `Turno` en lugar de una tabla separada de historial de notificaciones.
**Contexto**: El alcance v1.0 solo requiere evitar enviar el mismo recordatorio 24h antes múltiples veces.
**Trade-offs aceptados**: No se guarda historial completo de notificaciones; solo el último estado. **C-24 refuerza esta decisión**: el flag es el punto de sincronía entre los dos motores de recordatorio (n8n + APScheduler) y evita doble dispatch.

### DD-09 — Destinatario de notificación por turno (C-23) [user]
**Decisión**: Modelar el destinatario de confirmación/recordatorio como entidad hija `turno_destinatario(turno_id, canal, destinatario)` con `UNIQUE(turno_id, canal)`. Eliminar la columna `paciente.telegram_chat_id` por ser código muerto.
**Contexto**: El paciente no se autentica (se identifica por DNI). Una misma persona puede gestionar turnos desde múltiples chats de Telegram; una columna escalar `paciente.telegram_chat_id` no puede modelar la relación M:N chat↔paciente. Además, la verificación en código mostró que `paciente.telegram_chat_id` nunca se escribía, por lo que el job de recordatorios la leía `NULL` y marcaba `recordatorio_enviado=True` sin enviar nada (recordatorio silenciosamente roto).
**Alternativas consideradas**:
- **A) Columnas simples en `turno`** (`canal` + `destinatario`): un solo canal por turno. Rechazada porque el requisito es "uno o **ambos** canales" y la extensibilidad real exige tabla hija.
- **B) JSON/array de destinatarios en `turno`**: rechazada por perder `UNIQUE(turno_id, canal)`, no validar ENUM a nivel DB, complicar el query del sender.
- **C) Preferencia de notificación a nivel Paciente**: rechazada porque reintroduce el acoplamiento paciente↔chat y no soporta multi-chat por turno.
**Justificación**: la tabla hija es la forma normalizada mínima que cumple "uno o ambos canales" y multi-chat, sin over-engineering. Sigue el precedente de `ListaDeEspera` (contacto por registro, no por paciente). El scope de tenant se alcanza vía `turno.profesional_id`; no se necesita `profesional_id` propio en `turno_destinatario` [openspec · archive/2026-07-02-c-23-.../design.md §Decisión 1].
**Trade-offs aceptados**: El email queda modelado pero sin sender (futuro change). La columna `paciente.telegram_chat_id` se elimina — `downgrade` la recrea (sin datos).

### DD-10 — Orquestador n8n como single entry point de Telegram (C-24) [user]
**Decisión**: Cada profesional con bot importa en n8n **una instancia** del orquestador (`orquestador.json` + 3 sub-workflows + `flujo-recordatorio.json`) con 2 credenciales: `Telegram Bot` (token del bot) y `Header Auth` (`X-API-Key: <profesional.api_key>`). El orquestador es el **entry point principal** del bot (no el webhook del backend).
**Contexto**: Pre-C-24 los workflows n8n enviaban requests al backend sin `X-API-Key` (recibían 401), tenían 1 webhook por flujo (4 webhooks a configurar en `@BotFather`), y la lógica de routing estaba dispersa. El usuario diseñó un esqueleto de orquestador que se tomó como punto de partida.
**Alternativas consideradas**:
- **A) Un único orquestador para N bots**: rechazada porque el `Telegram Trigger` de n8n autentica con UN token por workflow; un orquestador multi-bot exige reemplazar el trigger por un `Webhook Trigger` + validación de `X-Telegram-Bot-Api-Secret-Token` + un `IF` por profesional, rompiendo el modelo "1 trigger = 1 bot" y dificultando el debugging por profesional.
- **B) Reemplazar el orquestador n8n por más lógica en el backend**: ya está hecho (C-08 / C-17 con `telegram_service.procesar_mensaje`). Rechazada porque el usuario explícitamente pidió el orquestador n8n como **capa de orquestación visible** en la demo de la tesis. El backend procesa Telegram vía su propio webhook, pero el orquestador n8n **demuestra la alternativa** y permite ver los workflows visualmente.
**Justificación**: un orquestador por bot, con credenciales dedicadas, minimiza acoplamiento, maximiza aislamiento entre profesionales y se alinea con los patrones canónicos de n8n. El `Header Auth` credential garantiza que el `X-API-Key` se inyecta en todos los `HTTP Request` nodes del workflow sin hardcodear.
**Trade-offs aceptados**: Cada profesional tiene su propia copia del orquestador en n8n (más instancias que mantener). El webhook del backend queda ocioso pero disponible como fallback. La rotación de `api_key` requiere reconfigurar la credencial en n8n (un cambio, todos los nodos actualizados) [openspec · archive/2026-07-02-c-24-.../design.md §Decisión 1, §Decisión 4].

### DD-11 — Dos motores de recordatorio conviviendo (C-24) [user]
**Decisión**: El sistema de recordatorios opera con dos motores paralelos que llaman a la misma lógica de `notificacion_service`:
1. **n8n primario** (`flujo-recordatorio.json`): `Schedule Trigger` cron `0 10 * * *` → `POST /api/v1/recordatorios/run?fecha=mañana`.
2. **APScheduler fallback** (`scheduler.jobs._enviar_recordatorios_job`): job interno en el backend (C-08).

El flag `turno.recordatorio_enviado` evita doble dispatch entre ambos.
**Contexto**: Si n8n está caído o no se configuró, el APScheduler del backend sigue mandando. Si n8n está activo, hace de primario y el APScheduler queda ocioso. Ambos motores llaman a la **misma** lógica de `notificacion_service` para mantener **una sola fuente de verdad** sobre "qué turnos recordar" y "cómo enviarlos".
**Alternativas consideradas**:
- **A) Reemplazar el APScheduler por n8n**: rechazada porque rompe el fallback (si n8n está caído, no hay recordatorios). El APScheduler sigue siendo útil como red de seguridad.
- **B) Un solo motor con fallback manual**: descartada por operacional (el operador tendría que recordar activar/desactivar el fallback).
- **C) n8n itera por profesional y llama a un endpoint por profesional**: rechazada porque multiplica requests (1 + N) y duplica la lógica de iteración en n8n.
**Justificación**: el backend es la fuente de verdad (tiene la lógica de `obtener_turnos_para_recordar` + `enviar_recordatorio_telegram` + `TurnoDestinatario`); n8n es el **trigger** (cron) y el **transport** (HTTP). Cada uno hace lo que sabe hacer mejor. El flag `recordatorio_enviado` es el punto de sincronía [openspec · archive/2026-07-02-c-24-.../design.md §Decisión 5 + R8].
**Trade-offs aceptados**: en v1.0 se recomienda activar **solo uno** por profesional (si ambos activos, el de n8n gana por horario y el de APScheduler queda ocioso).

## Supuestos inferidos

### SU-01 — Un único profesional por instancia en v1.0
**Supuesto**: El sistema está diseñado para operar con un único profesional (dentista) por despliegue en la versión inicial.
**Origen**: Documento fuente, sección 1.6 (Alcance y limitaciones) y sección 6.3 (Limitaciones).
**Riesgo si es falso**: Si se intenta usar con múltiples profesionales sin refactorizar, habrá conflictos de agenda y permisos.
**Cómo validar**: Confirmar con el director del proyecto que el MVP cubre solo un consultorio de un solo profesional.

### SU-02 — El profesional tiene acceso a Google Calendar
**Supuesto**: El profesional dispone de una cuenta de Google y permite la creación/modificación de eventos en su calendario vía API.
**Origen**: Documento fuente, sección 4.5.6.2 (Integración con Google Calendar).
**Riesgo si es falso**: La sincronización de turnos no funcionaría; el sistema perdería un pilar de su arquitectura.
**Cómo validar**: Verificar que se cuenta con credenciales de cuenta de servicio de Google Cloud y permisos de Calendar API.

### SU-03 — Los pacientes tienen Telegram instalado
**Supuesto**: Los pacientes del consultorio utilizan Telegram como aplicación de mensajería.
**Origen**: Documento fuente, sección 4.5.6.1 (Integración con Telegram).
**Riesgo si es falso**: Los pacientes no podrían interactuar con el sistema; sería necesario agregar WhatsApp u otro canal.
**Cómo validar**: Consultar al profesional o realizar encuesta breve a sus pacientes sobre uso de Telegram.

### SU-04 — El backend y la base de datos coexisten en la misma red o infraestructura
**Supuesto**: El despliegue del backend y PostgreSQL es co-ubicado o al menos con conectividad estable de baja latencia.
**Origen**: Arquitectura propuesta en sección 4.3.
**Riesgo si es falso**: Latencia en las respuestas del bot; posibles timeouts en la interacción conversacional.
**Cómo validar**: Realizar pruebas de conectividad y latencia en el entorno de despliegue planificado.

### SU-05 — La reserva temporal expira en 10 minutos (configurable)
**Supuesto**: El tiempo de expiración de la reserva temporal es de 10 minutos por defecto, configurable vía `RESERVA_TEMPORAL_MINUTOS`.
**Origen**: Implementación final (C-06 / C-13). El valor de 2 minutos del caso de prueba fue solo ilustrativo.
**Riesgo si es falso**: Si el tiempo es muy corto, los usuarios pueden frustrarse; si es muy largo, se bloquean horarios innecesariamente.
**Cómo validar**: Verificar `config.py` y ajustar la variable de entorno según feedback de usuarios reales [code · config.py:21].

### SU-06 — Sin multi-tenancy ni `tenant_id` en v1.0
**Supuesto**: A pesar de que la arquitectura se describe como SaaS, v1.0 opera con un único profesional por instancia y **no incluye `tenant_id`** en ningún modelo.
**Origen**: Decisión pragmática de MVP para reducir complejidad; el proyecto académico no requiere multi-consultorio en la versión inicial.
**Riesgo si es falso**: Si se necesita escalar a multi-profesional, será necesaria una migración de datos para agregar `tenant_id` y aplicar RLS.
**Cómo validar**: Confirmar con el director del proyecto que el MVP es estrictamente single-profesional. **Nota**: Las reglas duras de AGENTS.md recomiendan `tenant_id` desde v1, pero el código actual no lo implementa [code · models/*.py].
