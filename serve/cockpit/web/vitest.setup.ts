import '@porsche-design-system/components-react/jsdom-polyfill'
import '@testing-library/jest-dom/vitest'
import { skipPorscheDesignSystemCDNRequestsDuringTests } from '@porsche-design-system/components-react'
import { vi } from 'vitest'

skipPorscheDesignSystemCDNRequestsDuringTests()

if (typeof globalThis.requestAnimationFrame === 'undefined') {
  globalThis.requestAnimationFrame = (callback: FrameRequestCallback): number =>
    setTimeout(() => callback(Date.now()), 0) as unknown as number
}

if (typeof globalThis.cancelAnimationFrame === 'undefined') {
  globalThis.cancelAnimationFrame = (handle: number): void => {
    clearTimeout(handle)
  }
}

if (typeof window !== 'undefined') {
  window.requestAnimationFrame = globalThis.requestAnimationFrame
  window.cancelAnimationFrame = globalThis.cancelAnimationFrame
}

if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (query: string): MediaQueryList => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => true,
    }),
  })
}

// PDS global keydown handler (hideAllPopoversUntil) throws TypeError when
// accessing ownerDocument on a null element in jsdom. This is a known PDS/jsdom
// incompatibility: document.ownerDocument is null (document IS the document).
// Suppress this specific error so it does not surface as an Unhandled Error.
if (typeof window !== 'undefined') {
  window.addEventListener(
    'error',
    (event: ErrorEvent) => {
      if (
        event.error instanceof TypeError &&
        event.error.message === "Cannot read properties of null (reading 'ownerDocument')"
      ) {
        event.preventDefault()
      }
    },
    { capture: true },
  )
}

// jsdom does not implement showModal/close on HTMLDialogElement
if (typeof HTMLDialogElement !== 'undefined') {
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = vi.fn()
  }
  if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = vi.fn()
  }
}

// PDS form components need a complete ElementInternals surface. Newer jsdom
// exposes a partial attachInternals implementation that lacks setFormValue, so
// use a deterministic test shim rather than only filling the missing method.
if (typeof HTMLElement !== 'undefined') {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(
    () => ({
      setFormValue: vi.fn(),
      setValidity: vi.fn(),
      checkValidity: vi.fn(() => true),
      reportValidity: vi.fn(() => true),
    }),
  )
}

// jsdom has no native EventSource. Provide a closed-by-default stub so tests
// can opt into richer behavior per-suite without crashing on construction.
if (typeof globalThis.EventSource === 'undefined') {
  class MockEventSource {
    static readonly CONNECTING = 0
    static readonly OPEN = 1
    static readonly CLOSED = 2

    readonly url: string
    readonly withCredentials: boolean
    readyState: number
    onopen: ((event: Event) => void) | null = null
    onerror: ((event: Event) => void) | null = null

    constructor(url: string, eventSourceInitDict?: EventSourceInit) {
      this.url = url
      this.withCredentials = eventSourceInitDict?.withCredentials ?? false
      this.readyState = MockEventSource.CLOSED
    }

    addEventListener(): void {}
    removeEventListener(): void {}

    close(): void {
      this.readyState = MockEventSource.CLOSED
    }
  }

  globalThis.EventSource = MockEventSource as unknown as typeof EventSource
}
