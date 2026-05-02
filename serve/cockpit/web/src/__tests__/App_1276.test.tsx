/**
 * RED phase tests for #1276 — AC6: App.tsx wiring
 *
 * AC6 (td:1): <EventSourceProvider url="/api/events"> wraps <Shell /> in App.tsx
 *             inside <BrowserRouter>.
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

// ─── Mock EventSourceProvider before App is imported ─────────────────────────
// vi.mock is hoisted — it intercepts App's `import { EventSourceProvider } from
// './hooks/EventSourceProvider'` at module load time.
const capturedCalls: { url: unknown }[] = []

vi.mock('../hooks/EventSourceProvider', () => ({
  EventSourceProvider: vi.fn(
    ({ url, children }: { url: unknown; children: unknown }) => {
      capturedCalls.push({ url })
      return children
    },
  ),
  useSSEEvent: vi.fn(() => ({ mtime: null, status: 'connecting' })),
}))

// Import App AFTER vi.mock so the mock is in place when App.tsx resolves its deps
import App from '../App'

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
    it('App renders EventSourceProvider with url="/api/events" inside BrowserRouter', () => {
      render(<App />)

      // EventSourceProvider must have been rendered with the correct url prop.
      // Fails (RED) if App.tsx does not import + render EventSourceProvider.
      expect(capturedCalls.length).toBeGreaterThan(0)
      expect(capturedCalls[0].url).toBe('/api/events')
    })
  })
})
