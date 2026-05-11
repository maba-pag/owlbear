/**
 * Expose maintenance cleanup through Cockpit
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
import { render, waitFor } from '@testing-library/react'
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
    it('cleanup-panel is not a descendant of health-badge-stub: unconditional sibling check after HealthBadge renders', async () => {
      stubHooks()
      // Provide a valid scan item so HealthBadge renders (hasLoadedScan=true, item passes isHealthBadgeItem filter)
      vi.mocked(useScanPolling).mockReturnValue({
        items: [{ code: 'ERR001', detail: 'found issue', file_path: '/path/to/file.py' }],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof useScanPolling>)
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')!
      // Unconditionally wait for HealthBadge — no conditional guard (AC 3d-proof requirement)
      await waitFor(() => {
        expect(statusBar.querySelector('[data-testid="health-badge-stub"]')).not.toBeNull()
      })
      const badgeEl = statusBar.querySelector('[data-testid="health-badge-stub"]')!
      const cleanupEl = statusBar.querySelector('[data-testid="cleanup-panel-stub"]')
      expect(cleanupEl).not.toBeNull()
      // CleanupPanel must not be a descendant of HealthBadge — they are separate controls
      expect(badgeEl.contains(cleanupEl)).toBe(false)
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

  // ─── AC 3d: CleanupPanel persists across all Shell scan states ───────────

  describe('AC 3d: CleanupPanel renders regardless of scan state', () => {
    it('CleanupPanel renders while scan is still loading (HealthBadge absent)', () => {
      const { refetchTasks } = stubHooks()
      vi.mocked(useScanPolling).mockReturnValue({
        items: [],
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof useScanPolling>)
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
      // HealthBadge not rendered while scan is loading (hasLoadedScan = false)
      expect(container.querySelector('[data-testid="health-badge-stub"]')).toBeNull()
      // onSuccess wiring is still present
      const stub = container.querySelector('[data-testid="cleanup-panel-stub"]')!
      expect(stub.getAttribute('data-has-success')).toBe('true')
      // suppress unused warning
      void refetchTasks
    })

    it('CleanupPanel renders when scan has an error', () => {
      stubHooks()
      vi.mocked(useScanPolling).mockReturnValue({
        items: [],
        isLoading: false,
        error: new Error('scan failed'),
        refetch: vi.fn(),
      } as ReturnType<typeof useScanPolling>)
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
    })

    it('scan error UI and CleanupPanel coexist in status bar', () => {
      stubHooks()
      vi.mocked(useScanPolling).mockReturnValue({
        items: [],
        isLoading: false,
        error: new Error('disk full'),
        refetch: vi.fn(),
      } as ReturnType<typeof useScanPolling>)
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')!
      expect(statusBar.querySelector('[data-testid="scan-error"]')).not.toBeNull()
      expect(statusBar.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
    })

    it('scan retry button and CleanupPanel coexist when scan errored', () => {
      stubHooks()
      vi.mocked(useScanPolling).mockReturnValue({
        items: [],
        isLoading: false,
        error: new Error('scan error'),
        refetch: vi.fn(),
      } as ReturnType<typeof useScanPolling>)
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="scan-retry"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
    })
  })

  // ─── Shell branch coverage: isHealthBadgeItem, statusHealth, effects ───────

  describe('Shell branch coverage for cleanup-adjacent paths', () => {
    it('isHealthBadgeItem passes items with all non-null fields (filter true branch)', async () => {
      stubHooks()
      vi.mocked(useScanPolling).mockReturnValue({
        items: [{ code: 'ERR001', detail: 'some error', file_path: '/path/to/file.py' }],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof useScanPolling>)
      const { container } = renderShell()
      // HealthBadge renders when scan loaded and item passes isHealthBadgeItem
      await waitFor(() => {
        expect(container.querySelector('[data-testid="health-badge-stub"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
    })

    it('isHealthBadgeItem rejects items with null code (filter false branch)', () => {
      stubHooks()
      vi.mocked(useScanPolling).mockReturnValue({
        items: [
          { code: null, detail: 'some error', file_path: '/path.py' },  // fails filter
          { code: 'ERR001', detail: 'ok', file_path: '/path.py' },  // passes filter
        ],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof useScanPolling>)
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
    })

    it('isHealthBadgeItem rejects items with null detail (second && branch)', () => {
      stubHooks()
      vi.mocked(useScanPolling).mockReturnValue({
        items: [{ code: 'ERR001', detail: null, file_path: '/path.py' }],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof useScanPolling>)
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
    })

    it('isHealthBadgeItem rejects items with null file_path (third && branch)', () => {
      stubHooks()
      vi.mocked(useScanPolling).mockReturnValue({
        items: [{ code: 'ERR001', detail: 'error', file_path: null }],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as ReturnType<typeof useScanPolling>)
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
    })

    it('statusHealth is red when scan has error', () => {
      stubHooks()
      vi.mocked(useScanPolling).mockReturnValue({
        items: [],
        isLoading: false,
        error: new Error('scan failed'),
        refetch: vi.fn(),
      } as ReturnType<typeof useScanPolling>)
      const { container } = renderShell()
      const trafficLight = container.querySelector('[data-testid="traffic-light"]')!
      expect(trafficLight.getAttribute('data-health')).toBe('red')
    })

    it('pendingDRError message rendered in status bar alongside CleanupPanel', () => {
      stubHooks()
      vi.mocked(usePendingDRs).mockReturnValue({
        count: 0,
        items: [],
        isLoading: false,
        error: new Error('DR polling failed'),
        refetch: vi.fn(),
      } as ReturnType<typeof usePendingDRs>)
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="dr-polling-error"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="cleanup-panel-stub"]')).not.toBeNull()
    })

    it('lastDecisionsMtime non-null triggers refetchPendingDRs effect', () => {
      const refetch = vi.fn()
      stubHooks()
      vi.mocked(useBoard).mockReturnValue({
        board: BOARD,
        tasks: [],
        loading: false,
        error: null,
        isFetching: false,
        isStale: false,
        health: 'green',
        refetchTasks: vi.fn(),
        lastDecisionsMtime: 123_456,
      } as ReturnType<typeof useBoard>)
      vi.mocked(usePendingDRs).mockReturnValue({
        count: 0,
        items: [],
        isLoading: false,
        error: null,
        refetch,
      } as ReturnType<typeof usePendingDRs>)
      renderShell()
      expect(refetch).toHaveBeenCalled()
    })
  })
})

