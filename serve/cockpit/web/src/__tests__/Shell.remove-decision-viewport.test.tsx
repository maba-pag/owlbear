/**
 * Task #1648 — P2-04: Remove DecisionViewport from sidecar
 *
 * AC-1: DecisionViewport is no longer rendered inside the sidecar aside element
 *       — import removed from Shell.tsx, component no longer appears in sidecar DOM
 * AC-2: Decision state is route-owned: no global DRStatusIndicator renders, and
 *       the workspace nav badge carries pending-decision attention.
 * AC-3: No runtime errors or missing-import warnings after DecisionViewport removal
 *       from the sidecar
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks (hoisted, before all imports) ────────────────────────────

vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// DecisionViewport: spy so tests can assert Shell does (not) call it.
vi.mock('../components/DecisionViewport', () => ({
  default: vi.fn(() => <div data-testid="decision-viewport" />),
}))

// DRStatusIndicator: spy with per-item clickable buttons to trigger onItemClick.
vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(
    ({
      count,
      items,
      onItemClick,
    }: {
      count: number
      items: Array<{ id: string; title: string }>
      onItemClick: (id: string) => void
    }) => (
      <div data-testid="dr-status-indicator">
        <span data-testid="dr-spy-count">{count}</span>
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            data-testid={`dr-spy-item-${item.id}`}
            onClick={() => onItemClick(item.id)}
          >
            {item.title}
          </button>
        ))}
      </div>
    ),
  ),
}))

vi.mock('../components/ResolveModal', () => ({
  default: vi.fn(() => <div data-testid="resolve-modal-stub" />),
}))

vi.mock('../components/ActivityTab', () => ({
  default: vi.fn(() => <div data-testid="activity-tab-stub" />),
}))

vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => <div data-testid="kanban-board-stub" />),
}))

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Imports (after mocks) ─────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import { useScanPolling } from '../hooks/useScanPolling'
import DecisionViewport from '../components/DecisionViewport'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

// ─── Fixtures ──────────────────────────────────────────────────────────────

const BOARD = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }, { name: 'done' }],
  priorities: ['important', 'needed', 'critical'],
  valid_transitions: { todo: ['in-progress'], 'in-progress': ['done'], done: [] },
}

const DR_A = {
  id: 'dr-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 2 * 3_600_000).toISOString(),
  title: 'Should we refactor the cache layer?',
  body: '## Context\n\nCache is growing complex.',
  body_preview: 'Consider simplification.',
}

// ─── Stub helpers ──────────────────────────────────────────────────────────

function stubBoard(): void {
  vi.mocked(useBoard).mockReturnValue({
    board: BOARD,
    tasks: [],
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks: vi.fn(),
    lastDecisionsMtime: null,
  } as ReturnType<typeof useBoard>)
}

function stubPendingDRs(
  partial: Partial<ReturnType<typeof usePendingDRs>> = {},
): void {
  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...partial,
  } as ReturnType<typeof usePendingDRs>)
}

function stubScan(): void {
  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof useScanPolling>)
}

function renderShell(route = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ─────────────────────────────────────────────────────────────────

describe('DecisionViewportRemoval', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) =>
        new Promise<never>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () =>
            reject(new DOMException('Aborted', 'AbortError')),
          )
        }),
      ),
    )
    stubBoard()
    stubPendingDRs()
    stubScan()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ─── AC-1: DecisionViewport and retired sidecar are absent ─────────────

  describe('AC1: DecisionViewport is not rendered by Shell', () => {
    it('ac1 happy: Shell does not render sidecar or decision-viewport in desktop mode', () => {
      const { container } = renderShell('/')
      expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
      expect(container.querySelector('[data-testid="decision-viewport"]')).toBeNull()
    })

    it('ac1 happy: Shell does not call DecisionViewport component at all', () => {
      renderShell('/')
      expect(vi.mocked(DecisionViewport)).not.toHaveBeenCalled()
    })

    it('ac1 edge: Shell keeps decision-viewport absent even when pending DRs exist', () => {
      stubPendingDRs({ count: 1, items: [DR_A], isLoading: false })
      const { container } = renderShell('/')
      expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
      expect(container.querySelector('[data-testid="decision-viewport"]')).toBeNull()
    })

    it('ac1 edge: retired shell-sidecar-content is absent when DRs are loading', () => {
      stubPendingDRs({ count: 0, items: [], isLoading: true })
      const { container } = renderShell('/')
      expect(container.querySelector('#shell-sidecar-content')).toBeNull()
      expect(container.querySelector('[data-testid="decision-viewport"]')).toBeNull()
    })

    it('ac1 error: Shell keeps decision-viewport absent when DR fetch errors', () => {
      stubPendingDRs({
        count: 0,
        items: [],
        isLoading: false,
        error: new Error('Network error 503'),
      })
      const { container } = renderShell('/')
      expect(container.querySelector('[data-testid="decision-viewport"]')).toBeNull()
    })

    it('ac1 boundary: DecisionViewport call count is zero across full render', () => {
      stubPendingDRs({ count: 2, items: [DR_A], isLoading: false })
      renderShell('/')
      expect(vi.mocked(DecisionViewport).mock.calls).toHaveLength(0)
    })
  })

  // ─── AC-2: Decision state is route-owned ────────────────────────────────

  describe('AC2: decision state is carried by nav and route surfaces', () => {
    it('ac2 happy: global DRStatusIndicator is absent from the status bar', () => {
      stubPendingDRs({ count: 1, items: [DR_A], isLoading: false })
      const { container } = renderShell('/')
      expect(container.querySelector('[data-testid="dr-status-indicator"]')).toBeNull()
      expect(container.querySelector('[data-region="status-bar"] [data-testid="dr-status-indicator"]')).toBeNull()
    })

    it('ac2 happy: pending decisions render the decisions nav badge', () => {
      stubPendingDRs({ count: 1, items: [DR_A], isLoading: false })
      const { container } = renderShell('/')
      expect(container.querySelector('[data-surface="decisions"] [data-testid="nav-badge"]')?.textContent).toBe('1')
    })

    it('ac2 baseline: decisions nav badge is absent when there are no pending decisions', () => {
      stubPendingDRs({ count: 0, items: [], isLoading: false })
      const { container } = renderShell('/')
      expect(container.querySelector('[data-surface="decisions"] [data-testid="nav-badge"]')).toBeNull()
    })
  })

  // ─── AC-3: No runtime errors after DecisionViewport removal ───────────

  describe('AC3: Shell renders without missing-import or render errors', () => {
    it('ac3 smoke: Shell renders without throwing when DecisionViewport import is removed', () => {
      const { container } = renderShell('/')
      expect(container.firstChild).not.toBeNull()
    })

    it('ac3 smoke: Shell renders cleanly with pending DRs and no sidecar import errors', () => {
      stubPendingDRs({ count: 2, items: [DR_A], isLoading: false })
      const { container } = renderShell('/')
      expect(container.querySelector('[data-surface="decisions"] [data-testid="nav-badge"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="decision-viewport"]')).toBeNull()
    })
  })
})
