# Front Cliente

## 1. Propósito

### Objetivo del sistema
Portal web para que los pacientes puedan gestionar sus turnos odontológicos sin necesidad de usar Telegram. Permite sacar turnos, consultar los propios, cancelar, reprogramar y anotarse en lista de espera.

### Alcance
- Sacar un turno: seleccionar fecha y horario disponible, ingresar datos personales, confirmar
- Consultar mis turnos próximos y anteriores
- Cancelar un turno confirmado
- Reprogramar un turno a otra fecha/hora
- Anotarse en lista de espera si no hay disponibilidad
- Ver historial de turnos anteriores
- Editar datos personales (nombre, teléfono)

### Fuera de alcance
- Autenticación con usuario y contraseña (el paciente se identifica por DNI al reservar)
- Notificaciones push en el navegador
- Chat en vivo con el profesional
- Pagos online
- Recetas o historias clínicas
- Multi-idioma

---

## 2. Usuario objetivo

### Paciente odontológico
Cualquier persona que quiera sacar un turno. No requiere registro previo con contraseña. Se identifica por DNI al momento de la reserva.

### Familiar / asistente (caso de uso RN-PA-03)
Persona que gestiona turnos para un tercero (ej: hijo, adulto mayor). Ingresa los datos del paciente real.

---

## 3. Personas

### Persona 1 — Paciente joven
25 años, usa el celular para todo. Quiere sacar un turno rápido sin llamar. Valora la velocidad y la interfaz mobile-first.

### Persona 2 — Adulto mayor
65 años, no usa Telegram. Un familiar le ayuda a sacar turnos o lo hace desde su computadora. Necesita tipografía grande, pasos claros y confirmación visual.

### Persona 3 — Paciente frecuente
Va al dentista cada 6 meses. Ya está registrado. Solo quiere ver disponibilidad, elegir horario y confirmar en 3 pasos. Valora la velocidad de re-reserva.

---

## 4. Principios UX

### Simplicidad
Máximo 4 pasos para sacar un turno. Sin jerga técnica. Cada paso es una pantalla con una sola decisión.

### Rapidez
Sin registro previo. El paciente ingresa datos solo al final del proceso de reserva. No hay validación de cuenta de email.

### Accesibilidad
Tipografía grande (16px+), contraste alto, labels visibles. Botones grandes fáciles de tocar en mobile.

### Confianza
Cada paso muestra feedback claro. Al confirmar el turno, mostrar resumen completo (fecha, hora, dirección del consultorio). Número de contacto visible.

### Mobile First
Diseñado para celular primero. Escritorio es adaptación. Touch targets de al menos 44px.

---

## 5. Mapa de funcionalidades

### Inicio

#### Objetivo
Pantalla principal donde el paciente puede acceder a las acciones principales: sacar turno, ver mis turnos, o identificarse.

#### Información mostrada
- Logo/nombre del consultorio
- Botones principales: "Sacar turno", "Mis turnos"
- Información de contacto del consultorio (opcional, desde configuración)

#### Acciones
- Ir al flujo de reserva
- Ir a "Mis turnos" (requiere identificación por DNI)

---

### Sacar turno

#### Objetivo
Flujo guiado de 4 pasos para reservar un turno.

#### Flujo
1. **Seleccionar fecha**: calendario visual con días disponibles marcados
2. **Seleccionar horario**: lista de slots libres para la fecha elegida
3. **Ingresar datos**: nombre, apellido, DNI, teléfono
4. **Confirmar**: resumen del turno + botón confirmar

#### Acciones
- Volver al paso anterior (fecha u horario)
- Confirmar turno

#### User Story
**US-001**: Como paciente, quiero solicitar un turno odontológico de forma rápida y sin necesidad de llamar por teléfono.
**US-011**: Como sistema, quiero registrar los datos del paciente al momento de la reserva.

#### Endpoints
`GET /turnos/disponibles?fecha=YYYY-MM-DD` — obtener slots libres.
`POST /turnos` — crear reserva temporal (body: `{ fecha, hora_inicio }`).
`PUT /turnos/{id}/confirmar` — confirmar con datos del paciente (body: `{ nombre, apellido, dni, telefono }`).

---

### Mis turnos

#### Objetivo
Ver todos los turnos del paciente (próximos y anteriores).

#### Información
- Turno próximo (CONFIRMADO o RESERVADO_TEMPORAL): destacado, con acciones disponibles
- Turnos anteriores: historial con estado (COMPLETADO, CANCELADO)
- Por cada turno: fecha, hora, estado, profesional

#### Acciones
- Cancelar turno (solo si está CONFIRMADO)
- Reprogramar turno (solo si está CONFIRMADO)
- Ver detalle

#### Endpoint
`GET /pacientes/{id}/turnos` — lista de turnos del paciente.

---

### Reprogramar turno

#### Objetivo
Cambiar la fecha y/o hora de un turno confirmado.

#### Restricciones
- Solo se puede reprogramar un turno CONFIRMADO
- Reprogramar = se cancela el turno anterior y se crea uno nuevo
- El horario anterior vuelve a estar disponible

#### Flujo
1. Paciente selecciona "Reprogramar" en su turno
2. Selecciona nueva fecha
3. Selecciona nuevo horario
4. Confirma reprogramación

#### User Story
**US-004**: Como paciente, quiero cambiar la fecha/hora de mi turno confirmado para ajustar la cita a mi disponibilidad.

#### Endpoint
`PUT /turnos/{id}/reprogramar` (body: `{ nueva_fecha, nueva_hora_inicio }`).

---

### Cancelar turno

#### Objetivo
Cancelar un turno confirmado.

#### Confirmaciones
- Mostrar confirmación explícita: "¿Estás seguro que querés cancelar tu turno del [fecha] a las [hora]?"
- Botones: "Sí, cancelar" / "No, mantener"
- Al cancelar: mostrar toast de confirmación y ofrecer sacar otro turno

#### User Story
**US-003**: Como paciente, quiero cancelar un turno previamente confirmado para liberar el horario.

#### Endpoint
`PUT /turnos/{id}/cancelar`.

---

### Lista de espera

#### Objetivo
Si no hay turnos disponibles para una fecha, el paciente puede anotarse para ser notificado cuando se libere un turno.

#### Funcionamiento
1. Si no hay disponibilidad, mostrar opción "Anotarme en lista de espera"
2. Paciente selecciona fecha de preferencia
3. Se registra en orden de llegada (FIFO)
4. Cuando se libera un turno, se notifica al primero de la lista (vía Telegram)
5. El paciente puede darse de baja en cualquier momento

#### User Story
**US-007**: Como paciente, quiero anotarme en lista de espera cuando no haya turnos disponibles para ser notificado si se libera un horario.

#### Endpoints
`POST /lista-espera` — body: `{ paciente_id, fecha_solicitada }`.
`DELETE /lista-espera/{id}` — salir de la lista.

---

### Perfil / Datos personales

#### Objetivo
Consultar y modificar los datos personales del paciente.

#### Datos editables
- Nombre, apellido (solo lectura después del primer registro)
- Teléfono (editable)
- DNI (solo lectura, se usa como identificador único)

#### Endpoint
`POST /pacientes` — si el DNI ya existe, retorna el paciente existente (auto-identificación).

---

### Historial

#### Objetivo
Ver todos los turnos del paciente, incluyendo los completados y cancelados.

#### Información disponible
- Lista cronológica de turnos
- Fecha, hora, estado, profesional
- Filtros: próximos / anteriores

#### User Story
Derivado de US-011: como paciente, quiero consultar mi historial de atención.

#### Endpoint
`GET /pacientes/{id}/turnos`.

---

### Notificaciones (no aplica en front web)

Las notificaciones son enviadas exclusivamente vía Telegram (recordatorios 24h antes, ofertas de lista de espera). El front web no tiene sistema de notificaciones push en v1/v2.

---

## 6. Estados del turno

| Estado | Visible para el paciente | Descripción |
|--------|-------------------------|-------------|
| DISPONIBLE | No (solo slots libres) | Slot libre |
| RESERVADO_TEMPORAL | Sí (como "en proceso") | Bloqueado durante la reserva, expira en minutos |
| CONFIRMADO | Sí (como "confirmado") | Turno confirmado, paciente asignado |
| CANCELADO | Sí (como "cancelado") | Turno cancelado |
| COMPLETADO | Sí (como "finalizado") | Paciente atendido |

---

## 7. Acciones permitidas según el estado

| Estado | Ver | Cancelar | Reprogramar |
|--------|-----|----------|-------------|
| RESERVADO_TEMPORAL | Sí | No | No |
| CONFIRMADO | Sí | Sí | Sí |
| CANCELADO | Sí (en historial) | — | — |
| COMPLETADO | Sí (en historial) | — | — |

---

## 8. Flujos principales

### Inicio (sin identificación)
1. Paciente llega a la página
2. Ve dos opciones: "Sacar turno" o "Mis turnos"
3. "Sacar turno" → flujo de reserva (no requiere identificación previa)
4. "Mis turnos" → solicitar DNI → cargar turnos del paciente

### Reserva de turno
1. Paciente selecciona "Sacar turno"
2. Front llama a `GET /turnos/disponibles?fecha=YYYY-MM-DD` para la fecha seleccionada
3. Muestra slots disponibles
4. Paciente selecciona horario → `POST /turnos` (body: `{ fecha, hora_inicio }`)
5. Backend crea turno en estado RESERVADO_TEMPORAL (expira en N minutos)
6. Front pasa a paso "Datos del paciente"
7. Paciente ingresa nombre, apellido, DNI, teléfono
8. `PUT /turnos/{id}/confirmar` (body: datos del paciente)
9. Backend registra/identifica paciente, confirma turno, crea evento en Google Calendar
10. Front muestra pantalla de éxito con resumen del turno

### Reprogramación
1. Paciente va a "Mis turnos" → se identifica por DNI
2. Ve su turno CONFIRMADO → selecciona "Reprogramar"
3. Selecciona nueva fecha → `GET /turnos/disponibles`
4. Selecciona nuevo horario
5. Confirma → `PUT /turnos/{id}/reprogramar`
6. Front muestra confirmación

### Cancelación
1. Paciente va a "Mis turnos" → se identifica por DNI
2. Selecciona "Cancelar" en su turno CONFIRMADO
3. ConfirmDialog: "¿Estás seguro?"
4. Confirma → `PUT /turnos/{id}/cancelar`
5. Front muestra toast + opción de sacar otro turno

### Lista de espera
1. Paciente intenta sacar turno pero no hay disponibilidad
2. Front muestra opción "Anotarme en lista de espera"
3. Paciente selecciona fecha → `POST /lista-espera`
4. Confirmación: "Te vamos a avisar si se libera un turno"

Referencia: `knowledge-base/07_flujos_principales.md`

---

## 9. Reglas de negocio aplicables

| Código | Regla | Impacto en Front Cliente |
|--------|-------|--------------------------|
| RN-TU-01 | Un paciente solo puede tener un turno activo | Mostrar error si intenta reservar teniendo ya un turno CONFIRMADO. Ofrecer reprogramar |
| RN-TU-03 | Reserva temporal expira automáticamente | Mostrar cuenta regresiva si es posible. Si expira, notificar y volver a disponibilidad |
| RN-TU-04 | Cancelación libera el horario | Al cancelar, ofrecer sacar otro turno |
| RN-TU-05 | Reprogramar = cancelar + nuevo | El front debe mostrar los dos pasos (seleccionar nuevo horario + confirmar) |
| RN-TU-06 | Disponibilidad = slots posibles MINUS ocupados | El front muestra solo lo que devuelve la API |
| RN-PA-01 | DNI único | Si el paciente ya existe, se identifican automáticamente (no preguntar datos de nuevo) |

---

## 10. Restricciones funcionales

- **Sin autenticación tradicional**: el paciente no tiene email/password. Se identifica por DNI al consultar sus turnos
- **Una sesión por vez**: si un paciente abre la reserva en dos pestañas, puede haber conflictos. No hay bloqueo de sesión
- **Reserva temporal frágil**: si el paciente cierra el navegador durante el paso 3 (datos del paciente), la reserva temporal expirará sola. Debe empezar de nuevo
- **Lista de espera**: la notificación del turno liberado se envía SOLO por Telegram. Si el paciente no tiene Telegram, no podrá recibir la oferta

---

## 11. Objetivos no funcionales

- **Performance**: carga inicial < 2s. Cada paso de reserva debe sentirse instantáneo
- **Responsive**: mobile-first. Diseñado para 360px+. Escritorio es adaptación
- **Accesibilidad**: contraste WCAG AA, labels en todos los inputs, navegación por teclado, touch targets >= 44px
- **Seguridad**: el DNI se envía en el body de requests HTTPS. No almacenar DNI en localStorage
- **Offline graceful**: si hay error de conexión, mostrar mensaje claro y botón reintentar. No perder datos del paso actual
