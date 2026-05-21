/**
 * Test Cockpit operational sidecar UX and repair safeguards
 *
 * AC1: Session type nullability — null task_id / null agent must not render "null" text
 * AC2: Filter active state observable + session rows show human-readable durations
 * AC3: ActivityTab empty state and error state (no duplication of 1156/1278)
 * AC4: Session rows use semantic interactive roles (not bare div-with-onClick)
 * AC5: ActivityTab subtab hint ("history") forwarded to DetailTab via Shell
 * AC6: Repair confirmation shows file details, explicit irreversible consequences
 * AC7: Repair error phase has retry mechanism using error contract
 *
 *
 * Deduplication constraints observed:
 *   - ActivityTab_1156: filter buttons, data-state attrs, click-through → NOT duplicated
 *   - ActivityTab_1278: polling/SSE hooks → NOT duplicated
 *   - RepairPanel_1167: dialog flow, grouped results, error string display → NOT duplicated
 *   - Shell_1372: scan health/error chain → NOT duplicated
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { Session } from '../components/HistorySubtab'
import type { ActivityTabProps } from '../components/ActivityTab'
import type { UseRepairFlowResult } from '../hooks/useRepairFlow'

// ─── File-level mocks ─────────────────────────────────────────────────────────

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

vi.mock('../hooks/useRepairFlow', () => ({
  useRepairFlow: vi.fn(),
}))

vi.mock('../hooks/useBoard', () => ({
  useBoard: vi.fn(),
}))

vi.mock('../hooks/usePendingDRs', () => ({
  usePendingDRs: vi.fn(),
}))

vi.mock('../hooks/useScanPolling', () => ({
  useScanPolling: vi.fn(() => ({
    items: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}))

vi.mock('../components/DRStatusIndicator', () => ({
  default: vi.fn(() => null),
}))

vi.mock('../KanbanBoard', () => ({
  default: vi.fn(() => <div data-testid="kanban-stub" />),
}))

// ─── Imports after mocks ──────────────────────────────────────────────────────

import HistorySubtab from '../components/HistorySubtab'
import ActivityTab from '../components/ActivityTab'
import RepairPanel from '../components/RepairPanel'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'
import { MemoryRouter } from 'react-router'
import { useRepairFlow } from '../hooks/useRepairFlow'
import { useBoard } from '../hooks/useBoard'
import { usePendingDRs } from '../hooks/usePendingDRs'
import type { Board } from '../hooks/useBoard'
import { repairStorage } from '../api/repair'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const SESSION_RUNNING: Session = {
  task_id: 1,
  state: 'running',
  agent: 'builder',
  started_at: '2026-04-28T09:00:00+00:00',
  duration: null,
  outcome: null,
}

const SESSION_RELEASED: Session = {
  task_id: 5,
  state: 'released',
  agent: 'doc-writer',
  started_at: '2026-04-28T06:00:00+00:00',
  duration: 120,
  outcome: 'success',
}

const SESSION_WITH_DURATION: Session = {
  task_id: 10,
  state: 'released',
  agent: 'builder',
  started_at: '2026-04-28T08:00:00+00:00',
  duration: 120,
  outcome: 'success',
}

const BOARD: Board = {
  statuses: [{ name: 'todo' }, { name: 'in-progress' }, { name: 'done' }],
  priorities: ['important', 'needed', 'critical'],
  valid_transitions: { todo: ['in-progress'], 'in-progress': ['done'], done: [] },
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function stubRepairHook(overrides: Partial<UseRepairFlowResult> = {}): UseRepairFlowResult {
  const defaults: UseRepairFlowResult = {
    phase: 'idle',
    corruptionCount: null,
    results: null,
    error: null,
    requestRepair: vi.fn(),
    confirmRepair: vi.fn(),
    cancelRepair: vi.fn(),
    dismissResults: vi.fn(),
  }
  const merged = { ...defaults, ...overrides }
  vi.mocked(useRepairFlow).mockReturnValue(merged)
  return merged
}

function stubShellHooks(): void {
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
    error: null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof usePendingDRs>)
}

function renderHistorySubtab(
  sessions: unknown[],
  onSelectTask?: (taskId: number, subtab?: string) => void,
) {
  return render(
    <PorscheDesignSystemProvider>
      <HistorySubtab
        sessions={sessions as Session[]}
        onSelectTask={onSelectTask}
      />
    </PorscheDesignSystemProvider>,
  )
}

function renderActivity(props: ActivityTabProps = {}) {
  return render(
    <PorscheDesignSystemProvider>
      <ActivityTab {...props} />
    </PorscheDesignSystemProvider>,
  )
}

function renderRepairPanel(corruptionCount: number) {
  return render(
    <PorscheDesignSystemProvider>
      <RepairPanel corruptionCount={corruptionCount} />
    </PorscheDesignSystemProvider>,
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

// ─── AC1: Session type nullability ────────────────────────────────────────────

describe('TestFromAC_SessionNullability', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Backend SessionRecord: task_id: int | None, agent: str | None = None.
  // Frontend Session type: task_id: number, agent: string — nulls not allowed.
  // React renders null as empty string ''. The fix must show a fallback placeholder,
  // not leave fields empty, and must guard onSelectTask from being called with null.

  it('HistorySubtab shows non-empty fallback for agent span when agent is null', () => {
    const session = { ...SESSION_RUNNING, agent: null } as unknown as Session
    const { container } = renderHistorySubtab([session])
    const agentSpan = container.querySelector('[data-testid="session-agent"]')
    expect(agentSpan).not.toBeNull()
    // Currently: null renders as empty string '' — no fallback placeholder → FAILS
    expect(agentSpan!.textContent.trim()).not.toBe('')
  })

  it('HistorySubtab clicking row with null task_id does not invoke onSelectTask with null', () => {
    const onSelectTask = vi.fn()
    const session = { ...SESSION_RUNNING, task_id: null } as unknown as Session
    const { container } = renderHistorySubtab([session], onSelectTask)
    const row = container.querySelector('[data-testid="history-session-row"]')
    expect(row).not.toBeNull()
    fireEvent.click(row!)
    // Currently: calls onSelectTask(null, 'history') → FAILS
    expect(onSelectTask).not.toHaveBeenCalledWith(null, expect.any(String))
  })

  it('ActivityTab session-task span shows non-empty fallback when task_id is null', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({ sessions: [{ ...SESSION_RUNNING, task_id: null }] }),
        }),
      ),
    )
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
    const taskSpan = container.querySelector('[data-testid="session-task"]')
    expect(taskSpan).not.toBeNull()
    // Currently: null renders as empty string '' — no fallback placeholder → FAILS
    expect(taskSpan!.textContent.trim()).not.toBe('')
  })

  it('ActivityTab session-agent span shows non-empty fallback when agent is null', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({ sessions: [{ ...SESSION_RUNNING, agent: null }] }),
        }),
      ),
    )
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
    const agentSpan = container.querySelector('[data-testid="session-agent"]')
    expect(agentSpan).not.toBeNull()
    // Currently: null renders as empty string '' — no fallback placeholder → FAILS
    expect(agentSpan!.textContent.trim()).not.toBe('')
  })

  it('ActivityTab clicking row with null task_id does not invoke onSelectTask with null', async () => {
    const onSelectTask = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({ sessions: [{ ...SESSION_RUNNING, task_id: null }] }),
        }),
      ),
    )
    const { container } = renderActivity({ onSelectTask })
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
    fireEvent.click(container.querySelector('[data-testid="session-row"]')!)
    // Currently: onSelectTask(null, 'history') is called → FAILS
    expect(onSelectTask).not.toHaveBeenCalledWith(null, expect.any(String))
  })
})

// ─── AC2a: Filter active/inactive observable state ────────────────────────────

describe('TestFromAC_FilterActiveState', () => {
  // AC2: Filter buttons must show observable active/inactive state via aria attribute,
  // data attribute, or variant change. Currently all buttons have variant="secondary"
  // and no aria-pressed — no active state indicator exists.

  it('initially selected "active" filter button has aria-pressed="true"', () => {
    const { container } = renderActivity()
    const activeBtn = container.querySelector('[data-testid="filter-active"]') as HTMLElement | null
    expect(activeBtn).not.toBeNull()
    // Currently: no aria-pressed attribute → getAttribute returns null → FAILS
    expect(activeBtn!.getAttribute('aria-pressed')).toBe('true')
  })

  it('clicking "all" filter gives "all" button aria-pressed="true"', () => {
    const { container } = renderActivity()
    const allBtn = container.querySelector('[data-testid="filter-all"]')!
    fireEvent.click(allBtn)
    // Currently: no aria-pressed changes on click → FAILS
    expect((allBtn as HTMLElement).getAttribute('aria-pressed')).toBe('true')
  })

  it('clicking "all" filter sets "active" button aria-pressed="false"', () => {
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    const activeBtn = container.querySelector('[data-testid="filter-active"]')!
    // Currently: no aria-pressed attribute → FAILS (null ≠ 'false')
    expect((activeBtn as HTMLElement).getAttribute('aria-pressed')).toBe('false')
  })

  it('exactly one filter button has aria-pressed="true" after any filter click', () => {
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-blocked"]')!)
    const buttons = container.querySelectorAll('[data-testid^="filter-"]')
    const activePressedCount = Array.from(buttons).filter(
      (b) => (b as HTMLElement).getAttribute('aria-pressed') === 'true',
    ).length
    // Currently: 0 buttons have aria-pressed="true" → activePressedCount is 0 → FAILS
    expect(activePressedCount).toBe(1)
  })
})

// ─── AC2b: Human-readable duration display ────────────────────────────────────

describe('TestFromAC_HumanReadableDuration', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC2: Session rows must show human-readable durations, not raw numeric seconds.
  // HistorySubtab currently renders {s.duration ?? '—'} — outputs "120" for 120s.

  it('HistorySubtab duration 120 does not display raw number "120"', () => {
    const { container } = renderHistorySubtab([SESSION_WITH_DURATION])
    const durationSpan = container.querySelector('[data-testid="session-duration"]')
    expect(durationSpan).not.toBeNull()
    // Currently: textContent is "120" → FAILS
    expect(durationSpan!.textContent).not.toBe('120')
  })

  it('HistorySubtab duration 120 seconds displays in human-readable format', () => {
    const { container } = renderHistorySubtab([SESSION_WITH_DURATION])
    const durationSpan = container.querySelector('[data-testid="session-duration"]')
    const text = durationSpan!.textContent ?? ''
    // Currently: "120" — does not match any readable duration pattern → FAILS
    expect(text).toMatch(/\d+\s*m(in)?|\d+h|\d+:\d{2}/)
  })

  it('HistorySubtab duration 3661 does not display raw number "3661"', () => {
    const session = { ...SESSION_WITH_DURATION, duration: 3661 }
    const { container } = renderHistorySubtab([session])
    const durationSpan = container.querySelector('[data-testid="session-duration"]')
    const text = durationSpan!.textContent ?? ''
    // Currently: "3661" → FAILS
    expect(text).not.toBe('3661')
  })

  it('ActivityTab session row with duration 120 does not display raw "120"', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ sessions: [SESSION_RELEASED] }),
        }),
      ),
    )
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
    const durationSpan = container.querySelector('[data-testid="session-duration"]')
    // Currently: "120" → FAILS
    expect(durationSpan?.textContent).not.toBe('120')
  })
})

// ─── AC3: ActivityTab empty state and error state ─────────────────────────────

describe('TestFromAC_ActivityEmptyAndError', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC3: ActivityTab must show an empty state element when filter yields no results.
  // Currently: empty array map renders nothing — no empty state indicator.

  it('ActivityTab shows empty state element when active filter yields no matching sessions', async () => {
    // Only released sessions — won't match default "active" filter (running|stuck)
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ sessions: [SESSION_RELEASED] }),
        }),
      ),
    )
    const { container } = renderActivity()

    // Switch to 'all' filter to confirm sessions loaded, then back to 'active'
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
    fireEvent.click(container.querySelector('[data-testid="filter-active"]')!)

    // Default 'active' filter: released session excluded → 0 rows
    const rows = container.querySelectorAll('[data-testid="session-row"]')
    expect(rows.length).toBe(0)

    // Currently: no empty state element exists → FAILS
    const emptyEl =
      container.querySelector('[data-testid="activity-empty"]') ??
      container.querySelector('[data-testid="activity-no-results"]')
    expect(emptyEl).not.toBeNull()
  })

  // AC3: ActivityTab must show an error state element when fetch fails.
  // Currently: usePollingFetch has no onError handler in ActivityTab → error silently dropped.

  it('ActivityTab shows error state element when fetch returns a network error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Network error'))),
    )
    const { container } = renderActivity()
    await waitFor(
      () => {
        // Currently: no error state element → waitFor timeout → FAILS
        expect(container.querySelector('[data-testid="activity-error"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
  })

  it('ActivityTab shows error state element when fetch returns a 500 response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 500,
          json: () => Promise.resolve({ message: 'Internal server error' }),
        }),
      ),
    )
    const { container } = renderActivity()
    await waitFor(
      () => {
        // Currently: no error state element → FAILS
        expect(container.querySelector('[data-testid="activity-error"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
  })
})

// ─── AC4: Session rows — semantic interactive roles ───────────────────────────

describe('TestFromAC_SessionRowSemanticRoles', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC4: Session rows must use semantic interactive roles, not bare div-with-onClick.
  // Currently: <div onClick=...> with no role or tabIndex in both ActivityTab and HistorySubtab.

  it('ActivityTab session rows have role="button"', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ sessions: [SESSION_RUNNING] }),
        }),
      ),
    )
    const { container } = renderActivity()
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
    const row = container.querySelector('[data-testid="session-row"]')!
    // Currently: bare <div> — getAttribute('role') returns null → FAILS
    expect(row.getAttribute('role')).toBe('button')
  })

  it('ActivityTab session rows render as PButton hosts with an accessible label', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ sessions: [SESSION_RUNNING] }),
        }),
      ),
    )
    const { container } = renderActivity()
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
    const row = container.querySelector('[data-testid="session-row"]') as HTMLElement
    expect(row.tagName.toLowerCase()).toBe('p-button')
    expect(row.getAttribute('aria-label')).toContain('Session:')
  })

  it('HistorySubtab session rows have role="button"', () => {
    const { container } = renderHistorySubtab([SESSION_RUNNING])
    const row = container.querySelector('[data-testid="history-session-row"]')!
    // Currently: bare <div> — getAttribute('role') returns null → FAILS
    expect(row.getAttribute('role')).toBe('button')
  })

  it('HistorySubtab session rows are keyboard-focusable (tabIndex >= 0)', () => {
    const { container } = renderHistorySubtab([SESSION_RUNNING])
    const row = container.querySelector('[data-testid="history-session-row"]') as HTMLElement
    // Currently: no tabIndex set → tabIndex is -1 → FAILS
    expect(row.tabIndex).toBeGreaterThanOrEqual(0)
  })
})

// ─── AC5: Activity is retired from the shell sidecar ─────────────────────────

describe('TestFromAC_SubtabRoutingGap', () => {
  let _attachInternalsDescriptor: PropertyDescriptor | undefined

  beforeEach(() => {
    _attachInternalsDescriptor = Object.getOwnPropertyDescriptor(
      HTMLElement.prototype,
      'attachInternals',
    )
    ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(
      () => ({
        setFormValue: vi.fn(),
        setValidity: vi.fn(),
        checkValidity: vi.fn(() => true),
        reportValidity: vi.fn(() => true),
      }),
    )
    stubShellHooks()
    stubRepairHook()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
    if (_attachInternalsDescriptor !== undefined) {
      Object.defineProperty(
        HTMLElement.prototype,
        'attachInternals',
        _attachInternalsDescriptor,
      )
    } else {
      delete (HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals']
    }
  })

  it('Shell does not mount retired ActivityTab session rows by default', () => {
    const { container } = renderShell()

    expect(container.querySelector('[data-testid="session-row"]')).toBeNull()
    expect(container.querySelector('[data-testid="activity-tab-stub"]')).toBeNull()
  })
})

// ─── AC6: Repair confirmation dialog — file details and explicit consequences ─

describe('TestFromAC_RepairConfirmationDetails', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  // AC6: RepairPanel confirmation dialog must include affected file details (requires
  // a new prop), categorize outcomes, and state explicit irreversible/quarantine consequences.
  // Currently: only corruptionCount prop; no file list; no "irreversible"/"permanent" text.

  it('RepairPanel confirmation dialog explicitly states consequences are irreversible or permanent', () => {
    stubRepairHook({ phase: 'confirming', corruptionCount: 3 })
    const { container } = renderRepairPanel(3)
    const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
    expect(dialog).not.toBeNull()
    const text = dialog!.textContent ?? ''
    // Currently: "Fixed files are restored, unfixable files are quarantined." — no irreversible
    // language → FAILS
    expect(text).toMatch(/irreversible|permanent|cannot be undone|cannot undo/i)
  })

  it('RepairPanel confirmation dialog explicitly states quarantine destination path or directory', () => {
    stubRepairHook({ phase: 'confirming', corruptionCount: 2 })
    const { container } = renderRepairPanel(2)
    const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
    const text = dialog!.textContent ?? ''
    // Currently: "unfixable files are quarantined" — no path/directory mentioned → FAILS
    expect(text).toMatch(/quarantine\s*(directory|path|folder)|moved\s*to\s*quarantine/i)
  })

  it('RepairPanel confirmation dialog shows affected file path when files prop is provided', () => {
    stubRepairHook({ phase: 'confirming', corruptionCount: 1 })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const AnyRepairPanel = RepairPanel as React.ComponentType<any>
    const { container } = render(
      <PorscheDesignSystemProvider>
        <AnyRepairPanel
          corruptionCount={1}
          files={[{ file_path: '/tasks/TASK-001.md', code: 'CORRUPT_YAML' }]}
        />
      </PorscheDesignSystemProvider>,
    )
    const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
    expect(dialog).not.toBeNull()
    // Currently: files prop is unknown — file path not rendered in dialog → FAILS
    expect(dialog!.textContent).toContain('/tasks/TASK-001.md')
  })

  it('RepairPanel confirmation dialog lists all provided file paths when multiple files given', () => {
    stubRepairHook({ phase: 'confirming', corruptionCount: 2 })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const AnyRepairPanel = RepairPanel as React.ComponentType<any>
    const { container } = render(
      <PorscheDesignSystemProvider>
        <AnyRepairPanel
          corruptionCount={2}
          files={[
            { file_path: '/tasks/TASK-001.md', code: 'MISSING_STATUS' },
            { file_path: '/tasks/TASK-002.md', code: 'CORRUPT_YAML' },
          ]}
        />
      </PorscheDesignSystemProvider>,
    )
    const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
    const text = dialog?.textContent ?? ''
    // Currently: files prop unknown → neither path in dialog → FAILS
    expect(text).toContain('/tasks/TASK-001.md')
    expect(text).toContain('/tasks/TASK-002.md')
  })
})

// ─── AC7: Repair error contract — retry uses getResponseErrorMessage ──────────

describe('TestFromAC_RepairErrorContract', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC7: RepairPanel error phase must have a retry button (not just dismiss).
  // Currently: error phase renders only the dismiss button — no retry mechanism.

  it('RepairPanel shows a retry button in error phase', () => {
    stubRepairHook({ phase: 'error', error: 'Server error' })
    const { container } = renderRepairPanel(3)
    // Currently: no retry button in error phase → FAILS
    expect(container.querySelector('[data-testid="repair-retry-btn"]')).not.toBeNull()
  })

  it('clicking repair-retry-btn in error phase re-triggers confirmRepair via error contract', () => {
    const hook = stubRepairHook({ phase: 'error', error: 'Server error' })
    const { container } = renderRepairPanel(3)
    const retryBtn = container.querySelector('[data-testid="repair-retry-btn"]')
    // Currently: no retry button → querySelector returns null → FAILS
    expect(retryBtn).not.toBeNull()
    fireEvent.click(retryBtn!)
    // Retry must call confirmRepair (which uses getResponseErrorMessage via repairStorage)
    expect(hook.confirmRepair).toHaveBeenCalledOnce()
  })

})

// ─── AC1 (retry): Discriminating nullability — no literal "null" or "NaN" ─────

describe('TestFromAC_SessionNullabilityStrong', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Reviewer gap: existing tests only assert `not.toBe('')` — they pass if the component
  // renders the string literal "null" or "NaN". These tests pin the exact exclusion.

  it('HistorySubtab agent span does not render the string "null" when agent is null', () => {
    const session = { ...SESSION_RUNNING, agent: null } as unknown as Session
    const { container } = renderHistorySubtab([session])
    const agentSpan = container.querySelector('[data-testid="session-agent"]')
    expect(agentSpan).not.toBeNull()
    expect(agentSpan!.textContent).not.toBe('null')
    expect(agentSpan!.textContent).not.toContain('NaN')
  })

  it('ActivityTab task span does not render the string "null" when task_id is null', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({ sessions: [{ ...SESSION_RUNNING, task_id: null }] }),
        }),
      ),
    )
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
    const taskSpan = container.querySelector('[data-testid="session-task"]')
    expect(taskSpan).not.toBeNull()
    expect(taskSpan!.textContent).not.toBe('null')
    expect(taskSpan!.textContent).not.toContain('NaN')
  })

  it('ActivityTab agent span does not render the string "null" when agent is null', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({ sessions: [{ ...SESSION_RUNNING, agent: null }] }),
        }),
      ),
    )
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
    const agentSpan = container.querySelector('[data-testid="session-agent"]')
    expect(agentSpan).not.toBeNull()
    expect(agentSpan!.textContent).not.toBe('null')
    expect(agentSpan!.textContent).not.toContain('NaN')
  })
})

// ─── AC2 (retry): Discriminating ActivityTab duration — exact human-readable value ────

describe('TestFromAC_ActivityDurationFormat', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Reviewer gap: existing ActivityTab test only asserts `not.toBe('120')` which would accept
  // garbage like "1200" or "12 ". This test pins the exact human-readable format.

  it('ActivityTab session row with duration 120s renders exactly "2m", not a raw number', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ sessions: [SESSION_RELEASED] }),
        }),
      ),
    )
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
    const durationSpan = container.querySelector('[data-testid="session-duration"]')
    expect(durationSpan).not.toBeNull()
    // Exact assertion: 120s → "2m" per formatDuration in ActivityTab.tsx:14-29
    expect(durationSpan!.textContent).toBe('2m')
  })
})

// ─── AC7 (retry): Direct proof that repairStorage uses getResponseErrorMessage ───

describe('TestFromAC_RepairErrorContractProof', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Reviewer gap: existing tests mock useRepairFlow entirely — clicking retry only proves
  // the mock's confirmRepair was called, not that the real path uses getResponseErrorMessage.
  // These tests call repairStorage() directly with controlled fetch responses.

  it('repairStorage surfaces JSON body message via getResponseErrorMessage, not status fallback', async () => {
    // Server returns 422 with a specific JSON error body
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 422,
          json: () => Promise.resolve({ message: 'checksum-mismatch-probe' }),
        }),
      ),
    )
    // getResponseErrorMessage must extract the JSON body message, not produce the status fallback
    await expect(repairStorage()).rejects.toThrow('checksum-mismatch-probe')
  })

  it('repairStorage falls back to status message when JSON body has no message or detail field', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 503,
          json: () => Promise.resolve({ other: 'no-message-field' }),
        }),
      ),
    )
    // getResponseErrorMessage returns the fallback when body has neither message nor detail
    await expect(repairStorage()).rejects.toThrow('Repair request failed with status 503')
  })

  it('RepairPanel dismiss in done phase calls dismissResults without issuing a network request', () => {
    const hook = stubRepairHook({ phase: 'done', results: { fixed: [], quarantined: [], failed: [] } })
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    const { container } = renderRepairPanel(3)
    const dismissBtn = container.querySelector('[data-testid="repair-dismiss-btn"]')
    expect(dismissBtn).not.toBeNull()
    fireEvent.click(dismissBtn!)
    // Dismiss is local-state reset only — no network call
    expect(hook.dismissResults).toHaveBeenCalledOnce()
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
