/**
 * Refactor useBoard to consume EventSourceProvider context
 *
 * AC1 (td:1): useBoard calls useSSEEvent('tasks-changed') and useSSEEvent('decisions-changed')
 *   from EventSourceProvider context (not useEventSource).
 * AC2 (td:1): lastDecisionsMtime reflects decisions-changed mtime from context.
 * AC3 (td:1): effectiveHealth computed from context status — open → green.
 * AC4 (td:1): interval polling is paused when context status === 'open'.
 * AC5 (td:2): SSE-triggered task refetch fires when useSSEEvent('tasks-changed').mtime changes.
 * AC6,AC7,AC8 (td:0): skipped — no tests needed.
 *
 * context via useSSEEvent instead of calling useEventSource directly.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useBoard } from '../hooks/useBoard'
import { useSSEEvent } from '../hooks/EventSourceProvider'

// ─── Module-level mock: EventSourceProvider ───────────────────────────────────
//
// Replaces useSSEEvent with a controllable stub. Tests mutate the module-level
// state variables below to control what useSSEEvent returns on each render.
//
// RED: useBoard currently does not import from EventSourceProvider — it calls
// useEventSource() directly. This mock has no effect on current behavior.
// All assertions derived from context values fail until the builder migrates.

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(),
}))

// ─── No-op EventSource stub ───────────────────────────────────────────────────
//
// jsdom has no native EventSource. This stub prevents ReferenceError from the
// current useBoard (which still calls useEventSource → new EventSource).
// After the refactor useBoard will not construct an EventSource at all.

class NoopEventSource {
  readyState = 0
  onopen: ((e: Event) => void) | null = null
  onerror: ((e: Event) => void) | null = null
  close = vi.fn()
  addEventListener() {}
}

// ─── Controllable mock state ──────────────────────────────────────────────────
//
// Tests mutate these variables then call rerender() to simulate context changes.
// The mockImplementation (set in beforeEach) reads them at call time via closure.

let mockTasksMtime: number | null = null
let mockDecisionsMtime: number | null = null
let mockStatus: 'connecting' | 'open' | 'closed' = 'connecting'

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
    if ((url as string).includes('/api/board')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(BOARD) })
    }
    if ((url as string).includes('/api/tasks')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(tasksData) })
    }
    return Promise.resolve({ ok: false, status: 404 })
  })
}

function tasksFetchCount(fetchMock: ReturnType<typeof vi.fn>): number {
  return fetchMock.mock.calls.filter((c) => (c[0] as string).includes('/api/tasks')).length
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_UseBoardSSEContext', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockTasksMtime = null
    mockDecisionsMtime = null
    mockStatus = 'connecting'
    vi.stubGlobal('EventSource', NoopEventSource)
    // Configure useSSEEvent stub to return mock state by reference.
    // The implementation reads mockTasksMtime/mockDecisionsMtime/mockStatus at
    // call time, so mutating them between renders changes what the hook returns.
    vi.mocked(useSSEEvent).mockImplementation((eventType: string) => {
      if (eventType === 'tasks-changed') return { mtime: mockTasksMtime, status: mockStatus }
      if (eventType === 'decisions-changed')
        return { mtime: mockDecisionsMtime, status: mockStatus }
      return { mtime: null, status: 'connecting' as const }
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  // ─── AC1: useSSEEvent called with both event types ────────────────────────

  it('calls useSSEEvent with tasks-changed on mount (AC1)', async () => {
    // After refactor: useBoard imports useSSEEvent from EventSourceProvider and
    // calls it with 'tasks-changed'.
    // RED: useBoard does not import useSSEEvent → mock never called → FAILS.
    vi.stubGlobal('fetch', makeFetch())
    renderHook(() => useBoard())
    await act(async () => {})

    expect(vi.mocked(useSSEEvent)).toHaveBeenCalledWith('tasks-changed')
  })

  it('calls useSSEEvent with decisions-changed on mount (AC1)', async () => {
    // After refactor: useBoard also calls useSSEEvent with 'decisions-changed'.
    // RED: useBoard does not import useSSEEvent → mock never called → FAILS.
    vi.stubGlobal('fetch', makeFetch())
    renderHook(() => useBoard())
    await act(async () => {})

    expect(vi.mocked(useSSEEvent)).toHaveBeenCalledWith('decisions-changed')
  })

  // ─── AC2: lastDecisionsMtime derived from context ─────────────────────────

  it('lastDecisionsMtime reflects decisions-changed mtime from context (AC2)', async () => {
    // After refactor: lastDecisionsMtime = useSSEEvent('decisions-changed').mtime.
    // When mock returns 9999, result.current.lastDecisionsMtime must equal 9999.
    // RED: useBoard uses useEventSource (not context) → gets null (no events) → FAILS.
    mockDecisionsMtime = 9_999
    vi.stubGlobal('fetch', makeFetch())
    const { result } = renderHook(() => useBoard())
    await act(async () => {})

    expect(result.current.lastDecisionsMtime).toBe(9_999)
  })

  // ─── AC3: effectiveHealth from context status ─────────────────────────────

  it('health is green when context status is open (AC3)', async () => {
    // After refactor: effectiveHealth = status === 'open' ? 'green' : ...
    // where status comes from useSSEEvent context.
    // RED: useBoard reads status from useEventSource. NoopEventSource never fires
    // onopen → sseStatus stays 'connecting' → effectiveHealth = 'yellow' ≠ 'green' → FAILS.
    mockStatus = 'open'
    vi.stubGlobal('fetch', makeFetch())
    const { result } = renderHook(() => useBoard())
    await act(async () => {})

    expect(result.current.health).toBe('green')
  })

  // ─── AC4: polling paused when context status is open ─────────────────────

  it('interval polling is paused when context status is open (AC4)', async () => {
    // After refactor: usePollingFetch receives paused: status === 'open' where
    // status comes from useSSEEvent context. When open, no interval polls fire.
    // RED: paused is derived from useEventSource status ('connecting' with
    // NoopEventSource) → paused=false → interval fires → count increases → FAILS.
    mockStatus = 'open'
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderHook(() => useBoard())
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    await act(async () => {
      vi.advanceTimersByTime(3_001)
    })

    // Polling must be suppressed — status=open should prevent interval polls.
    expect(tasksFetchCount(fetchMock)).toBe(countAfterMount)
  })

  // ─── AC5: refetch fires when tasks-changed mtime changes ─────────────────

  it('refetches tasks when tasks-changed mtime changes from null to a value (AC5 — happy path)', async () => {
    // After refactor: useBoard watches useSSEEvent('tasks-changed').mtime.
    // Changing mockTasksMtime and re-rendering updates the dep → refetch fires.
    // RED: useBoard ignores context mtime → dep unchanged → no refetch → FAILS.
    mockStatus = 'open'
    mockTasksMtime = null
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { rerender } = renderHook(() => useBoard())
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    // Simulate SSE tasks-changed event arriving via context mtime change.
    mockTasksMtime = 9_001
    await act(async () => {
      rerender()
    })

    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countAfterMount)
  })

  it('refetches when tasks-changed mtime changes from one value to another (AC5 — edge)', async () => {
    // Edge: mtime was already non-null; a new distinct mtime change triggers refetch.
    // After refactor: dep change (1000 → 2000) fires the effect → refetch.
    // RED: useBoard ignores context mtime → no extra fetch → FAILS.
    mockStatus = 'open'
    mockTasksMtime = 1_000
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { rerender } = renderHook(() => useBoard())
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    // Second distinct mtime — should trigger another refetch.
    mockTasksMtime = 2_000
    await act(async () => {
      rerender()
    })

    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countAfterMount)
  })

  it('fires a refetch for each distinct mtime change (AC5 — boundary)', async () => {
    // Boundary: two consecutive SSE events with distinct mtimes each cause a refetch.
    // After refactor: each rerender with a new mtime changes the dep → two extra fetches.
    // RED: useBoard ignores context mtime → no extra fetches → FAILS.
    mockStatus = 'open'
    mockTasksMtime = null
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { rerender } = renderHook(() => useBoard())
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    // First mtime change.
    mockTasksMtime = 1_001
    await act(async () => {
      rerender()
    })
    const countAfterFirst = tasksFetchCount(fetchMock)
    expect(countAfterFirst).toBeGreaterThan(countAfterMount)

    // Second distinct mtime change — must trigger yet another refetch.
    mockTasksMtime = 2_002
    await act(async () => {
      rerender()
    })
    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countAfterFirst)
  })

  // ─── AC4 discriminating: exact pause predicate ────────────────────────────

  it('interval polling continues while context status is connecting (AC4 — exact predicate)', async () => {
    // Proves paused = (sseStatus === 'open'), not a broader predicate like
    // (sseStatus !== 'closed'). If polling were incorrectly paused during
    // 'connecting', this test would fail.
    // A wrong impl with paused=(status !== 'closed') keeps polls paused on
    // 'connecting', so the count would not rise — catching the bug.
    mockStatus = 'connecting'
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    renderHook(() => useBoard())
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    await act(async () => {
      vi.advanceTimersByTime(3_001)
    })

    // Polling must fire — 'connecting' must NOT pause the interval.
    expect(tasksFetchCount(fetchMock)).toBeGreaterThan(countAfterMount)
  })

  // ─── AC5 discriminating: mtime is the sole trigger ────────────────────────

  it('status change to open without mtime change does not trigger SSE refetch (AC5 — sole trigger)', async () => {
    // Proves mtime change is the SOLE trigger for the SSE-driven refetch.
    // If [lastTasksMtime, sseStatus] effect fires refetch whenever status becomes
    // 'open' (even with the same non-null mtime), this test catches the bug:
    // a status-only change must not produce an extra /api/tasks fetch.
    mockStatus = 'connecting'
    mockTasksMtime = 500 // non-null: simulates a previously-received SSE mtime
    const fetchMock = makeFetch()
    vi.stubGlobal('fetch', fetchMock)
    const { rerender } = renderHook(() => useBoard())
    await act(async () => {})
    const countAfterMount = tasksFetchCount(fetchMock)

    // Transition to 'open' — connection established. Mtime unchanged (no new SSE event).
    mockStatus = 'open'
    await act(async () => {
      rerender()
    })

    // SSE refetch must NOT fire from a status-only change — mtime is the trigger.
    // Correct impl: effect guards on a NEW mtime value, not on sseStatus change.
    expect(tasksFetchCount(fetchMock)).toBe(countAfterMount)
  })
})

