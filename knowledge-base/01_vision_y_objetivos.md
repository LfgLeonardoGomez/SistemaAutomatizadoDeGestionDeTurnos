# Visión y Objetivos

## Propósito del sistema

Automatizar la gestión de turnos odontológicos mediante un bot de Telegram integrado con servicios de calendario, reduciendo la carga operativa del profesional, minimizando la tasa de inasistencias y brindando una experiencia ágil y accesible para los pacientes.

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|-------|-------------------|----------------------|
| Paciente | Reservar, confirmar, cancelar o reprogramar turnos de forma simple vía Telegram | Recibir recordatorios automáticos; ser notificado de turnos liberados; gestionar turnos a nombre de terceros |
| Profesional odontológico | Organizar la agenda sin intervención manual | Reducir inasistencias; recibir métricas básicas de uso; sincronizar turnos con Google Calendar |
| Sistema (automático) | Gestionar el ciclo de vida completo de los turnos | Enviar recordatorios 24h antes; liberar reservas temporales vencidas; activar lista de espera ante cancelaciones |

## Alcance v1.0

- Solicitud, confirmación, cancelación y reprogramación de turnos vía bot de Telegram.
- Visualización de disponibilidad en tiempo real (fechas y horarios).
- Reserva temporal con expiración automática para evitar conflictos.
- Recordatorios automáticos 24 horas antes del turno con opciones de confirmar, cancelar o reprogramar.
- Lista de espera con notificación automática ante liberación de turnos.
- Integración con Google Calendar para sincronización de eventos.
- Registro y gestión de pacientes (nombre, apellido, DNI, teléfono).
- Panel básico para el profesional (turnos del día, métricas simples).
- Arquitectura SaaS orientada a un único profesional por instancia en esta versión.

## Fuera de alcance

- Aplicación móvil nativa independiente de Telegram.
- Integración con WhatsApp (se contempla como trabajo futuro).
- Sistema multi-profesional o multi-consultorio en v1.0.
- Integración con historias clínicas o sistemas de facturación.
- Procesamiento de lenguaje natural avanzado (flujos conversacionales rígidos en v1.0).
- Autenticación avanzada o protección de datos sensibles con cifrado end-to-end en v1.0.
- Escalabilidad a entornos hospitalarios de gran escala.

## Métricas de éxito

- Reducción de la tasa de inasistencias mediante recordatorios automáticos.
- Tiempo de respuesta del bot inferior a 2 segundos por interacción.
- Ocupación optimizada de la agenda gracias a la lista de espera y reprogramación.
- Satisfacción del profesional medida por reducción de carga administrativa.
