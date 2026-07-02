# Diseño UX/UI — Front Profesional

## Sistema de Diseño

El sistema está diseñado para un entorno de gestión dental, priorizando "Claridad Clínica" a través de una estética Corporativa/Moderna equilibrada.

El usuario target es el **profesional odontológico** que gestiona su consultorio: agenda, turnos, pacientes, configuración, métricas e integraciones.

### Colores

Paleta anclada en Teal profundo como color primario, por su asociación con higiene y profesionalismo clínico.

| Token | Hex | Uso |
|-------|-----|-----|
| `primary` | `#00614f` | Acciones principales, estados activos |
| `primary-container` | `#0d7c66` | Botones primarios, fondos de acento |
| `on-primary-container` | `#bbffe9` | Texto sobre primary-container |
| `secondary` | `#44655b` | Elementos secundarios |
| `error` | `#ba1a1a` | Errores, cancelar, alertas |
| `error-container` | `#ffdad6` | Fondo mensajes error |
| `background` | `#f6faf7` | Fondo general |
| `surface-container-lowest` | `#ffffff` | Tarjetas |
| `outline` | `#6e7a75` | Bordes |
| `outline-variant` | `#bdc9c4` | Bordes suaves |

**Colores semánticos**: Verde (`#22C55E`) éxito/completado, Rojo (`#EF4444`) cancelado/peligro, Azul (`#3B82F6`) CONFIRMADO.

### Tipografía

Familia: **Inter** — utilitaria, excelente rendimiento en tamaños pequeños (crítico para tablas de horarios).

| Level | Size | Weight | Line Height |
|-------|------|--------|-------------|
| `display-lg` | 36px | 700 | 44px |
| `headline-lg` | 28px | 600 | 36px |
| `headline-md` | 24px | 600 | 32px |
| `headline-sm` | 20px | 600 | 28px |
| `title-lg` | 18px | 600 | 26px |
| `body-lg` | 16px | 400 | 24px |
| `body-md` | 14px | 400 | 20px |
| `label-md` | 12px | 500 | 16px |
| `label-sm` | 11px | 600 | 14px |

### Layout & Spacing

- **Sidebar**: fija 240px. Contenido fluido.
- **Base rítmica**: 8px. Gutter 16px. Margen página 24px.
- **Breakpoints**: Mobile (<768px), Tablet (768-1280px), Desktop (>1280px).

### Elevation & Depth

- **Sombras**: `0 2px 4px rgba(31, 41, 55, 0.05)`.
- **Active States**: borde 2px primary en foco.

### Shapes

- **Estándar (8px)**: Cards, botones, inputs.
- **Large (16px)**: Modales y paneles.
- **Pill**: Status Chips.

### Componentes Globales

- **Botones**: Primarios sólidos Teal (#0D7C66) con texto blanco; secundarios outline.
- **Input Fields**: Borde 1px, focus → primary + glow.
- **Status Chips**: Pill-shaped, fondo semitransparente.
- **Cards**: Fondo blanco, 8px radius, shadow-sm.

---

## Pantallas del Profesional

---

### 1. Login — `profesional_login/`

**Layout**: Dos columnas — 1100px max-width, centrado vertical y horizontalmente.

#### Columna Izquierda (Branding) — Visible solo en desktop
- Fondo: `primary-container` (#0d7c66) con patrón decorativo SVG
- Logo: ícono `medical_services` + "Sistema de Gestión de Turnos"
- Tagline: "Panel del Profesional" en `display-lg`

#### Columna Derecha (Formulario)
- Header: "Bienvenido" (`headline-lg`) + "Panel del Profesional"
- **Estado de Error (cuenta desactivada)**: Alert box con icono `error`, "Tu cuenta está desactivada. Comunicate con el administrador." Fondo `error-container`, efecto shake.
- **Campo Email**: Ícono `mail`, placeholder `dr@consultorio.com`
- **Campo Contraseña**: Ícono `lock`, toggle visibilidad
- **Botón Submit**: Full-width, `primary-container`, "Iniciar Sesión"
- **Footer**: Copyright

**Nota**: No hay "Recordar sesión por 30 días". El JWT expira en 24h y no hay refresh token.

---

### 2. Dashboard de Turnos (Home) — `profesional_dashboard_de_turnos/`

**Layout**: Sidebar 240px + TopAppBar + Contenido principal.

#### Sidebar (240px)
- Logo: "SG Turnos" (`headline-sm`, bold, `primary`)
- Nav items con iconos:
  - Dashboard (activo, borde izquierdo primary)
  - Agenda (calendario)
  - Pacientes (personas)
  - Configuración (engranaje)
  - Métricas (gráfico)
  - Integraciones (plug)
- Perfil al pie: avatar + nombre del profesional + especialidad

#### TopAppBar
- Título: "Panel del Profesional"
- Botón logout (icono `exit_to_app`)

#### Contenido — Turnos de Hoy
- **Header**: "Turnos de hoy" (`headline-lg`) + fecha + badge "5 turnos"
- **CTA**: Botón "Nuevo Turno" navega a `/agenda`

**Lista de Turnos** (col-span-12):
Cada turno es una card con borde izquierdo de 4px codificado por estado:

| Paciente | Hora | Estado | Borde |
|----------|------|--------|-------|
| Ricardo Mendoza | 09:00–09:30 | CONFIRMADO (azul) | `primary` |
| Lucía Ferreyra | 10:15–11:00 | CONFIRMADO (azul) | `primary` |
| Marcos Paz | 08:00–08:30 | COMPLETADO (verde) | `#22C55E` |
| Elena Soler | 12:30–13:00 | CANCELADO (rojo) | `#EF4444` |

Cada card tiene acciones contextuales según estado:
- CONFIRMADO: botones "Completar" (verde) + "Cancelar" (rojo outline)
- COMPLETADO: solo visual, sin acciones
- CANCELADO: solo visual, texto tachado

**Nota**: No hay campo "tratamiento" en los turnos. La información es hora, paciente y estado. No existe el estado "EN CONSULTA" — los estados reales son DISPONIBLE, RESERVADO_TEMPORAL, CONFIRMADO, CANCELADO, COMPLETADO.

**Empty State**: "No tenés turnos programados para hoy" + ilustración.

---

### 3. Agenda y Calendario — `profesional_agenda_y_calendario/`

**Layout**: Sidebar 240px + contenido.

#### Sidebar
- Item "Agenda" activo con borde izquierdo primary.

#### Contenido

**Panel Izquierdo — Calendario Mensual** (col-span-4/5):
- Header: mes + año + chevron navigation
- Grid 7 columnas (Lu–Sa)
- Días con turnos: dot azul debajo del número
- Día seleccionado: fondo `primary-container`

**Panel Derecho — Slots del día** (col-span-7/8):
- Header: "Miércoles, 4 de Octubre" + resumen "3 slots ocupados • 4 disponibles"

**Estados de Slots**:

| Tipo | Visual | Acción |
|------|--------|--------|
| **Occupied** | Borde sólido, fondo `surface-container-low`, barra izquierda `primary` | Solo visual (tiene paciente asignado) |
| **Available** | Borde dashed 2px, hover → borde primary | Botón "+ Agendar" |
| **Cancelled** | Opacidad 70%, texto tachado, barra `error` | Solo visual |

**Nota**: No hay "Break Time" ni bloques de descanso. El backend no soporta ese concepto. Los slots son simplemente disponibles (verdes) u ocupados (grises). Si se necesita break time, debe implementarse en el backend primero.

**Modal Agendar Turno**:
1. Seleccionar slot disponible
2. Buscar paciente existente por DNI (`POST /pacientes`) o crear nuevo
3. `POST /turnos` con `{ fecha, hora_inicio, paciente_id }` → crea RESERVADO_TEMPORAL
4. `PUT /turnos/{id}/confirmar` con datos del paciente → CONFIRMADO

---

### 4. Pacientes — `profesional_pacientes/`

**Layout**: Sidebar 240px + contenido.

**⚠️ Limitación actual**: No existe endpoint de listado/búsqueda de pacientes. Solo está disponible `GET /pacientes/{id}` (obtener por ID) y `POST /pacientes` (crear o recuperar por DNI). La pantalla de pacientes requiere un endpoint `GET /pacientes?search=` que debe implementarse en el backend.

#### Diseño propuesto (requiere endpoint nuevo)

**Search Bar**: Input con ícono `search`, placeholder "Buscar por nombre, apellido o DNI...".

**Resultados**: Lista de pacientes con:
- Nombre completo + DNI
- Teléfono
- Botón "Ver perfil"

**Perfil del paciente**:
- Datos: nombre, apellido, DNI, teléfono
- Historial de turnos: lista cronológica inversa con fecha, hora, estado (badge coloreado)

**Nota**: No hay grid con paginación ni tarjetas con última cita o tratamiento — esos datos no existen en el backend actual.

---

### 5. Configuración — `profesional_configuracion/`

**Propósito**: Definir parámetros de atención del consultorio.

**Formulario** (tarjeta blanca):
- "Hora de inicio" — input HH:MM (placeholder `08:00`)
- "Hora de fin" — input HH:MM (placeholder `17:00`)
- "Días de atención" — checklist horizontal: Lunes a Sábado (badges seleccionables)
- "Duración del turno" — input número, minutos (placeholder `30`)
- "Especialidad" — input texto, solo lectura (se define al crear el profesional)

**Botón "Guardar cambios"** primary. Validaciones: horario_inicio < horario_fin, duración > 0, al menos 1 día.

**Endpoints**: `GET /profesional/configuracion`, `PUT /profesional/configuracion`

---

### 6. Métricas — `profesional_metricas/`

**Propósito**: Indicadores del consultorio en los últimos 30 días.

**Grid de 3 KPIs** (1 fila, 3 columnas desktop):

| KPI | Descripción |
|-----|-------------|
| 📋 Turnos hoy | Número de turnos CONFIRMADOS para hoy |
| 📈 Tasa confirmación 30d | Porcentaje (formateado, ej: 75%) |
| 📉 Tasa cancelación 30d | Porcentaje (rojo si >20%) |

**Notas**:
- No hay charts, progress bars ni filtros de fecha (período fijo 30 días)
- Los datos son escalares, sin serie temporal
- Endpoint: `GET /profesional/metricas`

---

### 7. Integraciones — `profesional_integraciones/`

**Propósito**: Conectar servicios externos (Telegram y Google Calendar).

**Tarjeta Telegram**:
- Badge "Conectado" (verde) o "Desconectado" (rojo)
- Input para token del bot (password, readonly si ya tiene)
- Botón "Guardar token" (requiere HTTPS)
- Texto ayuda: "El token se obtiene de @BotFather"

**Tarjeta Google Calendar**:
- Badge "Conectado" / "Desconectado"
- Input para refresh token (password)
- Input para Calendar ID (default "primary")
- Botón "Guardar" (requiere HTTPS)
- Texto ayuda: "El refresh token se genera desde Google Cloud Console"

**Endpoints**: `GET /profesional/integraciones`, `PUT /profesional/integraciones` (ambos requieren HTTPS)

---

## Sidebar — Navegación completa

| Item | Icono | Ruta |
|------|-------|------|
| Dashboard | `dashboard` | `/` |
| Agenda | `calendar_month` | `/agenda` |
| Pacientes | `group` | `/pacientes` |
| Configuración | `settings` | `/configuracion` |
| Métricas | `monitoring` | `/metricas` |
| Integraciones | `power_settings_new` | `/integraciones` |

---

## Resumen de Componentes Compartidos

| Componente | Descripción |
|-----------|-------------|
| Sidebar 240px | Logo + 6 nav items + perfil al pie |
| TopAppBar | Título + logout |
| Badge Estado | Pill: azul (CONFIRMADO), verde (COMPLETADO), rojo (CANCELADO), gris (RESERVADO) |
| TurnoCard | Card con hora, paciente, estado, acciones |
| Modal agendar | Formulario con selector de slot + datos paciente |
| ConfirmDialog | Acciones destructivas (cancelar) |
| Input/Select | Formularios con validación |
| KpiCard | Valor + label + icono |
| Skeleton | Loading state |
| EmptyState | Sin datos + ilustración |

---

## Endpoints necesarios (pendientes)

| Endpoint | Razón |
|----------|-------|
| `GET /pacientes?search=` | Buscar pacientes por nombre, apellido o DNI para la pantalla de Pacientes y el autocomplete en Agenda |
