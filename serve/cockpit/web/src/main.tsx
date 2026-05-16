import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { load } from '@porsche-design-system/components-js'
import './tailwind.css'
import './tokens.css'
import App from './App'

const REQUIRED_PDS_ELEMENTS = ['p-button', 'p-icon', 'p-tabs', 'p-tabs-item'] as const

function installPdsCdnTrap(): void {
  const docWithPds = document as { porscheDesignSystem?: Record<string, unknown> }
  const pds = (docWithPds.porscheDesignSystem ??= {})
  let assignedCdn: unknown

  Object.defineProperty(pds, 'cdn', {
    configurable: true,
    enumerable: true,
    get(): { url: string } & Record<string, unknown> {
      const fromAssigned =
        assignedCdn && typeof assignedCdn === 'object'
          ? (assignedCdn as Record<string, unknown>)
          : {}

      return { ...fromAssigned, url: window.location.origin }
    },
    set(value: unknown): void {
      assignedCdn = value
    },
  })
}

async function waitForRequiredPdsElements(): Promise<void> {
  await Promise.all(REQUIRED_PDS_ELEMENTS.map((tagName) => customElements.whenDefined(tagName)))
}

async function bootstrap(): Promise<void> {
  installPdsCdnTrap()
  load()
  await waitForRequiredPdsElements()

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void bootstrap()
