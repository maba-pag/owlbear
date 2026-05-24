import { useMemo, type ReactNode } from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from './Shell'
import { ErrorBoundary } from './components/ErrorBoundary'
import { CockpitProvider } from './hooks/CockpitProvider'
import * as EventSourceProviderModule from './hooks/EventSourceProvider'

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
      <CockpitProvider>
        <ErrorBoundary label="Cockpit">
          <Shell />
        </ErrorBoundary>
      </CockpitProvider>
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
