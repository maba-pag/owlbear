/**
 * Cockpit session history polish
 *
 * Covers: fetch uses filter=all, active-filter predicate fix (running not in-progress),
 * new blocked/stuck filter buttons, data-state visual indicators on ActivityTab rows
 * and HistorySubtab rows, HistorySubtab onSelectTask click-through, DetailTab prop
 * threading, FilterType union alignment, and applyFilter contract.
 *
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ActivityTab from '../components/ActivityTab'
import HistorySubtab from '../components/HistorySubtab'
import DetailTab, { type TaskDetail } from '../components/DetailTab'

// ─── Mocks ────────────────────────────────────────────────────────────────────

// ActivityTab now uses useSSEEvent; jsdom has no native EventSource so mock the
// provider hook. Returning status='closed' keeps paused:false → polling fires.
vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Session fixtures ─────────────────────────────────────────────────────────

const SESSION_RUNNING = {
  task_id: 1,
  state: 'running',
  agent: 'builder',
  started_at: '2026-04-28T09:00:00+00:00',
  duration: null,
  outcome: null,
}

const SESSION_STUCK = {
  task_id: 2,
  state: 'stuck',
  agent: 'reviewer',
  started_at: '2026-04-28T08:00:00+00:00',
  duration: null,
  outcome: null,
}

const SESSION_BLOCKED = {
  task_id: 3,
  state: 'blocked',
  agent: 'builder',
  started_at: '2026-04-28T07:00:00+00:00',
  duration: null,
  outcome: null,
}

const SESSION_REJECTED = {
  task_id: 4,
  state: 'rejected',
  agent: 'test-writer',
  started_at: '2026-04-28T06:30:00+00:00',
  duration: 30.0,
  outcome: 'rejected',
}

const SESSION_RELEASED = {
  task_id: 5,
  state: 'released',
  agent: 'doc-writer',
  started_at: '2026-04-28T06:00:00+00:00',
  duration: 45.0,
  outcome: 'success',
}

const SESSION_COMPLETED = {
  task_id: 6,
  state: 'completed',
  agent: 'builder',
  started_at: '2026-04-28T05:30:00+00:00',
  duration: 90.0,
  outcome: 'success',
}

const SESSION_EXPIRED = {
  task_id: 7,
  state: 'expired',
  agent: 'reviewer',
  started_at: '2026-04-28T05:00:00+00:00',
  duration: null,
  outcome: null,
}

// Session with old stale state name — must NOT match the fixed active predicate
const SESSION_IN_PROGRESS_STALE = {
  task_id: 8,
  state: 'in-progress',
  agent: 'auditor',
  started_at: '2026-04-28T04:00:00+00:00',
  duration: null,
  outcome: null,
}

const ALL_SESSIONS = {
  sessions: [
    SESSION_RUNNING,
    SESSION_STUCK,
    SESSION_BLOCKED,
    SESSION_REJECTED,
    SESSION_RELEASED,
    SESSION_COMPLETED,
    SESSION_EXPIRED,
  ],
}

// ─── Fetch stub helpers ────────────────────────────────────────────────────────

function stubFetchSessions(response: { sessions: object[] }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(response) })),
  )
}

// ─── Render helpers ────────────────────────────────────────────────────────────

function renderActivity(onSelectTask?: (taskId: number, subtab?: string) => void) {
  return render(
    <PorscheDesignSystemProvider>
      <ActivityTab onSelectTask={onSelectTask} />
    </PorscheDesignSystemProvider>,
  )
}

function renderHistorySubtab(
  sessions: object[],
  onSelectTask?: (taskId: number, subtab?: string) => void,
) {
  return render(
    <PorscheDesignSystemProvider>
      <HistorySubtab
        sessions={sessions as Parameters<typeof HistorySubtab>[0]['sessions']}
        onSelectTask={onSelectTask}
      />
    </PorscheDesignSystemProvider>,
  )
}

const BASE_TASK: TaskDetail = {
  id: 42,
  title: 'Test task',
  status: 'todo',
  priority: 'important',
  body: 'some body',
  updated: '2026-04-28T10:00:00+00:00',
  created: '2026-04-27T09:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
}

function renderDetailTab(onSelectTask?: (taskId: number, subtab?: string) => void) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={BASE_TASK} onSelectTask={onSelectTask} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_FetchStrategyFix', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC1: ActivityTab must fetch /api/sessions?filter=all

  it('ActivityTab fetches /api/sessions?filter=all on mount', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({ sessions: [] }) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderActivity()
    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringMatching(/\/api\/sessions\?filter=all/),
          expect.anything(),
        )
      },
      { timeout: 500 },
    )
  })

  it('ActivityTab does NOT fetch /api/sessions without filter param', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({ sessions: [] }) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderActivity()
    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalled()
      },
      { timeout: 500 },
    )
    const calls = fetchMock.mock.calls as [string, unknown][]
    const anyWithoutFilter = calls.some(([url]) => url === '/api/sessions')
    expect(anyWithoutFilter).toBe(false)
  })
})

describe('TestFromAC_ActiveFilterPredicate', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC1: Fix active predicate — state === 'running', not 'in-progress'

  it('active filter shows sessions with state=running', async () => {
    stubFetchSessions({ sessions: [SESSION_RUNNING, SESSION_RELEASED] })
    const { container } = renderActivity()
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        expect(rows.length).toBeGreaterThanOrEqual(1)
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        expect(states).toContain('running')
      },
      { timeout: 500 },
    )
  })

  it('active filter does NOT show sessions with state=in-progress (stale state name)', async () => {
    // Include SESSION_RUNNING so waitFor detects data-load via the fixed predicate.
    // Old code: active matches 'in-progress'||'stuck' — running not shown (waitFor never passes).
    // Fixed code: active matches 'running'||'stuck' — running shown; in-progress absent.
    stubFetchSessions({ sessions: [SESSION_RUNNING, SESSION_IN_PROGRESS_STALE] })
    const { container } = renderActivity()
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        expect(states).toContain('running')
      },
      { timeout: 500 },
    )
    const rows = container.querySelectorAll('[data-testid="session-row"]')
    const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
    expect(states).not.toContain('in-progress')
  })

  it('active filter includes state=stuck sessions', async () => {
    stubFetchSessions({ sessions: [SESSION_RUNNING, SESSION_STUCK, SESSION_RELEASED] })
    const { container } = renderActivity()
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        expect(states).toContain('stuck')
      },
      { timeout: 500 },
    )
  })

  it('active filter shows exactly running and stuck sessions (not released/blocked)', async () => {
    stubFetchSessions(ALL_SESSIONS)
    const { container } = renderActivity()
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        // Both must be present — empty array or missing either fails
        expect(states).toContain('running')
        expect(states).toContain('stuck')
        expect(states.every((s) => s === 'running' || s === 'stuck')).toBe(true)
      },
      { timeout: 500 },
    )
  })
})

describe('TestFromAC_NewFilterButtons', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC1: Replace "Failed" with "Blocked"; add "Stuck"

  it('filter-blocked button is present', () => {
    const { container } = renderActivity()
    expect(container.querySelector('[data-testid="filter-blocked"]')).not.toBeNull()
  })

  it('filter-failed button is NOT present (replaced by blocked)', () => {
    const { container } = renderActivity()
    expect(container.querySelector('[data-testid="filter-failed"]')).toBeNull()
  })

  it('filter-stuck button is present', () => {
    const { container } = renderActivity()
    expect(container.querySelector('[data-testid="filter-stuck"]')).not.toBeNull()
  })

  // Blocked filter: state === 'blocked' || state === 'rejected'

  it('clicking filter-blocked shows sessions with state=blocked', async () => {
    stubFetchSessions(ALL_SESSIONS)
    const { container } = renderActivity()
    await waitFor(() => expect(container.querySelector('[data-testid="filter-blocked"]')).not.toBeNull())
    fireEvent.click(container.querySelector('[data-testid="filter-blocked"]')!)
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        expect(states).toContain('blocked')
      },
      { timeout: 500 },
    )
  })

  it('clicking filter-blocked shows sessions with state=rejected', async () => {
    stubFetchSessions(ALL_SESSIONS)
    const { container } = renderActivity()
    await waitFor(() => expect(container.querySelector('[data-testid="filter-blocked"]')).not.toBeNull())
    fireEvent.click(container.querySelector('[data-testid="filter-blocked"]')!)
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        expect(states).toContain('rejected')
      },
      { timeout: 500 },
    )
  })

  it('clicking filter-blocked shows only blocked and rejected sessions', async () => {
    stubFetchSessions(ALL_SESSIONS)
    const { container } = renderActivity()
    await waitFor(() => expect(container.querySelector('[data-testid="filter-blocked"]')).not.toBeNull())
    fireEvent.click(container.querySelector('[data-testid="filter-blocked"]')!)
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        expect(states.every((s) => s === 'blocked' || s === 'rejected')).toBe(true)
        expect(rows.length).toBeGreaterThan(0)
      },
      { timeout: 500 },
    )
  })

  it('clicking filter-blocked does not show running sessions', async () => {
    stubFetchSessions(ALL_SESSIONS)
    const { container } = renderActivity()
    await waitFor(() => expect(container.querySelector('[data-testid="filter-blocked"]')).not.toBeNull())
    fireEvent.click(container.querySelector('[data-testid="filter-blocked"]')!)
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        expect(states).not.toContain('running')
      },
      { timeout: 500 },
    )
  })

  // Stuck filter: state === 'stuck' only

  it('clicking filter-stuck shows only stuck sessions', async () => {
    stubFetchSessions(ALL_SESSIONS)
    const { container } = renderActivity()
    await waitFor(() => expect(container.querySelector('[data-testid="filter-stuck"]')).not.toBeNull())
    fireEvent.click(container.querySelector('[data-testid="filter-stuck"]')!)
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        expect(states.every((s) => s === 'stuck')).toBe(true)
        expect(rows.length).toBeGreaterThan(0)
      },
      { timeout: 500 },
    )
  })

  it('clicking filter-stuck does not show blocked or running sessions', async () => {
    stubFetchSessions(ALL_SESSIONS)
    const { container } = renderActivity()
    await waitFor(() => expect(container.querySelector('[data-testid="filter-stuck"]')).not.toBeNull())
    fireEvent.click(container.querySelector('[data-testid="filter-stuck"]')!)
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        expect(states).not.toContain('blocked')
        expect(states).not.toContain('running')
      },
      { timeout: 500 },
    )
  })
})

describe('TestFromAC_VisualStateIndicators', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC2: data-state attribute on ActivityTab session rows

  it('ActivityTab session row has data-state attribute matching session state', async () => {
    stubFetchSessions({ sessions: [SESSION_RUNNING] })
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    await waitFor(
      () => {
        const row = container.querySelector('[data-testid="session-row"]')
        expect(row).not.toBeNull()
        expect(row!.getAttribute('data-state')).toBe('running')
      },
      { timeout: 500 },
    )
  })

  it.each(['running', 'stuck', 'blocked', 'rejected', 'released', 'completed', 'expired'])(
    'ActivityTab session row renders data-state="%s"',
    async (state) => {
      const session = {
        task_id: 10,
        state,
        agent: 'builder',
        started_at: '2026-04-28T09:00:00+00:00',
        duration: null,
        outcome: null,
      }
      stubFetchSessions({ sessions: [session] })
      const { container } = renderActivity()
      fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
      await waitFor(
        () => {
          const row = container.querySelector('[data-testid="session-row"]')
          expect(row).not.toBeNull()
          expect(row!.getAttribute('data-state')).toBe(state)
        },
        { timeout: 500 },
      )
    },
  )

  it('stuck session row has different data-state than completed row', async () => {
    stubFetchSessions({ sessions: [SESSION_STUCK, SESSION_COMPLETED] })
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const stuckRow = Array.from(rows).find((r) => r.getAttribute('data-state') === 'stuck')
        const completedRow = Array.from(rows).find((r) => r.getAttribute('data-state') === 'completed')
        expect(stuckRow).not.toBeNull()
        expect(completedRow).not.toBeNull()
        expect(stuckRow!.getAttribute('data-state')).not.toBe(completedRow!.getAttribute('data-state'))
      },
      { timeout: 500 },
    )
  })

  it('blocked session row has different data-state than completed row', async () => {
    stubFetchSessions({ sessions: [SESSION_BLOCKED, SESSION_COMPLETED] })
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-all"]')!)
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const blockedRow = Array.from(rows).find((r) => r.getAttribute('data-state') === 'blocked')
        const completedRow = Array.from(rows).find((r) => r.getAttribute('data-state') === 'completed')
        expect(blockedRow).not.toBeNull()
        expect(completedRow).not.toBeNull()
        expect(blockedRow!.getAttribute('data-state')).not.toBe(completedRow!.getAttribute('data-state'))
      },
      { timeout: 500 },
    )
  })

  // AC2: data-state on HistorySubtab rows

  it('HistorySubtab session row has data-state attribute matching session state', () => {
    const { container } = renderHistorySubtab([SESSION_RUNNING])
    const row = container.querySelector('[data-testid="history-session-row"]')
    expect(row).not.toBeNull()
    expect(row!.getAttribute('data-state')).toBe('running')
  })

  it.each(['running', 'stuck', 'blocked', 'rejected', 'released', 'completed', 'expired'])(
    'HistorySubtab session row renders data-state="%s"',
    (state) => {
      const session = {
        task_id: 10,
        state,
        agent: 'builder',
        started_at: '2026-04-28T09:00:00+00:00',
        duration: null,
        outcome: null,
      }
      const { container } = renderHistorySubtab([session])
      const row = container.querySelector('[data-testid="history-session-row"]')
      expect(row).not.toBeNull()
      expect(row!.getAttribute('data-state')).toBe(state)
    },
  )
})

describe('TestFromAC_HistorySubtabClickThrough', () => {
  // AC3: HistorySubtab onSelectTask prop and click behavior

  it('HistorySubtab session rows carry data-testid activating CSS cursor:pointer rule', () => {
    const { container } = renderHistorySubtab([SESSION_RUNNING])
    const row = container.querySelector('[data-testid="history-session-row"]') as HTMLElement | null
    expect(row).not.toBeNull()
    // Cursor is applied via SessionRows.css [data-testid='history-session-row'] { cursor: pointer }
    // not via inline style. Verify the testid is present and no inline cursor override exists.
    expect(row!.getAttribute('data-testid')).toBe('history-session-row')
    expect(row!.style.cursor).toBe('')
  })

  it('clicking HistorySubtab row calls onSelectTask with task_id', () => {
    const onSelectTask = vi.fn()
    const { container } = renderHistorySubtab([SESSION_RUNNING], onSelectTask)
    const row = container.querySelector('[data-testid="history-session-row"]')
    expect(row).not.toBeNull()
    fireEvent.click(row!)
    expect(onSelectTask).toHaveBeenCalledWith(SESSION_RUNNING.task_id, expect.anything())
  })

  it('clicking HistorySubtab row calls onSelectTask with subtab="history"', () => {
    const onSelectTask = vi.fn()
    const { container } = renderHistorySubtab([SESSION_RUNNING], onSelectTask)
    const row = container.querySelector('[data-testid="history-session-row"]')
    expect(row).not.toBeNull()
    fireEvent.click(row!)
    expect(onSelectTask).toHaveBeenCalledWith(expect.anything(), 'history')
  })

  it('clicking second HistorySubtab row calls onSelectTask with that row task_id', () => {
    const onSelectTask = vi.fn()
    const { container } = renderHistorySubtab([SESSION_RUNNING, SESSION_STUCK], onSelectTask)
    const rows = container.querySelectorAll('[data-testid="history-session-row"]')
    expect(rows.length).toBe(2)
    fireEvent.click(rows[1]!)
    expect(onSelectTask).toHaveBeenCalledWith(SESSION_STUCK.task_id, 'history')
  })

})

describe('TestFromAC_DetailTabPropThreading', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC3: DetailTab must accept onSelectTask and thread it to HistorySubtab

  it('opening history in DetailTab and clicking a row invokes onSelectTask', async () => {
    const onSelectTask = vi.fn()
    const sessionData = {
      sessions: [
        {
          task_id: BASE_TASK.id,
          state: 'released',
          agent: 'builder',
          started_at: '2026-04-28T09:00:00+00:00',
          duration: 120.0,
          outcome: 'success',
        },
      ],
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(sessionData) })),
    )
    const { container } = renderDetailTab(onSelectTask)

    const historyTab = container.querySelector('[data-testid="history-tab"]')
    expect(historyTab).not.toBeNull()
    fireEvent.click(historyTab!)

    await waitFor(
      () => {
        expect(container.querySelector('[data-testid="history-session-row"]')).not.toBeNull()
      },
      { timeout: 500 },
    )

    fireEvent.click(container.querySelector('[data-testid="history-session-row"]')!)
    expect(onSelectTask).toHaveBeenCalledWith(BASE_TASK.id, 'history')
  })
})

describe('TestFromAC_FilterTypeAlignment', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC4: FilterType union alignment; applyFilter handles all cases

  it('released filter still shows only released sessions (unchanged behavior)', async () => {
    stubFetchSessions(ALL_SESSIONS)
    const { container } = renderActivity()
    fireEvent.click(container.querySelector('[data-testid="filter-released"]')!)
    await waitFor(
      () => {
        const rows = container.querySelectorAll('[data-testid="session-row"]')
        const states = Array.from(rows).map((r) => r.getAttribute('data-state'))
        expect(states.every((s) => s === 'released')).toBe(true)
        expect(rows.length).toBeGreaterThan(0)
      },
      { timeout: 500 },
    )
  })

  it('blocked filter switch does not throw (no unhandled switch branch)', () => {
    stubFetchSessions(ALL_SESSIONS)
    const { container } = renderActivity()
    expect(() => {
      fireEvent.click(container.querySelector('[data-testid="filter-blocked"]')!)
    }).not.toThrow()
  })

  it('stuck filter switch does not throw (no unhandled switch branch)', () => {
    stubFetchSessions(ALL_SESSIONS)
    const { container } = renderActivity()
    expect(() => {
      fireEvent.click(container.querySelector('[data-testid="filter-stuck"]')!)
    }).not.toThrow()
  })

  // AC4: Session interface shared — HistorySubtab accepts same session fields as ActivityTab

})

describe('TestFromAC_CoverageProof', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // Covers: HistorySubtab duration ?? '—' — non-null branch
  it('HistorySubtab renders numeric duration when duration is not null', () => {
    const session = {
      task_id: 10,
      state: 'released',
      agent: 'builder',
      started_at: '2026-04-28T09:00:00+00:00',
      duration: 120.5,
      outcome: 'success',
    }
    const { container } = renderHistorySubtab([session])
    const el = container.querySelector('[data-testid="session-duration"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe('120.5')
  })

  // Covers: HistorySubtab onSelectTask?.() — undefined branch
  it('HistorySubtab row click does not throw when onSelectTask is not provided', () => {
    const { container } = renderHistorySubtab([SESSION_RUNNING])
    const row = container.querySelector('[data-testid="history-session-row"]')
    expect(row).not.toBeNull()
    expect(() => fireEvent.click(row!)).not.toThrow()
  })

  // Covers: HistorySubtab empty sessions array
  it('HistorySubtab renders empty container when sessions is empty', () => {
    const { container } = renderHistorySubtab([])
    expect(container.querySelector('[data-testid="history-view"]')).not.toBeNull()
    expect(container.querySelectorAll('[data-testid="history-session-row"]').length).toBe(0)
  })

  // Covers: DetailTab if (!task) return null
  it('DetailTab renders nothing when task is null', () => {
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={null} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.querySelector('[data-testid="history-tab"]')).toBeNull()
  })

  // Covers: t.blocked && <input data-field="block_reason">
  it('DetailTab shows block_reason input when task is blocked', () => {
    const blocked = { ...BASE_TASK, blocked: true, block_reason: 'Waiting on dep' }
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={blocked} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.querySelector('[data-field="block_reason"]')).not.toBeNull()
  })

  // Covers: t.blocked && <button data-testid="unblock-action">
  it('DetailTab shows unblock-action button when task is blocked', () => {
    const blocked = { ...BASE_TASK, blocked: true, block_reason: 'Waiting on dep' }
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={blocked} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.querySelector('[data-testid="unblock-action"]')).not.toBeNull()
  })

  // Covers: block_reason not shown when NOT blocked
  it('DetailTab does NOT show block_reason when task is not blocked', () => {
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={BASE_TASK} />
      </PorscheDesignSystemProvider>,
    )
    expect(container.querySelector('[data-field="block_reason"]')).toBeNull()
  })

  // Covers: block_reason defaultValue
  it('DetailTab block_reason input shows the block reason text', () => {
    const blocked = { ...BASE_TASK, blocked: true, block_reason: 'Blocked by #50' }
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={blocked} />
      </PorscheDesignSystemProvider>,
    )
    const input = container.querySelector('[data-field="block_reason"]')
    // DetailTab uses controlled value={blockReason} state (initialized from task.block_reason).
    // PDS v4 PInputText exposes the current value as the .value JS property on the host element.
    const inputEl = input as HTMLElement & { value?: string }
    expect(inputEl?.value).toBe('Blocked by #50')
  })
})
