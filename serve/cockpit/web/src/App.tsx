import { type ReactNode } from 'react'
import { BrowserRouter } from 'react-router'
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

function App() {
  return (
    <PorscheDesignSystemProvider>
      <BrowserRouter>
        <EventSourceProvider url="/api/events">
          <CockpitProvider>
            <ErrorBoundary label="Cockpit">
              <Shell />
            </ErrorBoundary>
          </CockpitProvider>
        </EventSourceProvider>
      </BrowserRouter>
    </PorscheDesignSystemProvider>
  )
}

export default App
