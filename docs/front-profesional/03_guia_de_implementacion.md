# Front Profesional - Guía de Implementación

## 1. Objetivo del documento
Guía paso a paso para implementar el Front Profesional del sistema de gestión de turnos odontológicos. Describe el orden de construcción, configuración inicial, y buenas prácticas.

---

## 2. Requisitos previos

### Versiones de Node
- Node.js 18+ (LTS recomendada: 20.x)
- npm 9+ o pnpm 8+

### Backend requerido
- Backend FastAPI corriendo en `http://localhost:8000`
- Base de datos PostgreSQL con seed de profesional
- Endpoints de auth funcionales (`POST /auth/login`)
- CORS habilitado para el origen del frontend

### Variables de entorno (`.env`)
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 3. Setup inicial

```bash
# Crear proyecto con Vite + React + TypeScript
npm create vite@latest front-profesional -- --template react-ts

# Entrar al directorio
cd front-profesional

# Instalar dependencias principales
npm install react-router-dom @tanstack/react-query zustand axios date-fns

# UI y formularios
npm install react-hook-form @hookform/resolvers zod

# Tailwind CSS
npm install -D tailwindcss @tailwindcss/vite

# Testing
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom

# Ejecutar proyecto
npm run dev
```

### Configurar Tailwind
Agregar plugin en `vite.config.ts`:
```typescript
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

Importar en `src/index.css`:
```css
@import "tailwindcss";
```

---

## 4. Arquitectura inicial

### Crear estructura base
```
src/
├── app/
│   ├── router.tsx
│   └── providers.tsx
├── shared/
│   ├── components/
│   │   ├── ui/
│   │   └── layout/
│   └── services/
│       └── api.ts
├── features/
│   ├── auth/
│   ├── dashboard/
│   ├── agenda/
│   ├── pacientes/
│   ├── configuracion/
│   ├── metricas/
│   └── integraciones/
└── types/
```

### Configurar router
Usar `createBrowserRouter` de React Router v6 con nested layouts y lazy loading.

### Configurar layouts
- `AuthLayout`: layout minimal sin sidebar (solo login)
- `AppLayout`: sidebar + header + `<Outlet>`

### Configurar tema
Tailwind: colores primarios personalizados. Sin dark mode en v1.

### Configurar cliente HTTP
Axios instance con interceptors para JWT y manejo de errores 401.

### Configurar autenticación
Zustand store con `auth: { token, profesional }`, persistido en localStorage. Componente `<ProtectedRoute>` que redirige a `/login` si no hay token.

---

## 5. Orden de implementación (Camino crítico)

### Fase 1 — Base del proyecto
- [ ] Crear proyecto con Vite + React + TS
- [ ] Configurar Tailwind CSS
- [ ] Configurar Router (createBrowserRouter)
- [ ] Layout principal (AppLayout: Sidebar + Header + Outlet)
- [ ] AuthLayout (layout minimal para login)
- [ ] Sidebar con navegación (iconos + labels)
- [ ] Header (nombre del profesional + botón logout)
- [ ] Página 404 (NotFound)
- [ ] Página de error genérico (ErrorBoundary)
- [ ] Providers wrapper (QueryClient, Auth provider)
- [ ] Axios instance con interceptors

### Fase 2 — Autenticación
- [ ] LoginPage (formulario email + password)
- [ ] Hook `useLogin` (llama a `POST /auth/login`, guarda token)
- [ ] AuthStore (Zustand + persist)
- [ ] Componente ProtectedRoute
- [ ] Logout (limpiar store + redirigir)
- [ ] Manejo de 401 en interceptor (logout automático)
- [ ] Test: login exitoso, login fallido, redirección

### Fase 3 — Dashboard
- [ ] DashboardPage layout (cards + lista)
- [ ] Hook `useTurnosHoy` (TanStack Query: `GET /profesional/turnos-hoy`)
- [ ] Componente `ResumenCards` (contador de turnos)
- [ ] Componente `TurnosDelDia` (lista de turnos)
- [ ] Componente `TurnoRow` (hora, paciente, acciones)
- [ ] Acción completar: `PUT /turnos/{id}/completar` con invalidación de queries
- [ ] Acción cancelar: `ConfirmDialog` + `PUT /turnos/{id}/cancelar`
- [ ] Loading state: Skeleton mientras carga
- [ ] Empty state: "No hay turnos programados para hoy"
- [ ] Error state: mensaje + botón reintentar

### Fase 4 — Agenda
- [ ] AgendaPage layout (calendario + slots)
- [ ] Calendario mensual (navegación entre meses)
- [ ] Al seleccionar fecha: `GET /turnos/disponibles?fecha=YYYY-MM-DD`
- [ ] SlotList: slots coloreados por disponibilidad (verde=disponible, gris=ocupado)
- [ ] Modal crear turno: seleccionar slot → buscar paciente → confirmar
- [ ] Modal detalle turno: ver datos, cancelar, reprogramar
- [ ] Reprogramar: selector de nuevo slot + confirmación

### Fase 5 — Pacientes
- [ ] PacientesListPage: barra de búsqueda + tabla
- [ ] Buscador por nombre/apellido/DNI (debounced input)
- [ ] Nota: no hay endpoint de listado genérico. Si se necesita, agregar endpoint backend o buscar por DNI exacto
- [ ] PacienteDetailPage: `GET /pacientes/{id}` + `GET /pacientes/{id}/turnos`
- [ ] Componente `HistorialTurnos`: tabla con fecha, hora, estado

### Fase 6 — Configuración
- [ ] ConfiguracionPage: formulario con todos los campos
- [ ] Cargar datos: `GET /profesional/configuracion`
- [ ] Guardar: `PUT /profesional/configuracion`
- [ ] Validaciones: horario_inicio < horario_fin, duración > 0, al menos 1 día
- [ ] DiasSelector: checkboxes para días de la semana
- [ ] Loading + error + success states

### Fase 7 — Métricas
- [ ] MetricasPage: grid de KPIs
- [ ] Hook `useMetricas` (TanStack Query: `GET /profesional/metricas`)
- [ ] KpiCard: icono + valor + label
- [ ] Tasa de confirmación: mostrar como porcentaje (0.75 → 75%)
- [ ] Tasa de cancelación: mostrar como porcentaje (0.10 → 10%)

### Fase 8 — Integraciones
- [ ] IntegracionesPage: secciones por servicio
- [ ] Estado actual: badge conectado/desconectado
- [ ] Formulario: token de Telegram (input password)
- [ ] Formulario: refresh token de Google (input password)
- [ ] Calendar ID: input de texto
- [ ] Guardar: `PUT /profesional/integraciones`
- [ ] **Requerimiento**: este endpoint requiere HTTPS. Mostrar warning si no es HTTPS

---

## 6. Componentes reutilizables (orden de creación)

1. **Button** — variantes: primary, secondary, danger, ghost. Prop `loading` con spinner
2. **Input** — label, error message, register de RHF
3. **Select** — options array, label, error
4. **Badge** — colores por variante (success=verde, danger=rojo, warning=amarillo)
5. **EstadoBadge** — mapeo de estados del turno a colores:
   - DISPONIBLE → gray
   - RESERVADO_TEMPORAL → yellow
   - CONFIRMADO → blue
   - CANCELADO → red
   - COMPLETADO → green
6. **Modal** — overlay + contenido centrado, cierra con Escape
7. **ConfirmDialog** — Modal con título + mensaje + botones confirmar/cancelar
8. **Toast** — notificación deslizable, auto-dismiss 4s
9. **Skeleton** — placeholder de carga (rectángulo animado)
10. **EmptyState** — icono + título + descripción
11. **ErrorState** — mensaje de error + botón reintentar
12. **Sidebar** — navegación con iconos + active state
13. **Header** — nombre del profesional + avatar + botón logout

---

## 7. Integración con Backend

### Base URL
```typescript
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
```

### Headers
```typescript
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})
```

### JWT Interceptor
```typescript
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

### Manejo de errores en TanStack Query
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,      // 30 segundos
      retry: 1,               // 1 reintento
      refetchOnWindowFocus: false,
    },
  },
})
```

---

## 8. Estrategia de desarrollo

### Crear Feature
1. Identificar el módulo (dashboard, agenda, etc.)
2. Crear carpeta bajo `features/` con estructura: `pages/`, `components/`, `hooks/`, `services/`
3. Agregar ruta en `app/router.tsx`

### Crear Servicio (API call)
```typescript
// features/dashboard/services/turnosHoyService.ts
import api from '@/shared/services/api'
import type { TurnoConPaciente } from '@/types/turno'

export const getTurnosHoy = async (): Promise<TurnoConPaciente[]> => {
  const { data } = await api.get('/profesional/turnos-hoy')
  return data
}

export const completarTurno = async (turnoId: number): Promise<void> => {
  await api.put(`/turnos/${turnoId}/completar`)
}

export const cancelarTurno = async (turnoId: number): Promise<void> => {
  await api.put(`/turnos/${turnoId}/cancelar`)
}
```

### Crear Hook (TanStack Query)
```typescript
// features/dashboard/hooks/useTurnosHoy.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as turnosHoyService from '../services/turnosHoyService'

export function useTurnosHoy() {
  return useQuery({
    queryKey: ['turnos-hoy'],
    queryFn: turnosHoyService.getTurnosHoy,
  })
}

export function useCompletarTurno() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: turnosHoyService.completarTurno,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['turnos-hoy'] })
      queryClient.invalidateQueries({ queryKey: ['metricas'] })
    },
  })
}
```

### Crear Componente
```typescript
// features/dashboard/components/TurnosDelDia.tsx
export function TurnosDelDia() {
  const { data, isLoading, error } = useTurnosHoy()
  const completar = useCompletarTurno()
  // ... render
}
```

### Testing
- Test del hook con msw mockeando la API
- Test del componente con RTL: renderizar, esperar datos, verificar botones
- Test de error: mockear error, verificar EmptyState/ErrorState

---

## 9. Testing

### Unitarios
- Hooks: mockear `api` con `vi.mock()`, verificar que llaman al endpoint correcto
- Servicios: testear que formatean correctamente los datos
- Componentes UI: renderizar con distintas props, verificar render

### Integración
- Login: llenar formulario → submit → verificar redirección a dashboard
- Dashboard: mockear `GET /profesional/turnos-hoy` → verificar lista de turnos
- Completar turno: click en botón → verificar que se llamó a la API
- Error 401: mockear 401 → verificar redirección a login

### Mocks
```typescript
// tests/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('*/profesional/turnos-hoy', () =>
    HttpResponse.json([
      {
        id: 1,
        fecha: '2026-07-01',
        hora_inicio: '09:00',
        hora_fin: '09:30',
        estado: 'CONFIRMADO',
        paciente: { id: 1, nombre: 'Juan', apellido: 'Pérez', dni: '12345678', telefono: '555-0001' },
      },
    ])
  ),
]
```

### Casos críticos a testear
- Token expirado: interceptor responde 401, usuario redirigido a login
- Cancelar turno: aparece ConfirmDialog, al confirmar se llama a la API
- Error 409 al completar: mostrar toast con mensaje del backend
- Configuración inválida: mostrar errores de validación en campos

---

## 10. Checklist de implementación

### Base
- [ ] Proyecto Vite + React + TypeScript configurado
- [ ] Tailwind CSS funcionando
- [ ] Router con lazy loading
- [ ] AppLayout con Sidebar + Header
- [ ] Axios instance con interceptors (JWT + 401)
- [ ] Zustand store para auth
- [ ] TanStack Query Client configurado
- [ ] 404 page
- [ ] ErrorBoundary global

### Login
- [ ] LoginPage con formulario email + password
- [ ] Hook useLogin
- [ ] ProtectedRoute implementado
- [ ] Logout funcional
- [ ] Test: login exitoso → redirige a dashboard

### Dashboard
- [ ] Lista de turnos del día
- [ ] Acción completar
- [ ] Acción cancelar con confirmación
- [ ] Loading state (Skeleton)
- [ ] Empty state ("Sin turnos hoy")
- [ ] Error state + reintentar
- [ ] Toast de éxito/error

### Agenda
- [ ] Calendario mensual
- [ ] Slots por fecha
- [ ] Modal crear turno
- [ ] Modal detalle turno
- [ ] Reprogramar turno

### Pacientes
- [ ] Búsqueda de pacientes
- [ ] Perfil del paciente con historial

### Configuración
- [ ] Formulario con carga de datos
- [ ] Validaciones del lado del front
- [ ] Guardar cambios

### Métricas
- [ ] Grid de KPIs
- [ ] Formateo de porcentajes

### Integraciones
- [ ] Estado de conexión (conectado/desconectado)
- [ ] Formulario de tokens

### Testing
- [ ] Tests de hooks y servicios
- [ ] Tests de componentes críticos
- [ ] Tests de flujo de login

### Optimización
- [ ] Lazy loading de rutas
- [ ] Caching con TanStack Query (staleTime configurado)
- [ ] Bundle size monitoreado

---

## 11. Checklist previo al Merge

- [ ] ESLint sin errores
- [ ] TypeScript strict mode sin errores
- [ ] Tests pasando
- [ ] Prueba manual: login → dashboard → completar turno → agenda → pacientes
- [ ] Manejo de errores visible en todos los componentes async
- [ ] Loading states en todos los componentes async
- [ ] Responsive: se ve bien en 1280px+
- [ ] No hay secretos hardcodeados
- [ ] Archivo `.env.example` con todas las variables

---

## 12. Problemas comunes

### Token expirado
- **Síntoma**: requests devuelven 401
- **Solución**: el interceptor redirige a login automáticamente. Si no funciona, verificar que el interceptor esté registrado.

### Error de CORS
- **Síntoma**: error en consola del navegador "CORS policy"
- **Solución**: verificar que el backend tenga configurado CORS para el origen del front. En desarrollo, asegurar que backend permita `http://localhost:5173`.

### Variables de entorno
- **Síntoma**: `import.meta.env.VITE_API_BASE_URL` es undefined
- **Solución**: crear archivo `.env` en la raíz del proyecto. En Vite, las variables deben tener prefijo `VITE_`.

### Backend caído
- **Síntoma**: requests fallan con timeout o ERR_CONNECTION_REFUSED
- **Solución**: toast "No se puede conectar con el servidor". Verificar que el backend esté corriendo.

### Error 422
- **Síntoma**: formulario válido pero backend rechaza
- **Solución**: revisar que los tipos de datos coincidan (date vs string, time vs string). Backend espera formatos específicos.

### Error 500
- **Síntoma**: respuesta 500 del backend
- **Solución**: toast genérico. Revisar logs del backend.

---

## 13. Buenas prácticas

- **Componentes pequeños**: un componente = una responsabilidad. Si un componente tiene más de ~150 líneas, dividirlo
- **Tipado fuerte**: evitar `any`. Tipos compartidos en `types/`, tipos específicos dentro de cada feature
- **Servicios desacoplados**: los componentes NO llaman a Axios directamente. Pasan por servicios y hooks
- **Separación de responsabilidades**: lógica de negocio en hooks, presentación en componentes, datos en servicios
- **Evitar duplicación**: si un patrón se repite (ej: card de turno), extraer a shared
- **Mutaciones optimistas**: para acciones rápidas (completar, cancelar), usar TanStack Query optimistic updates
- **Feedback visual**: toda acción (guardar, eliminar, crear) debe tener toast de éxito o error

---

## 14. Pendientes / Mejoras futuras

- **Modo oscuro**: implementar con clase `dark` en Tailwind + toggle en Zustand store
- **Internacionalización**: envolver textos con i18n (react-i18next) si se requiere multi-idioma
- **PWA + Offline**: service worker para funcionamiento offline parcial (ver datos cacheados)
- **Notificaciones push**: notificar al profesional sobre cancelaciones de último momento o lista de espera
- **Multi-consultorio**: si un profesional maneja más de una sede, agregar selector y scoping por sede
- **Exportar datos**: exportar turnos del día o métricas a PDF/CSV
