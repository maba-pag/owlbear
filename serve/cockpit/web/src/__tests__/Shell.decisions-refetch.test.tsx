/**
 * Workflow behavior tests1263: Wire usePendingDRs to SSE decisions-changed early-refetch
 * Scope: Shell.tsx wiring (AC4 + AC5)
 *
 * AC4 (td:2): Shell.tsx calls refetchPendingDRs() via useEffect when lastDecisionsMtime
 *   changes; uses ref-stabilized callback pattern (matching existing refetchTasksRef in
 *   useBoard.ts:81-88) to prevent rerender loops.
 * AC5 (td:1): usePendingDRs 60s polling remains active and unchanged — SSE supplements
 *   but does not replace polling.
 *
 * AC4 tests FAIL until builder adds the decisions-changed useEffect to Shell.tsx.
 * AC5 is a regression guard — verifies Shell continues calling usePendingDRs with
 * default options (no intervalMs override).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks (hoisted) ───────────────────────────────────────────────────

vi.mock('../hooks/useBoard', () => ({
  useBoard: vi.fn(),
}))

vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn(),
}))

vi.mock('../hooks/useScanPolling', () => ({
  useScanPolling: vi.fn(),
}))

vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => null),
}))

vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(() => null),
}))

vi.mock('../components/HealthBadge', () => ({
  default: vi.fn(() => null),
}))

vi.mock('../components/ActivityTab', () => ({
  default: vi.fn(() => null),
}))

vi.mock('../components/DetailTab', () => ({
  default: vi.fn(() => null),
}))

vi.mock('../components/ResolveModal', () => ({
  default: vi.fn(() => null),
}))

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import { useScanPolling } from '../hooks/useScanPolling'
import Shell from '../Shell'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BASE_BOARD = {
  statuses: [{ name: 'backlog' }],
  priorities: ['important'],
  valid_transitions: { backlog: [] } as Record<string, string[]>,
}

function stubUseScanPolling(): void {
  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })
}

function makeUseBoardReturn(lastDecisionsMtime: number | null = null) {
  return {
    board: BASE_BOARD,
    tasks: [],
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green' as const,
    refetchTasks: vi.fn(),
    // New field required by AC3 — cast needed until builder adds to type
    lastDecisionsMtime,
  } as unknown as ReturnType<typeof useBoard>
}

function makeUsePendingDRsReturn(refetch = vi.fn()) {
  return {
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch,
  }
}

function AppWrapper({ children }: { children: React.ReactNode }) {
  return (
    <PorscheDesignSystemProvider>
      <MemoryRouter>{children}</MemoryRouter>
    </PorscheDesignSystemProvider>
  )
}

// ─── Test suite ──────────────────────────────────────────────────────────────

describe('TestFromAC_ShellDecisionsRefetch', () => {
  beforeEach(() => {
    stubUseScanPolling()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ─── AC4: refetchPendingDRs called on lastDecisionsMtime change ───────────

  it('calls refetchPendingDRs when lastDecisionsMtime changes from null to a value (not on null initial)', () => {
    // Shell has no useEffect watching lastDecisionsMtime yet — this test fails at
    // the toHaveBeenCalledOnce() assertion.
    // Also verifies: null initial render does NOT eagerly call refetch.
    const refetchMock = vi.fn()
    let lastDecisionsMtime: number | null = null

    vi.mocked(useBoard).mockImplementation(() => makeUseBoardReturn(lastDecisionsMtime))
    vi.mocked(usePendingDRs).mockReturnValue(makeUsePendingDRsReturn(refetchMock))

    const { rerender } = render(<Shell />, { wrapper: AppWrapper })
    // Guard: null initial → no eager refetch
    expect(refetchMock).not.toHaveBeenCalled()

    // Simulate decisions-changed SSE → lastDecisionsMtime becomes non-null
    lastDecisionsMtime = 77_000
    rerender(<Shell />)

    // FAILS until builder adds useEffect([lastDecisionsMtime]) to Shell.tsx
    expect(refetchMock).toHaveBeenCalledOnce()
  })

  it('calls refetchPendingDRs again on subsequent lastDecisionsMtime change', () => {
    const refetchMock = vi.fn()
    let lastDecisionsMtime: number | null = 77_000

    vi.mocked(useBoard).mockImplementation(() => makeUseBoardReturn(lastDecisionsMtime))
    vi.mocked(usePendingDRs).mockReturnValue(makeUsePendingDRsReturn(refetchMock))

    const { rerender } = render(<Shell />, { wrapper: AppWrapper })
    // First render: lastDecisionsMtime=77_000 — effect fires once
    // (fails at count=0 if Shell has no effect, but expected=1 here)

    // Second decisions-changed event
    lastDecisionsMtime = 88_000
    rerender(<Shell />)

    // Two refetch calls (one per lastDecisionsMtime change)
    expect(refetchMock).toHaveBeenCalledTimes(2)
  })

  it('new refetchPendingDRs identity does not cause extra call when lastDecisionsMtime unchanged (ref-stabilized)', () => {
    // Without ref stabilization, adding refetchPendingDRs to the useEffect dependency
    // array would trigger an extra call whenever usePendingDRs returns a new function
    // identity (which it does on every re-render).
    // Shell must use a ref-stabilized pattern so only lastDecisionsMtime changes trigger the effect.
    let lastDecisionsMtime: number | null = null
    let refetchMock = vi.fn()

    vi.mocked(useBoard).mockImplementation(() => makeUseBoardReturn(lastDecisionsMtime))
    vi.mocked(usePendingDRs).mockImplementation(() => makeUsePendingDRsReturn(refetchMock))

    const { rerender } = render(<Shell />, { wrapper: AppWrapper })

    // Trigger first refetch by updating lastDecisionsMtime
    lastDecisionsMtime = 1_000
    rerender(<Shell />)
    expect(refetchMock).toHaveBeenCalledOnce()

    // Keep same lastDecisionsMtime but provide a new refetchPendingDRs function identity
    const newRefetchMock = vi.fn()
    refetchMock = newRefetchMock
    rerender(<Shell />)

    // lastDecisionsMtime unchanged → effect must NOT fire again
    expect(newRefetchMock).not.toHaveBeenCalled()
  })

  it('after refetchPendingDRs identity swap, new callback fires on next mtime change (not the stale one)', () => {
    // Proves both halves of the ref-stabilized pattern:
    // (a) initial mtime change → first refetch fires (already covered by earlier test)
    // (b) after identity swap + subsequent mtime change → NEW callback fires exactly once,
    //     OLD callback is not called again.
    // A naive implementation (no ref) would either:
    //   - call the stale old callback (ref not updated), OR
    //   - fire twice due to refetchPendingDRs in the dependency array.
    let lastDecisionsMtime: number | null = null
    let refetchMock = vi.fn()

    vi.mocked(useBoard).mockImplementation(() => makeUseBoardReturn(lastDecisionsMtime))
    vi.mocked(usePendingDRs).mockImplementation(() => makeUsePendingDRsReturn(refetchMock))

    const { rerender } = render(<Shell />, { wrapper: AppWrapper })

    // (a) First mtime change → first refetch
    const originalMock = refetchMock
    lastDecisionsMtime = 1_000
    rerender(<Shell />)
    expect(originalMock).toHaveBeenCalledOnce()

    // (b) Swap identity: same lastDecisionsMtime, new function reference
    const newRefetchMock = vi.fn()
    refetchMock = newRefetchMock
    rerender(<Shell />) // identity churn with unchanged mtime — must NOT trigger
    expect(newRefetchMock).not.toHaveBeenCalled()

    // Now change mtime → the NEW callback must fire exactly once; the old one must not fire again
    lastDecisionsMtime = 2_000
    rerender(<Shell />)
    expect(newRefetchMock).toHaveBeenCalledOnce()
    expect(originalMock).toHaveBeenCalledOnce() // still only the single original call
  })

  // ─── AC5: usePendingDRs 60s polling unchanged (regression guard) ──────────

  it('usePendingDRs is called with no options (default 60s interval preserved)', () => {
    // Guard: the builder must not pass intervalMs or any override to usePendingDRs.
    // SSE supplements polling — it must not replace it.
    vi.mocked(useBoard).mockReturnValue(makeUseBoardReturn(null))
    vi.mocked(usePendingDRs).mockReturnValue(makeUsePendingDRsReturn())

    render(<Shell />, { wrapper: AppWrapper })

    // usePendingDRs() called with no arguments
    const calls = vi.mocked(usePendingDRs).mock.calls
    expect(calls.length).toBeGreaterThan(0)
    expect(calls[0]).toHaveLength(0)
  })
})
