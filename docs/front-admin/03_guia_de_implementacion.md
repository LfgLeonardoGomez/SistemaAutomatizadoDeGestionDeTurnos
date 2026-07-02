# Front Admin (Super Admin) - Guía de Implementación

## 1. Objetivo del documento
Guía paso a paso para implementar el Front Admin (Super Admin) del sistema SaaS de gestión de turnos odontológicos.

---

## 2. Requisitos previos

- Node.js 18+
- Backend FastAPI corriendo en `http://localhost:8000`
- Super Admin configurado en backend (env vars `SUPER_ADMIN_EMAIL` y `SUPER_ADMIN_PASSWORD`)

### Variables de entorno
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 3. Setup inicial

```bash
npm create vite@latest front-admin -- --template react-ts
cd front-admin
npm install react-router-dom @tanstack/react-query zustand axios date-fns
npm install react-hook-form @hookform/resolvers zod
npm install -D tailwindcss @tailwindcss/vite
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

---

## 4. Orden de implementación

### Fase 1 — Base
- [ ] Proyecto Vite + React + TS
- [ ] Tailwind configurado
- [ ] Router con rutas
- [ ] AuthLayout (login)
- [ ] AppLayout (Sidebar + Header + Outlet)
- [ ] Sidebar: 3 items — Profesionales (icon building), Métricas (icon chart), nada más
- [ ] Header: nombre "Admin" + botón logout
- [ ] Página 404

### Fase 2 — Login
- [ ] LoginPage: formulario email + password
- [ ] Hook `useAdminLogin`: `POST /admin/auth/login`
- [ ] Zustand auth store (localStorage)
- [ ] ProtectedRoute
- [ ] Axios interceptor JWT + 401 redirect

### Fase 3 — Listar profesionales
- [ ] `GET /admin/profesionales`
- [ ] Tabla: ID, Nombre, Email, Especialidad, Estado (badge activo/inactivo), Fecha registro
- [ ] Paginación (skip/limit)
- [ ] Loading skeleton
- [ ] Empty state

### Fase 4 — Crear profesional
- [ ] Botón "Nuevo profesional" → abre modal
- [ ] Formulario: nombre, email, especialidad, password (min 8 chars)
- [ ] Validación Zod
- [ ] `POST /admin/profesionales`
- [ ] **Pantalla CredencialesGeneradas**: muestra api_key + telegram_secret_token con advertencia "Estas credenciales se muestran una sola vez. Copialas antes de cerrar."
- [ ] Botón "Ya copié las credenciales" → cierra pantalla, vuelve a listado
- [ ] Si intenta cerrar sin copiar → ConfirmDialog de advertencia
- [ ] Error handling: email duplicado (409)

### Fase 5 — Activar/Desactivar
- [ ] Botón toggle por fila en la tabla
- [ ] ConfirmDialog: "¿Estás seguro de [activar/desactivar] a [nombre]?"
- [ ] `PUT /admin/profesionales/{id}/activar` o `/desactivar`
- [ ] Invalidar query de listado post-mutación

### Fase 6 — Ver detalle
- [ ] `GET /admin/profesionales/{id}`
- [ ] Página de detalle: datos del profesional + estado

### Fase 7 — Métricas globales
- [ ] `GET /admin/metricas`
- [ ] Grid de 10 KPIs (2 filas × 5 o similar)
- [ ] Cada KPI: icono + valor grande + label
- [ ] Formateo: porcentajes (0.75 → 75%), números enteros

---

## 5. Componentes clave

| Componente | Fase | Detalle |
|-----------|------|---------|
| LoginPage | Fase 2 | Formulario centrado, email + password |
| ProfesionalTable | Fase 3 | Tabla con acciones |
| CreateProfesionalModal | Fase 4 | Modal con formulario |
| CredencialesGeneradas | Fase 4 | **Pantalla crítica**: credenciales one-time + advertencia |
| ActivarDesactivarButton | Fase 5 | Toggle con confirmación |
| GlobalKpiCard | Fase 7 | Card de KPI |
| MetricasGrid | Fase 7 | Grid responsivo de KPIs |

---

## 6. CredencialesGeneradas — Componente crítico

```typescript
// Comportamiento:
// 1. Muestra api_key y telegram_secret_token en inputs de solo lectura
// 2. Cada input tiene botón "Copiar" que copia al portapapeles
// 3. Mensaje visible: "⚠️ Estas credenciales se muestran UNA SOLA VEZ"
// 4. Botón "Ya copié las credenciales" → cierra y vuelve al listado
// 5. Si intenta cerrar con X o click fuera → ConfirmDialog:
//    "¿Estás seguro? No vas a poder volver a ver estas credenciales."
```

---

## 7. Testing

### Casos críticos
- Login exitoso → token guardado, redirect a listado
- Login fallido → mensaje de error
- Crear profesional exitoso → pantalla de credenciales visible
- Cerrar pantalla de credenciales → ConfirmDialog
- Activar profesional → estado cambia en tabla sin recargar
- Desactivar profesional → ConfirmDialog → estado cambia
- Error 409 al crear → toast sin cerrar modal
- Error 401 → redirect a login

---

## 8. Checklist

- [ ] Proyecto creado con Vite + React + TS
- [ ] Tailwind configurado
- [ ] Router con lazy loading
- [ ] Login funcional
- [ ] Listar profesionales con paginación
- [ ] Crear profesional con pantalla de credenciales
- [ ] Activar/Desactivar con confirmación
- [ ] Detalle de profesional
- [ ] Métricas globales
- [ ] Manejo de errores (401, 404, 409, 422)
- [ ] ConfirmDialog en acciones destructivas
- [ ] Loading states en componentes async
- [ ] Tests pasando
