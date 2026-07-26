import { useMemo } from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import NativeShell from './NativeShell'
import { ErrorBoundary } from './components/ErrorBoundary'
import { NativeInvalidationProvider } from './hooks/NativeInvalidationProvider'
import { NativeChangeProvider } from './hooks/NativeChangeProvider'

function CockpitRuntime() {
  return (
    <NativeInvalidationProvider>
      <NativeChangeProvider>
        <ErrorBoundary label="Cockpit">
          <NativeShell />
        </ErrorBoundary>
      </NativeChangeProvider>
    </NativeInvalidationProvider>
  )
}

function App() {
  const router = useMemo(
    () => createBrowserRouter([{ path: '*', element: <CockpitRuntime /> }]),
    [],
  )

  return (
    <PorscheDesignSystemProvider>
      <RouterProvider router={router} />
    </PorscheDesignSystemProvider>
  )
}

export default App
