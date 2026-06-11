# n8n Workflows — Turnos Telegram Bot

Este directorio contiene los workflows de n8n para la orquestación conversacional del bot de turnos vía Telegram.

## Workflows

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `flujo-reserva.json` | Reserva de turnos (fechas → horarios → reserva → confirmación) | ✅ Completo |
| `flujo-cancelacion.json` | Cancelación de turnos por ID | ✅ Completo |
| `flujo-recordatorio.json` | Envío de recordatorios automáticos | ⏳ Placeholder (C-10) |
| `flujo-lista-espera.json` | Notificación de lista de espera | ⏳ Placeholder (C-11) |

## Prerrequisitos

1. **n8n instalado** (local, cloud, o self-hosted)
2. **Bot de Telegram** creado vía [@BotFather](https://t.me/BotFather)
3. **Backend FastAPI** corriendo (endpoints de C-06 a C-08)

## Variables de entorno en n8n

Configurá estas variables en tu instancia de n8n (Settings → External Secrets o via `.env`):

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `FASTAPI_BASE_URL` | URL base del backend FastAPI | `http://localhost:8000` o `https://api.tuapp.com` |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram (de BotFather) | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `N8N_WEBHOOK_URL` | URL base de los webhooks de n8n (para configurar en Telegram) | `https://tu-n8n.app/webhook` |

> ⚠️ **Nunca hardcodees** tokens ni URLs en los workflows. Usá siempre `{{ $env.VARIABLE }}`.

## Cómo importar workflows

1. Abrí tu instancia de n8n en el navegador
2. Andá a **Workflows** → **Import from file** (o **Import from URL**)
3. Seleccioná el archivo `.json` que querés importar
4. n8n creará el workflow con todos los nodos y conexiones
5. Repetí para cada uno de los 4 workflows

## Cómo configurar webhooks en Telegram

1. Abrí [@BotFather](https://t.me/BotFather) en Telegram
2. Escribí `/setwebhook` y seleccioná tu bot
3. Ingresá la URL del webhook de n8n:
   - Reserva: `{{ $env.N8N_WEBHOOK_URL }}/reserva`
   - Cancelación: `{{ $env.N8N_WEBHOOK_URL }}/cancelar`
   - Lista de espera: `{{ $env.N8N_WEBHOOK_URL }}/lista-espera`

Alternativamente, podés usar el endpoint del backend como proxy:
```
POST {{ $env.FASTAPI_BASE_URL }}/webhooks/telegram
```

## Mapeo de workflows ↔ endpoints FastAPI

| Workflow | Endpoint | Método | Descripción |
|----------|----------|--------|-------------|
| flujo-reserva | `/turnos/disponibles` | GET | Lista fechas/horarios disponibles |
| flujo-reserva | `/turnos` | POST | Crea reserva temporal |
| flujo-reserva | `/turnos/{id}/confirmar` | PUT | Confirma turno reservado |
| flujo-cancelacion | `/turnos/{id}/cancelar` | PUT | Cancela turno confirmado |
| flujo-recordatorio | `/turnos/pendientes` | GET | ⏳ Placeholder C-10 |
| flujo-lista-espera | `/lista-espera/siguiente` | GET | ⏳ Placeholder C-11 |

## Testing

### Manual (sin n8n)

Los endpoints del backend son testeables de forma aislada:

```bash
# Listar disponibilidad
curl "http://localhost:8000/turnos/disponibles?fecha=2024-06-15"

# Crear reserva temporal
curl -X POST http://localhost:8000/turnos \
  -H "Content-Type: application/json" \
  -d '{"fecha":"2024-06-15","hora_inicio":"09:00","paciente_id":1}'

# Confirmar turno
curl -X PUT http://localhost:8000/turnos/1/confirmar \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Juan","apellido":"Pérez","dni":"12345678","telefono":"1234567890"}'

# Cancelar turno
curl -X PUT http://localhost:8000/turnos/1/cancelar
```

### Con n8n

1. Importá el workflow
2. Configurá las credenciales de Telegram (Settings → Credentials)
3. Activá el workflow (toggle ON)
4. Enviá un mensaje al bot en Telegram
5. Revisá la ejecución en n8n (Executions) para debug

### Simulación de webhook

Desde Postman o curl:

```bash
curl -X POST https://tu-n8n.app/webhook/reserva \
  -H "Content-Type: application/json" \
  -d '{"message":{"chat":{"id":123456789},"text":"/reservar"}}'
```

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| Webhook no llega a n8n | URL mal configurada o firewall | Verificá la URL y que el puerto esté abierto |
| Error 404 en HTTP Request | Backend no corriendo o URL incorrecta | Verificá `FASTAPI_BASE_URL` y que el backend esté activo |
| Timeout en HTTP Request | Backend lento o caído | Aumentá el timeout en el nodo HTTP Request (Options → Timeout) |
| Mensaje no llega a Telegram | Token inválido o bot no iniciado | Verificá `TELEGRAM_BOT_TOKEN` y que hayas iniciado chat con el bot |
| Error 409 Conflict | Slot ya ocupado | El workflow envía mensaje al usuario para elegir otro horario |
| Error 410 Gone | Reserva temporal expiró | El usuario debe reiniciar el flujo de reserva |

## Placeholders y dependencias futuras

### C-10 — Recordatorios
- Endpoint: `GET /turnos/pendientes`
- Trigger: Schedule (cada hora o diario a las 18:00)
- Este workflow enviará recordatorios automáticos a pacientes con turnos confirmados para el día siguiente

### C-11 — Lista de espera
- Endpoint: `GET /lista-espera/siguiente`
- Trigger: Webhook (invocado desde backend cuando se cancela un turno)
- Este workflow notificará al siguiente paciente en lista de espera cuando se libere un slot

## Notas

- Los workflows usan **botones inline** de Telegram para la navegación (fechas, horarios, confirmación).
- Los placeholders tienen URLs marcadas explícitamente; se actualizarán cuando C-10 y C-11 estén completos.
- No se modificó ningún archivo del backend en este change.

---

*Generado en el change C-09 (n8n-workflows).*
