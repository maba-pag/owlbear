import { BrowserRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from './Shell'
import { ErrorBoundary } from './components/ErrorBoundary'
import { CockpitProvider } from './hooks/CockpitProvider'
import { EventSourceProvider } from './hooks/EventSourceProvider'

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

