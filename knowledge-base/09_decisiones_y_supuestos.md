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
**Trade-offs aceptados**: No se guarda historial completo de notificaciones; solo el último estado.

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
