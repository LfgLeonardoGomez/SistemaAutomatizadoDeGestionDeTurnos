# Front Admin (Super Admin) - Arquitectura y Componentes

## 1. Objetivo del documento
Describir la arquitectura técnica, estructura de directorios, árbol de componentes y flujo de datos para implementar el Front Admin (Super Admin) del sistema SaaS de gestión de turnos odontológicos.

---

## 2. Stack tecnológico

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| Framework | React 18+ con Vite | Mismo stack que los otros frontends, consistencia |
| Lenguaje | TypeScript 5+ strict | Tipado fuerte |
| Build Tool | Vite | Build rápido |
| Router | React Router v6+ | Layout protegido + rutas públicas |
| Manejo de estado | Zustand (auth) + TanStack Query | Estado mínimo, solo token + datos del admin |
| Estilos | Tailwind CSS 3+ | Consistencia con el resto del ecosistema |
| Formularios | React Hook Form + Zod | Validación de creación de profesional |
| Cliente HTTP | Axios | Interceptor JWT, manejo de errores |
| Testing | Vitest + React Testing Library | Unitarios + integración |

---

## 3. Arquitectura general

Este front es **deliberadamente simple**: son pocas pantallas y poca lógica. No hay agenda, turnos, pacientes ni configuraciones complejas.

### Principios
- **Simplicidad máxima**: menos de 5 pantallas. Cada pantalla tiene una sola responsabilidad
- **Seguridad primero**: las credenciales generadas se muestran una sola vez. Confirmación en cada acción destructiva (desactivar)
- **Solo lectura de métricas**: el admin ve datos globales pero no puede modificarlos

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
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── ConfirmDialog.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   ├── Badge.tsx
│   │   │   └── EmptyState.tsx
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx       # Sidebar + Header + Outlet
│   │   │   ├── AuthLayout.tsx      # Layout minimal para login
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   └── profesional/
│   │       └── ProfesionalRow.tsx
│   ├── hooks/
│   │   └── useAuth.ts
│   ├── services/
│   │   └── api.ts                  # Axios instance + JWT interceptor
│   └── types/
│       └── index.ts
│
├── features/
│   ├── auth/
│   │   ├── pages/
│   │   │   └── LoginPage.tsx
│   │   ├── hooks/
│   │   │   └── useAdminLogin.ts
│   │   └── services/
│   │       └── authService.ts
│   │
│   ├── profesionales/
│   │   ├── pages/
│   │   │   ├── ProfesionalesListPage.tsx
│   │   │   └── ProfesionalDetailPage.tsx
│   │   ├── components/
│   │   │   ├── CreateProfesionalModal.tsx
│   │   │   ├── CredencialesGeneradas.tsx  # Pantalla one-time de credenciales
│   │   │   ├── ProfesionalTable.tsx
│   │   │   └── ActivarDesactivarButton.tsx
│   │   ├── hooks/
│   │   │   ├── useProfesionales.ts
│   │   │   └── useCrearProfesional.ts
│   │   └── services/
│   │       └── profesionalService.ts
│   │
│   └── metricas/
│       ├── pages/
│       │   └── MetricasPage.tsx
│       ├── components/
│       │   ├── GlobalKpiCard.tsx
│       │   └── MetricasGrid.tsx
│       ├── hooks/
│       │   └── useGlobalMetricas.ts
│       └── services/
│           └── metricasService.ts
│
└── assets/
    └── logo.svg
```

---

## 5. Sistema de rutas

```
/login                  → LoginPage           (pública, AuthLayout)
/                       → ProfesionalesList   (protegida, AppLayout)
/profesionales/:id      → ProfesionalDetail   (protegida, AppLayout)
/metricas               → MetricasPage        (protegida, AppLayout)
*                       → NotFoundPage
```

### Layouts
- **AuthLayout**: centrado, fondo simple, solo login
- **AppLayout**: sidebar (3 items: Profesionales, Métricas) + Header + Outlet

---

## 6. Arquitectura de componentes

### Sidebar (3 items)
```
Dashboard (icon: building) → ProfesionalesListPage
Métricas (icon: chart)     → MetricasPage
```

No hay más items. No hay agenda, no hay pacientes, no hay configuración.

### Componentes clave

| Componente | Descripción |
|-----------|-------------|
| CreateProfesionalModal | Modal con formulario: nombre, email, especialidad, password |
| CredencialesGeneradas | Pantalla one-time: muestra api_key + telegram_secret_token + advertencia |
| ProfesionalTable | Tabla con columnas: ID, Nombre, Email, Especialidad, Estado, Acciones |
| ActivarDesactivarButton | Toggle button con ConfirmDialog |
| GlobalKpiCard | Card de KPI con valor grande + label + icono |
| MetricasGrid | Grid de KPIs globales |

---

## 7. Gestión del estado

| Tipo | Herramienta | Qué almacena |
|------|------------|-------------|
| Estado global | Zustand | `auth: { token }` persistido en localStorage |
| Server state | TanStack Query | Lista de profesionales, detalle, métricas globales |

---

## 8. Flujo de autenticación

- `POST /admin/auth/login` con `{ email, password }`
- Devuelve `{ access_token, token_type: "bearer" }`
- Guardar token en Zustand (localStorage)
- Axios interceptor: `Authorization: Bearer <token>`
- 401 → logout + redirección a login
- No hay refresh token

---

## 9. Comunicación con Backend

### Base URL
`VITE_API_BASE_URL=http://localhost:8000`

### Endpoints

| Método | Endpoint | Uso |
|--------|----------|-----|
| POST | `/admin/auth/login` | Login Super Admin |
| GET | `/admin/profesionales` | Listar profesionales |
| GET | `/admin/profesionales/{id}` | Detalle profesional |
| POST | `/admin/profesionales` | Crear profesional (requiere HTTPS) |
| PUT | `/admin/profesionales/{id}/activar` | Activar |
| PUT | `/admin/profesionales/{id}/desactivar` | Desactivar |
| GET | `/admin/metricas` | Métricas globales |

---

## 10. Modelos (TypeScript)

```typescript
interface SuperAdminLoginRequest {
  email: string
  password: string
}

interface TokenResponse {
  access_token: string
  token_type: string  // "bearer"
}

interface ProfesionalCreateRequest {
  nombre: string
  email: string
  password: string     // min 8 caracteres
  especialidad: string
}

interface ProfesionalCreateResponse {
  id: number
  nombre: string
  email: string
  especialidad: string
  is_active: boolean
  duracion_turno: number
  horario_inicio: string
  horario_fin: string
  dias_atencion: string[]
  api_key: string            // ⚠️ Se muestra una sola vez
  telegram_secret_token: string  // ⚠️ Se muestra una sola vez
}

interface ProfesionalAdminResponse {
  id: number
  nombre: string
  especialidad: string
  email: string
  is_active: boolean
  creado_en: string
}

interface GlobalMetrics {
  total_profesionales: number
  profesionales_activos: number
  profesionales_inactivos: number
  total_turnos: number
  turnos_hoy: number
  turnos_confirmados_30d: number
  turnos_cancelados_30d: number
  total_pacientes: number
  tasa_confirmacion_30d: number
  tasa_cancelacion_30d: number
}
```

---

## 11. Manejo de errores HTTP

| Código | Causa | Acción |
|--------|-------|--------|
| 401 | Token inválido | Logout + redirect login |
| 404 | Profesional no encontrado | Toast + volver a listado |
| 409 | Email duplicado | Toast "Ya existe un profesional con ese email" |
| 422 | Datos inválidos | Errores en campos del formulario |

---

## 12. Componentes reutilizables

| Componente | Props | Notas |
|-----------|-------|-------|
| Button | variant, size, loading | Mismo estilo que Front Profesional |
| Input | label, name, error, type | Con validación |
| Modal | isOpen, onClose, title | Para crear profesional |
| ConfirmDialog | message, onConfirm | Para activar/desactivar |
| Toast | type, message | Success/error |
| Skeleton | count | Loading de tabla |
| Badge | variant, children | Estado activo (green) / inactivo (red) |
| EmptyState | title, description | Sin profesionales aún |

---

## 13. Testing

### Casos críticos
- Login exitoso → redirige a listado
- Login fallido → muestra error
- Crear profesional → muestra pantalla de credenciales
- Cerrar pantalla de credenciales sin copiar → confirmación "¿Las copiaste?"
- Activar/desactivar → ConfirmDialog → tabla actualizada
- Error 409 al crear (email duplicado) → toast + no cerrar modal

---

## 14. Consideraciones de seguridad

- La pantalla `CredencialesGeneradas` debe tener un botón "Ya copié las credenciales" que NO permita volver atrás
- Al cerrar la pantalla de credenciales sin copiar, mostrar ConfirmDialog: "¿Estás seguro? Estas credenciales no se podrán volver a ver"
- Los endpoints de creación y activación requieren HTTPS (el backend lo fuerza con `require_https`)
- No almacenar `api_key` ni `telegram_secret_token` en el front después de mostrarlos
