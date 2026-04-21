import { BrowserRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from './Shell'

function App() {
  return (
    <PorscheDesignSystemProvider>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </PorscheDesignSystemProvider>
  )
}

export default App
