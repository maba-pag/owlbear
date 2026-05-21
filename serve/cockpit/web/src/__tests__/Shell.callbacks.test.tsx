/**
 * Expose maintenance cleanup through Cockpit
 *
 * Shell.tsx function-coverage uplift — exercises all 13 uncovered anonymous
 * functions identified via coverage-final.json:
 *
 *   anonymous_2  (line  42) – pendingDRItems.find() predicate
 *   anonymous_3  (line  54) – kanbanProps.onSelectTask
 *   anonymous_11 (line 110) – async task-fetch IIFE
 *   anonymous_12 (line 138) – task-fetch effect cleanup
 *   anonymous_13 (line 228) – DetailTab.onSelectTask
 *   anonymous_14 (line 239) – setSelectedTaskSubtab functional updater inside onSelectTask
 *   anonymous_15 (line 241) – DetailTab.onTaskCleared
 *   anonymous_16 (line 243) – inner path inside onTaskCleared
 *   anonymous_17 (line 250) – DetailTab.onTaskUpdated
 *   anonymous_19 (line 283) – ResolveModal.onClose
 *   anonymous_20 (line 284) – ResolveModal.onResolved
 *
 * All stubs capture their callback props into module-level variables so tests
 * can invoke the callbacks and verify the resulting Shell state changes.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, waitFor, fireEvent, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Hoisted mocks ─────────────────────────────────────────────────────────────
// All vi.mock() calls are hoisted before imports by Vitest. The module-level
// `let` bindings are captured by reference inside the factory closures.

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: vi.fn() }))

vi.mock('../api/errorMessage', () => ({
  getResponseErrorMessage: vi.fn().mockResolvedValue('Task fetch failed'),
}))

// ── KanbanBoard: capture onSelectTask ──────────────────────────────────────────
let capturedKanbanOnSelectTask: ((taskId: number) => void) | undefined

vi.mock('../KanbanBoard', () => ({
  default: vi.fn((props: { onSelectTask?: (taskId: number) => void }) => {
    capturedKanbanOnSelectTask = props.onSelectTask
    return null
  }),
}))

// ── DetailTab: capture all three callback props ────────────────────────────────
let capturedDetailOnSelectTask: ((taskId: number, subtab?: string | null) => void) | undefined
let capturedDetailOnTaskCleared: ((message?: string | null) => void) | undefined
let capturedDetailOnTaskUpdated: ((task: unknown) => void) | undefined

vi.mock('../components/DetailTab', () => ({
  default: vi.fn(
    (props: {
      onSelectTask?: (taskId: number, subtab?: string | null) => void
      onTaskCleared?: (msg?: string | null) => void
      onTaskUpdated?: (task: unknown) => void
    }) => {
      capturedDetailOnSelectTask = props.onSelectTask
      capturedDetailOnTaskCleared = props.onTaskCleared
      capturedDetailOnTaskUpdated = props.onTaskUpdated
      return null
    },
  ),
}))

// ── ResolveModal: capture onClose / onResolved; render sentinel ────────────────
let capturedResolveOnClose: (() => void) | undefined
let capturedResolveOnResolved: (() => void) | undefined

vi.mock('../components/ResolveModal', () => ({
  default: vi.fn((props: { onClose?: () => void; onResolved?: () => void }) => {
    capturedResolveOnClose = props.onClose
    capturedResolveOnResolved = props.onResolved
    return <div data-testid="resolve-modal-stub" />
  }),
}))

// ── DRStatusIndicator: capture onItemClick to drive selectedDRId changes ───────
let capturedDROnItemClick: ((id: string) => void) | undefined

vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn((props: { onItemClick?: (id: string) => void }) => {
    capturedDROnItemClick = props.onItemClick
    return null
  }),
}))

// ── Other components – passthrough stubs ──────────────────────────────────────
vi.mock('../components/HealthBadge', () => ({
  default: vi.fn(() => null),
}))
vi.mock('../components/DecisionViewport', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/CleanupPanel', () => ({ default: vi.fn(() => null) }))

// ─── Imports (after mocks) ─────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import { useScanPolling } from '../hooks/useScanPolling'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import type { Board } from '../hooks/useBoard'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD: Board = {
  statuses: [{ name: 'todo' }],
  priorities: ['needed'],
  valid_transitions: { todo: [] },
}

const DR_ITEM = { id: 'dr-1', title: 'DR 1', status: 'pending', created: '', body: '' }
type DrItem = typeof DR_ITEM

// ─── Helpers ──────────────────────────────────────────────────────────────────

function stubHooks({
  refetchTasks = vi.fn(),
  pendingDRItems = [] as DrItem[],
  lastDecisionsMtime = null as string | null,
  scanError = null as Error | null,
} = {}) {
  vi.mocked(useBoard).mockReturnValue({
    board: BOARD,
    tasks: [],
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks,
    lastDecisionsMtime,
  } as ReturnType<typeof useBoard>)

  vi.mocked(usePendingDRs).mockReturnValue({
    count: pendingDRItems.length,
    items: pendingDRItems,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)

  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: scanError,
    refetch: vi.fn(),
  } as ReturnType<typeof useScanPolling>)

  return { refetchTasks }
}

function renderShell() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={['/']}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ShellCallbacks', () => {
  beforeEach(() => {
    capturedKanbanOnSelectTask = undefined
    capturedDetailOnSelectTask = undefined
    capturedDetailOnTaskCleared = undefined
    capturedDetailOnTaskUpdated = undefined
    capturedResolveOnClose = undefined
    capturedResolveOnResolved = undefined
    capturedDROnItemClick = undefined
    vi.resetAllMocks()
    vi.unstubAllGlobals()
  })

  // ─── anonymous_2: pendingDRItems.find() predicate (line 42) ──────────────

  describe('pendingDRItems.find() predicate (anonymous_2, line 42)', () => {
    it('find predicate runs when pendingDRItems is non-empty; no modal when id does not match', () => {
      stubHooks({ pendingDRItems: [DR_ITEM] })
      const { container } = renderShell()
      // selectedDRId is null → find returns undefined → no modal
      expect(container.querySelector('[data-testid="resolve-modal-stub"]')).toBeNull()
    })

    it('find predicate returns match when selectedDRId equals DR id', () => {
      stubHooks({ pendingDRItems: [DR_ITEM] })
      const { container } = renderShell()
      act(() => { capturedDROnItemClick?.('dr-1') })
      // selectedDR is now DR_ITEM → ResolveModal renders
      expect(container.querySelector('[data-testid="resolve-modal-stub"]')).not.toBeNull()
    })
  })

  // ─── anonymous_3: kanbanProps.onSelectTask (line 54) ─────────────────────

  describe('kanbanProps.onSelectTask (anonymous_3, line 54)', () => {
    it('onSelectTask opens the task detail modal by setting selectedTaskId', () => {
      stubHooks()
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="task-detail-modal"]')).toBeNull()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      expect(container.querySelector('[data-testid="task-detail-modal"]')).not.toBeNull()
    })

    it('onSelectTask clears any prior detailValidationMessage', () => {
      stubHooks()
      const { container } = renderShell()
      // Produce a validation message first via onTaskCleared
      act(() => { capturedKanbanOnSelectTask?.(42) })
      act(() => { capturedDetailOnTaskCleared?.('Task was moved') })
      // Select a task → validation message clears
      act(() => { capturedKanbanOnSelectTask?.(42) })
      expect(container.querySelector('[data-testid="validation-message"]')).toBeNull()
    })
  })

  // ─── anonymous_11: async task-fetch IIFE (line 110) ──────────────────────
  // ─── anonymous_12: task-fetch cleanup (line 138) ─────────────────────────

  describe('task-fetch IIFE and cleanup (anonymous_11 line 110, anonymous_12 line 138)', () => {
    it('selecting a task calls fetch /api/tasks/{id} (covers IIFE entry)', async () => {
      stubHooks()
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, json: vi.fn().mockResolvedValue({ id: 42 }) }),
      )
      renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      await waitFor(() => {
        expect(vi.mocked(global.fetch)).toHaveBeenCalledWith(
          '/api/tasks/42',
          expect.objectContaining({ signal: expect.any(AbortSignal) }),
        )
      })
    })

    it('successful fetch keeps task detail modal open and removes loading state', async () => {
      stubHooks()
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
          ok: true,
          json: vi.fn().mockResolvedValue({
            id: 42,
            title: 'Task 42',
            status: 'todo',
            priority: 'needed',
            body: '',
            updated: '2026-01-01T00:00:00+00:00',
            created: '2026-01-01T00:00:00+00:00',
            tags: [],
            blocked: false,
            block_reason: null,
            claimed: false,
            claimed_at: null,
            dep_status: null,
            parent: null,
            depends_on: [],
          }),
        }),
      )
      const { container } = renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      // After successful fetch, selectedTask is set and the modal remains open.
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-detail-modal"]')).not.toBeNull()
        expect(container.querySelector('[data-testid="task-detail-loading"]')).toBeNull()
      })
    })

    it('non-ok fetch shows task-fetch-error element (covers !response.ok branch)', async () => {
      stubHooks()
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 404 }),
      )
      const { container } = renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-fetch-error"]')).not.toBeNull()
      })
    })

    it('fetch network error (non-AbortError) shows task-fetch-error (covers catch branch)', async () => {
      stubHooks()
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network failure')))
      const { container } = renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-fetch-error"]')).not.toBeNull()
      })
    })

    it('switching tasks starts a new fetch for the new task (covers cleanup function path)', async () => {
      stubHooks()
      const fetchedUrls: string[] = []
      vi.stubGlobal(
        'fetch',
        vi.fn((url: string) => {
          fetchedUrls.push(url)
          return Promise.resolve({ ok: true, json: vi.fn().mockResolvedValue({ id: 99 }) })
        }),
      )
      renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      // Switch to task 99 — cleanup for task 42 fires, new effect starts for task 99
      act(() => { capturedKanbanOnSelectTask?.(99) })
      await waitFor(() => {
        expect(fetchedUrls).toContain('/api/tasks/99')
      })
    })

    it('task-fetch-retry button increments nonce and retriggers fetch (covers retry onClick)', async () => {
      stubHooks()
      let callCount = 0
      vi.stubGlobal(
        'fetch',
        vi.fn(() => {
          callCount++
          return Promise.resolve({ ok: false, status: 500 })
        }),
      )
      const { container } = renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      await waitFor(() => {
        expect(container.querySelector('[data-testid="task-fetch-retry"]')).not.toBeNull()
      })
      fireEvent.click(container.querySelector('[data-testid="task-fetch-retry"]')!)
      await waitFor(() => {
        expect(callCount).toBeGreaterThan(1)
      })
    })
  })

  // ─── anonymous_13–17: DetailTab callback functions ───────────────────────

  describe('DetailTab callbacks (anonymous_13–17, lines 228–250)', () => {
    it('DetailTab.onSelectTask opens task detail modal for the new task (covers anonymous_13)', () => {
      stubHooks()
      const { container } = renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      act(() => { capturedDetailOnSelectTask?.(99, null) })
      expect(container.querySelector('[data-testid="task-detail-modal"]')).not.toBeNull()
    })

    it('DetailTab.onSelectTask with non-null subtab exercises state functional updater (covers anonymous_14)', () => {
      stubHooks()
      const { container } = renderShell()
      // Pass a real subtab so the (current) => subtab ?? current path executes
      act(() => { capturedKanbanOnSelectTask?.(42) })
      act(() => { capturedDetailOnSelectTask?.(77, 'activity') })
      expect(container.querySelector('[data-testid="task-detail-modal"]')).not.toBeNull()
    })

    it('DetailTab.onTaskCleared resets selectedTaskId and closes modal (covers anonymous_15)', () => {
      stubHooks()
      const { container } = renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      expect(container.querySelector('[data-testid="task-detail-modal"]')).not.toBeNull()
      act(() => { capturedDetailOnTaskCleared?.(null) })
      expect(container.querySelector('[data-testid="task-detail-modal"]')).toBeNull()
    })

    it('DetailTab.onTaskCleared with non-null message closes modal (covers anonymous_15 message path)', () => {
      stubHooks()
      const { container } = renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      act(() => { capturedDetailOnTaskCleared?.('Task archived successfully') })
      expect(container.querySelector('[data-testid="task-detail-modal"]')).toBeNull()
    })

    it('DetailTab.onTaskUpdated with changed title triggers refetchTasks (covers anonymous_17)', () => {
      const { refetchTasks } = stubHooks()
      renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      act(() => {
        capturedDetailOnTaskUpdated?.({
          id: 42,
          title: 'Updated Title',
          priority: 'needed',
          status: 'todo',
          blocked: false,
        })
      })
      // previousTask is null (initial state) → refetchTasks is always called
      expect(refetchTasks).toHaveBeenCalled()
    })

    it('DetailTab.onTaskUpdated with identical fields still calls refetchTasks when previousTask is null', () => {
      const { refetchTasks } = stubHooks()
      renderShell()
      act(() => { capturedKanbanOnSelectTask?.(42) })
      act(() => {
        capturedDetailOnTaskUpdated?.({
          id: 1,
          title: 'Same',
          priority: 'needed',
          status: 'todo',
          blocked: false,
        })
      })
      expect(refetchTasks).toHaveBeenCalled()
    })
  })

  // ─── anonymous_19/20: ResolveModal callbacks (lines 283–284) ─────────────

  describe('ResolveModal callbacks (anonymous_19 line 283, anonymous_20 line 284)', () => {
    it('ResolveModal.onClose clears selectedDRId and dismisses modal (covers anonymous_19)', () => {
      stubHooks({ pendingDRItems: [DR_ITEM] })
      const { container } = renderShell()
      act(() => { capturedDROnItemClick?.('dr-1') })
      expect(container.querySelector('[data-testid="resolve-modal-stub"]')).not.toBeNull()
      act(() => { capturedResolveOnClose?.() })
      expect(container.querySelector('[data-testid="resolve-modal-stub"]')).toBeNull()
    })

    it('ResolveModal.onResolved calls refetchTasks and dismisses modal (covers anonymous_20)', () => {
      const { refetchTasks } = stubHooks({ pendingDRItems: [DR_ITEM] })
      const { container } = renderShell()
      act(() => { capturedDROnItemClick?.('dr-1') })
      expect(container.querySelector('[data-testid="resolve-modal-stub"]')).not.toBeNull()
      act(() => { capturedResolveOnResolved?.() })
      expect(refetchTasks).toHaveBeenCalled()
      expect(container.querySelector('[data-testid="resolve-modal-stub"]')).toBeNull()
    })
  })
})
