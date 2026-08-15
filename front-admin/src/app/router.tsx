import { lazy, Suspense } from 'react'
import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { AuthLayout } from '../shared/components/layout/AuthLayout'
import { AppLayout } from '../shared/components/layout/AppLayout'
import { ProtectedRoute } from '../shared/components/ProtectedRoute'

const LoginPage = lazy(() => import('../features/auth/pages/LoginPage'))
const ProfesionalesListPage = lazy(() => import('../features/profesionales/pages/ProfesionalesListPage'))
const ProfesionalDetailPage = lazy(() => import('../features/profesionales/pages/ProfesionalDetailPage'))
const MetricasPage = lazy(() => import('../features/metricas/pages/MetricasPage'))
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
          { path: '/', element: withSuspense(<ProfesionalesListPage />) },
          { path: '/profesionales/:id', element: withSuspense(<ProfesionalDetailPage />) },
          { path: '/metricas', element: withSuspense(<MetricasPage />) },
        ],
      },
    ],
  },
  { path: '*', element: withSuspense(<NotFoundPage />) },
]

export const router = createBrowserRouter(routes)
