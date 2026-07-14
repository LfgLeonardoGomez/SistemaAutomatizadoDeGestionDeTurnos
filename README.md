<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Telegram_Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Bot" />
  <img src="https://img.shields.io/badge/n8n-EA4B71?style=for-the-badge&logo=n8n&logoColor=white" alt="n8n" />
</p>

# Sistema Automatizado de Gestión de Turnos

**Tesis de grado — Tecnicatura Universitaria en Programación**
**UTN — Facultad Regional Mendoza**

---

## Integrantes

| Nombre    | Apellido |
| --------- | -------- |
| Leonardo  | Gómez    |
| Fausto    | Chirino  |
| Sebastián | Sáez     |

---

## Descripción del Proyecto

Sistema SaaS **multi-tenant** de gestión de turnos pensado para consultorios odontológicos. Cada consultorio opera de forma independiente dentro de la misma plataforma, y sus pacientes pueden gestionar sus turnos de manera automatizada a través de un **bot de Telegram**: reservar, cancelar y reprogramar sin intervención manual del consultorio.

El proyecto integra:

- Backend en **FastAPI** con persistencia en **PostgreSQL**
- Bot de **Telegram** como canal principal de interacción con el paciente
- Automatización de flujos con **n8n**
- Arquitectura multi-tenant (múltiples consultorios sobre la misma base)

> Este proyecto sigue una metodología de **Spec-Driven Development**: las funcionalidades se especifican y documentan (ver carpeta `openspec/`) antes de implementarse.

---

## Estado actual

| Funcionalidad                                   | Estado           |
| ------------------------------------------------ | ---------------- |
| Login y registro (multi-tenant, por consultorio) | ✅ Funcional       |
| Bot de Telegram — reservar turno                 | ✅ Funcional       |
| Bot de Telegram — cancelar turno                 | ✅ Funcional       |
| Bot de Telegram — reprogramar turno              | ✅ Funcional       |
| Backend (lógica de negocio y persistencia)       | ✅ Funcional       |
| Integración con Google Calendar                  | 🚧 En desarrollo  |
| Panel/frontend de métricas y turnos del día      | ⏳ Pendiente       |

---

## Tecnologías

| Tecnología          | Uso                                              |
| -------------------- | ------------------------------------------------- |
| **Python**            | Lenguaje principal del backend                    |
| **FastAPI**            | Framework web para la API                         |
| **PostgreSQL**         | Base de datos relacional, esquema multi-tenant    |
| **Telegram Bot API**   | Canal de interacción con pacientes                |
| **n8n**                | Orquestación y automatización de flujos           |
| **Docker / Docker Compose** | Contenerización y levantado del entorno     |
| **Google Calendar API** | Sincronización de turnos (en desarrollo)        |

---

## Cómo levantar el proyecto

```bash
cp .env.example .env
```

Completar `.env` con las credenciales necesarias (base de datos, token del bot de Telegram, etc.).

```bash
docker-compose up --build
```

---

## Estructura del repositorio

```
├── backend/         # API y lógica de negocio (FastAPI + PostgreSQL)
├── docs/            # Documentación del proyecto
├── knowledge-base/  # Base de conocimiento del dominio
├── n8n-workflows/   # Flujos de automatización exportados
└── openspec/         # Especificaciones (Spec-Driven Development)
```

---

## Demo

> 📌 Video de demostración y capturas de pantalla — próximamente.
