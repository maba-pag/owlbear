import { useMemo } from 'react'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import CockpitShell from './CockpitShell'
import { ErrorBoundary } from './components/ErrorBoundary'

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
      { path: '/', element: <Navigate to="/work" replace /> },
      { path: '*', element: <CockpitRuntime /> },
    ]),
    [],
  )

  return (
    <PorscheDesignSystemProvider>
      <RouterProvider router={router} />
    </PorscheDesignSystemProvider>
  )
}

export default App
