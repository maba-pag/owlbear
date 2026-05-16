/**
 * Test Cockpit health false-OK prevention
 *
 * Exercises the full fetch→render chain at Shell integration level:
 *   window.fetch → usePollingFetch → useScanPolling → Shell → HealthBadge
 *
 * window.fetch is mocked at the network boundary — useScanPolling and
 * usePollingFetch are NOT mocked so the error propagation path is proven.
 *
 * Error envelope fixture: {"code": "...", "message": "..."} with non-2xx status
 * matches the backend error envelope shape from #1371.
 *
 *   Shell.tsx L22 omits `error` from useScanPolling destructure, so a failed
 *   scan silently produces items=[] → isLoading=false → HealthBadge renders
 *   data-health="green" — a false-OK. No error state is rendered.
 *
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks (hoisted, before all imports) ───────────────────────────────
// Mocking unrelated hooks/components to isolate the scan→render chain.
// useScanPolling, usePollingFetch, and HealthBadge are NOT mocked.

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('../hooks/useBoard', () => ({
  useBoard: vi.fn(),
}))

vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn(),
}))

vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(() => null),
}))

vi.mock('../components/ActivityTab', () => ({
  default: vi.fn(() => <div data-testid="activity-tab-stub" />),
}))

vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => <div data-testid="kanban-board-stub" />),
}))

// Prevent RepairPanel from initiating repair fetch calls if popover opens.
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

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
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

/** Backend error envelope shape from #1371 — non-2xx HTTP with this JSON body. */
const SCAN_ERROR_ENVELOPE = {
  code: 'SCAN_FAILED',
  message: 'Board scan encountered an error and could not complete.',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

type ScanFetchResponse = { ok: boolean; status: number; body: unknown }

/**
 * Stub window.fetch so that /api/tasks/scan returns the given response.
 * All other URLs pend until aborted, preventing act() warnings from
 * unrelated hooks.
 */
function makeScanFetch(response: ScanFetchResponse) {
  return vi.fn((url: string, init?: RequestInit) => {
    if (url === '/api/tasks/scan') {
      return Promise.resolve({
        ok: response.ok,
        status: response.status,
        json: () => Promise.resolve(response.body),
      } as Response)
    }
    return new Promise<never>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () =>
        reject(new DOMException('Aborted', 'AbortError')),
      )
    })
  })
}

function stubHooks(): void {
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

  vi.mocked(usePendingDRs).mockReturnValue({
    count: 0,
    items: [],
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)
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

/**
 * Wait until the scan has settled (any post-scan indicator appears in status bar).
 * In pre-fix code: HealthBadge renders (even falsely green).
 * In post-fix code: scan-error element renders, or HealthBadge renders correctly.
 * Returns the status bar element.
 */
async function waitForScanSettled(container: HTMLElement, timeout = 2000): Promise<void> {
  await waitFor(
    () => {
      const badge = container.querySelector('[data-testid="health-badge"]')
      const errorEl = container.querySelector('[data-testid="scan-error"]')
      expect(badge !== null || errorEl !== null).toBe(true)
    },
    { timeout },
  )
}

// ─── File-level shim: save/restore HTMLElement.prototype.attachInternals ──────
// Each describe's beforeEach mutates this prototype property. A top-level
// afterEach restores the descriptor after every test so mutations never leak
// across describe boundaries (reviewer gap #4).
let _attachInternalsDescriptor: PropertyDescriptor | undefined

beforeEach(() => {
  _attachInternalsDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'attachInternals')
})

afterEach(() => {
  if (_attachInternalsDescriptor !== undefined) {
    Object.defineProperty(HTMLElement.prototype, 'attachInternals', _attachInternalsDescriptor)
  } else {
    // Property did not exist in jsdom before mutation — delete it.
    delete (HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals']
  }
})

// ─── AC1: All four scan states covered ────────────────────────────────────────

describe('TestFromAC_ScanHealthStates', () => {
  beforeEach(() => {
    ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(
      () => ({
        setFormValue: vi.fn(),
        setValidity: vi.fn(),
        checkValidity: vi.fn(() => true),
        reportValidity: vi.fn(() => true),
      }),
    )
    stubHooks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC1 error: scan failed → error state must appear (not a green health badge).
  // FAILS against current code: Shell ignores useScanPolling error, so
  // HealthBadge renders with items=[] → data-health="green". No scan-error shown.
  it('error: scan-error indicator is present in status bar after failed scan fetch', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="scan-error"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
  })

  // AC1 loading: while fetch is in-flight, neither HealthBadge nor scan-error
  // should be shown (hasLoadedScan=false; scanError=null).
  it('loading: health-badge and scan-error are absent while scan fetch is in flight', async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url === '/api/tasks/scan') {
        // Never resolves — keeps scan in isLoading=true state.
        return new Promise<Response>(() => {})
      }
      return new Promise<never>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderShell()
    // Wait until the scan fetch has been initiated (proving we're in loading state).
    await waitFor(
      () => {
        expect(fetchMock.mock.calls.some(([url]: [string]) => url === '/api/tasks/scan')).toBe(true)
      },
      { timeout: 1000 },
    )
    // While fetch is in-flight: hasLoadedScan=false → no HealthBadge, no scan-error.
    expect(container.querySelector('[data-testid="health-badge"]')).toBeNull()
    expect(container.querySelector('[data-testid="scan-error"]')).toBeNull()
  })

  // AC1 zero-issue success: HealthBadge renders green when scan returns empty array.
  it('happy: HealthBadge renders with data-health="green" when scan returns zero issues', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: true, status: 200, body: [] }))
    const { container } = renderShell()
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="health-badge"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
    expect(
      container.querySelector('[data-testid="health-badge"]')?.getAttribute('data-health'),
    ).toBe('green')
  })

  // AC1 non-empty success: HealthBadge renders red when scan returns issue items.
  it('happy: HealthBadge renders with data-health="red" when scan returns non-empty issues', async () => {
    const SCAN_ITEMS = [{ code: 'E001', detail: 'Issue found', file_path: '/path/to/file.md' }]
    vi.stubGlobal('fetch', makeScanFetch({ ok: true, status: 200, body: SCAN_ITEMS }))
    const { container } = renderShell()
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="health-badge"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
    expect(
      container.querySelector('[data-testid="health-badge"]')?.getAttribute('data-health'),
    ).toBe('red')
  })

})

// ─── AC2: Failed scan must never render as Health OK ─────────────────────────

describe('TestFromAC_ScanFalseOKPrevention', () => {
  beforeEach(() => {
    ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(
      () => ({
        setFormValue: vi.fn(),
        setValidity: vi.fn(),
        checkValidity: vi.fn(() => true),
        reportValidity: vi.fn(() => true),
      }),
    )
    stubHooks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC2: FAILS — current Shell renders data-health="green" after 500 error.
  it('error: no element has data-health="green" after a failed scan (500 + error envelope)', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitForScanSettled(container)
    // Current code: HealthBadge renders with items=[] → data-health="green" → assertion FAILS.
    expect(container.querySelectorAll('[data-health="green"]').length).toBe(0)
  })

  // AC2: FAILS — error state and empty-scan success state currently produce identical DOM.
  it('boundary: error state produces different status-bar DOM than a successful zero-issue scan', async () => {
    // Capture success state HTML.
    vi.stubGlobal('fetch', makeScanFetch({ ok: true, status: 200, body: [] }))
    const { container: successContainer, unmount: unmountSuccess } = renderShell()
    await waitFor(() => {
      expect(successContainer.querySelector('[data-testid="health-badge"]')).not.toBeNull()
    })
    const successHtml =
      successContainer.querySelector('[data-region="status-bar"]')?.innerHTML ?? ''
    unmountSuccess()
    vi.unstubAllGlobals()
    vi.clearAllMocks()
    stubHooks()
    ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(
      () => ({
        setFormValue: vi.fn(),
        setValidity: vi.fn(),
        checkValidity: vi.fn(() => true),
        reportValidity: vi.fn(() => true),
      }),
    )

    // Capture error state HTML.
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container: errorContainer } = renderShell()
    await waitForScanSettled(errorContainer)
    const errorHtml =
      errorContainer.querySelector('[data-region="status-bar"]')?.innerHTML ?? ''

    // Current code: both render HealthBadge with data-health="green" → identical → FAILS.
    expect(errorHtml).not.toBe(successHtml)
  })

  // AC2: FAILS — 404 response also produces a false-green state currently.
  it('error: no data-health="green" after a 404 scan response (not just 500)', async () => {
    vi.stubGlobal('fetch', makeScanFetch({
      ok: false,
      status: 404,
      body: { code: 'NOT_FOUND', message: 'Scan endpoint not found' },
    }))
    const { container } = renderShell()
    await waitForScanSettled(container)
    expect(container.querySelectorAll('[data-health="green"]').length).toBe(0)
  })

  // AC2 discriminating: after error, "Health OK" text (HealthBadge zero-issue label)
  // must be absent — the success copy cannot coexist with a scan-error state.
  it('error: "Health OK" button text is absent from status bar after a failed scan', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitForScanSettled(container)
    const statusBar = container.querySelector('[data-region="status-bar"]') as HTMLElement
    // HealthBadge with zero issues renders "Health OK" on its button.
    // After a scan error, HealthBadge must be suppressed entirely.
    expect(statusBar?.textContent ?? '').not.toContain('Health OK')
    expect(container.querySelector('[data-testid="scan-error"]')).not.toBeNull()
  })

  // AC2 gap (retry): "No issues" popover copy (HealthBadge.tsx:41) must also be
  // absent when scan fails — not just "Health OK". HealthBadge is suppressed
  // entirely on error, so neither copy can appear in the DOM.
  it('error: "No issues" popover text is absent from the DOM after a failed scan', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitForScanSettled(container)
    // HealthBadge emits "No issues" (HealthBadge.tsx:41) when items=[] and popover is open.
    // A failed scan must suppress HealthBadge entirely — "No issues" must not appear.
    expect(container.textContent ?? '').not.toContain('No issues')
    expect(container.querySelector('[data-testid="scan-error"]')).not.toBeNull()
  })
})

// ─── AC3: Actionable error text and retry mechanism must be accessible ────────

describe('TestFromAC_ScanErrorDisplay', () => {
  beforeEach(() => {
    ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(
      () => ({
        setFormValue: vi.fn(),
        setValidity: vi.fn(),
        checkValidity: vi.fn(() => true),
        reportValidity: vi.fn(() => true),
      }),
    )
    stubHooks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC3: FAILS — no error text is rendered anywhere after scan failure.
  it('error: status bar contains error-related text after a failed scan', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitFor(
      () => {
        const statusBar = container.querySelector('[data-region="status-bar"]') as HTMLElement
        const text = statusBar?.textContent?.toLowerCase() ?? ''
        const hasErrorText =
          text.includes('error') ||
          text.includes('failed') ||
          text.includes('unavailable') ||
          container.querySelector('[data-testid="scan-error"]') !== null
        expect(hasErrorText).toBe(true)
      },
      { timeout: 1000 },
    )
  })

  // AC3: FAILS — no retry mechanism is rendered after scan failure.
  it('error: a retry or refetch control is accessible in status bar after scan failure', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitFor(
      () => {
        const statusBar = container.querySelector('[data-region="status-bar"]') as HTMLElement
        const retryEl =
          statusBar?.querySelector('[data-testid="scan-retry"]') ??
          statusBar?.querySelector('[data-testid="health-error-retry"]') ??
          statusBar?.querySelector('button[aria-label*="retry" i]') ??
          statusBar?.querySelector('button[aria-label*="scan" i]')
        expect(retryEl).not.toBeNull()
      },
      { timeout: 1000 },
    )
  })

  // AC3: FAILS — the scan-error element does not exist at all.
  it('error: scan-error element is present and accessible after scan failure', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="scan-error"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
  })

  // AC3: FAILS — no scan-error element means no visible error for the user.
  it('edge: scan-error element is in the rendered DOM (not null) after network error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    )
    const { container } = renderShell()
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="scan-error"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
  })

  // AC3 specific message: usePollingFetch now surfaces parsed envelope body text.
  // Shell renders `Scan failed: {scanError.message}`.
  // The rendered text must contain the exact reason string, not just a generic keyword.
  it('error: status bar contains the exact HTTP failure reason after a 500 scan error', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="scan-error"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
    const statusBar = container.querySelector('[data-region="status-bar"]') as HTMLElement
    // usePollingFetch error message for non-2xx: parsed body message from envelope
    expect(statusBar?.textContent ?? '').toContain('Board scan encountered an error and could not complete.')
  })

  // AC3 specific network message: TypeError from fetch propagates as-is through
  // usePollingFetch.onError → useScanPolling.error → Shell renders the reason string.
  it('error: status bar contains the network failure reason after a fetch TypeError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    )
    const { container } = renderShell()
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="scan-error"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
    // Shell renders: "Scan failed: Failed to fetch"
    const statusBar = container.querySelector('[data-region="status-bar"]') as HTMLElement
    expect(statusBar?.textContent ?? '').toContain('Failed to fetch')
  })

  // AC3 gap (retry): clicking scan-retry control must invoke useScanPolling.refetch —
  // a new fetch call to /api/tasks/scan must be initiated after the button is activated.
  it('interaction: clicking scan-retry control triggers a new fetch call to /api/tasks/scan', async () => {
    const fetchMock = makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE })
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderShell()
    await waitFor(
      () => expect(container.querySelector('[data-testid="scan-retry"]')).not.toBeNull(),
      { timeout: 1000 },
    )
    const callsBefore = fetchMock.mock.calls.filter(
      ([url]: [string]) => url === '/api/tasks/scan',
    ).length
    fireEvent.click(container.querySelector('[data-testid="scan-retry"]')!)
    // After the click, useScanPolling.refetch must trigger a new /api/tasks/scan request.
    await waitFor(
      () => {
        const callsAfter = fetchMock.mock.calls.filter(
          ([url]: [string]) => url === '/api/tasks/scan',
        ).length
        expect(callsAfter).toBeGreaterThan(callsBefore)
      },
      { timeout: 1000 },
    )
  })
})

// ─── AC4: Full fetch→render chain exercised at window.fetch boundary ──────────

describe('TestFromAC_ScanFetchChain', () => {
  beforeEach(() => {
    ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(
      () => ({
        setFormValue: vi.fn(),
        setValidity: vi.fn(),
        checkValidity: vi.fn(() => true),
        reportValidity: vi.fn(() => true),
      }),
    )
    stubHooks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  // AC4: FAILS — error envelope does not trigger visible error state (Shell ignores error).
  it('chain: non-2xx + error envelope body triggers visible error propagation in Shell', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitFor(
      () => {
        // usePollingFetch throws → useScanPolling.onError sets error → Shell must propagate.
        // Builder must render an error indicator — currently absent.
        expect(container.querySelector('[data-testid="scan-error"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
  })

  // AC4: FAILS — network error (TypeError) currently produces false-OK green.
  it('chain: network failure (TypeError: Failed to fetch) does not produce data-health="green"', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))))
    const { container } = renderShell()
    await waitForScanSettled(container)
    expect(container.querySelectorAll('[data-health="green"]').length).toBe(0)
  })

  // AC4: FAILS — scan error does not propagate to visible state in status bar.
  it('chain: error from useScanPolling hook is surfaced in the status-bar region', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitFor(
      () => {
        const statusBar = container.querySelector('[data-region="status-bar"]')
        const hasErrorIndicator =
          statusBar?.querySelector('[data-testid="scan-error"]') !== null ||
          statusBar?.querySelector('[data-health="error"]') !== null
        expect(hasErrorIndicator).toBe(true)
      },
      { timeout: 1000 },
    )
  })
})

// ─── AC5: The proof fails against current code (td:1) ─────────────────────────

describe('TestFromAC_ScanCurrentCodeFails', () => {
  beforeEach(() => {
    ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(
      () => ({
        setFormValue: vi.fn(),
        setValidity: vi.fn(),
        checkValidity: vi.fn(() => true),
        reportValidity: vi.fn(() => true),
      }),
    )
    stubHooks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  /**
   * AC5 smoke — documents the exact false-OK bug in current Shell.
   *
   * Current code path on scan error:
   *   1. useScanPolling.onError: setItems([]), setError(err)
   *   2. Shell destructures only {items, isLoading, refetch} — `error` ignored
   *   3. normalizedItems = [] (no items)
   *   4. isLoading = false → hasLoadedScan = true → HealthBadge rendered
   *   5. HealthBadge(items=[]) → data-health="green" — FALSE OK
   *
   * FAILS now: data-health="green" IS present after error.
   * PASSES after #1373: error state rendered, no false-green.
   */
  it('smoke: a failed scan MUST NOT render data-health="green" — proves false-OK bug', async () => {
    vi.stubGlobal('fetch', makeScanFetch({ ok: false, status: 500, body: SCAN_ERROR_ENVELOPE }))
    const { container } = renderShell()
    await waitForScanSettled(container)
    // This assertion FAILS in current code because HealthBadge renders green after error.
    expect(container.querySelector('[data-health="green"]')).toBeNull()
  })
})
