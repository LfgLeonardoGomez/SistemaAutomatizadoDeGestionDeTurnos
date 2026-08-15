import { lazy, Suspense } from 'react'
import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { AuthLayout } from '../shared/components/layout/AuthLayout'
import { AppLayout } from '../shared/components/layout/AppLayout'
import { ProtectedRoute } from '../shared/components/ProtectedRoute'

const LoginPage = lazy(() => import('../features/auth/pages/LoginPage'))
const DashboardPage = lazy(() => import('../features/dashboard/pages/DashboardPage'))
const AgendaPage = lazy(() => import('../features/agenda/pages/AgendaPage'))
const PacientesListPage = lazy(() => import('../features/pacientes/pages/PacientesListPage'))
const PacienteDetailPage = lazy(() => import('../features/pacientes/pages/PacienteDetailPage'))
const ConfiguracionPage = lazy(() => import('../features/configuracion/pages/ConfiguracionPage'))
const MetricasPage = lazy(() => import('../features/metricas/pages/MetricasPage'))
const IntegracionesPage = lazy(() => import('../features/integraciones/pages/IntegracionesPage'))
const NotFoundPage = lazy(() => import('../pages/NotFoundPage'))

function withSuspense(element: React.ReactNode) {
  return <Suspense fallback={null}>{element}</Suspense>
}

export const routes: RouteObject[] = [
  {
    element: <AuthLayout />,
    children: [{ path: '/login', element: withSuspense(<LoginPage />) }],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: '/', element: withSuspense(<DashboardPage />) },
          { path: '/agenda', element: withSuspense(<AgendaPage />) },
          { path: '/pacientes', element: withSuspense(<PacientesListPage />) },
          { path: '/pacientes/:id', element: withSuspense(<PacienteDetailPage />) },
          { path: '/configuracion', element: withSuspense(<ConfiguracionPage />) },
          { path: '/metricas', element: withSuspense(<MetricasPage />) },
          { path: '/integraciones', element: withSuspense(<IntegracionesPage />) },
        ],
      },
    ],
  },
  { path: '*', element: withSuspense(<NotFoundPage />) },
]

export const router = createBrowserRouter(routes)
