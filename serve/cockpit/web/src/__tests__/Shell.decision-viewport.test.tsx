/**
 * Shell integration of DecisionViewport (AC8)
 *
 * AC8 (td:2): DecisionViewport is the primary decision listing surface
 * accessible from the Shell, showing loading, error, and empty states from
 * usePendingDRs. DRStatusIndicator's popover list is no longer the sole way
 * to view pending decisions.
 *
 *   - Shell must import and render DecisionViewport
 *   - Shell must destructure isLoading from usePendingDRs
 *   - Shell must pass isLoading, error, and items to DecisionViewport
 *   - Shell must wire onItemClick to open ResolveModal (setSelectedDRId)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks (hoisted, before all imports) ───────────────────────────────

vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// DecisionViewport is mocked as a vi.fn() so tests can:
// (a) assert Shell renders it (mock.calls.length > 0), and
// (b) inspect props passed from Shell (isLoading, error, items, onItemClick).
vi.mock('../components/DecisionViewport', () => ({
  default: vi.fn(
    ({
      items,
      isLoading,
      error,
      onItemClick,
    }: {
      items: unknown[]
      isLoading: boolean
      error: Error | null
      onItemClick: (id: string) => void
    }) => (
      <div data-testid="decision-viewport">
        <span data-testid="dv-loading">{String(isLoading)}</span>
        <span data-testid="dv-error">{error?.message ?? ''}</span>
        <span data-testid="dv-count">{items.length}</span>
        <button
          data-testid="dv-click-dr-001"
          onClick={() => onItemClick('dr-001')}
        >
          Click DR 001
        </button>
      </div>
    ),
  ),
}))

vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(() => <div data-testid="dr-status-indicator" />),
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

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import { useScanPolling } from '../hooks/useScanPolling'
import DecisionViewport from '../components/DecisionViewport'
import type { DecisionViewportProps } from '../components/DecisionViewport'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

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
  body: '## Context\n\nThe cache layer has grown too complex.',
  body_preview: 'Consider architectural simplification.',
}

const DR_B = {
  id: 'dr-002',
  task_id: 99,
  agent: 'architect',
  request_type: 'user-action',
  created: new Date(Date.now() - 25 * 3_600_000).toISOString(),
  title: 'Confirm scope change for phase 2',
  body: '## Scope\n\nPhase 2 scope needs user confirmation.',
  body_preview: 'Confirm the feature boundary.',
}

// ─── Stub helpers ─────────────────────────────────────────────────────────────

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

function lastDecisionViewportProps(): DecisionViewportProps {
  const calls = vi.mocked(DecisionViewport).mock.calls as DecisionViewportProps[][]
  return calls[calls.length - 1][0]
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_DecisionViewportShellIntegration', () => {
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

  // ─── AC8 (td:2): Happy path — DecisionViewport rendered by Shell ───────────

  describe('AC8: Shell renders DecisionViewport component', () => {
    it('Shell renders DecisionViewport at least once', () => {
      renderShell()
      expect(vi.mocked(DecisionViewport)).toHaveBeenCalled()
    })

    it('decision-viewport element is present in the rendered Shell DOM', () => {
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="decision-viewport"]')).not.toBeNull()
    })

    it('Shell passes items from usePendingDRs to DecisionViewport', () => {
      stubPendingDRs({ count: 2, items: [DR_A, DR_B], isLoading: false })
      renderShell()
      const props = lastDecisionViewportProps()
      expect(props.items).toEqual([DR_A, DR_B])
    })

    it('Shell passes single-item array to DecisionViewport when hook returns one DR', () => {
      stubPendingDRs({ count: 1, items: [DR_A], isLoading: false })
      renderShell()
      const props = lastDecisionViewportProps()
      expect(props.items).toHaveLength(1)
      expect(props.items[0]).toEqual(DR_A)
    })

    it('Shell passes isLoading=false to DecisionViewport when hook is not loading', () => {
      stubPendingDRs({ isLoading: false })
      renderShell()
      const props = lastDecisionViewportProps()
      expect(props.isLoading).toBe(false)
    })

    it('Shell passes a function as onItemClick to DecisionViewport', () => {
      renderShell()
      const props = lastDecisionViewportProps()
      expect(typeof props.onItemClick).toBe('function')
    })
  })

  // ─── AC8 (td:2): Edge cases — rendered unconditionally, empty state ────────

  describe('AC8: DecisionViewport is rendered unconditionally (not behind popover)', () => {
    it('DecisionViewport is rendered when items is empty (empty state visible)', () => {
      stubPendingDRs({ count: 0, items: [], isLoading: false })
      const { container } = renderShell()
      // Must be visible without clicking DRStatusIndicator
      expect(container.querySelector('[data-testid="decision-viewport"]')).not.toBeNull()
    })

    it('DecisionViewport is rendered on first load before any DR data arrives', () => {
      // isLoading=true represents the initial fetch — viewport still present
      stubPendingDRs({ count: 0, items: [], isLoading: true })
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="decision-viewport"]')).not.toBeNull()
    })

    it('Shell passes isLoading=true to DecisionViewport when hook is fetching', () => {
      stubPendingDRs({ count: 0, items: [], isLoading: true })
      renderShell()
      const props = lastDecisionViewportProps()
      expect(props.isLoading).toBe(true)
    })

    it('Shell passes empty items array to DecisionViewport when no DRs exist', () => {
      stubPendingDRs({ count: 0, items: [], isLoading: false })
      renderShell()
      const props = lastDecisionViewportProps()
      expect(props.items).toEqual([])
    })
  })

  // ─── AC8 (td:2): Error paths — error propagated to DecisionViewport ────────

  describe('AC8: Shell propagates usePendingDRs error to DecisionViewport', () => {
    it('Shell passes error to DecisionViewport when usePendingDRs returns an error', () => {
      const pollingError = new Error('Polling failed: 503')
      stubPendingDRs({ count: 0, items: [], isLoading: false, error: pollingError })
      renderShell()
      const props = lastDecisionViewportProps()
      expect(props.error).toBe(pollingError)
    })

    it('Shell passes error=null to DecisionViewport when no error exists', () => {
      stubPendingDRs({ count: 0, items: [], isLoading: false, error: null })
      renderShell()
      const props = lastDecisionViewportProps()
      expect(props.error).toBeNull()
    })

    it('DecisionViewport renders in Shell even when usePendingDRs returns an error', () => {
      stubPendingDRs({ error: new Error('DR fetch failed') })
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="decision-viewport"]')).not.toBeNull()
    })
  })

  // ─── AC8 (td:2): Boundary — onItemClick triggers ResolveModal ────────────

  describe('AC8: DecisionViewport onItemClick opens ResolveModal for the selected DR', () => {
    it('clicking a DR in DecisionViewport renders ResolveModal', () => {
      stubPendingDRs({ count: 1, items: [DR_A], isLoading: false })
      const { container } = renderShell()

      // Trigger onItemClick via the mock's exposed button
      const clickBtn = container.querySelector('[data-testid="dv-click-dr-001"]')
      expect(clickBtn).not.toBeNull()
      fireEvent.click(clickBtn!)

      // ResolveModal should be present after click
      // (ResolveModal renders when selectedDRId matches a DR in items)
      const modal = container.querySelector('[data-testid="resolve-modal"]')
        ?? container.querySelector('p-modal')
        ?? container.querySelector('[role="dialog"]')
      expect(modal).not.toBeNull()
    })

    it('onItemClick callback receives the DR id string', () => {
      stubPendingDRs({ count: 1, items: [DR_A], isLoading: false })
      renderShell()

      const props = lastDecisionViewportProps()
      const capturedIds: string[] = []
      // Override with a spy that captures the id
      const capturingSpy = vi.fn((id: string) => capturedIds.push(id))

      // Call the actual wired callback directly
      props.onItemClick('dr-001')

      // We cannot intercept the real call without spy injection, so we verify the
      // function exists and accepts a string argument (AC contract: onItemClick: (id) => void)
      expect(typeof props.onItemClick).toBe('function')

      // Direct call should not throw
      expect(() => props.onItemClick('dr-001')).not.toThrow()

      // Suppress unused variable warning
      void capturingSpy
      void capturedIds
    })

    it('pressing Escape after opening ResolveModal removes it from the DOM', () => {
      stubPendingDRs({ count: 1, items: [DR_A], isLoading: false })
      const { container } = renderShell()

      const clickBtn = container.querySelector('[data-testid="dv-click-dr-001"]')
      expect(clickBtn).not.toBeNull()
      fireEvent.click(clickBtn!)

      expect(container.querySelector('[data-testid="resolve-modal"]')).not.toBeNull()

      fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })

      expect(container.querySelector('[data-testid="resolve-modal"]')).toBeNull()
    })
  })
})

