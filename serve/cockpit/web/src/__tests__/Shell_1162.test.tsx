/**
 * Failing tests for #1162: HB-06 Integrate HealthBadge into Shell
 *
 * Shell.tsx must call useScanPolling(), filter items where any of
 * code/detail/file_path is null, pass normalised items to HealthBadge inside
 * the status-bar region, hide the badge while loading, and not override the
 * default 60 s poll interval.
 * All tests are RED (failing) until the builder wires Shell.tsx.
 *
 * Builder: move this file to serve/cockpit/web/src/__tests__/Shell_1162.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks ─────────────────────────────────────────────────────────────
// Both hooks are mocked so tests fully control Shell's inputs.
vi.mock('../hooks/useScanPolling', () => ({
  useScanPolling: vi.fn(),
}))

vi.mock('../hooks/usePolling', () => ({
  usePolling: vi.fn(),
}))

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

import { useScanPolling } from '../hooks/useScanPolling'
import type { ScanItem } from '../hooks/useScanPolling'
import { usePolling } from '../hooks/usePolling'
import type { HealthState } from '../hooks/usePolling'
import Shell from '../Shell'

// ─── Stub helpers ─────────────────────────────────────────────────────────────

function stubScan(items: ScanItem[], isLoading = false, error: Error | null = null) {
  vi.mocked(useScanPolling).mockReturnValue({ items, isLoading, error, refetch: vi.fn() })
}

function stubPolling(health: HealthState = 'green') {
  vi.mocked(usePolling).mockReturnValue({ health, skipNextPoll: vi.fn(), lastMtime: null })
}

// ─── Render helper ────────────────────────────────────────────────────────────

function renderShell(route = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <Shell />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const VALID_ITEM: ScanItem = { code: 'E001', detail: 'Missing field', file_path: '/a.py' }
const VALID_ITEM_2: ScanItem = { code: 'W042', detail: 'Unused import', file_path: '/b.py' }
const NULL_CODE: ScanItem = { code: null, detail: 'Missing field', file_path: '/a.py' }
const NULL_DETAIL: ScanItem = { code: 'E001', detail: null, file_path: '/a.py' }
const NULL_PATH: ScanItem = { code: 'E001', detail: 'Missing field', file_path: null }
const ALL_NULL: ScanItem = { code: null, detail: null, file_path: null }

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_HealthBadgeShellIntegration', () => {
  beforeEach(() => {
    // KanbanBoard fires fetch on mount; never-resolving keeps it in loading
    // state, preventing act() warnings from async state updates.
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
    stubScan([])
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // ─── AC1: HealthBadge rendered inside status-bar ───────────────────────────

  describe('AC1: health-badge rendered inside [data-region="status-bar"]', () => {
    it('renders data-testid="health-badge" inside status-bar when items is empty', () => {
      stubScan([])
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      expect(statusBar?.querySelector('[data-testid="health-badge"]')).not.toBeNull()
    })

    it('renders data-testid="health-badge" inside status-bar when items are present', () => {
      stubScan([VALID_ITEM])
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      expect(statusBar?.querySelector('[data-testid="health-badge"]')).not.toBeNull()
    })

    it('health-badge is a descendant of status-bar, not elsewhere in the shell', () => {
      stubScan([])
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      expect(statusBar).not.toBeNull()
      expect(statusBar?.querySelector('[data-testid="health-badge"]')).not.toBeNull()
    })
  })

  // ─── AC2: useScanPolling called; null-field items filtered ────────────────

  describe('AC2: useScanPolling called; items with any null field filtered out', () => {
    it('Shell calls useScanPolling()', () => {
      renderShell()
      expect(vi.mocked(useScanPolling)).toHaveBeenCalled()
    })

    it('valid item (all non-null fields) passes through — badge shows red', () => {
      stubScan([VALID_ITEM])
      const { container } = renderShell()
      const badge = container.querySelector('[data-testid="health-badge"]')
      expect(badge?.getAttribute('data-health')).toBe('red')
    })

    it('item with null code is filtered — badge shows green (0 issues)', () => {
      stubScan([NULL_CODE])
      const { container } = renderShell()
      const badge = container.querySelector('[data-testid="health-badge"]')
      expect(badge?.getAttribute('data-health')).toBe('green')
    })

    it('item with null detail is filtered — badge shows green (0 issues)', () => {
      stubScan([NULL_DETAIL])
      const { container } = renderShell()
      const badge = container.querySelector('[data-testid="health-badge"]')
      expect(badge?.getAttribute('data-health')).toBe('green')
    })

    it('item with null file_path is filtered — badge shows green (0 issues)', () => {
      stubScan([NULL_PATH])
      const { container } = renderShell()
      const badge = container.querySelector('[data-testid="health-badge"]')
      expect(badge?.getAttribute('data-health')).toBe('green')
    })

    it('item with all-null fields is filtered — badge shows green', () => {
      stubScan([ALL_NULL])
      const { container } = renderShell()
      const badge = container.querySelector('[data-testid="health-badge"]')
      expect(badge?.getAttribute('data-health')).toBe('green')
    })

    it('mixed items: only non-null item passes — badge shows red (1 issue)', () => {
      stubScan([VALID_ITEM, NULL_CODE, NULL_DETAIL])
      const { container } = renderShell()
      const badge = container.querySelector('[data-testid="health-badge"]')
      expect(badge?.getAttribute('data-health')).toBe('red')
      expect(badge?.getAttribute('aria-label')).toBe('Health: 1 issues')
    })

    it('all items have null fields — badge shows green (all filtered)', () => {
      stubScan([NULL_CODE, NULL_DETAIL, NULL_PATH])
      const { container } = renderShell()
      const badge = container.querySelector('[data-testid="health-badge"]')
      expect(badge?.getAttribute('data-health')).toBe('green')
    })
  })

  // ─── AC3: Badge reflects updated scan results ──────────────────────────────

  describe('AC3: badge reflects updated scan results from hook', () => {
    it('badge shows green when hook returns empty items', () => {
      stubScan([])
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="health-badge"]')?.getAttribute('data-health')).toBe('green')
    })

    it('badge shows red when hook returns one valid item', () => {
      stubScan([VALID_ITEM])
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="health-badge"]')?.getAttribute('data-health')).toBe('red')
    })

    it('badge reflects updated count on re-render with new items', () => {
      stubScan([VALID_ITEM])
      const { container, rerender } = renderShell()
      expect(
        container.querySelector('[data-testid="health-badge"]')?.getAttribute('data-health'),
      ).toBe('red')

      stubScan([VALID_ITEM, VALID_ITEM_2])
      rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter initialEntries={['/']}>
            <Shell />
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )
      expect(
        container.querySelector('[data-testid="health-badge"]')?.getAttribute('aria-label'),
      ).toBe('Health: 2 issues')
    })

    it('badge transitions from red to green when hook items become empty', () => {
      stubScan([VALID_ITEM])
      const { container, rerender } = renderShell()
      expect(
        container.querySelector('[data-testid="health-badge"]')?.getAttribute('data-health'),
      ).toBe('red')

      stubScan([])
      rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter initialEntries={['/']}>
            <Shell />
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )
      expect(
        container.querySelector('[data-testid="health-badge"]')?.getAttribute('data-health'),
      ).toBe('green')
    })
  })

  // ─── AC4: Not rendered while isLoading ────────────────────────────────────

  describe('AC4: HealthBadge absent while useScanPolling().isLoading is true', () => {
    it('health-badge is absent from DOM when isLoading=true', () => {
      stubScan([], true)
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="health-badge"]')).toBeNull()
    })

    it('health-badge is present when isLoading=false', () => {
      stubScan([], false)
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="health-badge"]')).not.toBeNull()
    })

    it('health-badge is absent even when items are present but isLoading=true', () => {
      stubScan([VALID_ITEM], true)
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="health-badge"]')).toBeNull()
    })

    it('health-badge appears after loading completes (re-render with isLoading=false)', () => {
      stubScan([], true)
      const { container, rerender } = renderShell()
      expect(container.querySelector('[data-testid="health-badge"]')).toBeNull()

      stubScan([], false)
      rerender(
        <PorscheDesignSystemProvider>
          <MemoryRouter initialEntries={['/']}>
            <Shell />
          </MemoryRouter>
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="health-badge"]')).not.toBeNull()
    })
  })

  // ─── AC5: Default 60 s poll interval (no intervalMs override) ─────────────

  describe('AC5: useScanPolling wired without custom intervalMs (uses default 60 s)', () => {
    it('useScanPolling is called without an intervalMs option', () => {
      renderShell()
      const calls = vi.mocked(useScanPolling).mock.calls
      expect(calls.length).toBeGreaterThan(0)
      // Shell must not override the default interval — first arg must be
      // undefined, absent, or an options object with no intervalMs.
      const firstArg = calls[0]?.[0]
      expect(firstArg?.intervalMs).toBeUndefined()
    })

    it('useScanPolling is not called with an explicit non-default intervalMs', () => {
      renderShell()
      const calls = vi.mocked(useScanPolling).mock.calls
      for (const [opts] of calls) {
        expect(opts?.intervalMs).not.toBeDefined()
      }
    })
  })
})
