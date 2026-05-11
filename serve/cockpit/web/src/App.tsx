import { BrowserRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from './Shell'
import { ErrorBoundary } from './components/ErrorBoundary'
import { EventSourceProvider } from './hooks/EventSourceProvider'

function App() {
  return (
    <PorscheDesignSystemProvider>
      <BrowserRouter>
        <EventSourceProvider url="/api/events">
          <ErrorBoundary label="Cockpit">
            <Shell />
          </ErrorBoundary>
        </EventSourceProvider>
      </BrowserRouter>
    </PorscheDesignSystemProvider>
  )
}

export default App

