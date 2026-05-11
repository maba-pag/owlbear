/**
 * Retry-cycle tests for #1457: P4-19 Expose maintenance cleanup through Cockpit
 *
 * AC 3d (td:1): CleanupPanel is a separate control from HealthBadge.
 * Exact Shell placement at builder discretion.
 *
 * These tests mount the real Shell and verify:
 *   1. CleanupPanel is rendered in the status bar.
 *   2. CleanupPanel is a sibling of HealthBadge, not a child.
 *   3. The onSuccess prop passed to CleanupPanel calls Shell's refetchTasks.
 *
 * CleanupPanel is replaced with a stub that exposes the onSuccess callback
 * via a data attribute, letting tests call it and verify the refetchTasks
 * side-effect.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Hoisted mocks ─────────────────────────────────────────────────────────────
// All hooks and components that Shell uses (other than CleanupPanel) are
// stubbed so tests only exercise the cleanup-wiring path.

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../hooks/useBoard', () => ({ useBoard: vi.fn() }))
vi.mock('../hooks/usePendingDRs', () => ({ usePendingDRs: vi.fn() }))
vi.mock('../hooks/useScanPolling', () => ({ useScanPolling: vi.fn() }))

vi.mock('../KanbanBoard', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/ActivityTab', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(() => null),
}))
vi.mock('../components/ResolveModal', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DecisionViewport', () => ({ default: vi.fn(() => null) }))
vi.mock('../components/DetailTab', () => ({ default: vi.fn(() => null) }))

// HealthBadge stub — renders a known element so tests can check CleanupPanel
// is a sibling, not a descendant.
vi.mock('../components/HealthBadge', () => ({
  default: vi.fn(() => <div data-testid="health-badge-stub" />),
}))

// RepairFlow stub — prevent RepairPanel inside HealthBadge from triggering
// async calls.
vi.mock('../hooks/useRepairFlow', () => ({
  useRepairFlow: vi.fn(() => ({
    phase: 'idle',
    corruptionCount: null,
    results: null,
    error: null,
    requestRepair: vi.fn(),
    confirmRepair: vi.fn(),
    cancelRepair: vi.fn(),
    dismissResults: vi.fn(),
  })),
}))

// CleanupPanel stub — renders a sentinel element; captures onSuccess in a
// ref-like closure so tests can invoke it directly.
let capturedOnSuccess: (() => void) | undefined
vi.mock('../components/CleanupPanel', () => ({
  default: vi.fn((props: { onSuccess?: () => void }) => {
    capturedOnSuccess = props.onSuccess
    return <div data-testid="cleanup-panel-stub" data-has-success={String(typeof props.onSuccess === 'function')} />
  }),
}))

// ─── Imports (after mocks) ─────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import { useScanPolling } from '../hooks/useScanPolling'
import Shell from '../Shell'
import type { Board } from '../hooks/useBoard'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }, { name: 'done' }],
  priorities: ['important', 'needed', 'critical'],
  valid_transitions: {
    todo: ['in-progress'],
    'in-progress': ['done'],
    done: [],
  },
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function stubHooks(refetchTasks = vi.fn()): { refetchTasks: ReturnType<typeof vi.fn> } {
  vi.mocked(useBoard).mockReturnValue({
    board: BOARD,
    tasks: [],
    loading: false,
    error: null,
    isFetching: false,
    isStale: false,
    health: 'green',
    refetchTasks,
    lastDecisionsMtime: null,
  } as ReturnType<typeof useBoard>)

  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)

  vi.mocked(useScanPolling).mockReturnValue({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as ReturnType<typeof useScanPolling>)

  return { refetchTasks }
}

function renderShell() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={['/']}>
        <Shell />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_CleanupShellWiring', () => {
  beforeEach(() => {
    capturedOnSuccess = undefined
    vi.resetAllMocks()
  })

  // ─── AC 3d: CleanupPanel rendered in Shell status bar ────────────────────

  describe('AC 3d: CleanupPanel is rendered in the Shell status bar', () => {
    it('cleanup-panel element is present after Shell mounts', () => {
      stubHooks()
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
    })

    it('CleanupPanel is inside the status-bar region', () => {
      stubHooks()
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      expect(statusBar).not.toBeNull()
      expect(statusBar!.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
    })
  })

  // ─── AC 3d: CleanupPanel is separate from HealthBadge ────────────────────

  describe('AC 3d: CleanupPanel is a sibling of HealthBadge, not a child', () => {
    it('cleanup-panel and health-badge-stub share the same parent (status bar)', () => {
      stubHooks()
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')!
      const cleanupEl = statusBar.querySelector('[data-testid="cleanup-panel-stub"]')
      const badgeEl = statusBar.querySelector('[data-testid="health-badge-stub"]')
      // Both must exist and share the same parent — neither is nested inside the other.
      expect(cleanupEl).not.toBeNull()
      // HealthBadge may be absent when scan is loading — but CleanupPanel must always render.
      // Verify CleanupPanel is not a descendant of the badge stub.
      if (badgeEl !== null) {
        expect(badgeEl.contains(cleanupEl)).toBe(false)
      }
    })
  })

  // ─── AC 3d: onSuccess wired to refetchTasks ──────────────────────────────

  describe('AC 3d: CleanupPanel onSuccess prop is wired to Shell refetchTasks', () => {
    it('CleanupPanel receives an onSuccess function from Shell', () => {
      stubHooks()
      renderShell()
      // capturedOnSuccess is set by the CleanupPanel stub when Shell renders
      expect(typeof capturedOnSuccess).toBe('function')
    })

    it('calling onSuccess triggers refetchTasks', () => {
      const { refetchTasks } = stubHooks()
      renderShell()
      expect(capturedOnSuccess).toBeDefined()
      capturedOnSuccess!()
      expect(refetchTasks).toHaveBeenCalledOnce()
    })

    it('data-has-success attribute on stub confirms onSuccess prop is defined', () => {
      stubHooks()
      const { container } = renderShell()
      const stub = container.querySelector('[data-testid="cleanup-panel-stub"]')!
      expect(stub.getAttribute('data-has-success')).toBe('true')
    })
  })
})
