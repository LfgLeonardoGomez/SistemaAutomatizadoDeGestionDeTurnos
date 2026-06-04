# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|-------|-------------|-----------------|
| Paciente | Persona que solicita o gestiona un turno odontológico | Vía bot de Telegram: solicita turnos, confirma, cancela, reprograma, responde recordatorios |
| Profesional odontológico | Dentista que atiende en el consultorio y gestiona la agenda | Accede a métricas básicas y turnos del día; configura horarios y duración de turno |
| Sistema (Scheduler/Bot) | Componentes automatizados que ejecutan tareas programadas | Envía recordatorios, libera reservas vencidas, notifica lista de espera, sincroniza Google Calendar |
| Administrador (implícito v1.0) | Configurador inicial del sistema | Define horarios, duración de turnos, días de atención del profesional |

## RBAC — Matriz de permisos

> **Nota v1.0**: el sistema está orientado a un único profesional. No hay autenticación de usuarios con roles diferenciados en esta versión. Los permisos se derivan de la naturaleza del actor y del canal de interacción.

| Rol | Recurso | Permisos |
|-----|---------|----------|
| Paciente | Turno (propio) | Crear (reservar), Leer (consultar), Actualizar (confirmar/reprogramar), Cancelar |
| Paciente | Paciente (propio) | Crear (registro inicial), Leer (datos propios) |
| Paciente | Lista de espera | Crear (inscribirse), Leer (estado propio) |
| Profesional | Turnos (todos) | Leer (todos), Actualizar (estados), Eliminar (solo lógico) |
| Profesional | Pacientes | Leer (todos) |
| Profesional | Configuración | Leer, Actualizar (horarios, duración) |
| Profesional | Métricas | Leer |
| Sistema | Turnos | Leer, Actualizar (estados automáticos), Crear (eventos en Google Calendar) |
| Sistema | Lista de espera | Leer, Actualizar (notificar), Eliminar (asignar turno) |

## Rutas públicas

En v1.0 no hay autenticación formal. El acceso se controla por:

- **Webhook de Telegram**: `POST /webhooks/telegram` — recibe mensajes del bot (público por naturaleza del webhook, validado por token del bot).
- **Endpoints de disponibilidad**: `GET /turnos/disponibles` — puede ser público para consulta de horarios (a definir si requiere rate limiting).

> **Pregunta abierta**: ¿Se requiere autenticación para el panel del profesional? En v1.0 se asume acceso restringido por URL o red interna.
