/**
 *
 * AC6 (td:1): <EventSourceProvider url="/api/events"> wraps <Shell /> in App.tsx
 *             inside the app router.
 *
 * Strategy: vi.mock intercepts App's import of EventSourceProvider with a spy.
 * If EventSourceProvider is not yet added to App.tsx (RED), the spy is never
 * called → assertion fails → RED ✓.
 * After builder wires it (GREEN), rendering App calls the spy → assertion passes.
 *
 * vi.mock with factory works even when the actual file does not yet exist;
 * the factory return value is the module. If the actual file is absent, any
 * import that reaches the real resolver fails → test fails → RED ✓.
 *
 * 1 test FAIL until builder creates hooks/EventSourceProvider.tsx and updates App.tsx.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { isValidElement } from 'react'

// ─── Mock EventSourceProvider before App is imported ─────────────────────────
// vi.mock is hoisted — it intercepts App's `import { EventSourceProvider } from
// './hooks/EventSourceProvider'` at module load time.
const capturedCalls: { url: unknown; children: unknown }[] = []

vi.mock('./hooks/EventSourceProvider', () => ({
  EventSourceProvider: vi.fn(
    ({ url, children }: { url: unknown; children: unknown }) => {
      capturedCalls.push({ url, children })
      return children
    },
  ),
  useSSEEvent: vi.fn(() => ({ mtime: null, status: 'connecting' })),
}))

// Import App AFTER vi.mock so the mock is in place when App.tsx resolves its deps
import App from './App'

// ─── Stubs ────────────────────────────────────────────────────────────────────

/** Minimal EventSource stub — prevents jsdom ReferenceError from useBoard path. */
class MinimalEventSource {
  url: string
  onopen: null = null
  onerror: null = null
  constructor(url: string) {
    this.url = url
  }
  addEventListener() {}
  close() {}
}

// ─── Test suite ───────────────────────────────────────────────────────────────

describe('TestFromAC_AppWiring', () => {
  beforeEach(() => {
    capturedCalls.length = 0
    vi.stubGlobal('EventSource', MinimalEventSource)
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_url: string, init?: RequestInit) =>
          new Promise<never>((_resolve, reject) => {
            init?.signal?.addEventListener('abort', () =>
              reject(new DOMException('Aborted', 'AbortError')),
            )
          }),
      ),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ─── AC6: EventSourceProvider wraps Shell in App.tsx ────────────────────

  describe('AC6: EventSourceProvider wraps Shell with url="/api/events" in App.tsx', () => {
    it('App renders EventSourceProvider with url="/api/events" wrapping Shell inside the app router', () => {
      render(<App />)

      // EventSourceProvider must have been rendered with the correct url prop.
      // Fails (RED) if App.tsx does not import + render EventSourceProvider.
      expect(capturedCalls.length).toBeGreaterThan(0)
      expect(capturedCalls[0].url).toBe('/api/events')

      const children = capturedCalls[0].children
      expect(isValidElement(children)).toBe(true)
      // Post-#1504: CockpitProvider is between EventSourceProvider and ErrorBoundary.
      expect((children as { type: { name?: string } }).type.name).toBe('CockpitProvider')

      const providerChildren = (children as { props: { children?: unknown } }).props.children
      expect(isValidElement(providerChildren)).toBe(true)
      expect((providerChildren as { type: { name?: string } }).type.name).toBe('ErrorBoundary')

      const boundaryChildren = (providerChildren as { props: { children?: unknown } }).props.children
      expect(isValidElement(boundaryChildren)).toBe(true)
      expect((boundaryChildren as { type: { name?: string } }).type.name).toBe('Shell')

      // The data router wraps the provider — Shell uses router hooks which require
      // router context. Rendering completes without a router context error,
      // proving the app router is ancestral to Shell.
      // (Without a router, Shell would throw "useHref() may be used only in
      // the context of a <Router>" during render.)
    })
  })
})
