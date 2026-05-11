import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { load } from '@porsche-design-system/components-js'
import './tokens.css'
import App from './App'

const PDS_CDN_SCRIPT = /^https:\/\/cdn\.ui\.porsche\.(com|cn)\/porsche-design-system\/components\/(.+)$/
const REQUIRED_PDS_ELEMENTS = ['p-button', 'p-icon', 'p-tabs', 'p-tabs-item'] as const

function installPdsRuntimeScriptRewrite(): void {
  const elementProto = Element.prototype
  const originalAppendChild = elementProto.appendChild

  elementProto.appendChild = function appendChildWithPdsRewrite<T extends Node>(node: T): T {
    if (node instanceof HTMLScriptElement && node.src) {
      const match = node.src.match(PDS_CDN_SCRIPT)
      if (match) {
        const docWithPds = document as { porscheDesignSystem?: { cdn?: { url?: string } } }
        const pds = (docWithPds.porscheDesignSystem ??= { cdn: { url: window.location.origin } })
        pds.cdn = { ...(pds.cdn ?? {}), url: window.location.origin }
        node.src = `${window.location.origin}/porsche-design-system/components/${match[2]}`
      }
    }

    return originalAppendChild.call(this, node) as T
  }
}

installPdsRuntimeScriptRewrite()

async function waitForRequiredPdsElements(): Promise<void> {
  await Promise.all(REQUIRED_PDS_ELEMENTS.map((tagName) => customElements.whenDefined(tagName)))
}

async function bootstrap(): Promise<void> {
  load()
  await waitForRequiredPdsElements()
    ;(document as { porscheDesignSystem?: { cdn?: { url?: string } } }).porscheDesignSystem = {
      ...((document as { porscheDesignSystem?: { cdn?: { url?: string } } }).porscheDesignSystem ?? {}),
      cdn: { url: window.location.origin },
    }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void bootstrap()

