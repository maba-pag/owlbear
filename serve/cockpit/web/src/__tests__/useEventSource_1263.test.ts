/**
 * RED phase tests for #1263: Wire usePendingDRs to SSE decisions-changed early-refetch
 * Scope: useEventSource extension (AC1 + AC2)
 *
 * AC1 (td:2): useEventSource accepts optional eventTypes?: string[] defaulting to
 *   ['tasks-changed']; registers addEventListener for each type; eventTypes identity
 *   changes do not cause reconnection (content-compare or caller-stabilized ref)
 * AC2 (td:2): useEventSource returns lastEventByType: Record<string, number> with
 *   per-type latest mtime; existing lastEventMtime equals max across all types for
 *   backward compatibility
 *
 * All tests FAIL until builder extends hooks/useEventSource.ts with eventTypes param
 * and lastEventByType return field.
 */
import { describe, it, expect, vi, beforeEach, afterEach, expectTypeOf } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useEventSource } from '../hooks/useEventSource'
import type { UseEventSourceResult } from '../hooks/useEventSource'

// ─── MockEventSource ─────────────────────────────────────────────────────────
//
// Matches the shape used by useEventSource: onopen, onerror, close, addEventListener,
// and readyState. Works for any event type via generic listeners map.

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

  simulateOpen(): void {
    this.readyState = MockEventSource.OPEN
    if (this.onopen) this.onopen(new Event('open'))
  }

  simulateEvent(type: string, data: string): void {
    const event = new MessageEvent(type, { data })
    ;(this.listeners[type] ?? []).forEach((fn) => fn(event))
  }
}

// ─── Test suite ──────────────────────────────────────────────────────────────

describe('TestFromAC_UseEventSourceEventTypes', () => {
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

  // ─── AC1: eventTypes param controls listener registration ─────────────────

  describe('AC1: eventTypes param', () => {
    it('registers a listener for "decisions-changed" when eventTypes includes it', () => {
      // The current implementation only registers "tasks-changed" and ignores eventTypes.
      // This test fails until the builder adds per-type addEventListener support.
      renderHook(() =>
        useEventSource('/api/events', {
          eventTypes: ['decisions-changed'],
        } as Parameters<typeof useEventSource>[1]),
      )
      const es = MockEventSource.instances[0]
      expect(es.listeners['decisions-changed']).toBeDefined()
      expect(es.listeners['decisions-changed'].length).toBeGreaterThan(0)
    })

    it('registers listeners for both "tasks-changed" and "decisions-changed" when both passed', () => {
      renderHook(() =>
        useEventSource('/api/events', {
          eventTypes: ['tasks-changed', 'decisions-changed'],
        } as Parameters<typeof useEventSource>[1]),
      )
      const es = MockEventSource.instances[0]
      expect(es.listeners['tasks-changed']).toBeDefined()
      expect(es.listeners['tasks-changed'].length).toBeGreaterThan(0)
      expect(es.listeners['decisions-changed']).toBeDefined()
      expect(es.listeners['decisions-changed'].length).toBeGreaterThan(0)
    })

    it('registers no type-specific listeners when eventTypes is empty []', () => {
      // The current implementation always registers "tasks-changed" regardless.
      // This test fails until the builder replaces the hardcoded registration.
      renderHook(() =>
        useEventSource('/api/events', {
          eventTypes: [],
        } as Parameters<typeof useEventSource>[1]),
      )
      const es = MockEventSource.instances[0]
      // No type listeners should be registered
      expect(Object.keys(es.listeners)).toHaveLength(0)
    })

    it('does not register tasks-changed when eventTypes explicitly omits it', () => {
      renderHook(() =>
        useEventSource('/api/events', {
          eventTypes: ['decisions-changed'],
        } as Parameters<typeof useEventSource>[1]),
      )
      const es = MockEventSource.instances[0]
      // Only decisions-changed — tasks-changed must not be registered by default
      expect(es.listeners['tasks-changed']).toBeUndefined()
    })

    it('same-content eventTypes array on re-render does not create a new EventSource (content-compare)', () => {
      // Caller passes a new array reference each render but with the same contents.
      // The hook must NOT reconnect (create a new EventSource) — only identity-changed
      // content should trigger reconnect.
      const { rerender } = renderHook(
        ({ eventTypes }: { eventTypes: string[] }) =>
          useEventSource('/api/events', {
            eventTypes,
          } as Parameters<typeof useEventSource>[1]),
        { initialProps: { eventTypes: ['tasks-changed', 'decisions-changed'] } },
      )
      const es = MockEventSource.instances[0]

      // Re-render with a new array reference but same content
      rerender({ eventTypes: ['tasks-changed', 'decisions-changed'] })
      rerender({ eventTypes: ['tasks-changed', 'decisions-changed'] })

      // Precondition: listeners must have been registered for both types
      // (fails with current impl which ignores eventTypes — anchors the RED state)
      expect(es.listeners['decisions-changed']).toBeDefined()
      // AND no reconnect after content-equivalent re-renders
      expect(MockEventSource.instances).toHaveLength(1)
    })
  })

  // ─── AC2: lastEventByType return field ────────────────────────────────────

  describe('AC2: lastEventByType return field', () => {
    it('return value includes lastEventByType property', () => {
      // Current return only has { status, lastEventMtime } — no lastEventByType.
      const { result } = renderHook(() => useEventSource('/api/events'))
      expect(result.current).toHaveProperty('lastEventByType')
    })

    it('lastEventByType is initially an empty record (no events received)', () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      // lastEventByType must exist and be an empty object, not undefined
      expect(result.current.lastEventByType).toEqual({})
    })

    it('tasks-changed event updates lastEventByType["tasks-changed"] to event mtime', async () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 11_000 }))
      })

      expect(result.current.lastEventByType?.['tasks-changed']).toBe(11_000)
    })

    it('decisions-changed event updates lastEventByType["decisions-changed"] to event mtime', async () => {
      const { result } = renderHook(() =>
        useEventSource('/api/events', {
          eventTypes: ['tasks-changed', 'decisions-changed'],
        } as Parameters<typeof useEventSource>[1]),
      )
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('decisions-changed', JSON.stringify({ mtime: 22_000 }))
      })

      expect(result.current.lastEventByType?.['decisions-changed']).toBe(22_000)
    })

    it('lastEventMtime equals the max value across all types in lastEventByType', async () => {
      // Backward compat: lastEventMtime = Math.max(...Object.values(lastEventByType))
      const { result } = renderHook(() =>
        useEventSource('/api/events', {
          eventTypes: ['tasks-changed', 'decisions-changed'],
        } as Parameters<typeof useEventSource>[1]),
      )
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 5_000 }))
        es.simulateEvent('decisions-changed', JSON.stringify({ mtime: 7_000 }))
      })

      // Max is 7_000 (decisions-changed fired later)
      expect(result.current.lastEventMtime).toBe(7_000)
    })

    it('lastEventMtime is null when no events received (backward compat with empty lastEventByType)', () => {
      const { result } = renderHook(() => useEventSource('/api/events'))
      // Precondition: lastEventByType must exist and be empty
      // (fails with current impl — anchors the RED state)
      expect(result.current.lastEventByType).toBeDefined()
      expect(result.current.lastEventByType).toEqual({})
      // Consequence: lastEventMtime is null when lastEventByType is empty
      expect(result.current.lastEventMtime).toBeNull()
    })

    it('UseEventSourceResult type includes lastEventByType: Record<string, number> field', () => {
      // Compile-time proof: UseEventSourceResult must be extended with lastEventByType.
      // This assertion fails until the builder adds the field to the exported type.
      const { result } = renderHook(() => useEventSource('/api/events'))
      const r = result.current as UseEventSourceResult & { lastEventByType?: unknown }
      // Runtime guard: property must exist
      expect(r.lastEventByType).toBeDefined()
      // Type-level: UseEventSourceResult must be structurally assignable to the full shape
      expectTypeOf<UseEventSourceResult>().toMatchTypeOf<{
        status: 'connecting' | 'open' | 'closed'
        lastEventMtime: number | null
        lastEventByType: Record<string, number>
      }>()
    })

    it('lastEventMtime stays at cross-type max when higher mtime arrives first (discriminates Math.max from last-write-wins)', async () => {
      // Discriminating scenario: decisions-changed arrives with mtime 9000 FIRST,
      // then tasks-changed arrives with mtime 3000 SECOND.
      // A last-write-wins implementation would set lastEventMtime=3000.
      // Only Math.max across all types yields the correct value of 9000.
      const { result } = renderHook(() =>
        useEventSource('/api/events', {
          eventTypes: ['tasks-changed', 'decisions-changed'],
        } as Parameters<typeof useEventSource>[1]),
      )
      const es = MockEventSource.instances[0]

      await act(async () => {
        es.simulateOpen()
        // Higher mtime arrives FIRST on decisions-changed
        es.simulateEvent('decisions-changed', JSON.stringify({ mtime: 9_000 }))
        // Lower mtime arrives SECOND on tasks-changed
        es.simulateEvent('tasks-changed', JSON.stringify({ mtime: 3_000 }))
      })

      // lastEventMtime must be the cross-type max (9000), not the last arrival (3000)
      expect(result.current.lastEventMtime).toBe(9_000)
      // Per-type values are independent
      expect(result.current.lastEventByType?.['decisions-changed']).toBe(9_000)
      expect(result.current.lastEventByType?.['tasks-changed']).toBe(3_000)
    })
  })
})
