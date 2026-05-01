/**
 * RED phase tests for #1192: P3-04 Integrate DRStatusIndicator + usePendingDRs into Shell
 *
 * AC1 (td:1): DRStatusIndicator renders inside Shell status bar
 * AC2 (td:1): Shows count of pending DRs from usePendingDRs hook
 * AC6 (td:1): onItemClick callback wired in Shell (selectedDRId handoff for #1194)
 *
 * AC3/4/5/7/8 are td:0 — already tested in #1191 or are design constraints.
 * All tests are RED until builder wires Shell.tsx.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn(),
}))

vi.mock('../hooks/useScanPolling', () => ({
  useScanPolling: vi.fn(),
}))

vi.mock('../hooks/usePolling', () => ({
  usePolling: vi.fn(),
}))

// DRStatusIndicator is mocked as a vi.fn() with JSX so tests can:
// (a) assert DOM presence via data-testid, and
// (b) inspect props via .mock.calls.
vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(({ count }: { count: number; items: unknown[]; onItemClick: (id: string) => void }) => (
    <button data-testid="dr-indicator" data-count={count}>
      DR {count}
    </button>
  )),
}))

import { usePendingDRs } from '../hooks/usePendingDRs'
import type { UsePendingDRsResult } from '../hooks/usePendingDRs'
import { useScanPolling } from '../hooks/useScanPolling'
import { usePolling } from '../hooks/usePolling'
import DRStatusIndicator from '../components/DRStatusIndicator'
import type { DRStatusIndicatorProps } from '../components/DRStatusIndicator'
import Shell from '../Shell'

// ─── Stub helpers ─────────────────────────────────────────────────────────────

function stubPendingDRs(partial: Partial<UsePendingDRsResult> = {}): void {
  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    isLoading: false,
    error: null,
    ...partial,
  })
}

function stubPolling(): void {
  vi.mocked(usePolling).mockReturnValue({ health: 'green', skipNextPoll: vi.fn(), lastMtime: null })
}

function stubScan(): void {
  vi.mocked(useScanPolling).mockReturnValue({ items: [], isLoading: false, error: null, refetch: vi.fn() })
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderShell() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={['/']}>
        <Shell />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const DR_A = {
  id: 'dr-001',
  task_id: 42,
  agent: 'builder',
  request_type: 'scope-decision',
  created: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  title: 'Should we use approach A?',
  body_preview: 'Context: the builder encountered a fork in the road...',
}

const DR_B = {
  id: 'dr-002',
  task_id: 43,
  agent: 'researcher',
  request_type: 'user-action',
  created: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  title: 'Confirm scope change',
  body_preview: 'Researcher requests user confirmation of revised scope...',
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_DRStatusIndicatorShellIntegration', () => {
  beforeEach(() => {
    // Never-resolving fetch keeps KanbanBoard in loading state, avoids act() warnings.
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
    stubPolling()
    stubScan()
    stubPendingDRs()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ─── AC1: DRStatusIndicator rendered inside status-bar ────────────────────

  describe('AC1: DRStatusIndicator rendered inside [data-region="status-bar"]', () => {
    it('renders [data-testid="dr-indicator"] inside the status-bar region', () => {
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      expect(statusBar).not.toBeNull()
      expect(statusBar?.querySelector('[data-testid="dr-indicator"]')).not.toBeNull()
    })

    it('dr-indicator is a descendant of status-bar, not elsewhere in the shell', () => {
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      const outsideStatusBar = container.querySelector('.shell__workspace [data-testid="dr-indicator"]')
      expect(statusBar?.querySelector('[data-testid="dr-indicator"]')).not.toBeNull()
      expect(outsideStatusBar).toBeNull()
    })
  })

  // ─── AC2: Count of pending DRs passed from hook to indicator ──────────────

  describe('AC2: count of pending DRs comes from usePendingDRs hook', () => {
    it('Shell calls usePendingDRs()', () => {
      renderShell()
      expect(vi.mocked(usePendingDRs)).toHaveBeenCalled()
    })

    it('DRStatusIndicator receives count=1 when hook returns count=1', () => {
      stubPendingDRs({ count: 1, items: [DR_A] })
      renderShell()
      const calls = vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][]
      const lastProps = calls[calls.length - 1][0]
      expect(lastProps.count).toBe(1)
    })

    it('DRStatusIndicator receives count=2 when hook returns count=2', () => {
      stubPendingDRs({ count: 2, items: [DR_A, DR_B] })
      renderShell()
      const calls = vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][]
      const lastProps = calls[calls.length - 1][0]
      expect(lastProps.count).toBe(2)
    })

    it('DRStatusIndicator receives count=0 when no pending DRs', () => {
      stubPendingDRs({ count: 0, items: [] })
      renderShell()
      const calls = vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][]
      const lastProps = calls[calls.length - 1][0]
      expect(lastProps.count).toBe(0)
    })

    it('DRStatusIndicator receives items array from hook', () => {
      stubPendingDRs({ count: 1, items: [DR_A] })
      renderShell()
      const calls = vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][]
      const lastProps = calls[calls.length - 1][0]
      expect(lastProps.items).toEqual([DR_A])
    })
  })

  // ─── AC6: onItemClick wired — selectedDRId handoff for #1194 ──────────────

  describe('AC6: onItemClick callback wired from Shell to DRStatusIndicator', () => {
    it('Shell passes a function as onItemClick to DRStatusIndicator', () => {
      renderShell()
      const calls = vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][]
      const lastProps = calls[calls.length - 1][0]
      expect(typeof lastProps.onItemClick).toBe('function')
    })

    it('onItemClick does not throw when invoked with a DR id', () => {
      renderShell()
      const calls = vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][]
      const lastProps = calls[calls.length - 1][0]
      expect(() => lastProps.onItemClick('dr-001')).not.toThrow()
    })

    it('onItemClick reference is stable when DRStatusIndicator re-renders ' +
      'with changed count (React state setter proof)', () => {
      // React Compiler memoizes DRStatusIndicator when props are unchanged.
      // Changing count forces DRStatusIndicator to re-render with fresh props.
      // A real setSelectedDRId has guaranteed stable identity (React contract);
      // an inline no-op () => {} creates a new function object on every render.
      stubPendingDRs({ count: 1, items: [DR_A] })
      const { rerender } = renderShell()
      const firstOnItemClick = (vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][])[0][0].onItemClick

      stubPendingDRs({ count: 2, items: [DR_A, DR_B] })
      rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter initialEntries={['/']}>
            <Shell />
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )

      const calls = vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][]
      expect(calls.length).toBeGreaterThan(1)
      const secondOnItemClick = calls[calls.length - 1][0].onItemClick
      expect(secondOnItemClick).toBe(firstOnItemClick)
    })

    it('onItemClick reference is stable when count decreases to zero — covers dormant state (setter identity)', () => {
      // Start with 2 DRs, rerender with 0 (dormant state).
      // A real setSelectedDRId is stable; an inline no-op () => {} is a new reference each render.
      stubPendingDRs({ count: 2, items: [DR_A, DR_B] })
      const { rerender } = renderShell()
      const firstOnItemClick = (vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][])[0][0].onItemClick

      stubPendingDRs({ count: 0, items: [] })
      rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter initialEntries={['/']}>
            <Shell />
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )

      const calls = vi.mocked(DRStatusIndicator).mock.calls as DRStatusIndicatorProps[][]
      expect(calls.length).toBeGreaterThan(1)
      const secondOnItemClick = calls[calls.length - 1][0].onItemClick
      expect(secondOnItemClick).toBe(firstOnItemClick)
    })
  })
})
