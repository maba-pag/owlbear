/**
 * CockpitProvider same-task refetch — task #1624
 *
 * Covers:
 *   AC2 — After a successful edit mutation, Shell calls CockpitProvider.update(task).
 *          For same-task refetches (task.id unchanged), selectedTask must NOT
 *          become null while the background refetch is in-flight.
 *
 *          Root cause: the taskFetchNonce useEffect unconditionally calls
 *          setSelectedTask(null) regardless of isTaskSwitch, causing DetailTab
 *          to unmount and the save-confirmed indicator to be torn down before
 *          its 2000ms visibility window elapses.
 *
 * FAILS until builder guards setSelectedTask(null) with isTaskSwitch check
 * in CockpitProvider.tsx (i.e., only null selectedTask when switching tasks,
 * not when refetching the same task).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { type ReactNode } from 'react'

// ─── Hoisted mock factories ───────────────────────────────────────────────────
// vi.hoisted() ensures these refs are available inside vi.mock() factory closures.

const mockGetTask = vi.hoisted(() => vi.fn())
const mockUseBoard = vi.hoisted(() => vi.fn())
const mockUsePendingDRs = vi.hoisted(() => vi.fn())
const mockUseScanPolling = vi.hoisted(() => vi.fn())

vi.mock('../hooks/useBoard', () => ({ useBoard: mockUseBoard }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: mockUsePendingDRs }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: mockUseScanPolling }))
vi.mock('../api/tasks', () => ({ getTask: mockGetTask }))

// ─── Import under test ────────────────────────────────────────────────────────

import { CockpitProvider, useTaskSelection } from '../hooks/CockpitProvider'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASK_DETAIL = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: 'Some body text.',
  updated: '2026-05-01T12:00:00+00:00',
  created: '2026-05-01T10:00:00+00:00',
  tags: ['bug'],
  blocked: false,
  block_reason: null,
  claimed: false,
  claimed_at: null,
  dep_status: null,
  parent: null,
  depends_on: [],
}

const DEFAULT_BOARD_STATE = {
  board: null,
  tasks: [],
  loading: false,
  error: null,
  health: 'yellow' as const,
  refetchTasks: vi.fn(),
  lastDecisionsMtime: null as number | null,
}

const DEFAULT_DR_STATE = {
  count: 0,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  items: [] as any[],
  isLoading: false,
  error: null as Error | null,
  refetch: vi.fn(),
}

const DEFAULT_SCAN_STATE = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  items: [] as any[],
  isLoading: false,
  error: null as Error | null,
  refetch: vi.fn(),
}

// ─── Wrapper ──────────────────────────────────────────────────────────────────

const wrapper = ({ children }: { children: ReactNode }) => (
  <CockpitProvider>{children}</CockpitProvider>
)

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_CockpitSameTaskRefetch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE })
    mockUsePendingDRs.mockReturnValue({ ...DEFAULT_DR_STATE })
    mockUseScanPolling.mockReturnValue({ ...DEFAULT_SCAN_STATE })
  })

  // AC2: selectedTask must not flash null during same-task refetch

  it('selectedTask is not null immediately after update(sameTask) increments refetch nonce', async () => {
    // First getTask call: initial fetch resolves with TASK_DETAIL.
    // Second getTask call: refetch hangs (deferred promise) so we can observe
    // the intermediate state before the background refetch completes.
    let resolveRefetch!: (task: typeof TASK_DETAIL) => void
    mockGetTask
      .mockResolvedValueOnce(TASK_DETAIL)
      .mockImplementationOnce(
        () => new Promise<typeof TASK_DETAIL>(resolve => { resolveRefetch = resolve }),
      )

    const { result } = renderHook(() => useTaskSelection(), { wrapper })

    // Select task 42 and wait for the initial fetch to populate selectedTask.
    await act(async () => {
      result.current.select(42)
    })
    expect(result.current.selectedTask).toEqual(TASK_DETAIL)

    // update(TASK_DETAIL): sets selectedTask = TASK_DETAIL and increments
    // taskFetchNonce, which triggers the useEffect.
    // The useEffect currently calls setSelectedTask(null) unconditionally —
    // even when the task.id is unchanged (isTaskSwitch = false).
    // Using synchronous act so the pending refetch promise does NOT resolve,
    // leaving the intermediate state observable.
    act(() => {
      result.current.update(TASK_DETAIL)
    })

    // FAILS on current code: the useEffect fires, calls setSelectedTask(null)
    // unconditionally, and the async refetch hasn't completed yet — selectedTask
    // is null, which causes DetailTab to return null and unmount TaskFieldsEditor,
    // tearing down the save-confirmed indicator before its 2000ms window.
    //
    // After fix: setSelectedTask(null) is guarded by isTaskSwitch (false for
    // same-task nonce increments) → selectedTask remains non-null throughout.
    expect(result.current.selectedTask).not.toBeNull()

    // Cleanup: resolve the pending refetch to avoid unhandled-promise warnings
    // during test teardown.
    await act(async () => {
      resolveRefetch(TASK_DETAIL)
    })
  })
})
