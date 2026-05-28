/**
 * Test Cockpit frontend error-contract adoption
 *
 *
 * Backend emits two error shapes:
 *   - Domain errors (KanbanError subclasses): {code: string, message: string}
 *   - FastAPI HTTPException:                  {detail: string}
 *
 *   1. usePollingFetch throws status-only error — response body never read
 *   2. DetailTab.runMutation ignores response body for non-422/409/404 status codes
 *   3. ResolveModal hardcodes 'Failed to resolve decision request.' for all errors
 *   4. repairStorage throws status-only error — response body never read
 *   5. Shell task-fetch: setSelectedTask(null) on error → blank detail pane, no indicator
 *   6. Shell: usePendingDRs().error is not destructured → DR polling errors silently dropped
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, renderHook, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'

// ─── Module mocks (hoisted before all imports) ────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

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

// KanbanBoard mock: exposes a select-task-42 button so tests can trigger
// the Shell's task-fetch flow without rendering the real board.
vi.mock('../KanbanBoard', () => ({
  default: vi.fn(({ onSelectTask }: { onSelectTask?: (id: number) => void }) => (
    <div data-testid="kanban-board-mock">
      <button data-testid="select-task-42" onClick={() => onSelectTask?.(42)}>
        Select 42
      </button>
    </div>
  )),
}))

// ConfirmDialog: simplified to a single confirm button so move-backward tests
// can trigger handleConfirm() without rendering full PDS modal.
vi.mock('../components/ConfirmDialog', () => ({
  default: vi.fn(({ onConfirm }: { onConfirm: () => void }) => (
    <button data-testid="confirm-dialog-confirm" onClick={onConfirm}>
      Confirm
    </button>
  )),
}))

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import { usePollingFetch } from '../hooks/usePollingFetch'
import { repairStorage } from '../api/repair'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import DetailTab from '../components/DetailTab'
import type { Board } from '../hooks/useBoard'
import type { TaskDetail } from '../components/DetailTab'

// ─── Global PDS jsdom polyfill ────────────────────────────────────────────────
// attachInternals is required by PDS custom elements. Save/restore per test
// to prevent polyfill mutations from leaking across describe boundaries.

let _attachInternalsDescriptor: PropertyDescriptor | undefined

beforeEach(() => {
  _attachInternalsDescriptor = Object.getOwnPropertyDescriptor(
    HTMLElement.prototype,
    'attachInternals',
  )
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

afterEach(() => {
  if (_attachInternalsDescriptor !== undefined) {
    Object.defineProperty(
      HTMLElement.prototype,
      'attachInternals',
      _attachInternalsDescriptor,
    )
  } else {
    delete (HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals']
  }
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const BOARD: Board = {
  statuses: [
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'done' },
  ],
  priorities: ['important', 'needed', 'critical'],
  valid_transitions: {
    todo: ['in-progress'],
    'in-progress': ['done', 'todo'],
    done: [],
  },
}

const TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'in-progress',
  priority: 'important',
  body: '## Objectives\n\n- item one',
  updated: '2026-04-18T10:00:00+00:00',
  created: '2026-04-17T09:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
}



// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Returns a fetch stub that responds with the given status and JSON body. */
function makeJsonFetch(status: number, body: unknown) {
  return vi.fn(() =>
    Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    } as Response),
  )
}

/**
 * Selective fetch stub: matches exact URLs; all other URLs pend (abortable).
 * Used for Shell tests that need some URLs to respond and others to stay in-flight.
 */
function makeSelectiveFetch(overrides: Record<string, { status: number; body: unknown }>) {
  return vi.fn((url: string, init?: RequestInit) => {
    const override = overrides[url]
    if (override) {
      return Promise.resolve({
        ok: override.status >= 200 && override.status < 300,
        status: override.status,
        json: () => Promise.resolve(override.body),
      } as Response)
    }
    return new Promise<never>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () =>
        reject(new DOMException('Aborted', 'AbortError')),
      )
    })
  })
}

function stubShellHooks(overrides?: { drError?: Error }) {
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
    isLoading: false,
    error: overrides?.drError ?? null,
    refetch: vi.fn(),
  } as ReturnType<typeof usePendingDRs>)
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

function renderDetail(task: TaskDetail = TASK) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab
        task={task}
        board={BOARD}
        onTaskUpdated={vi.fn()}
        onTaskCleared={vi.fn()}
      />
    </PorscheDesignSystemProvider>,
  )
}

async function clickMoveTarget(container: HTMLElement, targetStatus: string): Promise<void> {
  const moveTrigger = container.querySelector('[data-testid="task-detail-move-menu-trigger"]') as HTMLElement | null
  expect(moveTrigger).not.toBeNull()
  fireEvent.click(moveTrigger!)
  await waitFor(
    () => expect(container.querySelector('[data-testid="task-detail-move-menu"]')).not.toBeNull(),
    { timeout: 500 },
  )
  const target = container.querySelector(
    `[data-testid="task-detail-move-target"][data-status="${targetStatus}"]`,
  ) as HTMLElement | null
  expect(target).not.toBeNull()
  fireEvent.click(target!)
}

// ─── AC1: Error envelope parsing — both shapes across all flows ───────────────
//
// td:2 → multiple tests per flow, covering both {code,message} and {detail} shapes.

describe('TestFromAC_ErrorEnvelopeParsing', () => {
  // ── usePollingFetch: reads response body on non-ok response ──────────────────

  describe('usePollingFetch error body extraction', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    // FAILS: current code throws Error('Polling request failed with status 500')
    // without reading response body. Error.message doesn't contain body text.
    it('{code,message} shape — onError receives error whose message includes body message field', async () => {
      const errorBody = { code: 'SCAN_FAILED', message: 'board scan failed: index corrupted' }
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: false,
            status: 500,
            json: () => Promise.resolve(errorBody),
          } as Response),
        ),
      )
      const onError = vi.fn()
      renderHook(() => usePollingFetch('/api/tasks/scan', { onError }))
      await act(async () => {})
      expect(onError).toHaveBeenCalled()
      const err: Error = onError.mock.calls[0][0]
      expect(err.message).toContain('board scan failed: index corrupted')
    })

    // FAILS: same root cause — status-only throw discards {detail} body.
    it('{detail} shape — onError receives error whose message includes body detail field', async () => {
      const errorBody = { detail: 'service temporarily unavailable' }
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: false,
            status: 503,
            json: () => Promise.resolve(errorBody),
          } as Response),
        ),
      )
      const onError = vi.fn()
      renderHook(() => usePollingFetch('/api/tasks/scan', { onError }))
      await act(async () => {})
      expect(onError).toHaveBeenCalled()
      const err: Error = onError.mock.calls[0][0]
      expect(err.message).toContain('service temporarily unavailable')
    })
  })

  // ── repairStorage: reads response body on non-ok response ────────────────────

  describe('repairStorage error body extraction', () => {
    // FAILS: current code throws Error('Repair request failed with status 500')
    // without reading body. Thrown message doesn't include the body message field.
    it('{code,message} shape — thrown error message includes body message field', async () => {
      const errorBody = { code: 'STORAGE_ERROR', message: 'repair failed: disk quota exceeded' }
      vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))
      const err = await repairStorage().catch((e: unknown) => e as Error)
      expect(err).toBeInstanceOf(Error)
      expect(err.message).toContain('repair failed: disk quota exceeded')
    })

    // FAILS: same root cause — status-only throw discards {detail} body.
    it('{detail} shape — thrown error message includes body detail field', async () => {
      const errorBody = { detail: 'quota limit reached for storage backend' }
      vi.stubGlobal('fetch', makeJsonFetch(422, errorBody))
      const err = await repairStorage().catch((e: unknown) => e as Error)
      expect(err).toBeInstanceOf(Error)
      expect(err.message).toContain('quota limit reached for storage backend')
    })
  })

  // ── DetailTab.runMutation: reads response body for all non-ok statuses ───────

  describe('DetailTab mutation error body extraction', () => {
    // FAILS: runMutation does nothing for non-422/409/404 statuses.
    // validationMessage stays null → data-testid="validation-message" never renders.
    it('save 500 with {code,message} — validation-message rendered with body message text', async () => {
      const errorBody = { code: 'INTERNAL_ERROR', message: 'engine lock expired during edit' }
      vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))
      const { container } = renderDetail()
      fireEvent.click(container.querySelector('[data-testid="save-button"]')!)
      await waitFor(
        () => {
          const msg = container.querySelector('[data-testid="validation-message"]')
          expect(msg).not.toBeNull()
          expect(msg!.textContent).toContain('engine lock expired during edit')
        },
        { timeout: 1000 },
      )
    })

    // FAILS: same root cause — non-422 statuses never set validationMessage.
    it('save 500 with {detail} — validation-message rendered with body detail text', async () => {
      const errorBody = { detail: 'unexpected server fault in task engine' }
      vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))
      const { container } = renderDetail()
      fireEvent.click(container.querySelector('[data-testid="save-button"]')!)
      await waitFor(
        () => {
          const msg = container.querySelector('[data-testid="validation-message"]')
          expect(msg).not.toBeNull()
          expect(msg!.textContent).toContain('unexpected server fault in task engine')
        },
        { timeout: 1000 },
      )
    })

    // FAILS: DetailTab reads data.detail for 422 responses. When the backend sends
    // {code,message} (domain error) with status 422, data.detail is undefined →
    // falls back to 'Validation failed' instead of showing the body message field.
    it('save 422 with {code,message} — validation-message shows body message (not fallback "Validation failed")', async () => {
      const errorBody = { code: 'VALIDATION_ERROR', message: 'priority field is required' }
      vi.stubGlobal('fetch', makeJsonFetch(422, errorBody))
      const { container } = renderDetail()
      fireEvent.click(container.querySelector('[data-testid="save-button"]')!)
      await waitFor(
        () => {
          const msg = container.querySelector('[data-testid="validation-message"]')
          expect(msg).not.toBeNull()
          expect(msg!.textContent).toContain('priority field is required')
        },
        { timeout: 1000 },
      )
    })
  })
})

// ─── AC2: Error rendering and retry/refetch paths across all flows ─────────────
//
// td:2 → error rendering AND retry path per flow.

describe('TestFromAC_ErrorRenderingAndRetry', () => {
  // ── Scan error: message rendered from body (not status-only text) ────────────

  // FAILS: scan-error text is 'Scan failed: Polling request failed with status 500'
  // because usePollingFetch doesn't read body → Shell renders status-only message.
  it('Shell scan error: scan-error text includes body message (not generic status text)', async () => {
    const errorBody = { code: 'SCAN_FAILED', message: 'health scan failed: disk read error' }
    stubShellHooks()
    vi.stubGlobal(
      'fetch',
      makeSelectiveFetch({
        '/api/tasks/scan': { status: 500, body: errorBody },
      }),
    )
    const { container } = renderShell()
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="scan-error"]')).not.toBeNull()
      },
      { timeout: 2000 },
    )
    const scanError = container.querySelector('[data-testid="scan-error"]')
    expect(scanError!.textContent).toContain('health scan failed: disk read error')
  })

  // ── Task-fetch: error indicator replaces blank detail pane ───────────────────

  // FAILS: Shell sets selectedTask=null on fetch error → DetailTab renders null
  // → blank pane. No data-testid="task-fetch-error" element is ever rendered.
  it('Shell task-fetch failure: error indicator appears in detail pane', async () => {
    stubShellHooks()
    vi.stubGlobal(
      'fetch',
      makeSelectiveFetch({
        '/api/tasks/42': { status: 500, body: { code: 'INTERNAL', message: 'task fetch failed' } },
      }),
    )
    const { container } = renderShell()
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="task-fetch-error"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
  })

  // ── Task-fetch: retry button visible after failure ───────────────────────────

  // FAILS: no retry button exists in the Shell task-fetch error path.
  it('Shell task-fetch failure: retry button is rendered after error', async () => {
    stubShellHooks()
    vi.stubGlobal(
      'fetch',
      makeSelectiveFetch({
        '/api/tasks/42': { status: 404, body: { code: 'NOT_FOUND', message: 'task deleted' } },
      }),
    )
    const { container } = renderShell()
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="task-fetch-retry"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
  })

  // ── Task-fetch: clicking retry issues a second /api/tasks/{id} fetch ──────────

  // Proves the retry handler (setTaskFetchNonce increment → useEffect re-run → new fetch).
  // Error indicator must remain visible after a failing retry (behavior intact).
  it('Shell task-fetch: clicking task-fetch-retry issues a second fetch and error indicator remains', async () => {
    stubShellHooks()
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url === '/api/tasks/42') {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: () => Promise.resolve({ code: 'INTERNAL', message: 'task fetch failed' }),
        } as Response)
      }
      return new Promise<never>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        )
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderShell()

    // Trigger initial task-fetch failure.
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="task-fetch-error"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
    const callsAfterFirstFetch = fetchMock.mock.calls.filter(([url]) => url === '/api/tasks/42').length
    expect(callsAfterFirstFetch).toBe(1)

    // Click retry — must trigger a second fetch to /api/tasks/42.
    fireEvent.click(container.querySelector('[data-testid="task-fetch-retry"]')!)
    await waitFor(
      () => {
        const calls = fetchMock.mock.calls.filter(([url]) => url === '/api/tasks/42')
        expect(calls.length).toBeGreaterThanOrEqual(2)
      },
      { timeout: 1000 },
    )

    // Error indicator stays visible — retry still fails, behavior intact.
    expect(container.querySelector('[data-testid="task-fetch-error"]')).not.toBeNull()
  })

  // ── DR polling: error is surfaced in Decisions route UI ───────────────────────

  it('Decisions route: DR polling error is surfaced in UI — not silently swallowed', async () => {
    const drError = new Error('DR polling failed: connection refused')
    stubShellHooks({ drError })
    vi.stubGlobal('fetch', makeSelectiveFetch({}))
    const { container } = renderShell('/decisions')
    await waitFor(() => {
      expect(container.querySelector('[role="alert"]')).not.toBeNull()
    })
    expect(container.querySelector('[role="alert"]')?.textContent)
      .toContain('DR polling failed: connection refused')
  })

  // ── DetailTab move-backward: error renders validation message ─────────────────

  // FAILS: handleConfirm calls runMutation('/api/tasks/{id}/move', ...).
  // runMutation for non-422/409/404 status does not set validationMessage.
  it('DetailTab move menu mutation 500: validation-message rendered with response text', async () => {
    const errorBody = { code: 'ENGINE_ERROR', message: 'move blocked: task locked by reviewer' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))
    const { container } = renderDetail()
    await clickMoveTarget(container, 'todo')
    await waitFor(
      () => {
        const msg = container.querySelector('[data-testid="validation-message"]')
        expect(msg).not.toBeNull()
        expect(msg!.textContent).toContain('move blocked: task locked by reviewer')
      },
      { timeout: 1000 },
    )
  })
})

// ─── AC3: No expected backend error becomes a silent no-op or false empty state ─
//
// td:2 → tests across multiple flows that currently silently drop errors.

describe('TestFromAC_NoSilentErrors', () => {
  // ── Shell task-fetch 404: error indicator not blank pane ──────────────────────

  // FAILS: on 404, Shell's async IIFE calls setSelectedTask(null) and returns.
  // DetailTab receives task=null and renders null → blank pane.
  // data-testid="task-fetch-error" never appears.
  it('Shell task-fetch 404: visible error indicator replaces blank detail pane', async () => {
    stubShellHooks()
    vi.stubGlobal(
      'fetch',
      makeSelectiveFetch({
        '/api/tasks/42': { status: 404, body: { code: 'NOT_FOUND', message: 'task 42 deleted' } },
      }),
    )
    const { container } = renderShell()
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="task-fetch-error"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
    // detail-placeholder is for null selectedTaskId only — should not appear when 42 is selected
    expect(container.querySelector('[data-testid="detail-placeholder"]')).toBeNull()
  })

  // ── Shell task-fetch network exception: error indicator not blank ─────────────

  // FAILS: Shell's catch block checks for AbortError; non-abort exceptions
  // also hit setSelectedTask(null) → blank pane.
  it('Shell task-fetch network exception: visible error indicator, not blank pane', async () => {
    stubShellHooks()
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === '/api/tasks/42') {
          return Promise.reject(new TypeError('Failed to fetch'))
        }
        return new Promise<never>(() => {}) // other URLs pend indefinitely
      }),
    )
    const { container } = renderShell()
    fireEvent.click(container.querySelector('[data-testid="select-task-42"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="task-fetch-error"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
  })

  // ── ResolveModal: error text is specific, not the hardcoded generic string ────

  // FAILS: handleSubmit always sets 'Failed to resolve decision request.' regardless
  // of response. error text IS the hardcoded string → toNot assertion fails.
  // ── DetailTab non-422 error: validationMessage rendered (error not swallowed) ─

  // FAILS: non-422/409/404 status codes leave validationMessage null in runMutation.
  // data-testid="validation-message" is never rendered → assertion fails.
  it('DetailTab non-422 server error: validation-message element rendered (error not swallowed)', async () => {
    const errorBody = { code: 'INTERNAL_ERROR', message: 'unexpected failure in engine' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))
    const { container } = renderDetail()
    fireEvent.click(container.querySelector('[data-testid="save-button"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="validation-message"]')).not.toBeNull()
      },
      { timeout: 1000 },
    )
  })
})

// ─── AC4: Coexistence with Shell_1372 + preserve health false-OK protection ────
//
// td:1 → single smoke test that combines the false-OK guard from #1373 with the
// new body-message extraction from #1375. Tests can run alongside Shell_1372.test.tsx
// without fixture interference (different describe scopes, no shared mutable state).

describe('TestFromAC_FalseOKCoexistence', () => {
  // Exercises the full fetch → usePollingFetch → useScanPolling → Shell chain.
  //
  // The false-OK protection (from #1373): scan-error IS rendered (not a green badge).
  //   → This assertion passes against current code (assuming #1373 is implemented).
  //
  // The body-message extraction (from #1375): scan-error TEXT includes the body message.
  //   → This assertion FAILS against current code (text is status-only).
  //
  it('Shell scan error: false-OK prevented AND scan-error text includes body message field', async () => {
    const errorBody = { code: 'SCAN_FAILED', message: 'board scan failed: task index corrupted' }
    stubShellHooks()
    vi.stubGlobal(
      'fetch',
      makeSelectiveFetch({
        '/api/tasks/scan': { status: 500, body: errorBody },
      }),
    )
    const { container } = renderShell()

    // False-OK protection: error indicator is visible, no green health badge.
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="scan-error"]')).not.toBeNull()
      },
      { timeout: 2000 },
    )
    expect(container.querySelector('[data-health="green"]')).toBeNull()

    // Body-message extraction: scan-error text includes message from response body.
    // FAILS: current text is 'Scan failed: Polling request failed with status 500'.
    const scanError = container.querySelector('[data-testid="scan-error"]')
    expect(scanError!.textContent).toContain('board scan failed: task index corrupted')
  })
})
