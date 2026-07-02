# Front Profesional

## 1. Propósito

### Objetivo del sistema
Panel web para que el profesional odontológico gestione su consultorio: visualizar la agenda del día, administrar turnos, configurar horarios de atención, consultar métricas y gestionar integraciones con Telegram y Google Calendar.

### Alcance
- Visualizar turnos del día (confirmados) con datos del paciente
- Gestionar turnos: completar, cancelar, ver disponibilidad por fecha
- Configurar horarios: inicio, fin, días de atención, duración del turno
- Consultar métricas: turnos hoy, tasa de confirmación y cancelación (30 días)
- Ver listado de pacientes con historial de turnos
- Gestionar integraciones: token de Telegram bot, refresh token de Google Calendar
- Autenticación vía JWT (email + password)

### Fuera de alcance
- Procesar pagos
- Emitir recetas o historias clínicas
- Editar reglas de negocio del sistema
- Ejecutar procesos automáticos (recordatorios, liberación de reservas)
- Multi-consultorio en la misma sesión

---

## 2. Usuario objetivo

### Profesional odontológico (único rol)
Dueño del consultorio. Accede al panel para administrar su agenda. Se autentica con email + password (JWT).

No existen roles de recepcionista, asistente ni administrador del consultorio. En v2.0 existe un Super Admin (operador del SaaS) con endpoints separados para crear profesionales, listarlos, activarlos/desactivarlos y ver métricas globales — pero ese es otro frontend/módulo.

---

## 3. Personas

### Persona 1 — Dr. García
Odontólogo general, 45 años. Usa la PC del consultorio. Quiere ver rápidamente los turnos del día al llegar y marcar como completados. Revisa métricas una vez por semana para evaluar ocupación.

### Persona 2 — Dra. Martínez
Odontóloga, 35 años. Gestiona su agenda desde una tablet entre pacientes. Necesita poder cancelar turnos y ver el historial de pacientes rápidamente. Configuró su horario una vez y rara vez lo modifica.

---

## 4. Principios UX

### Simplicidad
La pantalla principal debe mostrar la información más importante del día sin interacciones innecesarias. Máximo 2 clics para cualquier acción crítica.

### Rapidez
Carga inicial < 2 segundos. Las operaciones (completar, cancelar) deben ser instantáneas con feedback visual optimista.

### Consistencia
Mismos patrones de interacción en todas las listas (turnos, pacientes). Misma estructura de formularios.

### Feedback
Toda acción debe mostrar confirmación visual (toast). Errores del backend deben mostrar mensajes legibles, no códigos crudos.

---

## 5. Mapa de funcionalidades

### Dashboard (turnos del día)

#### Objetivo
Mostrar al profesional los turnos confirmados del día actual al llegar al consultorio.

#### Información mostrada
- Lista de turnos ordenada por hora
- Por cada turno: hora de inicio/fin, nombre y apellido del paciente
- Indicador visual del estado (CONFIRMADO, COMPLETADO, CANCELADO)
- Contador de turnos del día (arriba)

#### Acciones disponibles
- Completar turno (pasa a COMPLETADO)
- Cancelar turno (pasa a CANCELADO, libera el slot)
- Ver detalle del paciente (redirige a perfil)

#### User Story
**US-005**: Como profesional, quiero ver los turnos programados para el día actual para organizar mi agenda de atención.

#### Endpoint
`GET /profesional/turnos-hoy` — lista turnos CONFIRMADO del día con datos del paciente.
`PUT /turnos/{id}/completar` — marca turno como COMPLETADO.
`PUT /turnos/{id}/cancelar` — cancela turno confirmado.

---

### Calendario / Agenda

#### Objetivo
Visualizar y gestionar turnos en un rango de fechas (no solo hoy). Crear turnos manualmente.

#### Información mostrada
- Calendario mensual con indicadores de días con turnos
- Al seleccionar un día: lista de turnos (todos los estados)
- Slots disponibles y ocupados

#### Acciones
- Ver disponibilidad de una fecha
- Crear turno manualmente (seleccionar slot + paciente)
- Cancelar / reprogramar turno
- Filtrar por estado

#### User Story
**US-001** (lado profesional): Como profesional, quiero ver la disponibilidad de cualquier fecha y poder agendar pacientes directamente.

#### Endpoints
`GET /turnos/disponibles?fecha=YYYY-MM-DD` — slots libres y ocupados.
`POST /turnos` — crear reserva temporal (asociada a paciente).
`PUT /turnos/{id}/confirmar` — confirmar turno.
`PUT /turnos/{id}/cancelar` — cancelar turno.
`PUT /turnos/{id}/reprogramar` — reprogramar turno.

---

### Gestión de Pacientes

#### Objetivo
Consultar datos de pacientes registrados y su historial de turnos.

#### Información mostrada
- Listado de pacientes con búsqueda por nombre o DNI
- Perfil del paciente: nombre, apellido, DNI, teléfono
- Historial de turnos (fecha, hora, estado)
- Última atención (último turno COMPLETADO)

#### Acciones
- Buscar paciente por nombre/apellido/DNI
- Ver perfil completo con historial
- Ver detalle de turnos pasados (COMPLETADOS, CANCELADOS)

#### User Story
**US-011**: Como profesional, quiero consultar los datos de un paciente y ver su historial de atención.

#### Endpoints
`GET /pacientes/{id}` — datos del paciente + historial de turnos.
`GET /pacientes/{id}/turnos` — lista de turnos del paciente.

---

### Configuración

#### Objetivo
Definir los parámetros de atención del consultorio para que el sistema calcule correctamente la disponibilidad.

#### Secciones
- **Horario de atención**: hora de inicio y fin (formato HH:MM)
- **Días de atención**: selección de días de la semana (Lunes a Sábado)
- **Duración del turno**: minutos por turno (ej: 30)
- **Especialidad**: descripción textual

#### User Story
**US-010**: Como profesional, quiero definir mis días y horarios de atención para que el sistema calcule correctamente la disponibilidad.

#### Endpoints
`GET /profesional/configuracion` — obtener configuración actual.
`PUT /profesional/configuracion` — actualizar configuración.

---

### Métricas

#### Objetivo
Evaluar el uso y la eficiencia de la agenda en los últimos 30 días.

#### Indicadores
- **Turnos hoy**: número de turnos CONFIRMADOS para el día actual
- **Tasa de confirmación (30d)**: proporción de turnos CONFIRMADO sobre el total creados
- **Tasa de cancelación (30d)**: proporción de turnos CANCELADO sobre el total creados

#### Filtros
- Período fijo de 30 días (no configurable en v1/v2)
- Los datos se actualizan en cada request (no hay caché)

#### User Story
**US-009**: Como profesional, quiero consultar métricas simples del sistema para evaluar el uso y la eficiencia de la agenda.

#### Endpoint
`GET /profesional/metricas` — turnos_hoy, tasa_confirmacion_30d, tasa_cancelacion_30d.

---

### Integraciones

#### Objetivo
Configurar los tokens de conexión con servicios externos (Telegram y Google Calendar).

#### Plataformas
- **Telegram**: Token del bot de Telegram (se genera desde @BotFather)
- **Google Calendar**: Refresh token OAuth 2.0 para sincronizar turnos
- **Calendar ID**: ID del calendario de Google (default: "primary")

#### Acciones
- Ver estado actual de cada integración (conectado/desconectado)
- Actualizar token de Telegram
- Actualizar refresh token de Google
- Cambiar Calendar ID

#### Endpoints
`GET /profesional/integraciones` — devuelve has_telegram, has_google, google_calendar_id.
`PUT /profesional/integraciones` — actualiza tokens (requiere HTTPS).

---

## 6. Estados del turno

| Estado | Descripción | Visible en Front Profesional |
|--------|-------------|----------------------|
| DISPONIBLE | Slot libre, sin paciente asignado | En agenda/calendario |
| RESERVADO_TEMPORAL | Bloqueado durante el proceso de reserva (expira en N minutos) | En agenda, como ocupado |
| CONFIRMADO | Turno confirmado con paciente asignado | Dashboard de hoy, agenda |
| CANCELADO | Turno cancelado por paciente o profesional | Solo en historial |
| COMPLETADO | Paciente atendido | Dashboard, historial |

---

## 7. Acciones permitidas según el estado

| Estado | Ver | Cancelar | Completar | Reprogramar |
|--------|-----|----------|-----------|-------------|
| DISPONIBLE | Sí | — | — | — |
| RESERVADO_TEMPORAL | Sí | — | — | — |
| CONFIRMADO | Sí | Sí | Sí | Sí |
| CANCELADO | Sí | — | — | — |
| COMPLETADO | Sí | — | — | — |

---

## 8. Flujos principales

### Inicio de sesión
1. Profesional ingresa email + password
2. Backend valida credenciales, devuelve JWT (access_token)
3. Front almacena token (localStorage/sessionStorage)
4. Cada request subsiguiente incluye `Authorization: Bearer <token>`
5. Si el token expira (1440 min default), redirigir a login

### Dashboard diario
1. Profesional inicia sesión → redirigir a dashboard
2. Front llama a `GET /profesional/turnos-hoy`
3. Muestra lista de turnos ordenada por hora
4. Al completar un turno: `PUT /turnos/{id}/completar` → feedback visual
5. Al cancelar: `PUT /turnos/{id}/cancelar` → confirmación previa

### Gestión de turnos (agenda)
1. Profesional selecciona fecha en el calendario
2. Front llama a `GET /turnos/disponibles?fecha=YYYY-MM-DD`
3. Muestra slots: verdes (disponibles), grises (ocupados), rojos (cancelados)
4. Para crear turno: seleccionar slot → buscar paciente → `POST /turnos` → `PUT /turnos/{id}/confirmar`
5. Para cancelar/reprogramar: seleccionar turno → acción correspondiente

### Atención del paciente
1. Profesional ve el turno en dashboard
2. Atiende al paciente
3. Marca como completado: `PUT /turnos/{id}/completar`
4. Si el paciente no asiste: cancela el turno

### Configuración
1. Profesional navega a Configuración
2. Front carga datos con `GET /profesional/configuracion`
3. Modifica campos, envía con `PUT /profesional/configuracion`
4. Validación: horario_inicio < horario_fin, duración > 0, al menos 1 día de atención

Referencia completa: `knowledge-base/07_flujos_principales.md`

---

## 9. Reglas de negocio aplicables

| Código | Regla | Impacto en Front Profesional |
|--------|-------|----------------------|
| RN-TU-01 | Un paciente solo puede tener un turno activo a la vez | Mostrar warning si el paciente ya tiene turno activo |
| RN-TU-02 | Turnos COMPLETADO forman el historial | Mostrar en perfil del paciente |
| RN-TU-03 | Reserva temporal expira automáticamente | Los slots RESERVADO_TEMPORAL se liberan solos |
| RN-TU-04 | Cancelación libera el horario | Al cancelar, el slot vuelve a disponible |
| RN-TU-06 | Disponibilidad = slots posibles MINUS ocupados | El front muestra solo lo que devuelve la API |
| RN-TU-07 | Al confirmar, se crea evento en Google Calendar | Transparente para el front |
| RN-TU-08 | Al cancelar, se elimina evento de Google Calendar | Transparente para el front |

---

## 10. Restricciones funcionales

- El profesional solo ve información de su propio consultorio (scoping por `profesional_id` del JWT)
- No pueden existir dos sesiones con el mismo email simultáneamente (el backend no lo impide, pero el front debe evitar duplicados de estado)
- Las modificaciones requieren autenticación válida (JWT no expirado)
- Las integraciones (Telegram, Google) solo se pueden actualizar vía HTTPS

---

## 11. Objetivos no funcionales

- **Performance**: carga inicial < 2 segundos. Tiempo de respuesta de acciones < 500ms percibidos
- **Responsive**: escritorio prioritario (1280px+), tablet aceptable (768px+). No requiere mobile-first
- **Accesibilidad**: contraste suficiente, navegación por teclado en formularios, labels en inputs
- **Seguridad**: JWT en header HTTP (no en URL), logout elimina token local, no almacenar tokens sensibles del profesional (refresh tokens de Google) en localStorage
- **Feedback visual**: toda acción (completar, cancelar, guardar) debe mostrar toast de éxito/error. Loader/skeleton durante llamadas HTTP. No bloquear toda la interfaz durante requests
