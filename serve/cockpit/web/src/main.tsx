import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { load } from '@porsche-design-system/components-js'
import './tailwind.css'
import './custom-tokens.css'
import App from './App'

const REQUIRED_PDS_ELEMENTS = ['p-button', 'p-icon', 'p-tabs', 'p-tabs-item'] as const
const PDS_BOOTSTRAP_TIMEOUT_MS = 10_000

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

function waitForRequiredPdsElements(): Promise<void> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new Error(`Porsche Design System components did not load within ${PDS_BOOTSTRAP_TIMEOUT_MS} ms`))
    }, PDS_BOOTSTRAP_TIMEOUT_MS)
  })

  return Promise.race([
    Promise.all(REQUIRED_PDS_ELEMENTS.map((tagName) => customElements.whenDefined(tagName))).then(() => undefined),
    timeout,
  ]).finally(() => {
    if (timeoutId !== undefined) clearTimeout(timeoutId)
  })
}

function renderBootstrapFailure(): void {
  const root = document.getElementById('root')
  if (!root) return

  const fallback = document.createElement('main')
  fallback.setAttribute('role', 'alert')
  fallback.setAttribute('aria-labelledby', 'cockpit-bootstrap-error')
  fallback.style.cssText = [
    'box-sizing:border-box',
    'min-height:100vh',
    'display:grid',
    'place-content:center',
    'gap:1rem',
    'padding:2rem',
    'font-family:system-ui,sans-serif',
    'color:#101820',
    'background:#fff',
  ].join(';')

  const heading = document.createElement('h1')
  heading.id = 'cockpit-bootstrap-error'
  heading.textContent = 'OwlBear Cockpit could not load'

  const message = document.createElement('p')
  message.textContent = 'The design system components did not finish loading. Reload the page to try again.'

  const reload = document.createElement('button')
  reload.type = 'button'
  reload.textContent = 'Reload page'
  reload.addEventListener('click', () => window.location.reload())

  fallback.append(heading, message, reload)
  root.replaceChildren(fallback)
}

async function bootstrap(): Promise<void> {
  try {
    installPdsCdnTrap()
    await load()
    applyTokenFallbacks()
    await waitForRequiredPdsElements()

    createRoot(document.getElementById('root')!).render(
      <StrictMode>
        <App />
      </StrictMode>,
    )
  } catch (error) {
    console.error('[Cockpit bootstrap]', error)
    renderBootstrapFailure()
  }
}

void bootstrap()
