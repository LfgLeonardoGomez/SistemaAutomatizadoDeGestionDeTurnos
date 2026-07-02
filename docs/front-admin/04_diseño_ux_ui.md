# Diseño UX/UI — Front Admin (Super Admin)

## Sistema de Diseño

El sistema está diseñado para un entorno de gestión dental, priorizando "Claridad Clínica" a través de una estética Corporativa/Moderna equilibrada.

El usuario target es el **Super Admin** (operador del SaaS), que gestiona profesionales y consulta métricas globales. No hay gestión de turnos, pacientes ni configuraciones individuales.

### Colores

Paleta anclada en un Teal profundo como color primario, elegido por su asociación con higiene, estabilidad y profesionalismo en entornos clínicos.

| Token | Hex | Uso |
|-------|-----|-----|
| `primary` | `#00614f` | Acciones principales, estados activos de navegación |
| `primary-container` | `#0d7c66` | Botones primarios, fondos de acento |
| `on-primary-container` | `#bbffe9` | Texto sobre primary-container |
| `on-primary` | `#ffffff` | Texto sobre primary |
| `secondary` | `#44655b` | Elementos secundarios |
| `secondary-container` | `#c3e8da` | Fondos de acento secundario |
| `error` | `#ba1a1a` | Errores, desactivar, alertas críticas |
| `error-container` | `#ffdad6` | Fondo de mensajes de error |
| `background` | `#f6faf7` | Fondo general (gris muy frío, sensación "sanitaria") |
| `surface` | `#f6faf7` | Superficie base |
| `surface-container-lowest` | `#ffffff` | Tarjetas, contenedores accionables |
| `surface-container-low` | `#f0f5f1` | Fondos de tabla, headers secundarios |
| `surface-container` | `#ebefeb` | Headers de tabla, hover states |
| `on-surface` | `#181d1b` | Texto principal |
| `on-surface-variant` | `#3e4945` | Texto secundario, labels |
| `outline` | `#6e7a75` | Bordes estándar |
| `outline-variant` | `#bdc9c4` | Bordes suaves, separadores |

**Colores semánticos**: Verde (`#22C55E`) éxito, Rojo (`#EF4444`) danger/alerta, Ámbar (`#F59E0B`) warning.

### Tipografía

Familia: **Inter** — utilitaria, performante en tamaños pequeños.

| Nivel | Tamaño | Weight | Line Height |
|-------|--------|--------|-------------|
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

- **Sidebar**: fija 60px (solo 2 íconos). Contenido fluido.
- **Base rítmica**: 8px gobierna todas las relaciones espaciales.
- **Breakpoints**: Mobile (<768px), Tablet (768-1280px), Desktop (>1280px).

### Elevation & Depth

- **Sombras**: `0 2px 4px rgba(31, 41, 55, 0.05)` — única sombra del sistema.
- **Bordes**: `1px solid outline-variant` en inputs, filas de tabla.
- **Active States**: borde 2px primary + `box-shadow 0 0 0 2px rgba(0, 97, 79, 0.1)`.

### Shapes

| Tamaño | Valor | Uso |
|--------|-------|-----|
| `rounded-lg` | 8px | Cards, botones, inputs |
| `rounded-xl` | 12px | Modales |
| `rounded-full` | 9999px | Status chips (pill) |

### Componentes Globales

- **Botones**: Primarios → sólidos teal + texto blanco. Secundarios → outline teal. Ambos con 8px rounding.
- **Input Fields**: Borde 1px `outline-variant`. On focus: borde primary + glow.
- **Status Chips**: Pill-shaped, fondo 10% opacidad del color semántico.
- **Data Tables**: Filas con hover sutil (`#f3f6f4`).
- **Cards**: Fondo blanco, 8px radius, `shadow-sm`. Nunca anidadas.

---

## Pantallas del Super Admin

---

### 1. Login — `super_admin_login/`

**Propósito**: Autenticación del Super Admin.

#### Estructura

```
+------------------------------------------+
|              Brand Section                 |
|   [ícono dentistry]                       |
|   Sistema de Gestión de Turnos            |
|   PANEL DE ADMINISTRACIÓN                 |
+------------------------------------------+
|  +--------------------------------------+ |
|  |          Login Card                   | |
|  |                                      | |
|  |  Email                               | |
|  |  [mail] [________________________]   | |
|  |                                      | |
|  |  Contraseña                          | |
|  |  [lock] [____________________][eye]  | |
|  |                                      | |
|  |  [     Iniciar Sesión           ]    | |
|  |                                      | |
|  |  [!] Credenciales inválidas (hidden) | |
|  +--------------------------------------+ |
|                                           |
|  © 2024 Sistema de Gestión de Turnos      |
+------------------------------------------+
```

**Nota**: No hay link "¿Olvidaste tu contraseña?" — no existe endpoint de recuperación.

#### Componentes
- **Brand Identity**: Ícono `dentistry` en contenedor circular.
- **Login Card**: `surface-container-lowest` con borde, padding responsive.
- **Email Input**: Ícono `mail` a izquierda, placeholder `admin@ejemplo.com`.
- **Password Input**: Ícono `lock` a izquierda, toggle visibilidad a derecha.
- **Submit Button**: Full-width, primary teal.
- **Error Message**: Banner oculto con ícono `error`, fondo `error-container`, animación shake.

#### Estados
| Estado | Trigger | Feedback |
|--------|---------|----------|
| **Initial** | Página cargada | Fade-in brand section |
| **Loading** | Submit | Botón disabled, texto "Verificando...", spinner |
| **Error** | Credenciales inválidas | Banner error, animación shake |

---

### 2. Listado de Profesionales — `super_admin_profesionales_listado/`

**Propósito**: Visualizar, buscar y gestionar profesionales registrados.

#### Estructura

```
+----+---------------------------------------------+
| S  | +-------------------------------------------+|
| i  | | TopAppBar                                 ||
| d  | | Admin Portal | Admin            [Logout]  ||
| e  | +-------------------------------------------+|
| b  | | Page Header                               ||
| a  | | Profesionales                             ||
| r  | | Gestión de especialistas... [+ Nuevo]     ||
|    | +-------------------------------------------+|
| 6  | | Search Bar                                ||
| 0  | | [ Buscar por nombre o email...       ]    ||
| p  | +-------------------------------------------+|
| x  | | Data Table                                ||
|    | | ID | Nombre | Email | Esp. | Est. | Acc.  ||
|    | | #9021 | Dr. Ricardo Mendoza | ...         ||
|    | | #9022 | Dra. Lucia Sanchez   | ...         ||
|    | | #9015 | Dr. Alberto Garcia   | ... (inac)  ||
|    | | ...                                       ||
|    | +-------------------------------------------+|
|    | | Pagination: < 1 2 3 ... 5 >   1-10 de 48  ||
|    | +-------------------------------------------+|
+----+---------------------------------------------+
```

**Nota**: No hay filtro por estado. El backend solo acepta `skip` y `limit`. La búsqueda es client-side sobre los resultados cargados (filtra por nombre o email).

#### Componentes
- **SideNavBar (60px)**: Fijo a izquierda. Íconos: `group` (Profesionales, activo), `monitoring` (Métricas).
- **TopAppBar**: Título "Admin Portal", botón Logout.
- **Page Header**: Título "Profesionales" + botón `+ Nuevo profesional`.
- **Search Bar**: Input con ícono `search`. Filtra client-side por nombre/email.
- **Data Table**: Columnas: ID, Nombre, Email, Especialidad, Estado (chip pill), Acciones (ver + desactivar/activar).
  - Fila inactiva: opacidad reducida, chip gris.
- **Pagination**: Navegación con números, texto "Mostrando X a Y de Z profesionales".

#### Estados de Fila
| Estado | Visual |
|--------|--------|
| **Activo** | Avatar a color, chip verde "Activo", botón "Desactivar" (texto error) |
| **Inactivo** | Fila grisácea (`opacity-60`), chip gris "Inactivo", botón "Activar" (texto primary) |

---

### 3. Modal Crear Profesional — `super_admin_modal_crear_profesional/`

**Propósito**: Formulario modal para registrar un nuevo profesional.

#### Estructura

```
+------------------------------------------+
|          (fondo dashboard blur)           |
|  +--------------------------------------+ |
|  | Nuevo profesional              [X]   | |
|  |--------------------------------------| |
|  | Nombre Completo                      | |
|  | [Dr. Alejandro Méndez             ]  | |
|  |                                      | |
|  | Correo Electrónico                   | |
|  | [profesional@clinica.com          ]  | |
|  |                                      | |
|  | Especialidad                         | |
|  | [Odontología general              ]  | |
|  |                                      | |
|  | Contraseña    | Confirmar Contraseña | |
|  | [           ] | [                  ] | |
|  |                                      | |
|  |--------------------------------------| |
|  |          [Cancelar] [Crear profesional]| |
|  +--------------------------------------+ |
+------------------------------------------+
```

**Nota**: `especialidad` es un campo de texto libre, no un select con opciones fijas. No hay validación de especialidades predefinidas.

#### Componentes
- **Modal Overlay**: Fixed inset, backdrop blur, fondo `rgba(24,29,27,0.4)`.
- **Header**: Título "Nuevo profesional", botón `close`.
- **Form Body**: Inputs texto/email/password. Todos con label arriba.
- **Footer**: Cancelar (outline) + Crear (primary sólido).

#### Estados
| Estado | Trigger | Feedback |
|--------|---------|----------|
| **Open** | Click "Nuevo profesional" | Modal scale-in |
| **Submitting** | Click "Crear profesional" | Botón disabled, spinner |
| **Success** | API responde 201 | Cierra modal, abre CredencialesGeneradas |
| **Error 409** | Email duplicado | Toast "Ya existe un profesional con ese email", modal se mantiene |
| **Error 422** | Datos inválidos | Errores en campos del formulario |

---

### 4. Credenciales Generadas — `super_admin_credenciales_generadas/`

**Propósito**: Modal de éxito posterior a la creación, mostrando API Key + Telegram Token. **No se puede cerrar con X, Escape ni click fuera.**

#### Estructura

```
+------------------------------------------+
|      (blur overlay, sin botón X)          |
|  +--------------------------------------+ |
|  |    [shield_lock icon]                 | |
|  |  ¡Profesional creado con éxito!       | |
|  |--------------------------------------| |
|  |  ⚠️ Estas credenciales se muestran   | |
|  |  UNA SOLA VEZ. Copialas antes de      | |
|  |  cerrar esta ventana.                 | |
|  |--------------------------------------| |
|  |  🔑 API Key                          | |
|  |  [pk_live_51Msz...]        [Copiar]  | |
|  |                                      | |
|  |  ✈️ Telegram Secret Token            | |
|  |  [6284910234...]          [Copiar]   | |
|  |--------------------------------------| |
|  |  [   Ya copié las credenciales    ]  | |
|  +--------------------------------------+ |
+------------------------------------------+
```

#### Comportamiento
- Escape deshabilitado, click fuera no cierra
- `beforeunload` si el usuario intenta recargar la página
- Cada input readonly con botón "Copiar" (feedback "¡Copiado!" por 2s)
- Único botón "Ya copié las credenciales" para cerrar

---

### 5. Métricas Globales — `super_admin_metricas_globales/`

**Propósito**: Dashboard ejecutivo con KPIs globales del sistema.

#### Estructura

```
+----+---------------------------------------------------+
| S  | TopAppBar                                          |
| i  | Admin Portal                         [Logout]      |
| d  +---------------------------------------------------+
| e  | Header: Métricas globales                          |
| b  | Estado operativo de la red de profesionales        |
| a  +---------------------------------------------------+
| r  | KPI Grid (2 columnas desktop, 5 filas × 2)         |
|    | [Total 142] [Activos 128]                          |
| 6  | [Inactivos 14] [Total turnos 3.482]               |
| 0  | [Turnos hoy 214⭐] [Confirmados 30d 2.840]       |
| p  | [Cancelados 30d 642] [Total pacientes 8.912]       |
| x  | [Tasa confirmación 81.5%] [Tasa cancel. 22.6%⚠️]  |
+----+---------------------------------------------------+
```

**Notas importantes**:
- No hay selector de rango de fechas (la API siempre devuelve métricas globales actuales)
- No hay botón "Exportar reporte" (no existe endpoint)
- No hay charts, pie charts ni progress bars (la API solo retorna valores escalares)
- No hay "Top clínicas" ni datos regionales (el sistema es single-tenant, solo existen profesionales)
- Todos los valores son numéricos planos, sin series temporales

#### KPIs (10 cards)

| Métrica | Tipo | Nota |
|---------|------|------|
| Total profesionales | entero | — |
| Profesionales activos | entero | Chip verde |
| Profesionales inactivos | entero | Chip gris |
| Total turnos | entero | — |
| Turnos hoy | entero | Card destacada (azul/fondo primary-container) |
| Turnos confirmados 30d | entero | — |
| Turnos cancelados 30d | entero | — |
| Total pacientes | entero | — |
| Tasa confirmación 30d | porcentaje (0-100%) | Verde si alto |
| Tasa cancelación 30d | porcentaje (0-100%) | Rojo si >20% |

#### Componentes
- **KPI Grid**: 10 cards en grilla 2 columnas desktop.
- **Card destacada "Turnos hoy"**: fondo primary-container, borde-bottom primary.
- **Card "Tasa cancelación"**: si >20%, borde error, label "ALERTA".
- **Skeleton**: mientras carga, 6 cards placeholder grises.

---

## Resumen de Componentes Compartidos

| Componente | Aparece en | Variantes |
|-----------|------------|-----------|
| **SideNavBar 60px** | Listado, Métricas | 2 íconos: group, monitoring |
| **TopAppBar** | Listado, Métricas | Con botón Logout |
| **Data Table** | Listado | Con paginación, sin avatar |
| **Chip Status** | Listado | Verde (Activo), Gris (Inactivo) |
| **Modal** | Crear Profesional, Credenciales | Formulario (500px), Confirmación |
| **Primary Button** | Todas | Sólido teal, con/sin loading |
| **Outline Button** | Login, Modal Crear | Borde primary |
| **Input Field** | Login, Modal Crear | Texto, email, password, readonly |
| **Card KPI** | Métricas | 10 cards en grid |
