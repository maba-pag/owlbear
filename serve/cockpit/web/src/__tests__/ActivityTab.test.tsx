/**
 * Sidecar Activity tab
 *
 * Covers: default active-session filter, filter switches (all / failed-or-rejected /
 * released), session row field rendering, and click-to-detail navigation.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ActivityTab from '../components/ActivityTab'

// ─── Mocks ────────────────────────────────────────────────────────────────────

// ActivityTab now uses useSSEEvent; jsdom has no native EventSource so mock the
// provider hook. Returning status='closed' keeps paused:false → polling fires.
vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const SESSION_RUNNING = {
  task_id: 1,
  state: 'running',
  agent: 'builder',
  started_at: '2026-04-18T09:00:00+00:00',
  duration: null,
  outcome: null,
}

const SESSION_STUCK = {
  task_id: 2,
  state: 'stuck',
  agent: 'reviewer',
  started_at: '2026-04-18T08:00:00+00:00',
  duration: null,
  outcome: null,
}

const SESSION_RELEASED_FAIL = {
  task_id: 3,
  state: 'released',
  agent: 'test-writer',
  started_at: '2026-04-18T07:00:00+00:00',
  duration: 60.0,
  outcome: 'fail',
}

const SESSION_RELEASED_OK = {
  task_id: 4,
  state: 'released',
  agent: 'doc-writer',
  started_at: '2026-04-18T06:00:00+00:00',
  duration: 45.0,
  outcome: 'success',
}

const SESSION_BLOCKED_OLD = {
  task_id: 5,
  state: 'blocked',
  agent: 'architect',
  started_at: '2026-04-18T05:00:00+00:00',
  duration: null,
  outcome: null,
}

const ALL_SESSIONS = {
  sessions: [SESSION_RUNNING, SESSION_STUCK, SESSION_RELEASED_FAIL, SESSION_RELEASED_OK],
}

const ACTIVE_SESSIONS = {
  sessions: [SESSION_RUNNING, SESSION_STUCK],
}

// ─── Fetch stub helpers ────────────────────────────────────────────────────────

function stubFetchSessions(response: { sessions: object[] }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(response) })),
  )
}

// ─── Render helper ─────────────────────────────────────────────────────────────

function renderActivity(onSelectTask?: (taskId: number, subtab?: string) => void) {
  return render(
    <PorscheDesignSystemProvider>
      <ActivityTab onSelectTask={onSelectTask} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ActivityTab', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── Default filter ───────────────────────────────────────────────────────

  describe('default filter: active sessions', () => {
    it('fetches sessions with active filter on mount', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(ACTIVE_SESSIONS) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      renderActivity()
      await waitFor(
        () => {
          expect(fetchMock).toHaveBeenCalledWith(
            expect.stringMatching(/\/api\/sessions/),
            expect.anything(),
          )
        },
        { timeout: 500 },
      )
    })

    it('default render shows session rows for active (running + stuck) sessions', async () => {
      stubFetchSessions(ALL_SESSIONS)
      const { container } = renderActivity()
      await waitFor(
        () => {
          const rows = container.querySelectorAll('[data-testid="session-row"]')
          expect(rows.length).toBe(2)
        },
        { timeout: 500 },
      )
    })
  })

  // ─── Filter switches ──────────────────────────────────────────────────────

  describe('filter switches', () => {
    it('all filter switch is present', () => {
      const { container } = renderActivity()
      expect(container.querySelector('[data-testid="filter-all"]')).not.toBeNull()
    })

    it('blocked filter switch is present', () => {
      const { container } = renderActivity()
      expect(container.querySelector('[data-testid="filter-blocked"]')).not.toBeNull()
    })

    it('released filter switch is present', () => {
      const { container } = renderActivity()
      expect(container.querySelector('[data-testid="filter-released"]')).not.toBeNull()
    })

    it('clicking all filter shows all sessions', async () => {
      stubFetchSessions(ALL_SESSIONS)
      const { container } = renderActivity()
      const allBtn = container.querySelector('[data-testid="filter-all"]') as HTMLElement | null
      expect(allBtn).not.toBeNull()
      fireEvent.click(allBtn!)
      await waitFor(
        () => {
          const rows = container.querySelectorAll('[data-testid="session-row"]')
          expect(rows.length).toBe(4)
        },
        { timeout: 500 },
      )
    })

    it('clicking blocked filter shows only blocked sessions', async () => {
      stubFetchSessions({ sessions: [SESSION_RUNNING, SESSION_BLOCKED_OLD] })
      const { container } = renderActivity()
      const blockedBtn = container.querySelector('[data-testid="filter-blocked"]') as HTMLElement | null
      expect(blockedBtn).not.toBeNull()
      fireEvent.click(blockedBtn!)
      await waitFor(
        () => {
          const rows = container.querySelectorAll('[data-testid="session-row"]')
          // Only SESSION_BLOCKED_OLD matches the blocked filter
          expect(rows.length).toBe(1)
        },
        { timeout: 500 },
      )
    })

    it('clicking released filter shows only released sessions', async () => {
      stubFetchSessions(ALL_SESSIONS)
      const { container } = renderActivity()
      const relBtn = container.querySelector('[data-testid="filter-released"]') as HTMLElement | null
      expect(relBtn).not.toBeNull()
      fireEvent.click(relBtn!)
      await waitFor(
        () => {
          const rows = container.querySelectorAll('[data-testid="session-row"]')
          // SESSION_RELEASED_FAIL and SESSION_RELEASED_OK are released
          expect(rows.length).toBe(2)
        },
        { timeout: 500 },
      )
    })
  })

  // ─── Session row fields ───────────────────────────────────────────────────

  describe('session row field rendering', () => {
    it('session row shows agent name', async () => {
      stubFetchSessions(ACTIVE_SESSIONS)
      const { container } = renderActivity()
      await waitFor(
        () => {
          const row = container.querySelector('[data-testid="session-row"]')
          expect(row).not.toBeNull()
          expect((row as HTMLElement).querySelector('[data-testid="session-agent"]')).not.toBeNull()
        },
        { timeout: 500 },
      )
    })

    it('session row agent name text matches the session agent field', async () => {
      stubFetchSessions(ACTIVE_SESSIONS)
      const { container } = renderActivity()
      await waitFor(
        () => {
          const row = container.querySelector('[data-testid="session-row"]')
          expect(row).not.toBeNull()
          expect((row as HTMLElement).querySelector('[data-testid="session-agent"]')?.textContent).toBe('builder')
        },
        { timeout: 500 },
      )
    })

    it('session row shows task reference (task_id)', async () => {
      stubFetchSessions(ACTIVE_SESSIONS)
      const { container } = renderActivity()
      await waitFor(
        () => {
          const row = container.querySelector('[data-testid="session-row"]')
          expect(row).not.toBeNull()
          expect((row as HTMLElement).querySelector('[data-testid="session-task"]')?.textContent).toBe('1')
        },
        { timeout: 500 },
      )
    })

    it('session row shows state label', async () => {
      stubFetchSessions(ACTIVE_SESSIONS)
      const { container } = renderActivity()
      await waitFor(
        () => {
          const row = container.querySelector('[data-testid="session-row"]')
          expect(row).not.toBeNull()
          expect((row as HTMLElement).querySelector('[data-testid="session-state"]')?.textContent).toBe('running')
        },
        { timeout: 500 },
      )
    })

    it('session row shows duration', async () => {
      stubFetchSessions(ACTIVE_SESSIONS)
      const { container } = renderActivity()
      await waitFor(
        () => {
          const row = container.querySelector('[data-testid="session-row"]')
          expect(row).not.toBeNull()
          expect((row as HTMLElement).querySelector('[data-testid="session-duration"]')?.textContent).toBe('\u2014')
        },
        { timeout: 500 },
      )
    })
  })

  // ─── Click row → Detail tab with History subtab ───────────────────────────

  describe('row click navigation', () => {
    it('clicking a session row calls onSelectTask with the task_id', async () => {
      stubFetchSessions(ACTIVE_SESSIONS)
      const onSelectTask = vi.fn()
      const { container } = renderActivity(onSelectTask)
      await waitFor(
        () => {
          expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
        },
        { timeout: 500 },
      )
      const row = container.querySelector('[data-testid="session-row"]') as HTMLElement | null
      expect(row).not.toBeNull()
      fireEvent.click(row!)
      expect(onSelectTask).toHaveBeenCalledWith(SESSION_RUNNING.task_id, expect.anything())
    })

    it('clicking a session row passes "history" as the subtab argument', async () => {
      stubFetchSessions(ACTIVE_SESSIONS)
      const onSelectTask = vi.fn()
      const { container } = renderActivity(onSelectTask)
      await waitFor(
        () => {
          expect(container.querySelector('[data-testid="session-row"]')).not.toBeNull()
        },
        { timeout: 500 },
      )
      const row = container.querySelector('[data-testid="session-row"]') as HTMLElement | null
      expect(row).not.toBeNull()
      fireEvent.click(row!)
      expect(onSelectTask).toHaveBeenCalledWith(expect.any(Number), 'history')
    })
  })
})

