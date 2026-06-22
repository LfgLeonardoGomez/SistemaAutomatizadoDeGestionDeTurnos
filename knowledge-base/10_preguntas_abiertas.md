# Preguntas Abiertas

## Inconsistencias detectadas

### IN-01 — Tiempo de expiración de reserva temporal ✅ RESUELTO
**Documento A dice**: En el caso de prueba 2 (Expiración de reserva temporal) se mencionan "2 minutos" como tiempo límite.
**Documento B dice**: En la descripción de la reserva temporal (sección 4.4.1, RF 4) no se especifica el tiempo exacto, solo que "libera automáticamente si no se confirma en el tiempo definido".
**Impacto**: El valor de 2 minutos puede ser solo ilustrativo para el caso de prueba. Si se implementa en producción como 2 minutos, puede generar frustración en usuarios reales.
**Resolución aplicada**: El tiempo de expiración se implementó como variable de entorno `RESERVA_TEMPORAL_MINUTOS` con valor por defecto de **10 minutos** en producción [code · config.py:21]. Los tests usan valores arbitrarios (ej. settings de test) para no depender del default.

### IN-02 — Lista de espera: modelo de datos no detallado ✅ RESUELTO
**Documento A dice**: En los requerimientos funcionales (RF 8) se describe la lista de espera con notificación automática y asignación de turnos liberados.
**Documento B dice**: En el modelo ER (sección 4.1) no aparece la entidad ListaDeEspera ni sus atributos.
**Impacto**: Falta definición formal de la entidad, lo que puede generar ambigüedad en la implementación.
**Resolución aplicada**: La entidad `ListaDeEspera` fue implementada con atributos extendidos: `id`, `paciente_id`, `fecha_solicitada`, `creado_en`, `notificado`, `turno_ofrecido_id`, `notificado_en`, `telegram_chat_id` [code · models/lista_de_espera.py]. Ver detalle actualizado en [04_modelo_de_datos.md](04_modelo_de_datos.md).

### IN-03 — Panel del profesional: ¿existe o no? ✅ RESUELTO
**Documento A dice**: En los requerimientos funcionales (RF 7) se menciona "permitir al profesional consultar los turnos programados para el día" y "generar métricas básicas".
**Documento B dice**: En la arquitectura (sección 4.3) no se describe ningún componente de panel web ni frontend para el profesional.
**Impacto**: No está claro si el profesional accede a esta información vía Telegram, una web, o directamente a la base de datos.
**Resolución aplicada**: En v1.0 el profesional opera **exclusivamente vía comandos de Telegram**: `/turnos_hoy`, `/metricas`, `/configurar` [code · telegram_service.py:835-848]. Los endpoints REST subyacentes (`GET /profesional/turnos-hoy`, `GET /profesional/metricas`, `PUT /profesional/configuracion`) también existen para uso directo o vía n8n [code · routers/profesional.py].

## Preguntas abiertas (priorizadas)

| Prioridad | Pregunta | Estado | Evidencia |
|-----------|----------|--------|-----------|
| Alta | ¿Cuál es el tiempo definitivo de expiración de reserva temporal para producción? | ✅ Resuelto | `RESERVA_TEMPORAL_MINUTOS=10` por defecto, configurable [code · config.py:21] |
| Alta | ¿El profesional gestionará su agenda solo por Telegram o se requiere panel web en v1.0? | ✅ Resuelto | Solo Telegram: `/turnos_hoy`, `/metricas`, `/configurar` [code · telegram_service.py:835-848] |
| Media | ¿Cómo se maneja la concurrencia si dos pacientes intentan reservar el mismo horario simultáneamente? | ✅ Resuelto | `SELECT FOR UPDATE` sobre turnos de la fecha [code · turno_service.py:81-85] |
| Media | ¿Se requiere autenticación o autorización formal para el panel del profesional en v1.0? | ✅ Resuelto | No hay auth formal en v1.0; acceso por canal (Telegram chat_id) o red interna [doc · 03_actores_y_roles.md] |
| Media | ¿Cuál es la estrategia de backup y recuperación de la base de datos? | 🔲 Abierta | Pendiente de definir política de backups de PostgreSQL |
| Baja | ¿Se contempla internacionalización (idiomas) para futuras versiones? | 🔲 Abierta | Solo español en v1.0; no hay infra de i18n |
| Baja | ¿Es necesario un sistema de logs y monitoreo desde v1.0 o se posterga? | ⚠️ Parcial | Logging estructurado implementado; falta monitoreo/alerting (Prometheus/Grafana) |
| Alta | ¿El sistema en v1.0 es estrictamente single-tenant single-user, o ya se diseña con multi-tenancy en mente? | 🔄 **DECISIÓN CAMBIADA** | Se optó por **single-tenant por instancia** en v1.0 por simplicidad, pero el modelo de negocio real requiere **multi-tenant por profesional en una sola instancia**. Pendiente de implementar en v2.0 (change C-14 o fase nueva). Ver `NEXT_SESSION.md` para contexto completo. |

> **Nota sobre discovery**: El documento fuente menciona orientación a "un solo profesional" en v1.0 pero describe el modelo como SaaS, lo que sugiere potencial multi-tenant a futuro. Se registró el scale como `single_user (inferred, low confidence — SaaS potential)`.
