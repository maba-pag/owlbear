/**
 * Workflow behavior tests1276: EventSourceProvider context and useSSEEvent hook
 *
 * AC1 (td:1): EventSourceProvider + useSSEEvent exported from hooks/EventSourceProvider
 * AC2 (td:2): Provider lifecycle — single EventSource, stall/retry timers, unmount cleanup
 * AC3 (td:2): Listener registration for 3 event types; per-type mtime storage; malformed events
 * AC4 (td:2): useSSEEvent(eventType) → { mtime: number | null, status } from context
 * AC5 (td:1): useSSEEvent throws descriptive error when called outside EventSourceProvider
 * AC6 (td:1): App.tsx wiring — covered in App_1276.test.tsx
 * AC7 (td:0): Existing hooks unchanged — no tests needed
 *
 * All 27 tests FAIL until builder creates hooks/EventSourceProvider.tsx.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { type ReactNode } from 'react'
import { EventSourceProvider, useSSEEvent } from '../hooks/EventSourceProvider'

// ─── MockEventSource ─────────────────────────────────────────────────────────
//
// jsdom does not implement EventSource. vi.stubGlobal replaces the global with
// this mock, which matches the shape the provider uses: onopen, onerror, close,
// and addEventListener (for three named event types). readyState mirrors spec constants.

class MockEventSource {
  static instances: MockEventSource[] = []
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSED = 2

  readyState: number = MockEventSource.CONNECTING
  url: string
  onopen: ((e: Event) => void) | null = null
  onerror: ((e: Event) => void) | null = null
  close = vi.fn()
  listeners: Record<string, ((e: MessageEvent) => void)[]> = {}

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  addEventListener(type: string, fn: (e: MessageEvent) => void): void {
    if (!this.listeners[type]) this.listeners[type] = []
    this.listeners[type].push(fn)
  }

  /** Simulate successful connection: readyState → OPEN, fires onopen */
  simulateOpen(): void {
    this.readyState = MockEventSource.OPEN
    if (this.onopen) this.onopen(new Event('open'))
  }

  /** Simulate transient error (browser will retry): readyState stays CONNECTING */
  simulateStallError(): void {
    this.readyState = MockEventSource.CONNECTING
    if (this.onerror) this.onerror(new Event('error'))
  }

  /** Simulate fatal error (browser will NOT retry): readyState → CLOSED */
  simulateFatalError(): void {
    this.readyState = MockEventSource.CLOSED
    if (this.onerror) this.onerror(new Event('error'))
  }

  /** Fire a named event with JSON data to all registered listeners */
  simulateEvent(type: string, data: string): void {
    const event = new MessageEvent(type, { data })
    ;(this.listeners[type] ?? []).forEach((fn) => fn(event))
  }
}

// ─── Test suite ──────────────────────────────────────────────────────────────

describe('TestFromAC_EventSourceProvider', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockEventSource.instances = []
    vi.stubGlobal('EventSource', MockEventSource)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  /** Renders a single useSSEEvent consumer inside EventSourceProvider. */
  const wrapper = ({ children }: { children: ReactNode }) => (
    <EventSourceProvider url="/api/events">{children}</EventSourceProvider>
  )

  // ─── AC1: exports ─────────────────────────────────────────────────────────

  describe('AC1: named exports from hooks/EventSourceProvider', () => {
    it('exports EventSourceProvider as a callable component', () => {
      expect(typeof EventSourceProvider).toBe('function')
    })

    it('exports useSSEEvent as a callable function', () => {
      expect(typeof useSSEEvent).toBe('function')
    })
  })

  // ─── AC2: provider lifecycle ───────────────────────────────────────────────

  describe('AC2: single EventSource, stall/retry timers, unmount cleanup', () => {
    // Happy paths

    it('opens exactly one EventSource on mount with the provided URL', () => {
      renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      expect(MockEventSource.instances).toHaveLength(1)
      expect(MockEventSource.instances[0].url).toBe('/api/events')
    })

    it('status is "connecting" immediately on mount (before any events)', () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      expect(result.current.status).toBe('connecting')
    })

    it('status transitions to "open" when EventSource onopen fires', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
      })

      expect(result.current.status).toBe('open')
    })

    it('status transitions to "closed" on fatal error (readyState===CLOSED)', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateFatalError()
      })

      expect(result.current.status).toBe('closed')
    })

    // Edge: unmount cleanup

    it('calls EventSource.close() on unmount', () => {
      const { unmount } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      act(() => {
        unmount()
      })

      expect(es.close).toHaveBeenCalled()
    })

    it('stall timer cleared on unmount — no new EventSource created after 50s', async () => {
      const { unmount } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateStallError() // stall timer starts (would fire at +15s)
      })

      act(() => {
        unmount()
      })

      await act(async () => {
        vi.advanceTimersByTime(50_000) // past stall (15s) + retry (30s) windows
      })

      // No retry connection because stall timer was cleared on unmount
      expect(MockEventSource.instances).toHaveLength(1)
    })

    it('retry timer cleared on unmount — no new EventSource created after 35s', async () => {
      const { unmount } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })

      await act(async () => {
        MockEventSource.instances[0].simulateFatalError() // retry timer starts at +30s
      })

      act(() => {
        unmount()
      })

      await act(async () => {
        vi.advanceTimersByTime(35_000)
      })

      // Retry timer was cleared on unmount — no new EventSource
      expect(MockEventSource.instances).toHaveLength(1)
    })

    // Boundary: stall timer constants match STALL_TIMEOUT_MS=15000

    it('stall timer fires after exactly 15s → status becomes "closed"', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateStallError() // readyState===CONNECTING → stall timer starts
      })
      // Timer has not fired yet
      expect(result.current.status).toBe('connecting')

      await act(async () => {
        vi.advanceTimersByTime(15_000)
      })

      expect(es.close).toHaveBeenCalled()
      expect(result.current.status).toBe('closed')
    })

    it('stall timer does NOT fire before 15s (boundary: t=14999ms)', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateStallError()
      })

      await act(async () => {
        vi.advanceTimersByTime(14_999)
      })

      expect(es.close).not.toHaveBeenCalled()
      expect(result.current.status).not.toBe('closed')
    })

    // Boundary: retry timer constant matches RETRY_TIMEOUT_MS=30000

    it('retry creates a new EventSource after 30s following fatal error', async () => {
      renderHook(() => useSSEEvent('tasks-changed'), { wrapper })

      await act(async () => {
        MockEventSource.instances[0].simulateFatalError()
      })
      expect(MockEventSource.instances).toHaveLength(1)

      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })

      expect(MockEventSource.instances).toHaveLength(2)
    })

    // Race/guard: timer-reset and stale-source protections copied from useEventSource

    it('second stall error resets the stall timer — first timer is cancelled', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      // First stall error at t=0 — timer would fire at t=15s
      await act(async () => {
        es.simulateStallError()
      })

      // Advance 10s — first timer has not fired yet
      await act(async () => {
        vi.advanceTimersByTime(10_000)
      })

      // Second stall error at t=10s — must clear first timer and start a new 15s timer
      await act(async () => {
        es.simulateStallError()
      })

      // Advance 5s more (t=15s total, only 5s into the reset timer) — still should not fire
      await act(async () => {
        vi.advanceTimersByTime(5_000)
      })

      // If the first timer were still active it would have fired at t=15s.
      // The reset means close() must NOT have been called yet.
      expect(es.close).not.toHaveBeenCalled()
      expect(result.current.status).not.toBe('closed')

      // Advance past the reset timer (t=25001ms, 15001ms since second error) — fires now
      await act(async () => {
        vi.advanceTimersByTime(10_001)
      })

      expect(es.close).toHaveBeenCalledOnce()
      expect(result.current.status).toBe('closed')
    })

    it('stale source onopen is ignored after a new connection is established', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const sourceA = MockEventSource.instances[0]

      // Fatal error → sourceA closed, retry timer starts at 30s
      await act(async () => {
        sourceA.simulateFatalError()
      })
      expect(result.current.status).toBe('closed')

      // Advance 30s → retry fires, sourceB becomes the active connection
      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })
      expect(MockEventSource.instances).toHaveLength(2)
      const sourceB = MockEventSource.instances[1]

      // Stale sourceA fires onopen — must be ignored (isCurrentSource guard)
      await act(async () => {
        sourceA.simulateOpen()
      })

      // Status must stay 'connecting' — sourceB has not opened, stale A's onopen is a no-op
      expect(result.current.status).toBe('connecting')

      // Verify sourceB's onopen still works normally
      await act(async () => {
        sourceB.simulateOpen()
      })
      expect(result.current.status).toBe('open')
    })

    it('stale source onerror is ignored — no additional retry timer created', async () => {
      renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const sourceA = MockEventSource.instances[0]

      // Fatal error on sourceA → closed, retry timer at 30s
      await act(async () => {
        sourceA.simulateFatalError()
      })

      // Advance 30s → sourceB created and becomes active
      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })
      expect(MockEventSource.instances).toHaveLength(2)

      // Stale sourceA fires another fatal error — must be ignored (isCurrentSource guard)
      await act(async () => {
        sourceA.simulateFatalError()
      })

      // Advance 30s more — if stale onerror triggered a retry, a third source would appear
      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })

      // Only sourceA and sourceB should exist — no stale-triggered retry connection
      expect(MockEventSource.instances).toHaveLength(2)
    })

    // Boundary: stall recovery — onopen before 15s cancels the stall timer
    //
    // Mirrors useEventSource_1260.test.ts:248-267.
    // Removing clearStallTimer() from the onopen handler would leave all other stall tests
    // green but break this test, making it the sole discriminating proof for the
    // clearStallTimer() call in onopen.

    it('stall timer is cleared when onopen fires within 15s — status remains "open"', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      // Stall timer starts at t=0 (fires at t=15s)
      await act(async () => {
        es.simulateStallError()
      })
      // onopen fires at t=5s — must clear the stall timer
      await act(async () => {
        vi.advanceTimersByTime(5_000)
        es.simulateOpen()
      })
      // Advance past t=15s — stall timer WOULD have fired but was cleared
      await act(async () => {
        vi.advanceTimersByTime(10_001)
      })

      expect(result.current.status).toBe('open')
      // No new EventSource — close was never triggered by the stall
      expect(MockEventSource.instances).toHaveLength(1)
      expect(es.close).not.toHaveBeenCalled()
    })

    // Boundary: full stall → close → retry composed path (AC2 discriminating proof)
    //
    // Removing the retryTimerRef.current = setTimeout(openConnection, ...) inside the stall
    // callback would leave all other stall tests green but break this one, making it the
    // sole discriminating proof for the stall-triggered reconnect branch.

    it('stall-triggered reconnect: stall after 15s then new EventSource after 30s more', async () => {
      renderHook(() => useSSEEvent('tasks-changed'), { wrapper })

      // Stall error at t=0 — readyState===CONNECTING, stall timer starts (fires at +15s)
      await act(async () => {
        MockEventSource.instances[0].simulateStallError()
      })

      // Only the initial EventSource exists — retry has not fired yet
      expect(MockEventSource.instances).toHaveLength(1)

      // Advance 15s — stall timer fires: source closes, status → 'closed', retry timer starts (+30s)
      await act(async () => {
        vi.advanceTimersByTime(15_000)
      })

      // Source was closed; still only one instance — retry has not fired yet
      expect(MockEventSource.instances[0].close).toHaveBeenCalledOnce()
      expect(MockEventSource.instances).toHaveLength(1)

      // Advance 30s — retry timer fires: openConnection() creates a second EventSource
      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })

      expect(MockEventSource.instances).toHaveLength(2)
      expect(MockEventSource.instances[1].url).toBe('/api/events')
    })
  })

  // ─── AC3: event listeners and per-type mtime storage ──────────────────────

  describe('AC3: listeners for 3 event types; per-type mtime; malformed events ignored', () => {
    // Happy: all three listeners registered

    it('registers listeners for tasks-changed, decisions-changed, and activity-changed on mount', () => {
      renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]
      for (const type of ['tasks-changed', 'decisions-changed', 'activity-changed']) {
        expect(es.listeners[type]?.length, `missing listener for ${type}`).toBeGreaterThan(0)
      }
    })

    // Happy: mtime stored per event type

    it('tasks-changed event updates mtime for tasks-changed type', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 11_000 }))
      })

      expect(result.current.mtime).toBe(11_000)
    })

    it('decisions-changed event updates mtime for decisions-changed type', async () => {
      const { result } = renderHook(() => useSSEEvent('decisions-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('decisions-changed', JSON.stringify({ mtime: 22_000 }))
      })

      expect(result.current.mtime).toBe(22_000)
    })

    it('activity-changed event updates mtime for activity-changed type', async () => {
      const { result } = renderHook(() => useSSEEvent('activity-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('activity-changed', JSON.stringify({ mtime: 33_000 }))
      })

      expect(result.current.mtime).toBe(33_000)
    })

    // Edge: initial state

    it('initial mtime is null for all three event types', () => {
      const { result } = renderHook(
        () => ({
          tasks: useSSEEvent('tasks-changed'),
          decisions: useSSEEvent('decisions-changed'),
          activity: useSSEEvent('activity-changed'),
        }),
        { wrapper },
      )

      expect(result.current.tasks.mtime).toBeNull()
      expect(result.current.decisions.mtime).toBeNull()
      expect(result.current.activity.mtime).toBeNull()
    })

    it('firing tasks-changed does not affect decisions-changed mtime', async () => {
      const { result } = renderHook(
        () => ({
          tasks: useSSEEvent('tasks-changed'),
          decisions: useSSEEvent('decisions-changed'),
        }),
        { wrapper },
      )
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 999 }))
      })

      expect(result.current.tasks.mtime).toBe(999)
      expect(result.current.decisions.mtime).toBeNull()
    })

    // Error: malformed events silently ignored

    it('malformed JSON event silently ignored — no throw, mtime stays null', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        // Malformed JSON must not throw or crash the stream
        expect(() => {
          es.simulateEvent('tasks-changed', 'not valid json{{{')
        }).not.toThrow()
      })

      expect(result.current.mtime).toBeNull()
    })

    it('event with non-number mtime field does not update stored mtime', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 'not-a-number' }))
      })

      expect(result.current.mtime).toBeNull()
    })

    // Error + Recovery: malformed event must not kill the listener

    it('after malformed JSON, a valid event still updates mtime (stream stays alive)', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        // Malformed event — listener must survive this
        es.simulateEvent('tasks-changed', 'not valid json{{{')
      })

      expect(result.current.mtime).toBeNull()

      // Valid event after malformed — proves the listener is still alive
      await act(async () => {
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 42_000 }))
      })

      expect(result.current.mtime).toBe(42_000)
    })
  })

  // ─── AC4: useSSEEvent return shape ────────────────────────────────────────

  describe('AC4: useSSEEvent returns { mtime, status } from context', () => {
    // Happy paths

    it('returns { mtime: null, status: "connecting" } initially', () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      expect(result.current).toMatchObject({ mtime: null, status: 'connecting' })
    })

    it('status field reflects provider connection state ("open" after connect)', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
      })

      expect(result.current.status).toBe('open')
    })

    it('mtime updates when the matching event type fires', async () => {
      const { result } = renderHook(() => useSSEEvent('tasks-changed'), { wrapper })
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 5_000 }))
      })

      expect(result.current.mtime).toBe(5_000)
    })

    // Edge: shared status, independent mtimes

    it('status is shared — all event types see the same connection status', async () => {
      const { result } = renderHook(
        () => ({
          tasks: useSSEEvent('tasks-changed'),
          decisions: useSSEEvent('decisions-changed'),
        }),
        { wrapper },
      )
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
      })

      expect(result.current.tasks.status).toBe('open')
      expect(result.current.decisions.status).toBe('open')
    })

    it('different event types maintain independent mtime values', async () => {
      const { result } = renderHook(
        () => ({
          tasks: useSSEEvent('tasks-changed'),
          decisions: useSSEEvent('decisions-changed'),
        }),
        { wrapper },
      )
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 100 }))
        es.simulateEvent('decisions-changed', JSON.stringify({ mtime: 200 }))
      })

      expect(result.current.tasks.mtime).toBe(100)
      expect(result.current.decisions.mtime).toBe(200)
    })

    // Boundary: unregistered event type

    it('unrecognized event type returns mtime: null (not registered, never updated)', () => {
      const { result } = renderHook(
        // Cast to known type to satisfy TypeScript — testing runtime boundary
        () => useSSEEvent('unknown-type' as 'tasks-changed'),
        { wrapper },
      )
      expect(result.current.mtime).toBeNull()
    })
  })

  // ─── AC5: error outside provider ─────────────────────────────────────────

  describe('AC5: useSSEEvent throws descriptive error when called outside EventSourceProvider', () => {
    it('throws a descriptive error when no EventSourceProvider is in the component tree', () => {
      // Suppress React's error boundary console noise during this intentional throw
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
      try {
        expect(() => renderHook(() => useSSEEvent('tasks-changed'))).toThrow(
          'useSSEEvent must be used within an EventSourceProvider',
        )
      } finally {
        consoleSpy.mockRestore()
      }
    })
  })
})
