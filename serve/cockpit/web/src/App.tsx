import { BrowserRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from './Shell'
import { EventSourceProvider } from './hooks/EventSourceProvider'

function App() {
  return (
    <PorscheDesignSystemProvider>
      <BrowserRouter>
        <EventSourceProvider url="/api/events">
          <Shell />
        </EventSourceProvider>
      </BrowserRouter>
    </PorscheDesignSystemProvider>
  )
}

export default App

