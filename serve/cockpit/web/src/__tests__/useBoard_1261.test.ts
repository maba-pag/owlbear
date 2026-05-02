/**
 * RED phase tests for #1261: Integrate EventSource into useBoard with fallback orchestration.
 *
 * AC1 (td:1): useBoard creates an EventSource for /api/events on mount
 * AC2 (td:2): paused=true propagated to usePollingFetch when SSE is open (polling suppressed)
 * AC3 (td:2): refetchTasks() triggered when lastEventMtime changes via SSE event
 * AC4 (td:2): polling resumes (paused=false) when SSE transitions to not-open
 * AC5 (td:2): health computed as green/yellow/polling-fallback based on SSE status
 * AC6 (td:0): skipped — no tests needed
 * AC7 (td:1): UseBoardResult interface intact when EventSource is globally stubbed
 * AC8 (td:1): health field name preserved in UseBoardResult
 *
 * All 12 tests FAIL until builder wires useEventSource into useBoard.ts.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useBoard } from '../hooks/useBoard'

// ─── MockEventSource ─────────────────────────────────────────────────────────
//
// jsdom has no EventSource. This mock matches the shape used by useEventSource:
// onopen, onerror, close, and addEventListener (for 'tasks-changed' events).
// readyState mirrors the Web spec constants.

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
  private listeners: Record<string, ((e: MessageEvent) => void)[]> = {}

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

  simulateFatalClose(): void {
    this.readyState = MockEventSource.CLOSED
    if (this.onerror) this.onerror(new Event('error'))
  }

  simulateEvent(type: string, data: unknown): void {
    const event = new MessageEvent(type, { data: JSON.stringify(data) })
    ;(this.listeners[type] ?? []).forEach((fn) => fn(event))
  }
}

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [{ name: 'backlog' }],
  priorities: ['important'],
  valid_transitions: { backlog: [] } as Record<string, string[]>,
}

const TASKS_V1 = {
  tasks: [
    {
      id: 1,
      title: 'T1',
      status: 'backlog',
      priority: 'important',
      tags: [],
      blocked: false,
      block_reason: null,
      claimed: false,
      updated: '2026-01-01',
    },
  ],
  mtime: 1000,
}

function makeFetch(tasksData: unknown = TASKS_V1): ReturnType<typeof vi.fn> {
  return vi.fn((url: string) => {
    if (url.includes('/api/board')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
    }
    if (url.includes('/api/tasks')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(tasksData) })
    }
    return Promise.resolve({ ok: false, status: 404 })
  })
}

function makeFailFetch(): ReturnType<typeof vi.fn> {
  return vi.fn((url: string) => {
    if (url.includes('/api/board')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
    }
    // /api/tasks always fails → useConnectionHealth degrades
    return Promise.resolve({ ok: false, status: 503 })
  })
}

function tasksFetchCount(fetchMock: ReturnType<typeof vi.fn>): number {
  return fetchMock.mock.calls.filter((c) => (c[0] as string).includes('/api/tasks')).length
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_UseBoardSSEIntegration', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    MockEventSource.instances = []
    vi.stubGlobal('EventSource', MockEventSource)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  // ─── AC1: useEventSource wired in ─────────────────────────────────────────

  it('creates an EventSource for /api/events on mount', async () => {
    vi.stubGlobal('fetch', makeFetch())
    renderHook(() => useBoard())
    await act(async () => {})

    expect(MockEventSource.instances).toHaveLength(1)
    expect(MockEventSource.instances[0].url).toBe('/api/events')
  })

  // ─── AC2: paused=true when SSE is open ────────────────────────────────────

  it('suppresses interval polling when SSE transitions to open', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderHook(() => useBoard())
    // Let mount-time (immediate) poll complete
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    // Open SSE — paused should become true
    await act(async () => {
      MockEventSource.instances[0]?.simulateOpen()
    })
    // Advance past one polling interval (3 s)
    await act(async () => {
      vi.advanceTimersByTime(3001)
    })
    // The interval poll should have been suppressed
    expect(tasksFetchCount(fetchMock)).toBe(countAfterMount)
  })

  it('polling does not fire across multiple intervals while SSE remains open', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderHook(() => useBoard())
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    await act(async () => {
      MockEventSource.instances[0]?.simulateOpen()
    })
    // Advance past three polling intervals (9 s)
    await act(async () => {
      vi.advanceTimersByTime(9001)
    })
    // All three interval polls must be suppressed
    expect(tasksFetchCount(fetchMock)).toBe(countAfterMount)
  })

  it('polling is paused immediately when SSE opens mid-interval (boundary)', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderHook(() => useBoard())
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    // SSE opens partway through the first 3 s interval
    await act(async () => {
      vi.advanceTimersByTime(1500)
    })
    await act(async () => {
      MockEventSource.instances[0]?.simulateOpen()
    })
    // Cross the interval boundary — would trigger a poll if not paused
    await act(async () => {
      vi.advanceTimersByTime(1501)
    })
    // The poll due at 3 s should be suppressed because SSE was open before it fired
    expect(tasksFetchCount(fetchMock)).toBe(countAfterMount)
  })

  // ─── AC3: refetchTasks on lastEventMtime change ────────────────────────────

  it('triggers refetchTasks when SSE delivers a tasks-changed event while open', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderHook(() => useBoard())
    await act(async () => {})

    await act(async () => {
      MockEventSource.instances[0]?.simulateOpen()
    })
    const countAfterOpen = tasksFetchCount(fetchMock)

    // Fire a tasks-changed event — should trigger an immediate refetch
    await act(async () => {
      MockEventSource.instances[0]?.simulateEvent('tasks-changed', { mtime: 9001 })
    })
    await act(async () => {})

    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countAfterOpen)
  })

  it('triggers refetchTasks for each distinct tasks-changed SSE event', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderHook(() => useBoard())
    await act(async () => {})

    await act(async () => {
      MockEventSource.instances[0]?.simulateOpen()
    })
    const countAfterOpen = tasksFetchCount(fetchMock)

    // First event — refetch
    await act(async () => {
      MockEventSource.instances[0]?.simulateEvent('tasks-changed', { mtime: 1001 })
    })
    await act(async () => {})

    // Second event with distinct mtime — another refetch
    await act(async () => {
      MockEventSource.instances[0]?.simulateEvent('tasks-changed', { mtime: 1002 })
    })
    await act(async () => {})

    // Exactly two additional fetches — one per SSE event
    expect(tasksFetchCount(fetchMock)).toBe(countAfterOpen + 2)
  })

  // ─── AC4: polling resumes when SSE is not open ────────────────────────────

  it('polling resumes when SSE closes after an open period', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderHook(() => useBoard())
    await act(async () => {})

    // Open SSE → polling pauses
    await act(async () => {
      MockEventSource.instances[0]?.simulateOpen()
    })
    const countAfterOpen = tasksFetchCount(fetchMock)

    // Confirm polling is paused
    await act(async () => {
      vi.advanceTimersByTime(3001)
    })
    expect(tasksFetchCount(fetchMock)).toBe(countAfterOpen)

    // Close SSE → polling should resume
    await act(async () => {
      MockEventSource.instances[0]?.simulateFatalClose()
    })
    await act(async () => {
      vi.advanceTimersByTime(3001)
    })
    // At least one interval poll should have fired after SSE closed
    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countAfterOpen)
  })

  it('polling fires normally after SSE stall closes the connection (open → stall → closed)', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderHook(() => useBoard())
    await act(async () => {})

    await act(async () => {
      MockEventSource.instances[0]?.simulateOpen()
    })
    const countAfterOpen = tasksFetchCount(fetchMock)

    // Polling must be paused while SSE is open — proves integration (fails without it)
    await act(async () => {
      vi.advanceTimersByTime(3001)
    })
    expect(tasksFetchCount(fetchMock)).toBe(countAfterOpen)

    // Simulate stall-induced connection close
    await act(async () => {
      MockEventSource.instances[0]?.simulateFatalClose()
    })
    await act(async () => {
      vi.advanceTimersByTime(3001)
    })
    // Polling should have resumed (at least one fetch after close)
    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countAfterOpen)
  })

  // ─── AC5: health computed from SSE status ─────────────────────────────────

  it('returns health=green when SSE is open, overriding a degraded polling health', async () => {
    // Polling always fails so useConnectionHealth degrades
    const fetchMock = makeFailFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useBoard())

    // Advance until polling health degrades past the 6 s green threshold
    await act(async () => {
      vi.advanceTimersByTime(7000)
    })
    // Health should have degraded (yellow or red) due to failed polling
    expect(['yellow', 'red']).toContain(result.current.health)

    // Open SSE → health must override to green
    await act(async () => {
      MockEventSource.instances[0]?.simulateOpen()
    })
    expect(result.current.health).toBe('green')
  })

  it('returns health=yellow when SSE is connecting, overriding a healthy polling result', async () => {
    // Polling succeeds → useConnectionHealth would report green
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useBoard())
    // Let initial poll complete (polling health = green)
    await act(async () => {})

    // SSE remains in connecting state (simulateOpen never called)
    // After integration: health must be 'yellow' (connecting override)
    // Currently: health is 'green' (polling-based only, no SSE override)
    expect(result.current.health).toBe('yellow')
  })

  it('health remains green throughout an extended SSE-open period even when polling fails', async () => {
    const fetchMock = makeFailFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useBoard())
    await act(async () => {})

    // Open SSE
    await act(async () => {
      MockEventSource.instances[0]?.simulateOpen()
    })
    // Advance well past the polling-health degradation threshold (15 s → red from polling)
    await act(async () => {
      vi.advanceTimersByTime(16000)
    })
    // SSE is still open — health must stay green (SSE override in effect)
    expect(result.current.health).toBe('green')
  })

  // ─── AC4 (retry): polling fires while SSE remains in connecting state ────

  it('polling fires on schedule when SSE remains in connecting state for a full interval', async () => {
    // SSE never opens — readyState stays CONNECTING.
    // paused must be false (only 'open' suppresses polling).
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderHook(() => useBoard())
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    // Advance a full polling interval without ever opening SSE
    await act(async () => {
      vi.advanceTimersByTime(3001)
    })
    await act(async () => {})

    // Interval poll must have fired — connecting is not paused
    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countAfterMount)
  })

  // ─── AC5 (retry): health falls through to polling value when SSE is closed ─

  it('health falls through to polling-based value (green) when SSE is closed', async () => {
    // Polling succeeds → useConnectionHealth will be green after markHealthy()
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useBoard())

    // Let initial poll complete — polling health becomes green
    await act(async () => {})

    // SSE starts in connecting → effectiveHealth is yellow
    expect(result.current.health).toBe('yellow')

    // Close SSE (fatal error with readyState=CLOSED) → sseStatus becomes 'closed'
    await act(async () => {
      MockEventSource.instances[0]?.simulateFatalClose()
    })
    await act(async () => {})

    // SSE is now closed → effectiveHealth must fall through to polling health
    // Polling succeeded earlier → polling health = green → effectiveHealth = green
    expect(result.current.health).toBe('green')
  })

  // ─── AC7 + AC8: UseBoardResult interface with EventSource ─────────────────

  it('returns all UseBoardResult fields including health when EventSource is globally available', async () => {
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useBoard())
    await act(async () => {})

    // EventSource must have been instantiated — proves SSE is wired in (AC7 gate)
    expect(MockEventSource.instances.length).toBeGreaterThan(0)

    // All required UseBoardResult fields present with correct types (AC7 interface, AC8 field names)
    expect(result.current).toHaveProperty('board')
    expect(result.current).toHaveProperty('tasks')
    expect(result.current).toHaveProperty('loading')
    expect(result.current).toHaveProperty('error')
    expect(result.current).toHaveProperty('isFetching')
    expect(result.current).toHaveProperty('isStale')
    expect(result.current).toHaveProperty('refetchTasks')
    // health field name must be exactly 'health' — not renamed to sseHealth/effectiveHealth
    expect(result.current).toHaveProperty('health')
    expect(['green', 'yellow', 'red']).toContain(result.current.health)
  })
})
