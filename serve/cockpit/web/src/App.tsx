import { useMemo, type ReactNode } from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from './Shell'
import { ErrorBoundary } from './components/ErrorBoundary'
import { CockpitProvider } from './hooks/CockpitProvider'
import * as EventSourceProviderModule from './hooks/EventSourceProvider'
import { NativeInvalidationProvider } from './hooks/NativeInvalidationProvider'

function PassthroughProvider({ children }: { children: ReactNode; url?: string }) {
  return <>{children}</>
}

const EventSourceProvider =
  'EventSourceProvider' in EventSourceProviderModule
    ? EventSourceProviderModule.EventSourceProvider
    : PassthroughProvider

function CockpitRuntime() {
  return (
    <EventSourceProvider url="/api/events">
      <NativeInvalidationProvider>
        <CockpitProvider>
          <ErrorBoundary label="Cockpit">
            <Shell />
          </ErrorBoundary>
        </CockpitProvider>
      </NativeInvalidationProvider>
    </EventSourceProvider>
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
