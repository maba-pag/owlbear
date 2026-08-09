import { useMemo } from 'react'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router'
import { PorscheDesignSystemProvider, PToast } from '@porsche-design-system/components-react'
import CockpitShell from './CockpitShell'
import { ErrorBoundary } from './components/ErrorBoundary'
import { legacyRouteRedirects } from './routes'

function CockpitRuntime() {
  return (
    <ErrorBoundary label="Cockpit">
      <CockpitShell />
    </ErrorBoundary>
  )
}

function App() {
  const router = useMemo(
    () => createBrowserRouter([
      ...legacyRouteRedirects.map(({ from, to }) => ({
        path: from,
        element: <Navigate to={to} replace />,
      })),
      { path: '*', element: <CockpitRuntime /> },
    ]),
    [],
  )

  return (
    <PorscheDesignSystemProvider>
      <RouterProvider router={router} />
      <PToast />
    </PorscheDesignSystemProvider>
  )
}

export default App
