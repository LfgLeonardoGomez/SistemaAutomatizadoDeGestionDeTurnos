# Preguntas Abiertas

## Inconsistencias detectadas

### IN-01 — Tiempo de expiración de reserva temporal
**Documento A dice**: En el caso de prueba 2 (Expiración de reserva temporal) se mencionan "2 minutos" como tiempo límite.
**Documento B dice**: En la descripción de la reserva temporal (sección 4.4.1, RF 4) no se especifica el tiempo exacto, solo que "libera automáticamente si no se confirma en el tiempo definido".
**Impacto**: El valor de 2 minutos puede ser solo ilustrativo para el caso de prueba. Si se implementa en producción como 2 minutos, puede generar frustración en usuarios reales.
**Resolución propuesta**: Definir el tiempo de expiración como una variable de entorno configurable (`RESERVA_TEMPORAL_MINUTOS`) con un valor por defecto razonable (ej. 5 o 10 minutos), y documentar explícitamente el valor elegido para casos de prueba vs. producción.

### IN-02 — Lista de espera: modelo de datos no detallado
**Documento A dice**: En los requerimientos funcionales (RF 8) se describe la lista de espera con notificación automática y asignación de turnos liberados.
**Documento B dice**: En el modelo ER (sección 4.1) no aparece la entidad ListaDeEspera ni sus atributos.
**Impacto**: Falta definición formal de la entidad, lo que puede generar ambigüedad en la implementación.
**Resolución propuesta**: Agregar la entidad `ListaDeEspera` al modelo ER con atributos mínimos: `id`, `paciente_id`, `fecha_solicitada`, `creado_en`, `notificado`.

### IN-03 — Panel del profesional: ¿existe o no?
**Documento A dice**: En los requerimientos funcionales (RF 7) se menciona "permitir al profesional consultar los turnos programados para el día" y "generar métricas básicas".
**Documento B dice**: En la arquitectura (sección 4.3) no se describe ningún componente de panel web ni frontend para el profesional.
**Impacto**: No está claro si el profesional accede a esta información vía Telegram, una web, o directamente a la base de datos.
**Resolución propuesta**: Definir si en v1.0 el profesional opera vía comandos de Telegram (ej. /turnos_hoy) o si se requiere un panel web mínimo. Se recomienda comandos de Telegram para reducir scope en v1.0.

## Preguntas abiertas (priorizadas)

| Prioridad | Pregunta | Bloquea | Decisor |
|-----------|----------|---------|---------|
| Alta | ¿Cuál es el tiempo definitivo de expiración de reserva temporal para producción? | Sprint 1 | Equipo / Product Owner |
| Alta | ¿El profesional gestionará su agenda solo por Telegram o se requiere panel web en v1.0? | Sprint 1 | Director del proyecto |
| Media | ¿Cómo se maneja la concurrencia si dos pacientes intentan reservar el mismo horario simultáneamente? | Sprint 2 | Equipo técnico |
| Media | ¿Se requiere autenticación o autorización formal para el panel del profesional en v1.0? | Sprint 2 | Director del proyecto |
| Media | ¿Cuál es la estrategia de backup y recuperación de la base de datos? | Sprint 3 | Equipo técnico |
| Baja | ¿Se contempla internacionalización (idiomas) para futuras versiones? | Lanzamiento | Product Owner |
| Baja | ¿Es necesario un sistema de logs y monitoreo desde v1.0 o se posterga? | Sprint 3 | Equipo técnico |
| Baja | [DISCOVERY] `scale` could not be inferred with confidence from the source docs. Please confirm: ¿El sistema en v1.0 es estrictamente single-tenant single-user, o ya se diseña con multi-tenancy en mente? | Sprint 1 | Director del proyecto |

> **Nota sobre discovery**: El documento fuente menciona orientación a "un solo profesional" en v1.0 pero describe el modelo como SaaS, lo que sugiere potencial multi-tenant a futuro. Se registró el scale como `single_user (inferred, low confidence — SaaS potential)`.
