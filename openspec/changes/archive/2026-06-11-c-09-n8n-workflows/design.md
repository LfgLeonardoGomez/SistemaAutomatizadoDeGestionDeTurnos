## Context

Los cambios C-06 a C-08 entregaron los endpoints REST del backend para turnos, pacientes, webhooks y disponibilidad. Sin embargo, la capa de orquestación conversacional en Telegram aún no existe en forma de workflows n8n importables. Este change cubre exactamente esa brecha: generar los archivos JSON de workflow que n8n puede importar y ejecutar para responder a mensajes de usuarios, consultar disponibilidad, reservar turnos, cancelarlos y preparar los flujos de recordatorio y lista de espera.

## Goals / Non-Goals

**Goals:**
- Entregar 4 archivos JSON de workflow n8n listos para importar en una instancia de n8n (local o cloud).
- Cada workflow debe incluir: Webhook Trigger → HTTP Request a FastAPI → Formateo de respuesta → Telegram Send Message.
- Documentar en `README.md` las variables de entorno necesarias (`N8N_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `FASTAPI_BASE_URL`) y el paso a paso de importación.
- Los workflows de reserva y cancelación deben ser completos y funcionales con los endpoints actuales.
- Los workflows de recordatorio y lista de espera pueden ser templates/placeholders que se activarán en C-10 y C-11.

**Non-Goals:**
- No se modifica código del backend ni se agregan endpoints nuevos.
- No se incluye automatización de tests (n8n es herramienta externa; los tests serán manuales).
- No se configura la instancia de n8n del usuario (solo se documentan los pasos).

## Decisions

1. **Formato de workflow: JSON nativo de n8n**
   - **Rationale**: Es el estándar de importación/exportación de n8n. Cualquier instancia puede importar el archivo directamente sin pasos intermedios.
   - **Alternativas consideradas**: Crear workflows desde cero manualmente en la UI (descartado: no es reproducible ni versionable), usar la API de n8n para crear workflows programáticamente (descartado: requiere credenciales de instancia y es más complejo).

2. **Webhook Trigger como punto de entrada universal**
   - **Rationale**: El webhook `POST /webhooks/telegram` del backend ya recibe updates de Telegram. Los workflows n8n pueden exponer sus propios webhooks y ser invocados desde el backend o directamente desde Telegram. Para máxima flexibilidad, cada workflow expone un webhook propio.
   - **Alternativas consideradas**: Usar un único workflow router que delega a sub-workflows (descartado: agrega complejidad innecesaria para v1; se puede refactorizar después si el número de flujos crece).

3. **HTTP Request nodes para llamar a FastAPI**
   - **Rationale**: Es la forma nativa de n8n de consumir APIs REST. Permite configurar headers, query params, body y parsear la respuesta sin código custom.
   - **Alternativas consideradas**: Nodo "Execute Command" o código custom (descartado: viola la regla "nunca hardcodear"; HTTP Request permite usar variables de n8n para URLs).

4. **Telegram Send Message como salida única**
   - **Rationale**: Garantiza que la respuesta vuelva al chat de Telegram del usuario. El nodo de n8n usa `TELEGRAM_BOT_TOKEN` y soporta markdown inline para botones.

5. **Placeholders para recordatorio y lista de espera**
   - **Rationale**: C-10 y C-11 aún no implementan los endpoints necesarios. Los placeholders documentan la estructura esperada y aceleran la implementación futura.

## Risks / Trade-offs

- **[Riesgo] Los endpoints de FastAPI pueden cambiar en C-10/C-11** → **Mitigación**: Las URLs de los workflows usan variables de n8n (`{{$FASTAPI_BASE_URL}}`) que se actualizan en un solo lugar. El README documenta cómo modificarlas.
- **[Riesgo] n8n no está disponible en el entorno de CI/CD** → **Mitigación**: Los workflows son archivos estáticos; no requieren CI. El backend sigue siendo testeable de forma aislada (regla dura del proyecto).
- **[Riesgo] Formato de mensaje de Telegram supera los 4096 caracteres** → **Mitigación**: Los workflows de reserva paginan la lista de fechas/horarios usando botones inline de Telegram (máximo 100 botones por mensaje, bien por debajo del límite de caracteres).
- **[Trade-off] Placeholders vs esperar a C-10/C-11** → Se eligen placeholders para mantener la velocidad del equipo y tener un mapa completo de flujos desde ahora.
