/**
 * CockpitProvider same-task refetch guard — task #1624 (retry cycle 3)
 *
 * Covers:
 *   AC2 — After a successful edit mutation, CockpitProvider must NOT null
 *          selectedTask during the same-task refetch triggered by update().
 *          Specifically: update(task) where task.id === selectedTaskId must
 *          keep selectedTask non-null throughout the refetch cycle.
 *
 * All tests FAIL on current code where setSelectedTask(null) fires
 * unconditionally in the nonce-driven effect, even for same-task refetches.
 * They pass after the fix guards setSelectedTask(null) with isTaskSwitch.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { type ReactNode } from 'react'

// ─── Hoisted mock factories ───────────────────────────────────────────────────

const mockGetTask = vi.hoisted(() => vi.fn())
const mockUseBoard = vi.hoisted(() => vi.fn())
const mockUsePendingDRs = vi.hoisted(() => vi.fn())
const mockUseScanPolling = vi.hoisted(() => vi.fn())

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('../api/tasks', () => ({ getTask: mockGetTask }))
vi.mock('../hooks/useBoard', () => ({ useBoard: mockUseBoard }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: mockUsePendingDRs }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: mockUseScanPolling }))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { CockpitProvider, useTaskSelection } from '../hooks/CockpitProvider'
import type { TaskDetail } from '../api/tasks'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASK_DETAIL: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: 'Some body text.',
  updated: '2026-05-01T12:00:00+00:00',
  created: '2026-05-01T10:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
  claimed_at: null,
  dep_status: null,
  parent: null,
  depends_on: [],
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function setupDefaultMocks() {
  mockUseBoard.mockReturnValue({
    board: null,
    tasks: [],
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks: vi.fn(),
    lastDecisionsMtime: null,
  })
  mockUsePendingDRs.mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })
  mockUseScanPolling.mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })
}

function wrapper({ children }: { children: ReactNode }) {
  return <CockpitProvider>{children}</CockpitProvider>
}

// ─── Tests ────────────────────────────────────────────────────────────────────

// ════════════════════════════════════════════════════════════════════════════
// TestFromAC_CockpitProviderSameTaskRefetch
// AC2: After update(task) with the same task.id as selectedTaskId,
//      selectedTask must never become null during the refetch cycle.
//      Root cause: setSelectedTask(null) fires unconditionally in the
//      nonce-driven effect even when isTaskSwitch is false.
// ════════════════════════════════════════════════════════════════════════════

describe('TestFromAC_CockpitProviderSameTaskRefetch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupDefaultMocks()
  })

  // ─── Happy path: selectedTask never null during same-task refetch ─────────

  it('selectedTask is never null after update() triggers a same-task refetch', async () => {
    // Arrange: initial select resolves immediately; update-triggered refetch stays pending.
    // By leaving the refetch pending we can inspect selectedTask while the refetch
    // is in-flight — the critical window where the null occurs on current code.
    const REFRESHED: TaskDetail = { ...TASK_DETAIL, updated: '2026-05-01T12:01:00+00:00' }

    let resolveRefetch!: (task: TaskDetail) => void
    const pendingRefetch = new Promise<TaskDetail>((resolve) => {
      resolveRefetch = resolve
    })

    mockGetTask
      .mockResolvedValueOnce(TASK_DETAIL)  // initial select() fetch
      .mockReturnValueOnce(pendingRefetch)  // update()-triggered refetch (stays pending)

    const { result } = renderHook(() => useTaskSelection(), { wrapper })

    // Select task 42 — triggers initial fetch.
    await act(async () => {
      result.current.select(42)
    })

    // Wait for the initial fetch to resolve and selectedTask to be populated.
    await waitFor(() => {
      expect(result.current.selectedTask?.id).toBe(42)
    })

    // Call update() with the refreshed task (same id=42, newer updated timestamp).
    //
    // Current code behaviour:
    //   1. setSelectedTask(REFRESHED)    — optimistic update (good)
    //   2. setTaskFetchNonce(n+1)        — triggers nonce-driven effect
    //   3. Effect fires: setSelectedTask(null)  ← UNCONDITIONAL (bug)
    //   4. Effect starts pending refetch
    //   After act() flushes: selectedTask === null
    //
    // Fixed code behaviour:
    //   1. setSelectedTask(REFRESHED)    — optimistic update (good)
    //   2. setTaskFetchNonce(n+1)        — triggers nonce-driven effect
    //   3. Effect: isTaskSwitch === false (same task id) → setSelectedTask(null) SKIPPED
    //   4. Effect starts pending refetch
    //   After act() flushes: selectedTask === REFRESHED (non-null)
    await act(async () => {
      result.current.update(REFRESHED)
    })

    // FAILS on current code: selectedTask is null because the effect cleared it
    // unconditionally (setSelectedTask(null) fires regardless of isTaskSwitch).
    expect(result.current.selectedTask).not.toBeNull()

    // Clean up: resolve the pending refetch so the effect can complete cleanly.
    await act(async () => {
      resolveRefetch(REFRESHED)
    })
  })

  // ─── Stronger contract: selectedTask shows non-null id during refetch ─────

  it('selectedTask.id remains 42 while same-task refetch is in-flight after update()', async () => {
    // More specific assertion: not only must selectedTask be non-null,
    // but it must still reflect the task id (42) throughout the refetch window.
    const REFRESHED: TaskDetail = { ...TASK_DETAIL, updated: '2026-05-01T12:02:00+00:00' }

    let resolveRefetch!: (task: TaskDetail) => void
    const pendingRefetch = new Promise<TaskDetail>((resolve) => {
      resolveRefetch = resolve
    })

    mockGetTask
      .mockResolvedValueOnce(TASK_DETAIL)
      .mockReturnValueOnce(pendingRefetch)

    const { result } = renderHook(() => useTaskSelection(), { wrapper })

    await act(async () => { result.current.select(42) })
    await waitFor(() => { expect(result.current.selectedTask?.id).toBe(42) })

    await act(async () => { result.current.update(REFRESHED) })

    // FAILS on current code: selectedTask is null → .id is undefined, not 42.
    expect(result.current.selectedTask?.id).toBe(42)

    await act(async () => { resolveRefetch(REFRESHED) })
  })

  // ─── Edge: selectedTask updated to refreshed data after refetch resolves ──

  it('selectedTask is updated to the refreshed task after same-task refetch resolves', async () => {
    // After the refetch resolves, selectedTask must reflect the refreshed data.
    // This test also exercises the full same-task refetch lifecycle:
    //   select → initial fetch → update (optimistic + nonce) → refetch resolves.
    const REFRESHED: TaskDetail = { ...TASK_DETAIL, updated: '2026-05-01T12:03:00+00:00' }

    let resolveRefetch!: (task: TaskDetail) => void
    const pendingRefetch = new Promise<TaskDetail>((resolve) => {
      resolveRefetch = resolve
    })

    mockGetTask
      .mockResolvedValueOnce(TASK_DETAIL)
      .mockReturnValueOnce(pendingRefetch)

    const { result } = renderHook(() => useTaskSelection(), { wrapper })

    await act(async () => { result.current.select(42) })
    await waitFor(() => { expect(result.current.selectedTask?.id).toBe(42) })

    await act(async () => { result.current.update(REFRESHED) })

    // FAILS on current code at this assertion (selectedTask is null).
    expect(result.current.selectedTask).not.toBeNull()

    // Allow refetch to resolve.
    await act(async () => { resolveRefetch(REFRESHED) })

    // After refetch: selectedTask must reflect the refreshed updated timestamp.
    await waitFor(() => {
      expect(result.current.selectedTask?.updated).toBe(REFRESHED.updated)
    })
  })
})
