# Tesis-N8N-turnos — Base de Conocimiento

Base de conocimiento generada a partir del documento fuente `docs/Cuarta iteracion.docx`.

## Indice de Archivos

| Archivo | Contenido |
|---------|-----------|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Proposito, objetivos por actor, alcance v1.0, fuera de alcance, metricas de exito |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack tecnologico, arquitectura general, integraciones externas, API REST |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores del sistema, matriz RBAC, rutas publicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Dominios, ERD, entidades (Paciente, Profesional, Turno, ReservaTemporal, ListaDeEspera), seed data |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | Reglas codificadas por dominio: Turnos, Pacientes, Recordatorios, Lista de Espera, Excepciones globales |
| [06_funcionalidades.md](06_funcionalidades.md) | Historias de usuario organizadas por epica (Reserva, Gestion, Comunicaciones, Lista de espera, Metricas, Pacientes) |
| [07_flujos_principales.md](07_flujos_principales.md) | Flujos e2e: Reserva, Cancelacion, Reprogramacion, Recordatorio, Lista de espera |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones aplicados, estructura de directorios, seguridad, variables de entorno |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | Decisiones de diseno documentadas (n8n, Google Calendar, Telegram, PostgreSQL, FastAPI) y supuestos inferidos |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | Inconsistencias detectadas y preguntas abiertas priorizadas |

## Quick Start para Desarrolladores

1. Entender el dominio → [01](01_vision_y_objetivos.md), [03](03_actores_y_roles.md)
2. Entender los datos → [04](04_modelo_de_datos.md)
3. Entender las reglas → [05](05_reglas_de_negocio.md)
4. Entender la arquitectura → [02](02_descripcion_general.md), [08](08_arquitectura_propuesta.md)
5. Implementar → [07](07_flujos_principales.md), [06](06_funcionalidades.md)
6. Antes de codificar → [10](10_preguntas_abiertas.md)

## Resumen Ejecutivo

Sistema SaaS para automatizar la gestion de turnos odontologicos mediante un bot de Telegram, backend FastAPI, base PostgreSQL y sincronizacion con Google Calendar. Incluye reservas temporales, recordatorios automaticos y lista de espera. Orientado a un unico profesional en v1.0.
