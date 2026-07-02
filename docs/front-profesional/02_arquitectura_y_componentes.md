# Front Profesional - Arquitectura y Componentes

## 1. Objetivo del documento
Describir la arquitectura técnica, estructura de directorios, árbol de componentes, flujo de datos y convenciones para implementar el Front Profesional del sistema de gestión de turnos odontológicos.

---

## 2. Stack tecnológico

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| Framework | React 18+ con Vite | Ecosistema maduro, tipado con TypeScript, HMR rápido |
| Lenguaje | TypeScript 5+ strict | Tipado fuerte, detección temprana de errores |
| Build Tool | Vite | Build rápido, HMR nativo, tree-shaking |
| Router | React Router v6+ | Routing declarativo, nested layouts, loaders |
| Manejo de estado | Zustand (global) + TanStack Query (server state) | Liviano, desacoplado, caching automático de API |
| Estilos | Tailwind CSS 3+ | Utilidades atómicas, consistencia, responsive |
| Formularios | React Hook Form + Zod | Validación declarativa, tipado fuerte, performance |
| Cliente HTTP | Axios o fetch nativo + interceptors | Manejo centralizado de JWT, errores, retries |
| Manejo de fechas | date-fns (o Day.js) | Liviano, immutable, formateo de fechas/horas |
| Testing | Vitest + React Testing Library | Unitarios + integración de componentes |

---

## 3. Arquitectura general

### Principios
- **Organización por funcionalidades (features)**: cada feature contiene todo lo que necesita (componentes, hooks, servicios, tipos)
- **Separación de responsabilidades**: componentes = presentación, hooks/servicios = lógica, store = estado global
- **Unidirectional data flow**: componentes leen estado y disparan acciones, nunca mutan directamente
- **API como fuente de verdad**: el estado del servidor se gestiona con TanStack Query (caching, refetch, mutaciones)

### Flujo de datos
```
Componente → Hook/Service → API Client → Backend FastAPI → PostgreSQL
                 ↑                                ↓
            TanStack Query ← ← ← ← ← ← Response ← ←
                 ↓
          Componente (re-render)
```

---

## 4. Estructura de directorios

```text
src/
├── main.tsx                          # Entry point
├── App.tsx                           # Root component + RouterProvider
├── vite-env.d.ts
│
├── app/
│   ├── router.tsx                    # Definición de rutas (createBrowserRouter)
│   └── providers.tsx                 # Wrappers globales (QueryClient, Auth, Theme)
│
├── shared/
│   ├── components/                   # Componentes reutilizables
│   │   ├── ui/                       # Botones, inputs, modales, toasts, loaders
│   │   │   ├── Button.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   ├── Badge.tsx             # Para estados del turno (coloreados)
│   │   │   └── EmptyState.tsx
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx         # Sidebar + Header + Outlet
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   └── turno/
│   │       ├── TurnoCard.tsx         # Card individual de turno
│   │       └── EstadoBadge.tsx       # Badge coloreado por estado
│   ├── hooks/                        # Hooks genéricos
│   │   ├── useAuth.ts
│   │   └── useMediaQuery.ts
│   ├── services/                     # Cliente HTTP base
│   │   └── api.ts                    # Axios instance + interceptors
│   └── types/                        # Tipos compartidos
│       ├── turno.ts
│       ├── paciente.ts
│       └── profesional.ts
│
├── features/
│   ├── auth/
│   │   ├── pages/
│   │   │   └── LoginPage.tsx
│   │   ├── hooks/
│   │   │   └── useLogin.ts
│   │   ├── services/
│   │   │   └── authService.ts
│   │   └── types/
│   │       └── index.ts
│   │
│   ├── dashboard/
│   │   ├── pages/
│   │   │   └── DashboardPage.tsx
│   │   ├── components/
│   │   │   ├── TurnosDelDia.tsx
│   │   │   ├── TurnoRow.tsx
│   │   │   └── ResumenCards.tsx      # Cards de KPIs rápidos
│   │   ├── hooks/
│   │   │   └── useTurnosHoy.ts
│   │   └── services/
│   │       └── turnosHoyService.ts
│   │
│   ├── agenda/
│   │   ├── pages/
│   │   │   └── AgendaPage.tsx
│   │   ├── components/
│   │   │   ├── CalendarView.tsx
│   │   │   ├── SlotList.tsx
│   │   │   ├── AppointmentModal.tsx  # Crear/editar turno
│   │   │   └── DateSelector.tsx
│   │   ├── hooks/
│   │   │   ├── useDisponibilidad.ts
│   │   │   └── useGestionTurno.ts
│   │   └── services/
│   │       └── turnoService.ts
│   │
│   ├── pacientes/
│   │   ├── pages/
│   │   │   ├── PacientesListPage.tsx
│   │   │   └── PacienteDetailPage.tsx
│   │   ├── components/
│   │   │   ├── PacienteSearchBar.tsx
│   │   │   ├── PacienteTable.tsx
│   │   │   └── HistorialTurnos.tsx
│   │   ├── hooks/
│   │   │   └── usePacientes.ts
│   │   └── services/
│   │       └── pacienteService.ts
│   │
│   ├── configuracion/
│   │   ├── pages/
│   │   │   └── ConfiguracionPage.tsx
│   │   ├── components/
│   │   │   ├── HorariosForm.tsx
│   │   │   ├── DiasSelector.tsx
│   │   │   └── DuracionInput.tsx
│   │   ├── hooks/
│   │   │   └── useConfiguracion.ts
│   │   └── services/
│   │       └── configuracionService.ts
│   │
│   ├── metricas/
│   │   ├── pages/
│   │   │   └── MetricasPage.tsx
│   │   ├── components/
│   │   │   ├── KpiCard.tsx
│   │   │   └── MetricasGrid.tsx
│   │   ├── hooks/
│   │   │   └── useMetricas.ts
│   │   └── services/
│   │       └── metricasService.ts
│   │
│   └── integraciones/
│       ├── pages/
│       │   └── IntegracionesPage.tsx
│       ├── components/
│       │   ├── TelegramConfig.tsx
│       │   ├── GoogleCalendarConfig.tsx
│       │   └── IntegrationStatus.tsx
│       ├── hooks/
│       │   └── useIntegraciones.ts
│       └── services/
│           └── integracionesService.ts
│
└── assets/
    └── logo.svg
```

---

## 5. Sistema de rutas

### Mapa de navegación

```
/login                          → LoginPage          (pública, layout minimal)
/                               → DashboardPage      (protegida, AppLayout)
/agenda                         → AgendaPage         (protegida, AppLayout)
/agenda?fecha=YYYY-MM-DD       → AgendaPage (fecha pre-seleccionada)
/pacientes                      → PacientesListPage  (protegida, AppLayout)
/pacientes/:id                  → PacienteDetailPage (protegida, AppLayout)
/configuracion                  → ConfiguracionPage  (protegida, AppLayout)
/metricas                       → MetricasPage       (protegida, AppLayout)
/integraciones                  → IntegracionesPage  (protegida, AppLayout)
*                               → NotFoundPage
```

### Parámetros dinámicos
- `/pacientes/:id` — `id` del paciente (integer)
- `/agenda?fecha=YYYY-MM-DD` — query param para fecha

### Layouts
- **AuthLayout**: centrado, fondo simple, solo formulario de login (sin sidebar)
- **AppLayout**: sidebar izquierdo + header superior + `<Outlet>` para contenido

---

## 6. Arquitectura de componentes

### Componentes Shared (src/shared/components/)

```
shared/components/
├── ui/
│   ├── Button.tsx            # Botón con variantes (primary, secondary, danger, ghost)
│   ├── Input.tsx             # Input + label + error message
│   ├── Select.tsx            # Select con opciones tipadas
│   ├── Modal.tsx             # Modal genérico con header, body, footer
│   ├── ConfirmDialog.tsx     # Modal de confirmación (cancelar/completar)
│   ├── Toast.tsx             # Notificación toast (success, error, info)
│   ├── Skeleton.tsx          # Loader placeholder
│   ├── Spinner.tsx           # Loader circular
│   ├── Badge.tsx             # Badge de estado (coloreado por tipo)
│   ├── EmptyState.tsx        # Estado vacío con icono + mensaje + CTA
│   └── ErrorState.tsx        # Estado de error con reintentar
├── layout/
│   ├── AppLayout.tsx         # Sidebar + Header + Outlet
│   ├── AuthLayout.tsx        # Layout centrado para login
│   ├── Sidebar.tsx           # Navegación lateral con iconos
│   └── Header.tsx            # Barra superior con nombre del profesional + logout
└── turno/
    ├── TurnoCard.tsx         # Card con datos del turno + acciones
    └── EstadoBadge.tsx       # Badge según estado del turno
```

### Componentes de Feature (src/features/)

Cada feature tiene su propia carpeta con `pages/`, `components/`, `hooks/`, `services/`. Los componentes específicos de una feature NO se comparten.

---

## 7. Gestión del estado

| Tipo | Herramienta | Qué almacena |
|------|------------|-------------|
| Estado global (cliente) | Zustand | `auth: { token, profesional }`, `sidebar: { collapsed }` |
| Server state | TanStack Query | Turnos hoy, agenda, pacientes, configuración, métricas |
| Estado local | useState / useReducer | Formularios, modales abiertos/cerrados, selección actual |

### Cache del servidor
- **TanStack Query**: configuración global con `staleTime: 30s`, `retry: 1`
- Invalidar queries al mutar: ej, al completar un turno → invalidar `['turnos-hoy']` y `['metricas']`
- Mutaciones optimistas para acciones rápidas (completar, cancelar)

### Persistencia
- `zustand/middleware/persist` para el token JWT en localStorage
- NO persistir datos sensibles del profesional (refresh tokens, API keys)

---

## 8. Flujo de autenticación

### Login
1. POST `/auth/login` con `{ email, password }`
2. Backend devuelve `{ access_token, token_type: "bearer" }`
3. Guardar token en Zustand (persistido en localStorage)
4. Redirigir a `/` (dashboard)

### JWT
- Token tipo Bearer, enviado en header `Authorization: Bearer <token>`
- Payload: `{ sub: profesional_id, email: <email>, exp: <timestamp> }`
- Expiración: 1440 minutos (24 horas) por defecto, configurable vía `ACCESS_TOKEN_EXPIRE_MINUTES`

### Logout
- Eliminar token de Zustand y localStorage
- Redirigir a `/login`

### Protected Routes
- Componente `<ProtectedRoute>` que verifica existencia del token
- Si no hay token → redirigir a `/login`
- Si el token existe pero el backend responde 401 → intentar refrescar o redirigir a login

### Manejo de expiración
- Axios interceptor: si response es 401, limpiar auth y redirigir a login
- No hay refresh token automático. El usuario debe volver a login

---

## 9. Comunicación con Backend

### Base URL
`VITE_API_BASE_URL=http://localhost:8000` (configurable vía `.env`)

### Cliente HTTP
Axios instance con:
- `baseURL` desde variable de entorno
- `timeout: 15000` (15 segundos)
- Interceptor request: agrega `Authorization: Bearer <token>` si existe
- Interceptor response: captura errores 401 (limpiar sesión), 500 (log + toast genérico)

### Headers
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <jwt_token>"
}
```

### Manejo de errores HTTP

| Código | Causa | Acción en Front |
|--------|-------|-----------------|
| 401 | Token inválido/expirado | Limpiar sesión, redirigir a login |
| 403 | Sin permisos | Mostrar toast "No tenés permisos" |
| 404 | Recurso no encontrado | Mostrar EmptyState o mensaje específico |
| 409 | Conflicto (turno activo, DNI duplicado) | Mostrar mensaje del backend en toast |
| 422 | Validación de datos | Mostrar errores de campo en formularios |
| 500 | Error interno del servidor | Toast genérico "Error del servidor. Intentá de nuevo." |
| Timeout | Backend no responde | Toast "El servidor no respondió. Verificá tu conexión." |

---

## 10. Integración por módulos

### Dashboard
- **Endpoint**: `GET /profesional/turnos-hoy`
- **Modelos**: `ProfesionalTurnoHoyResponse` (id, fecha, hora_inicio, hora_fin, estado, paciente: {id, nombre, apellido, dni, telefono})
- **Componentes**: TurnosDelDia, TurnoRow, ResumenCards
- **Acciones**: `PUT /turnos/{id}/completar`, `PUT /turnos/{id}/cancelar`

### Agenda
- **Endpoint**: `GET /turnos/disponibles?fecha=YYYY-MM-DD`
- **Modelos**: `SlotResponse`[] (hora_inicio, hora_fin, disponible: bool)
- **Componentes**: CalendarView, SlotList, AppointmentModal, DateSelector
- **Acciones**: `POST /turnos`, `PUT /turnos/{id}/confirmar`, `PUT /turnos/{id}/cancelar`, `PUT /turnos/{id}/reprogramar`

### Pacientes
- **Endpoint**: `GET /pacientes/{id}`, `GET /pacientes/{id}/turnos`
- **Modelos**: `PacienteConHistorial` (hereda PacienteRead + turnos[]), `TurnoRead`
- **Componentes**: PacienteSearchBar, PacienteTable, HistorialTurnos
- **Nota**: No hay endpoint de listado genérico de pacientes. Se necesita buscar por ID o agregar un endpoint de búsqueda si es necesario

### Configuración
- **Endpoint**: `GET /profesional/configuracion`, `PUT /profesional/configuracion`
- **Modelos**: `ProfesionalConfigResponse` (horario_inicio, horario_fin, dias_atencion, duracion_turno, especialidad)
- **Componentes**: HorariosForm, DiasSelector, DuracionInput
- **Validaciones**: horario_inicio < horario_fin, duracion > 0, al menos 1 día

### Métricas
- **Endpoint**: `GET /profesional/metricas`
- **Modelos**: `ProfesionalMetricasResponse` (turnos_hoy: int, tasa_confirmacion_30d: float, tasa_cancelacion_30d: float)
- **Componentes**: KpiCard, MetricasGrid
- **Nota**: Sin filtros de fecha (período fijo 30 días)

### Integraciones
- **Endpoint**: `GET /profesional/integraciones`, `PUT /profesional/integraciones` (requiere HTTPS)
- **Modelos**: `ProfesionalIntegracionesResponse` (has_telegram: bool, has_google: bool, google_calendar_id: str)
- **Componentes**: TelegramConfig, GoogleCalendarConfig, IntegrationStatus

---

## 11. Modelos de datos (TypeScript)

```typescript
// Turno
interface Turno {
  id: number
  fecha: string        // YYYY-MM-DD
  hora_inicio: string  // HH:MM
  hora_fin: string     // HH:MM
  estado: 'DISPONIBLE' | 'RESERVADO_TEMPORAL' | 'CONFIRMADO' | 'CANCELADO' | 'COMPLETADO'
  profesional_id: number
  paciente_id: number | null
  google_event_id: string | null
  creado_en: string
}

// Turno con datos del paciente (para dashboard)
interface TurnoConPaciente extends Turno {
  paciente: PacienteInfo | null
}

interface PacienteInfo {
  id: number
  nombre: string
  apellido: string
  dni: string
  telefono: string
}

// Paciente
interface Paciente {
  id: number
  nombre: string
  apellido: string
  dni: string
  telefono: string
  creado_en: string
}

interface PacienteConHistorial extends Paciente {
  turnos: Turno[]
}

// Profesional / Configuración
interface ProfesionalConfig {
  horario_inicio: string    // HH:MM
  horario_fin: string       // HH:MM
  dias_atencion: string[]   // ["Lunes", "Martes", ...]
  duracion_turno: number    // minutos
  especialidad: string
}

// Métricas
interface Metricas {
  turnos_hoy: number
  tasa_confirmacion_30d: number  // 0.0 - 1.0
  tasa_cancelacion_30d: number   // 0.0 - 1.0
}

// Integraciones
interface Integraciones {
  has_telegram: boolean
  has_google: boolean
  google_calendar_id: string
}

// Auth
interface LoginRequest {
  email: string
  password: string
}

interface LoginResponse {
  access_token: string
  token_type: string  // "bearer"
}
```

---

## 12. Convenciones del proyecto

### Naming
- **Archivos**: PascalCase para componentes (`DashboardPage.tsx`), camelCase para hooks (`useTurnosHoy.ts`), kebab-case para servicios (`turno-service.ts`)
- **Componentes**: nombre descriptivo del rol (`TurnoCard`, `PacienteTable`, `SlotList`)
- **Hooks**: prefijo `use`, nombre describe función (`useTurnosHoy`, `useGestionTurno`)
- **Servicios**: nombre del recurso + `Service` (`turnoService.ts`, `pacienteService.ts`)
- **Tipos/Interfaces**: PascalCase, sin prefijo `I` (`Turno`, `PacienteConHistorial`)

### Imports
1. Librerías externas (react, zustand, tanstack-query)
2. Componentes de shared
3. Hooks y servicios de features
4. Tipos

### Archivos
- Un componente por archivo
- Un hook por archivo
- Un servicio por archivo (agrupado por recurso)

---

## 13. Componentes reutilizables

| Componente | Descripción | Props |
|-----------|-------------|-------|
| Button | Botón con variantes | variant, size, loading, disabled, onClick, children |
| Input | Input con label y error | label, name, error, register (RHF) |
| Select | Select con opciones | label, options, error, register |
| Modal | Modal overlay | isOpen, onClose, title, children |
| ConfirmDialog | Confirmación de acción | isOpen, title, message, onConfirm, onCancel, variant |
| Toast | Notificación | type (success/error/info), message, duration |
| Badge | Tag coloreado | variant (primary/success/danger/warning), children |
| EstadoBadge | Badge específico para estado de turno | estado: TurnoEstado |
| Skeleton | Placeholder de carga | width, height, variant |
| EmptyState | Estado sin datos | icon, title, description, action |
| ErrorState | Estado de error | message, onRetry |

---

## 14. Manejo de errores

| Escenario | UX |
|-----------|-----|
| 401 Unauthorized | Redirigir a login, toast "Sesión expirada" |
| 404 Not found | Página/componente con EmptyState + mensaje |
| 409 Conflict | Toast con mensaje del backend (ej: "El paciente ya tiene un turno activo") |
| 422 Validation | Errores en inputs del formulario (mensajes por campo) |
| 500 Server error | Toast "Error del servidor. Intentá de nuevo." + log |
| Offline | Toast "Sin conexión a internet" + deshabilitar acciones |
| Timeout | Toast "El servidor no responde. Verificá tu conexión." |

---

## 15. Performance

- **Lazy Loading**: cargar rutas con `React.lazy()` + `<Suspense>`
- **Memoización**: `React.memo` en listas largas, `useMemo` en cálculos pesados
- **TanStack Query**: caching automático con staleTime. Evitar refetch innecesario
- **Code Splitting**: split por feature (cada página es un chunk)
- **Virtualización**: no necesaria en v1/v2 (volumen de datos bajo)
- **Bundle**: monitorear con `vite-bundle-visualizer`

---

## 16. Accesibilidad

- **ARIA**: roles en componentes interactivos, `aria-label` en iconos sin texto
- **Teclado**: navegación por Tab en formularios, Enter/Escape en modales
- **Contraste**: ratio mínimo 4.5:1 en texto normal
- **Focus**: indicadores visibles de focus en todos los elementos interactivos
- **Labels**: todo input debe tener `<label>` asociado

---

## 17. Testing

| Tipo | Herramienta | Qué testear |
|------|------------|-------------|
| Unitarios | Vitest | Hooks, servicios, utilidades, formateo de fechas |
| Integración | Vitest + RTL | Comportamiento de página (login exitoso, lista de turnos, confirmación de cancelación) |
| E2E | Playwright (opcional) | Flujo completo: login → dashboard → completar turno → ver métricas |

### Mocks
- Mockear Axios/ApiClient con `vi.mock()` o `msw`
- Mockear TanStack Query para tests de componentes aislados
- Usar datos de prueba que reflejen los schemas reales del backend

### Cobertura esperada
- Hooks y servicios: 90%+
- Componentes críticos (login, dashboard, formularios): 80%+
- Páginas completas: 70%+

---

## 18. Consideraciones futuras

- **Dark mode**: preparar con clases de Tailwind (`dark:`), tema en Zustand
- **Multi-consultorio**: si el profesional tuviera múltiples sedes, requeriría selector de sede y scoping adicional
- **Internacionalización**: usar react-i18next o similar si se requiere i18n
- **Notificaciones push**: integrar con Service Workers para notificaciones del navegador
- **PWA**: agregar manifest.json + service worker para instalación en escritorio/móvil
