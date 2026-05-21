import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { load } from '@porsche-design-system/components-js'
import './tailwind.css'
import './custom-tokens.css'
import App from './App'

const REQUIRED_PDS_ELEMENTS = ['p-canvas', 'p-button', 'p-icon', 'p-tabs', 'p-tabs-item'] as const

function applyTokenFallbacks(): void {
  const rootStyle = document.documentElement.style
  const computed = getComputedStyle(document.documentElement)

  if (!computed.getPropertyValue('--p-color-canvas').trim()) {
    rootStyle.setProperty('--p-color-canvas', 'rgb(255 255 255)')
  }
  if (!computed.getPropertyValue('--p-spacing-static-md').trim()) {
    rootStyle.setProperty('--p-spacing-static-md', '1rem')
  }
  if (!computed.getPropertyValue('--p-font-porsche-next').trim()) {
    rootStyle.setProperty('--p-font-porsche-next', '"Porsche Next", "Helvetica Neue", Arial, sans-serif')
  }
  if (!computed.getPropertyValue('--color-focus').trim()) {
    rootStyle.setProperty('--color-focus', 'rgb(26 68 234)')
  }
}

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
  applyTokenFallbacks()
  await waitForRequiredPdsElements()

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void bootstrap()
