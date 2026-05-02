/**
 * RED phase tests for #1260: useEventSource hook
 *
 * AC1 (td:1): named exports — useEventSource function + UseEventSourceResult type
 * AC2 (td:2): connection state machine — connecting → open → closed (fatal error)
 * AC3 (td:2): tasks-changed event handling — addEventListener + lastEventMtime
 * AC4 (td:2): reconnect-stall detection — 15s timer, single-timer guarantee, onopen clears timer
 * AC5 (td:2): retry after failure — 30s retry, one timer at a time, reconnect success
 * AC6 (td:2): cleanup on unmount — close(), stall timer, retry timer, no post-unmount updates
 * AC7 (td:1): enabled option — disabled state, enable/disable transitions, re-enable
 *
 * All 24 tests FAIL until builder creates hooks/useEventSource.ts.
 */
import { describe, it, expect, vi, beforeEach, afterEach, expectTypeOf } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useEventSource } from '../hooks/useEventSource'
import type { UseEventSourceResult } from '../hooks/useEventSource'

// ─── MockEventSource ─────────────────────────────────────────────────────────
//
// jsdom does not implement EventSource. vi.stubGlobal replaces the global with
// this mock, which matches the shape the hook uses: onopen, onerror, close,
// and addEventListener (for 'tasks-changed'). readyState mirrors spec constants.

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

describe('TestFromAC_UseEventSource', () => {
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

  // ─── AC1: named exports ─────────────────────────────────────────────────────

  describe('AC1: named exports and result type shape', () => {
    it('exports useEventSource as a callable function', () => {
      expect(typeof useEventSource).toBe('function')
    })

    it('return value has status and lastEventMtime properties (UseEventSourceResult shape)', () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      expect(result.current).toHaveProperty('status')
      expect(result.current).toHaveProperty('lastEventMtime')
    })

    it('UseEventSourceResult named type export has exact union shape (compile-time discriminating proof)', () => {
      // expectTypeOf verifies the named UseEventSourceResult export at compile time.
      // Removing the export or changing the union members causes a TypeScript error here.
      expectTypeOf<UseEventSourceResult['status']>().toEqualTypeOf<'connecting' | 'open' | 'closed'>()
      expectTypeOf<UseEventSourceResult['lastEventMtime']>().toEqualTypeOf<number | null>()
      // Runtime: the return value satisfies the type contract
      const { result } = renderHook(() => useEventSource('/api/events'))
      expectTypeOf(result.current).toMatchTypeOf<UseEventSourceResult>()
    })

    it('UseEventSourceResult full object shape matches exactly (no extra or missing properties)', () => {
      // toEqualTypeOf is structurally exact: fails if extra properties are added or if
      // UseEventSourceResult is narrowed/widened beyond the AC1 contract.
      // Updated for #1263: lastEventByType added additively by the builder.
      expectTypeOf<UseEventSourceResult>().toEqualTypeOf<{
        status: 'connecting' | 'open' | 'closed'
        lastEventMtime: number | null
        lastEventByType: Record<string, number>
      }>()
    })
  })

  // ─── AC2: connection state machine ──────────────────────────────────────────

  describe('AC2: connection state machine', () => {
    it('status is "connecting" immediately after mount (before any events)', () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      expect(result.current.status).toBe('connecting')
    })

    it('creates a native EventSource targeting the provided url', () => {
      renderHook(() => useEventSource('/api/events'))
      expect(MockEventSource.instances).toHaveLength(1)
      expect(MockEventSource.instances[0].url).toBe('/api/events')
    })

    it('status transitions to "open" when onopen fires', async () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
      })

      expect(result.current.status).toBe('open')
    })

    it('status transitions to "closed" when onerror fires with readyState===CLOSED (fatal error)', async () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateFatalError()
      })

      expect(result.current.status).toBe('closed')
    })
  })

  // ─── AC3: tasks-changed event handling ──────────────────────────────────────

  describe('AC3: tasks-changed event handling', () => {
    it('lastEventMtime is null initially (no events received yet)', () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      expect(result.current.lastEventMtime).toBeNull()
    })

    it('registers a listener for "tasks-changed" events on the EventSource', () => {
      renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]
      // Listener registration is proven by the fact that simulateEvent can reach it
      expect(Array.isArray(es.listeners['tasks-changed'])).toBe(true)
      expect(es.listeners['tasks-changed'].length).toBeGreaterThan(0)
    })

    it('updates lastEventMtime to event.data.mtime when "tasks-changed" event fires', async () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 99_000 }))
      })

      expect(result.current.lastEventMtime).toBe(99_000)
    })
  })

  // ─── AC4: reconnect-stall detection ─────────────────────────────────────────

  describe('AC4: reconnect-stall detection', () => {
    it('status becomes "closed" and EventSource.close() called after 15s stall timer fires', async () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateStallError() // readyState===CONNECTING → stall timer starts
      })
      expect(result.current.status).toBe('connecting')

      await act(async () => {
        vi.advanceTimersByTime(15_000)
      })

      expect(es.close).toHaveBeenCalled()
      expect(result.current.status).toBe('closed')
    })

    it('status is NOT "closed" before the 15s stall timer fires (boundary: t=14999ms)', async () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateStallError()
      })
      await act(async () => {
        vi.advanceTimersByTime(14_999)
      })

      expect(result.current.status).not.toBe('closed')
      expect(es.close).not.toHaveBeenCalled()
    })

    it('single-timer guarantee: second onerror resets stall timer (first timer is cleared)', async () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      // T=0: stall timer T1 starts — would fire at T=15s
      await act(async () => {
        es.simulateStallError()
      })
      // T=5s: advance, T1 has NOT fired
      await act(async () => {
        vi.advanceTimersByTime(5_000)
      })
      // T=5s: onerror again — T1 cleared, T2 starts — fires at T=20s
      await act(async () => {
        es.simulateStallError()
      })
      // T=15001ms: T1 WOULD have fired here, but was cleared — status NOT 'closed'
      await act(async () => {
        vi.advanceTimersByTime(10_001)
      })

      expect(result.current.status).not.toBe('closed')
    })

    it('stall timer is cleared when onopen fires within 15s — status remains "open"', async () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      // Stall timer starts at T=0 (fires at T=15s)
      await act(async () => {
        es.simulateStallError()
      })
      // onopen fires at T=5s — clears the stall timer
      await act(async () => {
        vi.advanceTimersByTime(5_000)
        es.simulateOpen()
      })
      // Advance past T=15s — stall timer WOULD have fired but was cleared
      await act(async () => {
        vi.advanceTimersByTime(10_001)
      })

      expect(result.current.status).toBe('open')
    })
  })

  // ─── AC5: retry after failure ────────────────────────────────────────────────

  describe('AC5: retry after failure', () => {
    it('creates a new EventSource after 30s retry timer fires (fatal error path)', async () => {
      renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateFatalError()
      })
      expect(MockEventSource.instances).toHaveLength(1)

      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })

      expect(MockEventSource.instances).toHaveLength(2)
    })

    it('creates a new EventSource after 30s retry timer fires (stall-timeout path)', async () => {
      renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      // Enter 'closed' via stall timeout
      await act(async () => {
        es.simulateStallError()
      })
      await act(async () => {
        vi.advanceTimersByTime(15_000) // stall fires → closed
      })
      expect(MockEventSource.instances).toHaveLength(1)

      await act(async () => {
        vi.advanceTimersByTime(30_000) // retry fires → new EventSource
      })

      expect(MockEventSource.instances).toHaveLength(2)
    })

    it('does not create new EventSource before 30s retry timer fires (boundary: t=29999ms)', async () => {
      renderHook(() => useEventSource('/api/events'))

      await act(async () => {
        MockEventSource.instances[0].simulateFatalError()
      })
      await act(async () => {
        vi.advanceTimersByTime(29_999)
      })

      expect(MockEventSource.instances).toHaveLength(1)
    })

    it('status transitions to "open" when retry EventSource onopen fires', async () => {
      const { result } = renderHook(() => useEventSource('/api/events'))

      // Enter 'closed' via fatal error
      await act(async () => {
        MockEventSource.instances[0].simulateFatalError()
      })
      expect(result.current.status).toBe('closed')

      // Retry fires → new EventSource created
      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })
      const es2 = MockEventSource.instances[1]

      // New connection succeeds
      await act(async () => {
        es2.simulateOpen()
      })

      expect(result.current.status).toBe('open')
    })

    it('stale onerror (CLOSED) from superseded source does not close the active new connection', async () => {
      // Regression guard for the stale-source race: after retry creates es2, a late
      // onerror callback captured in the es1 closure must not call closeActiveSource()
      // (which would close es2 via eventSourceRef.current) or regress status to 'closed'.
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es1 = MockEventSource.instances[0]

      // es1 fatal error → closed → retry timer scheduled
      await act(async () => {
        es1.simulateFatalError()
      })

      // Advance 30s → retry fires → es2 created
      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })
      const es2 = MockEventSource.instances[1]

      // es2 connects successfully
      await act(async () => {
        es2.simulateOpen()
      })
      expect(result.current.status).toBe('open')

      // Late onerror from es1 (es1.readyState is CLOSED from simulateFatalError)
      await act(async () => {
        if (es1.onerror) es1.onerror(new Event('error'))
      })

      // Stale callback must be inert: es2 must not be closed and status must stay 'open'
      expect(es2.close).not.toHaveBeenCalled()
      expect(result.current.status).toBe('open')
    })

    it('stale tasks-changed from superseded source does not overwrite lastEventMtime set by new source', async () => {
      // After retry, events from the old (closed) source must not clobber mtime state
      // that was set by the new source.
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es1 = MockEventSource.instances[0]

      // es1 opens and receives an event
      await act(async () => {
        es1.simulateOpen()
        es1.simulateEvent('tasks-changed', JSON.stringify({ mtime: 1_000 }))
      })
      expect(result.current.lastEventMtime).toBe(1_000)

      // es1 fatal error → retry
      await act(async () => {
        es1.simulateFatalError()
      })
      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })
      const es2 = MockEventSource.instances[1]

      // es2 opens and records a newer mtime
      await act(async () => {
        es2.simulateOpen()
        es2.simulateEvent('tasks-changed', JSON.stringify({ mtime: 2_000 }))
      })
      expect(result.current.lastEventMtime).toBe(2_000)

      // Stale tasks-changed from es1 fires (e.g. buffered in JS engine)
      await act(async () => {
        es1.simulateEvent('tasks-changed', JSON.stringify({ mtime: 500 }))
      })

      // lastEventMtime must stay 2_000 — stale event from superseded source is inert
      expect(result.current.lastEventMtime).toBe(2_000)
    })

    it('stale onopen from a superseded source does not mutate status after new source is active', async () => {
      // Regression guard: after retry creates es2, a late onopen from es1 must not call
      // setStatus('open') — the isCurrentSource identity guard must drop it silently.
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es1 = MockEventSource.instances[0]

      // es1 fatal error → closed → retry timer scheduled
      await act(async () => {
        es1.simulateFatalError()
      })

      // 30s → retry fires → es2 created, connecting
      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })
      const es2 = MockEventSource.instances[1]
      expect(result.current.status).toBe('connecting')

      // Stale onopen from es1 (e.g. buffered in JS engine after reconnect)
      await act(async () => {
        if (es1.onopen) es1.onopen(new Event('open'))
      })

      // es2 must still be connecting — stale es1 onopen must not flip status to 'open'
      // and must not close or interfere with es2
      expect(result.current.status).toBe('connecting')
      expect(es2.close).not.toHaveBeenCalled()
    })

    it('only one retry timer active — two consecutive fatal errors schedule exactly one retry', async () => {
      // AC5 single-timer guarantee: if two fatal errors arrive before the retry fires,
      // exactly one new EventSource must be created at +30s, not two.
      // Fails if clearRetryTimer() is removed from the fatal-error path.
      renderHook(() => useEventSource('/api/events'))
      const es1 = MockEventSource.instances[0]

      // First fatal error → retry T1 scheduled, eventSourceRef set to null
      await act(async () => {
        es1.simulateFatalError()
      })
      expect(MockEventSource.instances).toHaveLength(1)

      // Second fatal error from es1 (stale callback; isCurrentSource guard fires)
      await act(async () => {
        if (es1.onerror) es1.onerror(new Event('error'))
      })

      // Advance exactly 30s — only T1 fires; no stacking
      await act(async () => {
        vi.advanceTimersByTime(30_000)
      })

      // Only ONE new instance — timer did not stack
      expect(MockEventSource.instances).toHaveLength(2)
    })
  })

  // ─── AC6: cleanup on unmount ─────────────────────────────────────────────────

  describe('AC6: cleanup on unmount', () => {
    it('calls EventSource.close() on unmount', () => {
      const { unmount } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      act(() => {
        unmount()
      })

      expect(es.close).toHaveBeenCalled()
    })

    it('stall timer cleared on unmount — does not fire after unmount', async () => {
      const { unmount } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      // Start stall timer
      await act(async () => {
        es.simulateStallError()
      })

      act(() => {
        unmount()
      })

      // Advance past stall (15s) + retry (30s) windows
      await act(async () => {
        vi.advanceTimersByTime(50_000)
      })

      // Stall timer didn't fire → no 'closed' transition → no retry → no new instance
      expect(MockEventSource.instances).toHaveLength(1)
    })

    it('retry timer cleared on unmount — does not create new EventSource after unmount', async () => {
      const { unmount } = renderHook(() => useEventSource('/api/events'))

      // Enter 'closed' → retry timer scheduled
      await act(async () => {
        MockEventSource.instances[0].simulateFatalError()
      })

      act(() => {
        unmount()
      })

      // Advance past the 30s retry window
      await act(async () => {
        vi.advanceTimersByTime(35_000)
      })

      // Retry timer was cleared — no new EventSource created
      expect(MockEventSource.instances).toHaveLength(1)
    })

    it('EventSource callbacks firing after unmount do not create new instances', async () => {
      const { unmount } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      act(() => {
        unmount()
      })

      // Simulate delayed callbacks arriving after unmount (race condition in real browser)
      await act(async () => {
        if (es.onopen) es.onopen(new Event('open'))
        vi.advanceTimersByTime(45_000)
      })

      // No new EventSource instances — all timers and event handlers are inert post-unmount
      expect(MockEventSource.instances).toHaveLength(1)
    })

    it('callbacks firing after unmount do not write status or lastEventMtime (direct state suppression)', async () => {
      // Direct AC6 proof: result.current must not change after unmount even when
      // onopen and tasks-changed fire — the isMountedRef guard must suppress setStatus
      // and setLastEventMtime, not only prevent new instance creation.
      const { result, unmount } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      act(() => {
        unmount()
      })

      const statusAtUnmount = result.current.status
      const mtimeAtUnmount = result.current.lastEventMtime

      // Fire callbacks that would normally mutate status and lastEventMtime
      await act(async () => {
        if (es.onopen) es.onopen(new Event('open'))
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 9_999 }))
        vi.advanceTimersByTime(50_000)
      })

      // result.current must be identical to values at unmount time
      expect(result.current.status).toBe(statusAtUnmount)
      expect(result.current.lastEventMtime).toBe(mtimeAtUnmount)
    })
  })

  // ─── AC7: enabled option ─────────────────────────────────────────────────────

  describe('AC7: enabled option', () => {
    it('does not create EventSource when enabled=false; returns status="closed" and lastEventMtime=null', () => {
      const { result } = renderHook(() =>
        useEventSource('/api/events', { enabled: false }),
      )

      expect(MockEventSource.instances).toHaveLength(0)
      expect(result.current.status).toBe('closed')
      expect(result.current.lastEventMtime).toBeNull()
    })

    it('closes EventSource and status becomes "closed" when enabled transitions true → false', async () => {
      let enabled = true
      const { result, rerender } = renderHook(() =>
        useEventSource('/api/events', { enabled }),
      )
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
      })
      expect(result.current.status).toBe('open')

      enabled = false
      await act(async () => {
        rerender()
      })

      expect(es.close).toHaveBeenCalled()
      expect(result.current.status).toBe('closed')
    })

    it('creates a fresh EventSource when re-enabled after being disabled', async () => {
      let enabled = false
      const { rerender } = renderHook(() =>
        useEventSource('/api/events', { enabled }),
      )

      expect(MockEventSource.instances).toHaveLength(0)

      enabled = true
      await act(async () => {
        rerender()
      })

      expect(MockEventSource.instances).toHaveLength(1)
    })

    it('stale tasks-changed from prior source does not repopulate lastEventMtime after disable', async () => {
      // After enabled transitions true→false, the disable effect resets lastEventMtime to null.
      // A tasks-changed listener registered on the old EventSource must not fire
      // after disable and repopulate lastEventMtime — the handler must check source identity,
      // not only isMountedRef.
      let enabled = true
      const { result, rerender } = renderHook(() =>
        useEventSource('/api/events', { enabled }),
      )
      const es1 = MockEventSource.instances[0]

      // Connect, open, receive an event — establishes lastEventMtime
      await act(async () => {
        es1.simulateOpen()
        es1.simulateEvent('tasks-changed', JSON.stringify({ mtime: 1_234 }))
      })
      expect(result.current.lastEventMtime).toBe(1_234)

      // Disable → status='closed', lastEventMtime reset to null
      enabled = false
      await act(async () => {
        rerender()
      })
      expect(result.current.lastEventMtime).toBeNull()

      // Stale tasks-changed from es1 fires after disable (race: listener was already registered)
      await act(async () => {
        es1.simulateEvent('tasks-changed', JSON.stringify({ mtime: 5_678 }))
      })

      // lastEventMtime must remain null — stale source cannot repopulate state after disable
      expect(result.current.lastEventMtime).toBeNull()
    })

    it('disabling while stall timer is pending clears the timer — no retry EventSource created', async () => {
      // AC7 "clears all timers" proof for active stall timer:
      // if clearStallTimer() is removed from the disabled path, the stall timer would fire
      // after disable, transitioning to 'closed' again and scheduling a retry, creating
      // a spurious new EventSource despite the hook being disabled.
      let enabled = true
      const { rerender } = renderHook(() =>
        useEventSource('/api/events', { enabled }),
      )
      const es = MockEventSource.instances[0]

      // Start 15s stall timer
      await act(async () => {
        es.simulateStallError()
      })

      // Disable before stall fires
      enabled = false
      await act(async () => {
        rerender()
      })

      // Advance past stall (15s) + retry (30s) windows
      await act(async () => {
        vi.advanceTimersByTime(50_000)
      })

      // Stall timer cleared → did not fire → no retry → no new EventSource
      expect(MockEventSource.instances).toHaveLength(1)
    })

    it('disabling while retry timer is pending clears the timer — no new EventSource after disable', async () => {
      // AC7 "clears all timers" proof for active retry timer:
      // if clearRetryTimer() is removed from the disabled path, the retry would fire
      // after disable and create a new EventSource despite the hook being disabled.
      let enabled = true
      const { rerender } = renderHook(() =>
        useEventSource('/api/events', { enabled }),
      )

      // Fatal error → enter 'closed' → retry timer starts
      await act(async () => {
        MockEventSource.instances[0].simulateFatalError()
      })

      // Disable before 30s retry fires
      enabled = false
      await act(async () => {
        rerender()
      })

      // Advance past the 30s retry window
      await act(async () => {
        vi.advanceTimersByTime(35_000)
      })

      // Retry timer cleared — no new EventSource created
      expect(MockEventSource.instances).toHaveLength(1)
    })
  })
})
