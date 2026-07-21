/**
 * CockpitProvider_1504.test.tsx
 *
 * Tests for task #1504: Implement CockpitProvider and slim Shell.tsx
 *
 * AC-1:  hooks/CockpitProvider.tsx exports CockpitProvider, useBoardState,
 *        useTaskSelection, useDRState
 * AC-2:  useBoard and usePendingDRs remain as separate modules
 *        with unchanged exports (regression guards)
 * AC-3:  useBoardState() return shape: board, tasks, loading, error (string|null),
 *        health (HealthState), refetchTasks, and workspaceHealth
 * AC-4:  useTaskSelection() return shape: selectedTaskId, selectedTask,
 *        selectedTaskError, select/clear/update actions; AbortController aborts
 *        on task switch and unmount
 * AC-5:  useDRState() return shape: count, items, isLoading, error (Error|null),
 *        refetch, selectedDRId, setSelectedDRId, selectedDR (derived PendingDR|null)
 * AC-6:  lastDecisionsMtime change (non-null) triggers refetchPendingDRs inside
 *        CockpitProvider; initial null does not trigger refetch
 * AC-7:  useConnectionHealth is NOT re-exported from CockpitProvider (regression guard)
 * AC-11: useBoardState/useTaskSelection/useDRState throw Error when called outside
 *        CockpitProvider (following useSSEEvent pattern)
 *
 * RED: The top-level import from '../hooks/CockpitProvider' fails with
 * module-not-found until the builder creates the file → all tests fail.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { type ReactNode } from 'react'
import type { PendingDR } from '../hooks/usePendingDRs'

// ─── Hoisted mock factories ───────────────────────────────────────────────────
// vi.hoisted() runs before vi.mock() factories, making these refs safe to use
// inside factory closures.

const mockRefetchTasks = vi.hoisted(() => vi.fn())
const mockRefetchPendingDRs = vi.hoisted(() => vi.fn())
const mockGetTask = vi.hoisted(() => vi.fn())

const DEFAULT_BOARD_STATE = {
  board: null,
  tasks: [],
  loading: false,
  error: null,
  isFetching: false,
  isStale: false,
  health: 'yellow' as const,
  refetchTasks: mockRefetchTasks,
  lastDecisionsMtime: null as number | null,
}

const DEFAULT_DR_STATE = {
  count: 0,
  items: [] as PendingDR[],
  isLoading: false,
  error: null as Error | null,
  refetch: mockRefetchPendingDRs,
}

const mockUseBoard = vi.hoisted(() => vi.fn())
const mockUsePendingDRs = vi.hoisted(() => vi.fn())
const mockUseWorkspaceHealth = vi.hoisted(() => vi.fn())

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('../hooks/useBoard', () => ({ useBoard: mockUseBoard }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: mockUsePendingDRs }))
vi.mock('../hooks/useWorkspaceHealth', () => ({ useWorkspaceHealth: mockUseWorkspaceHealth }))
vi.mock('../api/tasks', () => ({ getTask: mockGetTask }))

// ─── Import module under test ─────────────────────────────────────────────────
// RED: This import fails with module-not-found before the builder creates
// hooks/CockpitProvider.tsx. All tests therefore fail in RED.

import {
  CockpitProvider,
  useBoardState,
  useTaskSelection,
  useDRState,
} from '../hooks/CockpitProvider'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASK_DETAIL = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: '## Objectives\n\n- fix',
  updated: '2026-05-12T00:00:00+00:00',
  created: '2026-05-11T00:00:00+00:00',
  tags: ['backend'],
  blocked: false,
  block_reason: null,
  claimed: false,
  claimed_at: null,
  dep_status: null,
  parent: null,
  depends_on: [],
}

const PENDING_DR: PendingDR = {
  id: 'dr-abc-123',
  task_id: 99,
  agent: 'builder',
  request_type: 'decision',
  created: '2026-05-12T00:00:00+00:00',
  title: 'Approve approach?',
  kind: 'decision',
  options: [],
  body: 'Full body text',
  body_preview: 'Full body text',
}

// ─── Wrapper ──────────────────────────────────────────────────────────────────

const wrapper = ({ children }: { children: ReactNode }) => (
  <CockpitProvider>{children}</CockpitProvider>
)

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_CockpitProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE })
    mockUsePendingDRs.mockReturnValue({ ...DEFAULT_DR_STATE })
    mockUseWorkspaceHealth.mockReturnValue({
      health: { status: 'healthy', modules: {} },
      connectionError: null,
      isFetching: false,
      receipt: null,
      refresh: vi.fn(),
      refreshAfterMutation: vi.fn(),
      mergeRepair: vi.fn(),
      dismissReceipt: vi.fn(),
    })
  })

  // ─── AC-1: Named exports ───────────────────────────────────────────────────

  describe('AC-1: named exports from hooks/CockpitProvider', () => {
    it('exports CockpitProvider as a callable component', () => {
      expect(typeof CockpitProvider).toBe('function')
    })

    it('exports useBoardState as a callable function', () => {
      expect(typeof useBoardState).toBe('function')
    })

    it('exports useTaskSelection as a callable function', () => {
      expect(typeof useTaskSelection).toBe('function')
    })

    it('exports useDRState as a callable function', () => {
      expect(typeof useDRState).toBe('function')
    })
  })

  // ─── AC-2: Underlying hooks remain unchanged ───────────────────────────────
  // Regression guards: builder must not remove or fold these separate modules.
  // These pass by importActual (bypassing vi.mock) and fail if modules are deleted.

  describe('AC-2: underlying hooks remain as separate modules with unchanged exports', () => {
    it('useBoard is still a named export of hooks/useBoard', async () => {
      const actual = await vi.importActual<typeof import('../hooks/useBoard')>('../hooks/useBoard')
      expect(typeof actual.useBoard).toBe('function')
    })

    it('usePendingDRs is still a named export of hooks/usePendingDRs', async () => {
      const actual =
        await vi.importActual<typeof import('../hooks/usePendingDRs')>('../hooks/usePendingDRs')
      expect(typeof actual.usePendingDRs).toBe('function')
    })

  })

  // ─── AC-3: useBoardState() return shape ───────────────────────────────────

  describe('AC-3: useBoardState() return shape', () => {
    // Happy path: field presence and types

    it('exposes board (Board | null)', () => {
      const { result } = renderHook(() => useBoardState(), { wrapper })
      expect('board' in result.current).toBe(true)
    })

    it('exposes tasks (Task[])', () => {
      const { result } = renderHook(() => useBoardState(), { wrapper })
      expect(Array.isArray(result.current.tasks)).toBe(true)
    })

    it('exposes loading (boolean)', () => {
      const { result } = renderHook(() => useBoardState(), { wrapper })
      expect(typeof result.current.loading).toBe('boolean')
    })

    it('exposes board error as string or null', () => {
      mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE, error: 'fetch failed' })
      const { result } = renderHook(() => useBoardState(), { wrapper })
      const { error } = result.current
      expect(error === null || typeof error === 'string').toBe(true)
      expect(result.current.error).toBe('fetch failed')
    })

    it('exposes health (HealthState)', () => {
      mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE, health: 'green' as const })
      const { result } = renderHook(() => useBoardState(), { wrapper })
      expect(result.current.health).toBe('green')
    })

    it('exposes refetchTasks as a function', () => {
      const { result } = renderHook(() => useBoardState(), { wrapper })
      expect(typeof result.current.refetchTasks).toBe('function')
    })

    it('exposes ordered aggregate workspace health state', () => {
      const { result } = renderHook(() => useBoardState(), { wrapper })
      expect(result.current.workspaceHealth.health.status).toBe('healthy')
      expect(typeof result.current.workspaceHealth.refresh).toBe('function')
    })

    // Edge: board value flows through from useBoard()
    it('board value is forwarded from useBoard()', () => {
      const board = {
        statuses: [{ name: 'todo' }, { name: 'done' }],
        priorities: ['high', 'low'],
        valid_transitions: { todo: ['done'] },
      }
      mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE, board })
      const { result } = renderHook(() => useBoardState(), { wrapper })
      expect(result.current.board).toEqual(board)
    })

    // Edge: tasks list flows through from useBoard()
    it('tasks list is forwarded from useBoard()', () => {
      const tasks = [
        {
          id: 1,
          title: 'Task A',
          status: 'todo',
          priority: 'important',
          updated: '2026-05-12T00:00:00+00:00',
          tags: [],
          blocked: false,
          block_reason: null,
          claimed: false,
        },
      ]
      mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE, tasks })
      const { result } = renderHook(() => useBoardState(), { wrapper })
      expect(result.current.tasks).toEqual(tasks)
    })
  })

  // ─── AC-4: useTaskSelection() shape and AbortController ───────────────────

  describe('AC-4: useTaskSelection() shape and AbortController', () => {
    beforeEach(() => {
      // Default: getTask never resolves (prevents state-update-after-unmount warnings)
      mockGetTask.mockReturnValue(new Promise(() => {}))
    })

    // Happy path: initial state

    it('returns selectedTaskId as null initially', () => {
      const { result } = renderHook(() => useTaskSelection(), { wrapper })
      expect(result.current.selectedTaskId).toBeNull()
    })

    it('returns selectedTask as null initially', () => {
      const { result } = renderHook(() => useTaskSelection(), { wrapper })
      expect(result.current.selectedTask).toBeNull()
    })

    it('returns selectedTaskError as null initially', () => {
      const { result } = renderHook(() => useTaskSelection(), { wrapper })
      expect(result.current.selectedTaskError).toBeNull()
    })

    it('exposes a select action function', () => {
      const { result } = renderHook(() => useTaskSelection(), { wrapper })
      expect(typeof result.current.select).toBe('function')
    })

    it('exposes a clear action function', () => {
      const { result } = renderHook(() => useTaskSelection(), { wrapper })
      expect(typeof result.current.clear).toBe('function')
    })

    it('exposes an update action function', () => {
      const { result } = renderHook(() => useTaskSelection(), { wrapper })
      expect(typeof result.current.update).toBe('function')
    })

    it('select(taskId) sets selectedTaskId', async () => {
      const { result } = renderHook(() => useTaskSelection(), { wrapper })

      await act(async () => {
        result.current.select(42)
      })

      expect(result.current.selectedTaskId).toBe(42)
    })

    it('clear() resets selectedTaskId to null', async () => {
      const { result } = renderHook(() => useTaskSelection(), { wrapper })

      await act(async () => {
        result.current.select(42)
      })
      await act(async () => {
        result.current.clear()
      })

      expect(result.current.selectedTaskId).toBeNull()
    })

    // Happy path: successful task fetch populates selectedTask

    it('selectedTask is populated after successful getTask', async () => {
      mockGetTask.mockResolvedValue(TASK_DETAIL)
      const { result } = renderHook(() => useTaskSelection(), { wrapper })

      await act(async () => {
        result.current.select(42)
      })

      expect(result.current.selectedTask).toEqual(TASK_DETAIL)
    })

    // Error path: ApiError → selectedTaskError is a non-null string

    it('selectedTaskError is a non-null string when getTask throws ApiError', async () => {
      const { ApiError } = await vi.importActual<typeof import('../api/errors')>('../api/errors')
      mockGetTask.mockRejectedValue(new ApiError(404, 'Get task request failed with status 404'))
      const { result } = renderHook(() => useTaskSelection(), { wrapper })

      await act(async () => {
        result.current.select(99)
      })

      expect(typeof result.current.selectedTaskError).toBe('string')
      expect(result.current.selectedTaskError).not.toBeNull()
    })

    // AbortController: abort on task switch

    it('aborts in-flight getTask fetch when selectedTaskId changes (task switch)', async () => {
      let capturedSignal: AbortSignal | undefined
      mockGetTask.mockImplementation((_id: number, opts?: { signal?: AbortSignal }) => {
        capturedSignal = opts?.signal
        return new Promise(() => {}) // never resolves
      })

      const { result } = renderHook(() => useTaskSelection(), { wrapper })

      await act(async () => {
        result.current.select(42)
      })
      expect(capturedSignal?.aborted).toBe(false)
      const firstSignal = capturedSignal

      await act(async () => {
        result.current.select(99) // switch task → abort previous
      })

      expect(firstSignal?.aborted).toBe(true)
    })

    // AbortController: abort on unmount

    it('aborts in-flight getTask fetch on provider unmount', async () => {
      let capturedSignal: AbortSignal | undefined
      mockGetTask.mockImplementation((_id: number, opts?: { signal?: AbortSignal }) => {
        capturedSignal = opts?.signal
        return new Promise(() => {})
      })

      const { result, unmount } = renderHook(() => useTaskSelection(), { wrapper })

      await act(async () => {
        result.current.select(42)
      })
      expect(capturedSignal?.aborted).toBe(false)

      act(() => {
        unmount()
      })

      expect(capturedSignal?.aborted).toBe(true)
    })

    // Boundary: getTask receives AbortController signal

    it('getTask is called with an AbortController signal', async () => {
      const { result } = renderHook(() => useTaskSelection(), { wrapper })

      await act(async () => {
        result.current.select(42)
      })

      expect(mockGetTask).toHaveBeenCalledWith(
        42,
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      )
    })

    // Boundary: update() triggers a re-fetch for the same task

    it('update() triggers a new getTask call for the currently selected task', async () => {
      mockGetTask.mockResolvedValue(TASK_DETAIL)
      const { result } = renderHook(() => useTaskSelection(), { wrapper })

      await act(async () => {
        result.current.select(42)
      })
      const countAfterSelect = mockGetTask.mock.calls.length

      await act(async () => {
        result.current.update()
      })

      expect(mockGetTask.mock.calls.length).toBeGreaterThan(countAfterSelect)
      const lastCall = mockGetTask.mock.calls[mockGetTask.mock.calls.length - 1]
      expect(lastCall[0]).toBe(42) // same task id
    })
  })

  // ─── AC-5: useDRState() return shape ──────────────────────────────────────

  describe('AC-5: useDRState() return shape', () => {
    // Happy path: initial state field types

    it('returns count (number)', () => {
      const { result } = renderHook(() => useDRState(), { wrapper })
      expect(typeof result.current.count).toBe('number')
    })

    it('returns items (PendingDR[])', () => {
      const { result } = renderHook(() => useDRState(), { wrapper })
      expect(Array.isArray(result.current.items)).toBe(true)
    })

    it('returns isLoading (boolean)', () => {
      const { result } = renderHook(() => useDRState(), { wrapper })
      expect(typeof result.current.isLoading).toBe('boolean')
    })

    it('returns error as Error or null', () => {
      const { result } = renderHook(() => useDRState(), { wrapper })
      expect(result.current.error === null || result.current.error instanceof Error).toBe(true)
    })

    it('returns refetch as a function', () => {
      const { result } = renderHook(() => useDRState(), { wrapper })
      expect(typeof result.current.refetch).toBe('function')
    })

    it('returns selectedDRId as null initially', () => {
      const { result } = renderHook(() => useDRState(), { wrapper })
      expect(result.current.selectedDRId).toBeNull()
    })

    it('returns setSelectedDRId as a function', () => {
      const { result } = renderHook(() => useDRState(), { wrapper })
      expect(typeof result.current.setSelectedDRId).toBe('function')
    })

    it('returns selectedDR as null initially', () => {
      const { result } = renderHook(() => useDRState(), { wrapper })
      expect(result.current.selectedDR).toBeNull()
    })

    // Edge: selectedDR is derived from items.find(dr => dr.id === selectedDRId)

    it('selectedDR is the PendingDR matching selectedDRId when found in items', async () => {
      mockUsePendingDRs.mockReturnValue({ ...DEFAULT_DR_STATE, count: 1, items: [PENDING_DR] })

      const { result } = renderHook(() => useDRState(), { wrapper })

      await act(async () => {
        result.current.setSelectedDRId('dr-abc-123')
      })

      expect(result.current.selectedDR).toEqual(PENDING_DR)
    })

    it('selectedDR is null when selectedDRId does not match any item in items', async () => {
      mockUsePendingDRs.mockReturnValue({ ...DEFAULT_DR_STATE, count: 1, items: [PENDING_DR] })

      const { result } = renderHook(() => useDRState(), { wrapper })

      await act(async () => {
        result.current.setSelectedDRId('dr-no-match')
      })

      expect(result.current.selectedDR).toBeNull()
    })

    // Boundary: count and items flow from usePendingDRs()

    it('count and items flow through from usePendingDRs()', () => {
      mockUsePendingDRs.mockReturnValue({
        ...DEFAULT_DR_STATE,
        count: 3,
        items: [PENDING_DR, PENDING_DR, PENDING_DR],
      })

      const { result } = renderHook(() => useDRState(), { wrapper })

      expect(result.current.count).toBe(3)
      expect(result.current.items).toHaveLength(3)
    })

    // Error path: error from usePendingDRs flows through as Error|null

    it('error from usePendingDRs flows through as an Error instance', () => {
      const err = new Error('polling failed')
      mockUsePendingDRs.mockReturnValue({ ...DEFAULT_DR_STATE, error: err })

      const { result } = renderHook(() => useDRState(), { wrapper })

      expect(result.current.error).toBe(err)
      expect(result.current.error instanceof Error).toBe(true)
    })
  })

  // ─── AC-6: lastDecisionsMtime cross-domain effect ─────────────────────────

  describe('AC-6: lastDecisionsMtime cross-domain effect', () => {
    // Happy path: non-null change → refetchPendingDRs called

    it('triggers refetchPendingDRs when lastDecisionsMtime changes from null to non-null', async () => {
      mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE, lastDecisionsMtime: null })

      const { rerender } = renderHook(() => useBoardState(), { wrapper })

      expect(mockRefetchPendingDRs).not.toHaveBeenCalled()

      // Simulate an SSE event that sets lastDecisionsMtime to a non-null value
      mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE, lastDecisionsMtime: 12345 })

      await act(async () => {
        rerender()
      })

      expect(mockRefetchPendingDRs).toHaveBeenCalledTimes(1)
    })

    // Edge: initial mount with null → no refetch

    it('does NOT trigger refetchPendingDRs on initial mount when lastDecisionsMtime is null', () => {
      mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE, lastDecisionsMtime: null })

      renderHook(() => useBoardState(), { wrapper })

      expect(mockRefetchPendingDRs).not.toHaveBeenCalled()
    })

    // Boundary: subsequent non-null changes each trigger refetch

    it('triggers refetchPendingDRs again on each subsequent lastDecisionsMtime change', async () => {
      mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE, lastDecisionsMtime: null })

      const { rerender } = renderHook(() => useBoardState(), { wrapper })

      // First SSE event
      mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE, lastDecisionsMtime: 11111 })
      await act(async () => {
        rerender()
      })
      expect(mockRefetchPendingDRs).toHaveBeenCalledTimes(1)

      // Second SSE event
      mockUseBoard.mockReturnValue({ ...DEFAULT_BOARD_STATE, lastDecisionsMtime: 22222 })
      await act(async () => {
        rerender()
      })
      expect(mockRefetchPendingDRs).toHaveBeenCalledTimes(2)
    })
  })

  // ─── AC-7: useConnectionHealth not re-exported ────────────────────────────
  // Regression guard: useConnectionHealth stays inside useBoard, never surfaces
  // as a top-level export of CockpitProvider.

  describe('AC-7: useConnectionHealth not re-exported from CockpitProvider', () => {
    it('CockpitProvider module does not export useConnectionHealth', async () => {
      const module = await import('../hooks/CockpitProvider')
      expect('useConnectionHealth' in module).toBe(false)
    })
  })

  // ─── AC-11: Consumer hooks throw outside CockpitProvider ──────────────────

  describe('AC-11: consumer hooks throw Error when called outside CockpitProvider', () => {
    let consoleErrorSpy: ReturnType<typeof vi.spyOn>

    beforeEach(() => {
      // Suppress React's error boundary logging for the expected throws
      consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    })

    afterEach(() => {
      consoleErrorSpy.mockRestore()
    })

    // Error path: no provider ancestor → throw

    it('useBoardState throws when rendered outside CockpitProvider', () => {
      expect(() => {
        renderHook(() => useBoardState())
      }).toThrow()
    })

    it('useTaskSelection throws when rendered outside CockpitProvider', () => {
      expect(() => {
        renderHook(() => useTaskSelection())
      }).toThrow()
    })

    it('useDRState throws when rendered outside CockpitProvider', () => {
      expect(() => {
        renderHook(() => useDRState())
      }).toThrow()
    })

    // Boundary: error message is descriptive, references CockpitProvider

    it('useBoardState error message references CockpitProvider', () => {
      let caught: unknown
      try {
        renderHook(() => useBoardState())
      } catch (err) {
        caught = err
      }
      expect(caught instanceof Error).toBe(true)
      expect((caught as Error).message).toMatch(/CockpitProvider/i)
    })
  })
})
