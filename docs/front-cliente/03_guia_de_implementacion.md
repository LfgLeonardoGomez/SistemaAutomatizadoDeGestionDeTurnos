# Front Cliente - Guía de Implementación

## 1. Objetivo
Guía paso a paso para implementar el Front Cliente del sistema de gestión de turnos odontológicos. Describe el orden de construcción, configuración inicial, y buenas prácticas.

---

## 2. Requisitos previos

### Versiones de Node
- Node.js 18+ (LTS recomendada: 20.x)
- npm 9+ o pnpm 8+

### Backend requerido
- Backend FastAPI corriendo en `http://localhost:8000`
- CORS habilitado para el origen del frontend
- Endpoints de disponibilidad y turnos funcionales

### Variables de entorno (`.env`)
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 3. Setup inicial

```bash
npm create vite@latest front-cliente -- --template react-ts
cd front-cliente

npm install react-router-dom @tanstack/react-query zustand axios date-fns
npm install react-hook-form @hookform/resolvers zod
npm install -D tailwindcss @tailwindcss/vite
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom

npm run dev
```

### Configurar Tailwind
```typescript
// vite.config.ts
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

```css
/* src/index.css */
@import "tailwindcss";
```

---

## 4. Configuración base

### Router
Usar `createBrowserRouter` con:
- Layout público (Header + Outlet + Footer)
- Ruta `/` → InicioPage
- Ruta `/reserva` → ReservaFlowPage
- Ruta `/mis-turnos` → IdentificacionPage (pide DNI)
- Ruta `/mis-turnos/:pacienteId` → MisTurnosPage

### Layout
- Header minimal: logo + "Sacar turno" + "Mis turnos" (links)
- Footer: información de contacto del consultorio
- Sin sidebar. Sin auth guard

### Tema
- Tailwind config: colores amigables (verde/clínico), tipografía legible
- Mobile-first: container padding generoso en mobile, max-width en desktop

### Cliente HTTP
```typescript
// shared/services/api.ts
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})
```
No se necesita interceptor de JWT (el front cliente es público).

### Autenticación (lo más simple posible)
- Store en Zustand con `pacienteId: number | null`
- Persistido en `sessionStorage` (se borra al cerrar la pestaña)
- Al identificar por DNI: `POST /pacientes` → guardar `id` → redirigir a `/mis-turnos/:id`

---

## 5. Camino crítico

### Fase 1 — Base
- [ ] Proyecto Vite + React + TS
- [ ] Tailwind configurado
- [ ] Router con rutas base
- [ ] AppLayout: Header + Outlet + Footer
- [ ] InicioPage: dos botones principales + info de contacto
- [ ] Página 404

### Fase 2 — Identificación (para Mis turnos)
- [ ] IdentificacionPage: input de DNI + botón "Ver mis turnos"
- [ ] Hook `useIdentificarPaciente`: `POST /pacientes` con DNI
- [ ] Zustand store: `pacienteId` en sessionStorage
- [ ] Redirección a `/mis-turnos/:id`

### Fase 3 — Reserva de turno (wizard 4 pasos)
Este es el feature más importante. Implementar en orden:

- [ ] **Paso 1 — Fecha**: calendario visual. Al seleccionar fecha, pasar a paso 2
- [ ] **Paso 2 — Horario**: `GET /turnos/disponibles?fecha=...`. Mostrar slots disponibles como botones. Al seleccionar, `POST /turnos` (reserva temporal)
- [ ] **Paso 3 — Datos**: formulario con nombre, apellido, DNI, teléfono. Validación con Zod
- [ ] **Paso 4 — Confirmación**: resumen + botón confirmar. `PUT /turnos/{id}/confirmar`
- [ ] **ReservaStore**: Zustand con paso actual, fecha, hora, turno_id, datos del paciente
- [ ] **Expiración**: si la reserva temporal expira (error 409 en confirmar), mostrar mensaje y volver a paso 1
- [ ] **Sin disponibilidad**: mostrar mensaje + opción de lista de espera

### Fase 4 — Mis turnos
- [ ] MisTurnosPage: carga turnos con `GET /pacientes/{id}/turnos`
- [ ] Turno próximo: destacado, con acciones (cancelar, reprogramar)
- [ ] Historial: lista de turnos anteriores
- [ ] Cancelar: ConfirmDialog + `PUT /turnos/{id}/cancelar`
- [ ] Reprogramar: modal con selector de fecha + horario + `PUT /turnos/{id}/reprogramar`

### Fase 5 — Cancelar / Reprogramar
- [ ] Acción cancelar con ConfirmDialog
- [ ] Acción reprogramar con ReprogramarModal (seleccionar nueva fecha y hora)
- [ ] Manejo de errores: 409 si el nuevo slot ya no está disponible
- [ ] Toast de éxito después de cada acción

### Fase 6 — Lista de espera
- [ ] ListaEsperaForm: después de buscar disponibilidad sin resultados
- [ ] Input: fecha de preferencia
- [ ] `POST /lista-espera`: body `{ paciente_id, fecha_solicitada }`
- [ ] Confirmación: "Te vamos a avisar si se libera un turno"

### Fase 7 — Mejoras UX
- [ ] Loading skeletons en todos los componentes async
- [ ] Empty states: "No tenés turnos programados"
- [ ] Error states con reintentar
- [ ] Toasts de feedback en todas las acciones

---

## 6. Componentes Shared

| Componente | Cuándo implementar | Detalle |
|-----------|-------------------|---------|
| Button | Fase 1 | Primary, secondary, ghost. Prop `fullWidth` para mobile |
| Input | Fase 1 | Con label, error message, type (text/tel) |
| Modal | Fase 1 | Fullscreen mobile (bottom sheet), centered desktop |
| ConfirmDialog | Fase 5 | Para cancelar turno |
| Toast | Fase 3 | Success/error/info, auto-dismiss |
| Skeleton | Fase 3 | Placeholder para carga de slots y turnos |
| EmptyState | Fase 4 | "No tenés turnos" con CTA "Sacar turno" |
| EstadoBadge | Fase 3 | Colores: CONFIRMADO=blue, CANCELADO=red, COMPLETADO=green |
| TurnoCard | Fase 4 | Card compacta con fecha, hora, estado, acciones |

---

## 7. Integración Backend

### Base URL
```typescript
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
```

### Endpoints clave
```typescript
// reservaService.ts
export const getDisponibilidad = (fecha: string) =>
  api.get<Slot[]>('/turnos/disponibles', { params: { fecha } }).then(r => r.data)

export const crearReserva = (fecha: string, hora_inicio: string) =>
  api.post<Turno>('/turnos', { fecha, hora_inicio }).then(r => r.data)

export const confirmarTurno = (turnoId: number, data: ConfirmarData) =>
  api.put<Turno>(`/turnos/${turnoId}/confirmar`, data).then(r => r.data)

// turnoService.ts
export const getTurnosPaciente = (pacienteId: number) =>
  api.get<Turno[]>(`/pacientes/${pacienteId}/turnos`).then(r => r.data)

export const cancelarTurno = (turnoId: number) =>
  api.put<Turno>(`/turnos/${turnoId}/cancelar`).then(r => r.data)

export const reprogramarTurno = (turnoId: number, nuevaFecha: string, nuevaHora: string) =>
  api.put<Turno>(`/turnos/${turnoId}/reprogramar`, { nueva_fecha: nuevaFecha, nueva_hora_inicio: nuevaHora }).then(r => r.data)

// pacienteService.ts
export const crearObtenerPaciente = (data: PacienteCreate) =>
  api.post<Paciente>('/pacientes', data).then(r => r.data)

// listaEsperaService.ts
export const registrarListaEspera = (pacienteId: number, fecha: string) =>
  api.post<ListaEspera>('/lista-espera', { paciente_id: pacienteId, fecha_solicitada: fecha }).then(r => r.data)

export const salirListaEspera = (id: number) =>
  api.delete(`/lista-espera/${id}`)
```

### Manejo de errores
```typescript
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 409) {
      // Conflict — mostrar mensaje del backend
      // No redirigir, solo toast
    }
    if (!error.response) {
      // Network error / timeout
    }
    return Promise.reject(error)
  }
)
```

---

## 8. Estrategia de desarrollo

### Crear Feature
1. Definir ruta en `app/router.tsx`
2. Crear página (componente principal)
3. Crear servicio (llamadas API)
4. Crear hook (TanStack Query: useQuery + useMutation)
5. Crear componentes secundarios
6. Conectar todo

### Ejemplo: Paso 2 del wizard (seleccionar horario)
```typescript
// 1. Servicio
// features/reserva/services/reservaService.ts
export const getDisponibilidad = (fecha: string) =>
  api.get<Slot[]>('/turnos/disponibles', { params: { fecha } }).then(r => r.data)

// 2. Hook
// features/reserva/hooks/useDisponibilidad.ts
export function useDisponibilidad(fecha: string | null) {
  return useQuery({
    queryKey: ['disponibilidad', fecha],
    queryFn: () => getDisponibilidad(fecha!),
    enabled: !!fecha,
    staleTime: 60_000,
  })
}

// 3. Componente
// features/reserva/components/StepHorario.tsx
export function StepHorario() {
  const { fecha, setHorario, setPaso } = useReservaStore()
  const { data: slots, isLoading } = useDisponibilidad(fecha)

  if (isLoading) return <Skeleton count={8} />

  const disponibles = slots?.filter(s => s.disponible) ?? []

  if (disponibles.length === 0) {
    return <EmptyState title="No hay horarios disponibles" />
  }

  return (
    <div className="grid grid-cols-2 gap-2">
      {disponibles.map(slot => (
        <Button
          key={slot.hora_inicio}
          onClick={() => {
            setHorario(slot.hora_inicio)
            setPaso(3)
          }}
        >
          {slot.hora_inicio.slice(0, 5)}
        </Button>
      ))}
    </div>
  )
}
```

---

## 9. Testing

### Unitarios
- Store del wizard: `reservaStore` — setear fecha, hora, avanzar paso, resetear
- Hooks: mockear `api.get` con `vi.mock()`, verificar queries y mutations
- Validaciones Zod: DNI inválido, teléfono incompleto

### Integración
- **Flujo de reserva exitoso**:
  1. Mock `GET /turnos/disponibles?fecha=...` → 3 slots
  2. Mock `POST /turnos` → turno con estado RESERVADO_TEMPORAL
  3. Mock `PUT /turnos/{id}/confirmar` → turno CONFIRMADO
  4. Verificar pantalla de éxito con resumen
- **Error 409 al confirmar**:
  1. Mock `PUT /turnos/{id}/confirmar` → 409
  2. Verificar toast + volver a paso 2
- **Cancelar turno**:
  1. Mock `GET /pacientes/{id}/turnos` → 1 turno CONFIRMADO
  2. Click cancelar → ConfirmDialog aparece
  3. Click confirmar → `PUT /turnos/{id}/cancelar` llamado
  4. Turno desaparece de lista de próximos

### Mocks
```typescript
// tests/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('*/turnos/disponibles', ({ request }) => {
    return HttpResponse.json([
      { hora_inicio: '09:00', hora_fin: '09:30', disponible: true },
      { hora_inicio: '09:30', hora_fin: '10:00', disponible: true },
      { hora_inicio: '10:00', hora_fin: '10:30', disponible: false },
    ])
  }),
  http.post('*/turnos', () =>
    HttpResponse.json({
      id: 1, fecha: '2026-07-05', hora_inicio: '09:00',
      hora_fin: '09:30', estado: 'RESERVADO_TEMPORAL',
    }, { status: 201 })
  ),
  http.put('*/turnos/1/confirmar', () =>
    HttpResponse.json({
      id: 1, fecha: '2026-07-05', hora_inicio: '09:00',
      hora_fin: '09:30', estado: 'CONFIRMADO', paciente_id: 1,
    })
  ),
]
```

---

## 10. Checklist

### Base
- [ ] Proyecto Vite + React + TS creado
- [ ] Tailwind funcionando
- [ ] Router con rutas
- [ ] AppLayout (Header + Outlet + Footer)
- [ ] Axios instance configurada
- [ ] Página 404

### Identificación
- [ ] Formulario de DNI
- [ ] Store con pacienteId (sessionStorage)
- [ ] Redirección a Mis turnos

### Reserva
- [ ] Paso 1: Calendario / selector de fecha
- [ ] Paso 2: Slots disponibles
- [ ] Paso 3: Datos del paciente
- [ ] Paso 4: Confirmación
- [ ] Manejo de expiración de reserva
- [ ] Opción de lista de espera cuando no hay disponibilidad

### Mis Turnos
- [ ] Lista de turnos (próximos + historial)
- [ ] Cancelar con confirmación
- [ ] Reprogramar
- [ ] Manejo de errores (404, 409)

### Testing
- [ ] Tests del store del wizard
- [ ] Tests del flujo de reserva (mockeado)
- [ ] Tests de cancelación
- [ ] Tests de identificación por DNI

### Optimización
- [ ] Lazy loading de rutas
- [ ] Skeleton loading en componentes async
- [ ] Toast de feedback en todas las acciones

---

## 11. Checklist previo al Merge

- [ ] ESLint + TypeScript sin errores
- [ ] Tests pasando
- [ ] Prueba manual mobile (360px): flujo completo de reserva
- [ ] Prueba manual: mis turnos → cancelar → ver historial
- [ ] Manejo de errores visible en todas las pantallas async
- [ ] Loading states en todas las pantallas async
- [ ] Responsive: mobile-first 360px+, desktop hasta 1920px
- [ ] Sin secretos hardcodeados
- [ ] Archivo `.env.example` creado

---

## 12. Problemas comunes

### Error 422 en POST /turnos
- **Causa**: formato de fecha u hora incorrecto
- **Solución**: enviar `fecha` como YYYY-MM-DD, `hora_inicio` como HH:MM

### Slots no aparecen
- **Causa**: el backend no tiene slots generados para esa fecha (día no laborable o sin configuración)
- **Solución**: verificar `GET /profesional/configuracion` para días de atención

### Error 409 al confirmar
- **Causa**: la reserva temporal expiró o el paciente ya tiene otro turno activo
- **Solución**: mostrar el mensaje exacto del backend. Ofrecer volver a seleccionar horario

### El paciente no aparece en "Mis turnos"
- **Causa**: se usó un DNI diferente al de la reserva
- **Solución**: el front debe mostrar los datos del paciente al identificarse

---

## 13. Buenas prácticas

- **Componentes pequeños**: un componente = una pantalla o sección visible
- **Tipado fuerte**: evitar `any`. Schemas de Zod para formularios replican la validación del backend
- **Servicios desacoplados**: los componentes nunca llaman a Axios directamente
- **Estado mínimo**: el wizard no persiste en localStorage, solo en memoria. Si el usuario recarga, pierde el progreso
- **Mobile-first**: todo el CSS parte de mobile. Usar `sm:`, `md:` para mejoras en desktop
- **Feedback inmediato**: al hacer clic en "Confirmar", deshabilitar botón y mostrar spinner para evitar doble submit

---

## 14. Pendientes

- **Push notifications**: implementar Service Worker + API de notificaciones para reemplazar/mejorar las notificaciones de Telegram
- **PWA**: agregar manifest.json para instalación en el celular
- **Offline support**: cachear disponibilidad reciente para consulta offline
- **Modo oscuro**: implementar con clase `dark` en Tailwind
