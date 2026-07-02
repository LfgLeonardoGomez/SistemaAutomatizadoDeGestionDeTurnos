# Front Admin (Super Admin)

## 1. Propósito

### Objetivo del sistema
Panel de administración del SaaS para que el operador del sistema (Super Admin) gestione los profesionales registrados: crearlos, activarlos/desactivarlos, consultar métricas globales del sistema.

### Alcance
- Iniciar sesión como Super Admin (email + password)
- Listar profesionales registrados con paginación
- Ver detalle de un profesional
- Crear un nuevo profesional (con generación automática de credenciales)
- Activar / desactivar un profesional
- Ver métricas globales del sistema (totales, no por profesional)
- Generar API key y telegram_secret_token automáticamente al crear profesional

### Fuera de alcance
- Ver datos particulares de un profesional (turnos, pacientes, configuraciones)
- Editar configuración de un profesional
- Acceder como profesional (usa Front Profesional)
- Gestionar turnos o pacientes
- Procesar pagos o facturación

---

## 2. Usuario objetivo

### Super Admin (operador del SaaS)
Persona encargada de administrar la plataforma. Crea cuentas de profesionales, las activa al habilitar un nuevo consultorio, las desactiva si corresponde. Consulta métricas globales para evaluar la adopción del sistema.

No existe el rol de "Super Admin" como profesional. Es una cuenta separada con permisos exclusivos sobre los endpoints `/admin/*`.

---

## 3. Mapa de funcionalidades

### Login

#### Objetivo
Autenticar al Super Admin con email + password.

#### Endpoint
`POST /admin/auth/login` — body: `{ email, password }` → response: `{ access_token, token_type }`

---

### Listar profesionales

#### Objetivo
Ver todos los profesionales registrados, con su estado (activo/inactivo) y datos básicos.

#### Información mostrada
- Tabla con columnas: ID, Nombre, Email, Especialidad, Estado (Activo/Inactivo), Fecha de registro
- Paginación (skip/limit)
- Búsqueda por nombre o email (client-side, sobre datos cargados)

#### Endpoint
`GET /admin/profesionales?skip=0&limit=100` → `ProfesionalAdminResponse[]` (id, nombre, especialidad, email, is_active, creado_en)

---

### Ver detalle de profesional

#### Objetivo
Consultar la información completa de un profesional específico.

#### Endpoint
`GET /admin/profesionales/{id}` → `ProfesionalAdminResponse`

---

### Crear profesional

#### Objetivo
Registrar un nuevo profesional en el sistema. El backend genera automáticamente:
- API key para autenticación de servicios
- Telegram secret token para validación de webhooks

#### Proceso
1. Super Admin completa formulario: nombre, email, especialidad, password
2. Backend crea el profesional con valores por defecto (horarios, duración del turno)
3. Backend genera y devuelve: api_key y telegram_secret_token (se muestran UNA SOLA VEZ)
4. Super Admin entrega estas credenciales al profesional

#### Endpoint
`POST /admin/profesionales` — body: `{ nombre, email, password, especialidad }` → response: `ProfesionalCreateResponse` (incluye api_key, telegram_secret_token)

---

### Activar / Desactivar profesional

#### Objetivo
Controlar qué profesionales pueden acceder al sistema.

#### Comportamiento
- **Activar**: el profesional puede iniciar sesión y operar su consultorio
- **Desactivar**: el profesional no puede iniciar sesión (sus datos se conservan)

#### Endpoints
`PUT /admin/profesionales/{id}/activar` → `ProfesionalAdminResponse`
`PUT /admin/profesionales/{id}/desactivar` → `ProfesionalAdminResponse`

---

### Métricas globales

#### Objetivo
Visualizar indicadores generales del sistema para evaluar adopción y uso.

#### Indicadores
- **Total profesionales**: cantidad de profesionales registrados
- **Profesionales activos**: cuántos pueden operar
- **Profesionales inactivos**: cuántos están desactivados
- **Total turnos**: todos los turnos creados
- **Turnos hoy**: turnos CONFIRMADO del día actual
- **Turnos confirmados 30d**: turnos CONFIRMADO en los últimos 30 días
- **Turnos cancelados 30d**: turnos CANCELADO en los últimos 30 días
- **Total pacientes**: pacientes registrados en el sistema
- **Tasa de confirmación 30d**: proporción de confirmados sobre total (float)
- **Tasa de cancelación 30d**: proporción de cancelados sobre total (float)

#### Endpoint
`GET /admin/metricas` → `GlobalMetricsResponse`

---

## 4. Estados del profesional

| Estado | Descripción |
|--------|-------------|
| Activo (`is_active: true`) | Puede iniciar sesión y operar |
| Inactivo (`is_active: false`) | No puede iniciar sesión, datos preservados |

---

## 5. Flujos principales

### Inicio de sesión
1. Super Admin ingresa email + password
2. Backend valida contra credenciales del Super Admin (configuradas via env vars)
3. Devuelve JWT con rol de Super Admin
4. Front almacena token, redirige a listado de profesionales

### Crear profesional
1. Super Admin navega a "Nuevo profesional"
2. Completa formulario: nombre, email, especialidad, password
3. Envía → `POST /admin/profesionales`
4. Backend crea profesional + genera api_key + telegram_secret_token
5. Front muestra pantalla de éxito con las credenciales generadas
6. **IMPORTANTE**: mostrar mensaje "Estas credenciales se muestran una sola vez. Copialas antes de cerrar."

### Activar/Desactivar
1. Super Admin ve listado de profesionales
2. Hace clic en activar/desactivar
3. ConfirmDialog: "¿Estás seguro de [activar/desactivar] a [nombre]?"
4. Confirma → `PUT /admin/profesionales/{id}/activar` o `/desactivar`
5. Tabla se actualiza con el nuevo estado

### Ver métricas globales
1. Super Admin navega a "Métricas"
2. Front llama a `GET /admin/metricas`
3. Muestra KPIs en cuadrícula

---

## 6. Reglas de negocio aplicables

| Código | Regla | Impacto en Front |
|--------|-------|-----------------|
| RN-GL-01 | Si un servicio externo falla, reintentar y loguear | Mostrar toast de error si la creación falla |
| — | Al crear profesional, las credenciales se muestran una sola vez | Pantalla de "credenciales generadas" con advertencia explícita |
| — | Super Admin no puede acceder a datos de negocio | No incluir navegación a turnos/pacientes |

---

## 7. Restricciones funcionales

- Super Admin ve TODOS los profesionales (no hay scoping)
- No puede modificar datos del profesional (solo activar/desactivar)
- Las métricas son globales (no filtrables por profesional)
- La creación requiere HTTPS (el endpoint de creación está protegido con `require_https`)

---

## 8. Objetivos no funcionales

- **Performance**: carga de listado < 2s incluso con 100+ profesionales
- **Responsive**: desktop prioritario (1280px+)
- **Seguridad**: JWT requerido en todos los endpoints `/admin/*`. HTTPS obligatorio para creación. Las credenciales generadas (api_key, telegram_secret_token) son secretos sensibles
- **Feedback**: toda acción (crear, activar, desactivar) debe tener toast de confirmación. La pantalla de credenciales generadas debe ser imposible de ignorar
