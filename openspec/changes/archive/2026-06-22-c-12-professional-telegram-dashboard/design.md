## Context

El proyecto Tesis-N8N-turnos es un sistema de turnos odontológicos con backend FastAPI + PostgreSQL y un bot de Telegram como interfaz principal. Tras completar C-03 (professional-config) y C-13 (turno-hardening), el profesional tiene endpoints REST para leer/escribir su configuración y el bot maneja reservas, cancelaciones y reprogramaciones de pacientes. Sin embargo, el profesional no puede consultar su agenda ni modificar su configuración desde Telegram.

La pregunta abierta IN-03 fue resuelta a favor de comandos de Telegram para v1.0, evitando desarrollar un panel web. Este change cierra esa decisión implementando los comandos necesarios.

## Goals / Non-Goals

**Goals:**
- Permitir al profesional ver los turnos confirmados del día actual desde Telegram (`/turnos_hoy`).
- Permitir al profesional consultar métricas básicas de la agenda desde Telegram (`/metricas`).
- Permitir al profesional modificar su configuración (horarios, duración, días) desde Telegram vía wizard conversacional (`/configurar`).
- Exponer los mismos datos vía endpoints REST para mantener la API funcional de forma aislada (n8n puede consumirlos en el futuro).
- Respetar todas las reglas duras del proyecto: type hints estrictos, `response_model`, TDD, no hardcodear config, no bloquear event loop.

**Non-Goals:**
- Panel web para el profesional (fuera de scope v1.0, resuelto por IN-03).
- Autenticación formal del profesional en Telegram (v1.0 asume single-user; no hay multi-tenant ni auth por rol).
- Notificaciones push al profesional (ej. "nuevo turno reservado"). Eso puede venir en v2.
- Modificación de configuración vía REST con body complejo (ya existe PUT parcial en C-03; no se cambia).

## Decisions

### 1. Wizard `/configurar` como secuencia de estados conversacionales
**Decisión**: Implementar `/configurar` como un wizard paso a paso dentro del `telegram_service.py`, reutilizando el patrón de estados por `chat_id` ya existente.
**Pasos**: `config_esperando_hora_inicio` → `config_esperando_hora_fin` → `config_esperando_dias` → `config_esperando_duracion` → `config_confirmar`.
**Rationale**: Mantiene consistencia con los flujos de paciente (reserva, reprogramación). Telegram no tiene formularios nativos; el paso a paso con validación inline es la UX más predecible.
**Alternativas consideradas**:
- Enviar un solo mensaje con formato estructurado (ej. JSON o CSV) → descartado: muy propenso a errores de usuario.
- Usar un webapp de Telegram (Mini App) → descartado: añade complejidad de frontend y hosting; contradice la decisión de IN-03 de no hacer panel web.

### 2. Días de atención seleccionables vía botones inline
**Decisión**: En el paso de días, presentar los 7 días de la semana como botones inline de toggle (multiselección). Un botón "Confirmar días" finaliza la selección.
**Rationale**: Es más amigable que pedir texto libre (ej. "Lunes, Martes"). Permite validar en cada paso.
**Implementación**: Los estados del wizard guardan `dias_seleccionados: list[str]` en el state del chat. Cada click en un día hace toggle y actualiza el teclado (usando `answer_callback_query` + `edit_message_reply_markup`).

### 3. Métricas calculadas en endpoint, no materializadas
**Decisión**: Las métricas (`total_turnos_hoy`, `tasa_confirmacion`, `tasa_cancelacion`) se calculan on-the-fly en el endpoint `GET /profesional/metricas` con queries SQL agregadas.
**Rationale**: El volumen de datos en v1.0 es bajo (un solo profesional). Materializar métricas añadiría complejidad innecesaria (triggers o jobs de agregación).
**Alternativas consideradas**:
- Tabla de métricas materializada actualizada por scheduler → descartado por over-engineering en v1.0.

### 4. Endpoints REST con `response_model` Pydantic v2
**Decisión**: Los endpoints `GET /profesional/turnos-hoy` y `GET /profesional/metricas` usan schemas Pydantic v2 con `response_model`, alineado con la regla dura del proyecto.
**Rationale**: Serialización consistente, documentación OpenAPI automática, y type safety.

### 5. Listado de turnos formateado en Telegram con splitting > 4096 chars
**Decisión**: El mensaje de `/turnos_hoy` lista los turnos con MarkdownV2, uno por línea. Si supera 4096 caracteres, se divide en múltiples mensajes usando la utilidad `split_message` ya existente.
**Rationale**: Regla dura del proyecto. Además, un día con turnos de 30 min tiene como máximo ~30 turnos, lo cual raramente supera el límite, pero debe manejarse defensivamente.

### 6. No se distingue profesional vs paciente por chat_id en v1.0
**Decisión**: Los comandos `/turnos_hoy`, `/metricas`, `/configurar` están disponibles para cualquier chat que los envíe. No hay whitelist de `chat_id` de profesional.
**Rationale**: El sistema es single-profesional single-tenant en v1.0. El profesional es quien opera el bot. Agregar autorización por chat_id añadiría una variable de entorno (`PROFESIONAL_CHAT_ID`) y complejidad que no aporta valor en esta versión.
**Alternativas consideradas**:
- Variable de entorno `PROFESIONAL_CHAT_ID` + validación → descartado: el profesional ya es el único operador humano del sistema.

## Risks / Trade-offs

- **[Risk]** El wizard `/configurar` puede quedar interrumpido si el profesional cierra Telegram o el bot se reinicia. → **Mitigation**: Los estados son en memoria; al reiniciarse el bot, el estado se pierde. Esto es aceptable para v1.0 (configuración no es crítica en tiempo real). El profesional puede reintentar. Si en el futuro se requiere persistencia, se puede migrar a Redis o tabla de estados.
- **[Risk]** Cualquier usuario con acceso al bot puede ejecutar `/configurar` y cambiar la agenda. → **Mitigation**: Aceptado como riesgo de v1.0 (single-user). Documentado en decisiones.
- **[Risk]` /metricas` puede volverse lenta con años de datos. → **Mitigation**: Las queries filtran por rango relevante (hoy para turnos del día; últimos 30 días para tasas). Si escala, se puede agregar índices compuestos o materialización.
- **[Trade-off]** No se notifica al profesional de cambios de configuración. → Aceptado. El feedback es visual inmediato en Telegram.

## Migration Plan

No aplica. Este change es puramente aditivo:
- Sin migraciones de base de datos.
- Sin cambios breaking en API (nuevos endpoints GET, no modifica existentes).
- Sin cambios en variables de entorno (reutiliza `telegram_bot_token`).
- Despliegue: mergear, deployar backend, opcionalmente registrar comandos en `@BotFather`.

## Open Questions

- ¿Se requiere que `/metricas` incluya métricas semanales/mensuales, o solo diarias? → **Resuelto**: se implementa resumen del día + tasas sobre los últimos 30 días como default. Fácil de extender.
- ¿El wizard `/configurar` debe permitir cancelar en cualquier paso? → **Resuelto**: sí, botón "Cancelar" disponible en cada paso, que resetea estado a `idle`.
