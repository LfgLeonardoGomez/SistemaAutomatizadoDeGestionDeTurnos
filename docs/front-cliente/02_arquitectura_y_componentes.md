# Front Cliente - Arquitectura y Componentes

## 1. Objetivo
Describir la arquitectura técnica, estructura de directorios, árbol de componentes y flujo de datos para implementar el Front Cliente del sistema de gestión de turnos odontológicos.

---

## 2. Stack tecnológico

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| Framework | React 18+ con Vite | Ecosistema maduro, tipado con TypeScript, HMR rápido |
| Lenguaje | TypeScript 5+ strict | Tipado fuerte, detección temprana de errores |
| Build Tool | Vite | Build rápido, tree-shaking, optimización para producción |
| Router | React Router v6+ (Data Router) | Nested layouts, loaders, actions para formularios |
| Manejo de estado | Zustand (sesión) + TanStack Query (server state) | Estado mínimo (solo DNI del paciente), caching de disponibilidad |
| Estilos | Tailwind CSS 3+ | Utilidades atómicas, mobile-first responsive |
| Formularios | React Hook Form + Zod | Validación client-side, tipado fuerte |
| Cliente HTTP | Axios | Interceptors, timeout, manejo de errores |
| Manejo de fechas | date-fns | Liviano, immutable, formateo de fechas/horas |
| Testing | Vitest + React Testing Library | Unitarios + integración de componentes |

---

## 3. Arquitectura general

### Principios
- **Organización por funcionalidades (features)**: cada feature contiene páginas, componentes, hooks y servicios
- **Mobile-first**: todas las decisiones de layout parten de 360px. Escritorio es mejora progresiva
- **Sin autenticación tradicional**: el paciente se identifica por DNI al final del flujo de reserva. No hay sesión persistente con JWT
- **Estado mínimo**: el único estado global es el DNI del paciente actual (para "Mis turnos"). Todo lo demás es server state

### Flujo de datos
```
Página → Hook (TanStack Query) → API Service → Axios → Backend FastAPI
                              ← Response ←
Hook → Componente (render)
```

Para el flujo de reserva multi-paso:
```
ReservaStore (Zustand, no persistido)
  → fecha seleccionada
  → hora seleccionada
  → turno_id (post-reserva temporal)
  → datos del paciente
  → paso actual (1: fecha, 2: hora, 3: datos, 4: confirmación)
```

---

## 4. Estructura de directorios

```text
src/
├── main.tsx
├── App.tsx
│
├── app/
│   ├── router.tsx
│   └── providers.tsx
│
├── shared/
│   ├── components/
│   │   ├── ui/                       # Botones, inputs, modales, toasts
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── EmptyState.tsx
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx         # Header + Outlet (minimal, mobile-first)
│   │   │   ├── Header.tsx            # Logo + nav simple
│   │   │   └── Footer.tsx            # Información de contacto
│   │   └── turno/
│   │       ├── EstadoBadge.tsx
│   │       └── TurnoCard.tsx
│   ├── hooks/
│   │   └── usePacienteByDNI.ts
│   ├── services/
│   │   └── api.ts                    # Axios instance
│   └── types/
│       ├── turno.ts
│       └── paciente.ts
│
├── features/
│   ├── inicio/
│   │   └── pages/
│   │       └── InicioPage.tsx        # Landing con botones principales
│   │
│   ├── reserva/
│   │   ├── pages/
│   │   │   └── ReservaFlowPage.tsx   # Contenedor del wizard multi-paso
│   │   ├── components/
│   │   │   ├── StepFecha.tsx         # Calendario para elegir fecha
│   │   │   ├── StepHorario.tsx       # Slots disponibles para la fecha
│   │   │   ├── StepDatos.tsx         # Formulario: nombre, apellido, DNI, teléfono
│   │   │   └── StepConfirmacion.tsx  # Resumen + confirmar
│   │   ├── hooks/
│   │   │   ├── useDisponibilidad.ts
│   │   │   └── useReservaTurno.ts
│   │   ├── services/
│   │   │   └── reservaService.ts
│   │   └── store/
│   │       └── reservaStore.ts       # Zustand: estado del wizard
│   │
│   ├── mis-turnos/
│   │   ├── pages/
│   │   │   ├── IdentificacionPage.tsx  # Pedir DNI para acceder
│   │   │   └── MisTurnosPage.tsx       # Lista de turnos del paciente
│   │   ├── components/
│   │   │   ├── TurnoCardList.tsx
│   │   │   ├── TurnoDetalle.tsx
│   │   │   └── ReprogramarModal.tsx
│   │   ├── hooks/
│   │   │   ├── useMisTurnos.ts
│   │   │   └── useGestionTurno.ts
│   │   └── services/
│   │       └── turnoService.ts
│   │
│   └── lista-espera/
│       ├── components/
│       │   └── ListaEsperaForm.tsx
│       ├── hooks/
│       │   └── useListaEspera.ts
│       └── services/
│           └── listaEsperaService.ts
│
└── assets/
    └── logo.svg
```

---

## 5. Sistema de rutas

```
/                           → InicioPage        (pública)
/reserva                    → ReservaFlowPage   (pública, sin auth)
/mis-turnos                 → IdentificacionPage (pública, pide DNI)
/mis-turnos/:id             → MisTurnosPage      (requiere DNI en store)
```

### Parámetros dinámicos
- `/mis-turnos` → sin parámetro. Pide DNI, redirige a `/mis-turnos/:id`
- `/mis-turnos/:id` — `id` del paciente

### Layouts
- **AppLayout**: header minimal + `<Outlet>`. Sin sidebar. Footer con datos de contacto

---

## 6. Arquitectura de componentes

### Componentes Shared

```
shared/components/
├── ui/
│   ├── Button.tsx           # Variantes: primary, secondary, ghost. Props: loading, fullWidth
│   ├── Input.tsx            # Label + input + error. Props: label, error, type (text/tel/dni)
│   ├── Modal.tsx            # Full-screen en mobile, centered en desktop
│   ├── ConfirmDialog.tsx    # Confirmación de acción sensible (cancelar)
│   ├── Toast.tsx            # Feedback visual
│   ├── Skeleton.tsx         # Placeholder de carga
│   └── EmptyState.tsx       # Estado sin datos
├── layout/
│   ├── AppLayout.tsx        # Header + Outlet + Footer
│   ├── Header.tsx           # Logo + "Sacar turno" + "Mis turnos"
│   └── Footer.tsx           # Dirección, teléfono, horarios
└── turno/
    ├── EstadoBadge.tsx      # Colores por estado
    └── TurnoCard.tsx        # Card compacta: fecha, hora, estado, acciones
```

### Componentes de Feature (Reserva - el más complejo)

```
features/reserva/
├── components/
│   ├── StepFecha.tsx        # Calendario con días disponibles resaltados
│   ├── StepHorario.tsx      # Grid de horarios, coloreados por disponibilidad
│   ├── StepDatos.tsx        # Formulario con RHF + Zod validación
│   └── StepConfirmacion.tsx # Resumen + "Confirmar turno" button
├── hooks/
│   ├── useDisponibilidad.ts # TanStack Query: GET /turnos/disponibles
│   └── useReservaTurno.ts   # Mutations: POST /turnos + PUT /turnos/{id}/confirmar
├── services/
│   └── reservaService.ts
└── store/
    └── reservaStore.ts      # Estado del wizard (paso actual, selecciones, datos)
```

---

## 7. Gestión del estado

| Tipo | Herramienta | Qué almacena |
|------|------------|-------------|
| Estado de sesión (global) | Zustand | `pacienteId: number | null` (persistido en sessionStorage) |
| Server state | TanStack Query | Slots disponibles, turnos del paciente, lista de espera |
| Estado del wizard de reserva | Zustand (no persistido) | Paso actual, fecha, hora, turno_id, datos del paciente |
| Estado local | useState | Modales abiertos, loading de acciones |

### Cache del servidor
- Disponibilidad: `staleTime: 60s` (los slots cambian con frecuencia)
- Mis turnos: `staleTime: 30s`
- Mutaciones: invalidar queries relacionadas (ej, al cancelar → invalidar mis turnos)

### Persistencia
- `sessionStorage` para el ID del paciente (se borra al cerrar la pestaña)
- NO persistir datos sensibles (DNI, teléfono)

---

## 8. Flujo de autenticación

No hay autenticación tradicional con email/password. El paciente se identifica por DNI.

### Registro (implícito al reservar)
1. El paciente ingresa nombre, apellido, DNI, teléfono en el paso 3 del wizard
2. `PUT /turnos/{id}/confirmar` envía los datos
3. Backend: si el DNI no existe, crea el paciente. Si existe, lo reutiliza
4. Front recibe el `paciente_id` en la respuesta

### Identificación para "Mis turnos"
1. Paciente ingresa su DNI en un formulario simple
2. `POST /pacientes` (crear o retornar existente) — permite conocer el `paciente_id`
3. Store guarda `pacienteId` en sessionStorage
4. Redirige a `/mis-turnos/:pacienteId`

### Logout implícito
- Al cerrar la pestaña se pierde el sessionStorage
- No hay botón de logout explícito

---

## 9. Comunicación con Backend

### Base URL
`VITE_API_BASE_URL=http://localhost:8000`

### Headers
```json
{
  "Content-Type": "application/json"
}
```
No se envía JWT ni API Key (el front cliente es público).

### Manejo de errores

| Código | Causa | Acción en Front |
|--------|-------|-----------------|
| 404 | Turno/paciente no encontrado | Mostrar mensaje + redirigir a inicio |
| 409 | Conflicto (turno activo, slot ocupado) | Toast con mensaje del backend |
| 422 | Validación de datos | Errores en campos del formulario |
| 500 | Error del servidor | Toast + reintentar |

---

## 10. Integración por módulos

### Inicio
- **Endpoint**: ninguno (página estática)
- **Componentes**: nada, solo links de navegación

### Reserva
- **GET /turnos/disponibles?fecha=YYYY-MM-DD**: `SlotResponse[]` (`{ hora_inicio, hora_fin, disponible }`)
- **POST /turnos**: body `{ fecha, hora_inicio }`, response `TurnoResponse`
- **PUT /turnos/{id}/confirmar**: body `{ nombre, apellido, dni, telefono }`, response `TurnoResponse`
- **Componentes**: StepFecha, StepHorario, StepDatos, StepConfirmacion
- **Estado**: reservaStore (Zustand, no persistido)

### Mis Turnos
- **POST /pacientes**: body `{ nombre, apellido, dni, telefono }`, response `PacienteRead`
- **GET /pacientes/{id}/turnos**: `TurnoRead[]`
- **PUT /turnos/{id}/cancelar**: response `TurnoResponse`
- **PUT /turnos/{id}/reprogramar**: body `{ nueva_fecha, nueva_hora_inicio }`, response `TurnoResponse`
- **Componentes**: TurnoCardList, TurnoDetalle, ReprogramarModal
- **Estado**: pacienteId en Zustand (sessionStorage)

### Lista de Espera
- **POST /lista-espera**: body `{ paciente_id, fecha_solicitada }`, response `ListaEsperaResponse`
- **DELETE /lista-espera/{id}**: 204 No Content
- **Componentes**: ListaEsperaForm

---

## 11. Modelos (TypeScript)

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
  creado_en: string
}

// Slot (disponibilidad)
interface Slot {
  hora_inicio: string
  hora_fin: string
  disponible: boolean
}

// Paciente
interface Paciente {
  id: number
  nombre: string
  apellido: string
  dni: string
  telefono: string
}

// Lista de espera
interface ListaEspera {
  id: number
  paciente_id: number
  fecha_solicitada: string
  creado_en: string
  notificado: boolean
  turno_ofrecido_id: number | null
  notificado_en: string | null
}
```

---

## 12. Convenciones

### Naming
- **Componentes**: PascalCase, rol descriptivo (`StepFecha`, `TurnoCardList`)
- **Hooks**: `use` + recurso (`useDisponibilidad`, `useReservaTurno`)
- **Servicios**: nombre del recurso + `Service` (`reservaService`, `turnoService`)
- **Archivos**: mismo nombre que el componente/hook/servicio

### Hooks
- Cada hook de TanStack Query sigue el patrón: `useRecurso()` para query, `useAccionRecurso()` para mutation
- Los hooks expone `isLoading`, `error`, `data` para que los componentes los consuman

### Servicios
- Funciones async que llaman a Axios
- Tipado estricto: parámetros y retorno tipados
- Un archivo por recurso

### Tipos
- Tipos compartidos en `@/types/`
- Schemas de Zod para formularios cerca del componente que los usa

---

## 13. Componentes reutilizables

| Componente | Descripción | Props clave |
|-----------|-------------|-------------|
| Button | Botón con variantes y loading | variant, loading, fullWidth, disabled, onClick |
| Input | Input con validación | label, name, error, type, register (RHF) |
| Modal | Modal responsive (fullscreen mobile, centered desktop) | isOpen, onClose, title, children |
| ConfirmDialog | Confirmación de acción | isOpen, title, message, confirmLabel, onConfirm, variant |
| Toast | Notificación | type, message, duration |
| Skeleton | Placeholder de carga | width, height, count |
| EmptyState | Estado sin datos | icon, title, description |
| EstadoBadge | Badge de estado de turno | estado |
| TurnoCard | Card de turno con acciones | turno, onCancel, onReschedule |

---

## 14. Manejo de errores

| Escenario | UX |
|-----------|-----|
| 404 (turno no encontrado) | Mensaje "El turno que buscás no existe" + link a inicio |
| 409 (turno activo) | Toast "Ya tenés un turno confirmado. Podés reprogramarlo desde Mis turnos" |
| 409 (slot ocupado) | Toast "Ese horario ya no está disponible. Elegí otro." + recargar slots |
| 422 (datos inválidos) | Errores en campos del formulario |
| 500 (error servidor) | Toast "Hubo un error. Intentá de nuevo." |
| Timeout / offline | Toast "No hay conexión con el servidor. Verificá tu internet." |

---

## 15. Performance

- **Lazy Loading**: `React.lazy()` para las rutas
- **TanStack Query**: staleTime de 60s para disponibilidad (evita refetch innecesario al cambiar de paso)
- **Code Splitting**: split por ruta
- **No virtualización**: volumen de datos bajo (máximo ~50 turnos en historial)

---

## 16. Accesibilidad

- **Mobile-first**: touch targets >= 44px, espaciado generoso
- **ARIA**: `role="progressbar"` para el wizard multi-paso, `aria-live` para toasts
- **Teclado**: navegación por Tab en formularios, Enter para confirmar
- **Contraste**: mínimo 4.5:1
- **Labels**: todo input con label visible

---

## 17. Testing

| Tipo | Herramienta | Qué testear |
|------|------------|-------------|
| Unitarios | Vitest | Hooks, servicios, store del wizard |
| Integración | Vitest + RTL | Flujo de reserva completo mockeado, cancelación, identificación por DNI |
| E2E | Playwright (opcional) | Reserva real contra backend de test |

### Mocks
- Mockear Axios con `msw`
- Scenario típico: mock de `GET /turnos/disponibles` → devuelve slots → usuario selecciona → mock de `POST /turnos` → etc.

### Casos críticos
- Reserva exitosa: paso 1 → 2 → 3 → 4 → confirmación
- Slots no disponibles: mostrar EmptyState + lista de espera
- DNI existente: auto-identificación sin pedir datos de nuevo
- Error 409 al confirmar: slot expiró, volver a paso 2
- Cancelar con confirmación: aparece modal, al confirmar se cancela

---

## 18. Evolución futura

- **Push notifications**: integrar con Service Worker para notificar al paciente sobre recordatorios ofertas de lista de espera sin Telegram
- **PWA**: manifest.json + service worker para instalar en el celular
- **Offline**: cachear disponibilidad reciente para consulta offline
- **Modo oscuro**: clase `dark` en Tailwind
- **Multi-idioma**: react-i18next si se requiere
