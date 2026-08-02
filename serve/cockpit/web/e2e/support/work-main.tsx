import { createRoot } from 'react-dom/client'
import { load } from '@porsche-design-system/components-js'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import '../../src/tailwind.css'
import '../../src/custom-tokens.css'
import WorkPortfolioPage from '../../src/pages/WorkPortfolioPage'

const documentWithPds = document as { porscheDesignSystem?: Record<string, unknown> }
const pds = (documentWithPds.porscheDesignSystem ??= {})
let assignedCdn: unknown
Object.defineProperty(pds, 'cdn', {
  configurable: true,
  get: () => ({
    ...(assignedCdn && typeof assignedCdn === 'object' ? assignedCdn as Record<string, unknown> : {}),
    url: window.location.origin,
  }),
  set: (value: unknown) => {
    assignedCdn = value
  },
})
load()

createRoot(document.getElementById('root')!).render(
  <PorscheDesignSystemProvider>
    <WorkPortfolioPage />
  </PorscheDesignSystemProvider>,
)
