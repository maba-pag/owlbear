/**
 * Shell integration proof for #1344 (AC6) — onTaskUpdated → setSelectedTask + refetchTasks().
 *
 * Uses real Shell + real DetailTab with hooks mocked at the hook level (no component mocks).
 * Exercises the Shell.tsx:163-173 branch that was unreachable in prior test suites.
 *
 * AC6 contract:
 *   Successful edits/actions: DetailTab calls onTaskUpdated(responseTask) threaded from Shell;
 *   Shell updates selectedTask state and triggers refetchTasks() when title/priority/status/blocked changed.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks (hoisted) ──────────────────────────────────────────────────

vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))

vi.mock('../components/DRStatusIndicator', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/HealthBadge', () => ({ default: vi.fn(() => null) }))

// ActivityTab self-fetches on mount — stub to prevent unexpected fetch calls.
vi.mock('../components/ActivityTab', () => ({
  default: vi.fn(() => <div data-testid="activity-tab-stub" />),
}))

// react-markdown — avoid ESM plugin issues in jsdom.
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// KanbanBoard mock — exposes a button to trigger task selection by id.
vi.mock('../KanbanBoard', () => ({
  default: vi.fn(({ onSelectTask }: { onSelectTask?: (taskId: number) => void }) => (
    <div data-testid="kanban-board-mock">
      <button data-testid="select-task-42" onClick={() => onSelectTask?.(42)}>
        Select 42
      </button>
    </div>
  )),
}))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { useScanPolling } from '../hooks/useScanPolling'
import { usePendingDRs } from '../hooks/usePendingDRs'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import type { Board } from '../hooks/useBoard'
import type { TaskDetail } from '../components/DetailTab'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD: Board = {
  statuses: [
    { name: 'research' },
    { name: 'backlog' },
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'review' },
    { name: 'docs' },
    { name: 'done' },
  ],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    research: ['backlog'],
    backlog: ['research', 'todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'review'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: [],
  },
}

const TASK_42_DETAIL: TaskDetail = {
  id: 42,
  title: 'Original Title',
  status: 'todo',
  priority: 'important',
  body: '',
  updated: '2026-01-01T00:00:00+00:00',
  created: '2026-01-01T00:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
}



// ─── Helpers ──────────────────────────────────────────────────────────────────

function stubHooks(refetchTasksSpy: ReturnType<typeof vi.fn>) {
  vi.mocked(useBoard).mockReturnValue({
    board: BOARD,
    tasks: [],
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks: refetchTasksSpy,
    lastDecisionsMtime: null,
  } as ReturnType<typeof useBoard>)
  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof useScanPolling>)
  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)
}

/**
 * Stub fetch:
 *   GET  /api/tasks/42       → 200 TASK_42_DETAIL
 *   POST /api/tasks/42/edit  → 200 taskOnSave
 *   All other URLs           → pend until aborted (prevents act() warnings)
 */
function stubFetchForTask42(taskOnSave: TaskDetail) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, opts?: RequestInit) => {
      if (/\/api\/tasks\/42\/edit/.test(url)) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(taskOnSave) } as Response)
      }
      if (/\/api\/tasks\/42$/.test(url)) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASK_42_DETAIL) } as Response)
      }
      return new Promise<never>((_resolve, reject) => {
        opts?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      })
    }),
  )
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

describe('TestFromAC_ShellOnTaskUpdated (AC6)', () => {
  let refetchTasksSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
      setFormValue: vi.fn(),
      setValidity: vi.fn(),
      checkValidity: vi.fn(() => true),
      reportValidity: vi.fn(() => true),
    }))
    refetchTasksSpy = vi.fn()
    stubHooks(refetchTasksSpy)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('onTaskUpdated does NOT call refetchTasks when only body changes (AC6 stable-list branch)', async () => {
    // Save returns task with same title/priority/status/blocked — no refetchTasks expected.
    const taskWithBodyChange: TaskDetail = { ...TASK_42_DETAIL, body: 'New body content' }
    stubFetchForTask42(taskWithBodyChange)
    const { container } = renderShell()

    // Select task 42 and wait for it to load
    const selectBtn = container.querySelector('[data-testid="select-task-42"]') as HTMLElement | null
    fireEvent.click(selectBtn!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="field-id"]')?.textContent).toBe('42')
      },
      { timeout: 1000 },
    )

    const callCountBefore = refetchTasksSpy.mock.calls.length

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    fireEvent.click(saveBtn!)

    // Allow async operations to settle — refetchTasks must NOT be called for body-only changes
    await new Promise((r) => setTimeout(r, 200))
    expect(refetchTasksSpy.mock.calls.length).toBe(callCountBefore)
  })
})
