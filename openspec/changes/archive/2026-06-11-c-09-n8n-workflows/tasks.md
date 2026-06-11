## 1. Preparación

- [x] 1.1 Verificar que el directorio `n8n-workflows/` existe y está vacío (creado en C-01)
- [x] 1.2 Revisar endpoints de FastAPI disponibles (C-06 a C-08) para confirmar URLs y payloads
- [x] 1.3 Definir estructura de variables de entorno en n8n (`N8N_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `FASTAPI_BASE_URL`)

## 2. Workflow de Reserva (flujo-reserva.json)

- [x] 2.1 Crear nodo Webhook Trigger configurado para recibir POST de Telegram
- [x] 2.2 Crear nodo HTTP Request `GET /turnos/disponibles` para listar fechas
- [x] 2.3 Crear nodo Format Response que transforme la respuesta en botones inline de Telegram
- [x] 2.4 Crear nodo HTTP Request `GET /turnos/disponibles?fecha=YYYY-MM-DD` para listar horarios
- [x] 2.5 Crear nodo Format Response que transforme horarios en botones inline
- [x] 2.6 Crear nodo HTTP Request `POST /turnos` para reserva temporal
- [x] 2.7 Crear nodo Format Response para mensaje de reserva temporal con botón de confirmación
- [x] 2.8 Crear nodo HTTP Request `PUT /turnos/{id}/confirmar` para confirmar turno
- [x] 2.9 Crear nodos Telegram Send Message para cada paso del flujo (fechas, horarios, confirmación, error)
- [x] 2.10 Agregar manejo de errores (HTTP 409, 410, 404) con mensajes de Telegram apropiados
- [x] 2.11 Validar que el JSON se importa correctamente en n8n sin errores de estructura

## 3. Workflow de Cancelación (flujo-cancelacion.json)

- [x] 3.1 Crear nodo Webhook Trigger para recibir comando de cancelación
- [x] 3.2 Crear nodo HTTP Request `PUT /turnos/{id}/cancelar` con extracción de `turno_id` del payload
- [x] 3.3 Crear nodo Telegram Send Message para confirmación de cancelación exitosa
- [x] 3.4 Crear nodos Telegram Send Message para errores (404 Not Found, 400 Bad Request)
- [x] 3.5 Agregar botón inline opcional para reprogramar tras cancelación
- [x] 3.6 Validar importación del JSON en n8n

## 4. Placeholder Workflows (C-10 y C-11)

- [x] 4.1 Crear `flujo-recordatorio.json` con Schedule Trigger diario, HTTP Request placeholder y Telegram Send Message
- [x] 4.2 Crear `flujo-lista-espera.json` con Webhook Trigger, HTTP Request placeholder y Telegram Send Message
- [x] 4.3 Documentar en cada placeholder los endpoints que se activarán en C-10 y C-11
- [x] 4.4 Validar que los placeholders importan correctamente en n8n

## 5. Documentación (README.md)

- [x] 5.1 Redactar guía de importación de workflows en n8n (paso a paso)
- [x] 5.2 Documentar las variables de entorno necesarias (`N8N_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `FASTAPI_BASE_URL`)
- [x] 5.3 Explicar cómo configurar los webhooks en Telegram BotFather
- [x] 5.4 Incluir sección de troubleshooting (webhooks no llegan, errores 404, timeouts)
- [x] 5.5 Agregar mapeo de workflows ↔ endpoints de FastAPI
- [x] 5.6 Nota sobre placeholders y dependencias futuras (C-10, C-11)

## 6. Testing Manual

- [x] 6.1 Importar `flujo-reserva.json` en instancia local de n8n
- [x] 6.2 Ejecutar webhook de prueba desde Postman/curl simulando update de Telegram
- [x] 6.3 Verificar que el HTTP Request llega a `GET /turnos/disponibles` y recibe respuesta
- [x] 6.4 Testear flujo completo de reserva: fechas → horarios → reserva → confirmación
- [x] 6.5 Testear camino de error: slot ocupado (409) y reserva expirada (410)
- [x] 6.6 Importar `flujo-cancelacion.json` y testear cancelación exitosa
- [x] 6.7 Testear cancelación de turno inexistente (404)
- [x] 6.8 Documentar resultados de tests manuales en README o nota separada

## 7. Entrega y Cierre

- [x] 7.1 Verificar que los 4 archivos JSON están en `n8n-workflows/`
- [x] 7.2 Verificar que `README.md` está en `n8n-workflows/`
- [x] 7.3 Confirmar que ningún archivo de backend fue modificado
- [x] 7.4 Revisar que los placeholders tienen URLs/variables claramente marcadas como "C-10" o "C-11"
- [x] 7.5 Marcar el change como completado en `CHANGES.md`
