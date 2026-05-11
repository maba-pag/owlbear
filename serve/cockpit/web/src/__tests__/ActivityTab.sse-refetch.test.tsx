/**
 * Implement ActivityTab SSE live refetch
 *
 * Covers:
 *   AC1 — usePollingFetch replaces one-shot fetch (URL, intervalMs, paused flag, onSuccess)
 *   AC2 — useSSEEvent called with 'activity-changed'
 *   AC3 — mtime guard triggers refetch when SSE is open and mtime changes
 *   AC4 — negative guard: no refetch when sseStatus !== 'open' or mtime is null
 *   AC5 — initial mount fetch fires immediately (usePollingFetch called on mount)
 *   AC6 — EventSourceProvider mocked via vi.mock (jsdom lacks native EventSource)
 *
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, act, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ActivityTab from '../components/ActivityTab'
import { useSSEEvent } from '../hooks/EventSourceProvider'
import { usePollingFetch } from '../hooks/usePollingFetch'
import type { Session } from '../components/HistorySubtab'

// ─── Hoisted mutable SSE state ─────────────────────────────────────────────────

const sseState = vi.hoisted(() => ({
  status: 'closed' as 'connecting' | 'open' | 'closed',
  mtime: null as number | null,
}))

// ─── Hoisted polling mock capture ─────────────────────────────────────────────

const pollingCapture = vi.hoisted(() => ({
  refetch: vi.fn(),
}))

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: sseState.status, mtime: sseState.mtime })),
}))

vi.mock('../hooks/usePollingFetch', () => ({
  usePollingFetch: vi.fn((_url: string, _options?: unknown) => ({
    isFetching: false,
    hasFetched: false,
    refetch: pollingCapture.refetch,
  })),
}))

// ─── Render helpers ───────────────────────────────────────────────────────────

function renderActivity() {
  return render(
    <PorscheDesignSystemProvider>
      <ActivityTab />
    </PorscheDesignSystemProvider>,
  )
}

function activityJsx() {
  return (
    <PorscheDesignSystemProvider>
      <ActivityTab />
    </PorscheDesignSystemProvider>
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ActivityTabSSE', () => {
  beforeEach(() => {
    sseState.status = 'closed'
    sseState.mtime = null
    pollingCapture.refetch = vi.fn()
    vi.mocked(usePollingFetch).mockClear()
    vi.mocked(useSSEEvent).mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  // ─── AC1: usePollingFetch with correct options ───────────────────────────────

  describe('AC1 — usePollingFetch replaces one-shot fetch', () => {
    it('calls usePollingFetch with /api/sessions?filter=all URL', () => {
      renderActivity()
      expect(vi.mocked(usePollingFetch)).toHaveBeenCalledWith(
        '/api/sessions?filter=all',
        expect.anything(),
      )
    })

    it('calls usePollingFetch with intervalMs 120000', () => {
      renderActivity()
      expect(vi.mocked(usePollingFetch)).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ intervalMs: 120_000 }),
      )
    })

    it('passes paused: true to usePollingFetch when sseStatus is open', () => {
      sseState.status = 'open'
      renderActivity()
      expect(vi.mocked(usePollingFetch)).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ paused: true }),
      )
    })

    it('passes paused: false to usePollingFetch when sseStatus is closed', () => {
      sseState.status = 'closed'
      renderActivity()
      expect(vi.mocked(usePollingFetch)).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ paused: false }),
      )
    })

    it('passes paused: false to usePollingFetch when sseStatus is connecting', () => {
      sseState.status = 'connecting'
      renderActivity()
      expect(vi.mocked(usePollingFetch)).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ paused: false }),
      )
    })

    it('onSuccess callback populates sessions in the rendered component', async () => {
      const sessions: Session[] = [
        {
          task_id: 1,
          state: 'running',
          agent: 'builder',
          started_at: '2026-01-01T00:00:00Z',
          duration: null,
          outcome: null,
        },
      ]
      const { container } = renderActivity()

      // Fails with current impl — usePollingFetch never called, so no options captured
      expect(vi.mocked(usePollingFetch)).toHaveBeenCalled()

      const options = vi.mocked(usePollingFetch).mock.calls[0][1] as {
        onSuccess?: (data: { sessions: Session[] }) => void
      }
      expect(options?.onSuccess).toBeDefined()

      await act(async () => {
        options.onSuccess?.({ sessions })
      })

      // Running session passes the default 'active' filter (running | stuck)
      await waitFor(() => {
        expect(container.querySelectorAll('[data-testid="session-row"]').length).toBeGreaterThan(0)
      })
    })
  })

  // ─── AC2: useSSEEvent called with 'activity-changed' ────────────────────────

  describe('AC2 — useSSEEvent called with activity-changed', () => {
    it('calls useSSEEvent with the activity-changed event type', () => {
      renderActivity()
      expect(vi.mocked(useSSEEvent)).toHaveBeenCalledWith('activity-changed')
    })
  })

  // ─── AC3: mtime guard triggers refetch when SSE is open ──────────────────────

  describe('AC3 — mtime change with open SSE triggers refetch', () => {
    it('triggers refetch when sseStatus is open and mtime changes from null to a value', async () => {
      sseState.status = 'open'
      sseState.mtime = null
      const { rerender } = renderActivity()
      await act(async () => {})

      pollingCapture.refetch.mockClear()

      sseState.mtime = 1000
      rerender(activityJsx())
      await act(async () => {})

      expect(pollingCapture.refetch).toHaveBeenCalledTimes(1)
    })

    it('does not trigger refetch again for same mtime value (deduplication guard)', async () => {
      sseState.status = 'open'
      sseState.mtime = null
      const { rerender } = renderActivity()
      await act(async () => {})

      // First new mtime — should trigger refetch (fails with current impl)
      sseState.mtime = 1000
      rerender(activityJsx())
      await act(async () => {})
      expect(pollingCapture.refetch).toHaveBeenCalledTimes(1)

      // Same mtime repeated — dedup guard must suppress re-fetch
      pollingCapture.refetch.mockClear()
      rerender(activityJsx())
      await act(async () => {})
      expect(pollingCapture.refetch).not.toHaveBeenCalled()
    })

    it('triggers refetch again when mtime advances to a new value', async () => {
      sseState.status = 'open'
      sseState.mtime = 1000
      const { rerender } = renderActivity()
      await act(async () => {})

      pollingCapture.refetch.mockClear()

      sseState.mtime = 2000
      rerender(activityJsx())
      await act(async () => {})

      expect(pollingCapture.refetch).toHaveBeenCalledTimes(1)
    })
  })

  // ─── AC4: No refetch when guard conditions are unmet ─────────────────────────

  describe('AC4 — no SSE-triggered refetch when guard conditions unmet', () => {
    it('does not trigger refetch when sseStatus is closed and mtime changes', async () => {
      sseState.status = 'closed'
      sseState.mtime = null
      const { rerender } = renderActivity()
      await act(async () => {})

      pollingCapture.refetch.mockClear()
      sseState.mtime = 1000
      rerender(activityJsx())
      await act(async () => {})

      // Guard assertion: useSSEEvent must be called (fails with current impl)
      expect(vi.mocked(useSSEEvent)).toHaveBeenCalledWith('activity-changed')
      expect(pollingCapture.refetch).not.toHaveBeenCalled()
    })

    it('does not trigger refetch when sseStatus is connecting and mtime changes', async () => {
      sseState.status = 'connecting'
      sseState.mtime = null
      const { rerender } = renderActivity()
      await act(async () => {})

      pollingCapture.refetch.mockClear()
      sseState.mtime = 1000
      rerender(activityJsx())
      await act(async () => {})

      expect(vi.mocked(useSSEEvent)).toHaveBeenCalledWith('activity-changed')
      expect(pollingCapture.refetch).not.toHaveBeenCalled()
    })

    it('does not trigger refetch when sseStatus is open but mtime is null', async () => {
      sseState.status = 'open'
      sseState.mtime = null
      const { rerender } = renderActivity()
      await act(async () => {})

      pollingCapture.refetch.mockClear()
      // mtime stays null — no change, guard must not fire
      rerender(activityJsx())
      await act(async () => {})

      expect(vi.mocked(useSSEEvent)).toHaveBeenCalledWith('activity-changed')
      expect(pollingCapture.refetch).not.toHaveBeenCalled()
    })
  })

  // ─── AC5: Initial mount fetch fires immediately ───────────────────────────────

  describe('AC5 — initial mount fetch fires immediately', () => {
    it('calls usePollingFetch on mount, preserving initial fetch behavior', () => {
      renderActivity()
      // Fails with current impl — usePollingFetch is never called
      expect(vi.mocked(usePollingFetch)).toHaveBeenCalled()
    })
  })

  // ─── AC6: EventSourceProvider mock (jsdom compatibility) ─────────────────────

  describe('AC6 — EventSourceProvider mock enables jsdom-compatible rendering', () => {
    it('renders with useSSEEvent mocked via EventSourceProvider — no native EventSource required', () => {
      const { container } = renderActivity()
      // Basic smoke: filter buttons should render
      expect(container.querySelector('[data-testid="filter-active"]')).not.toBeNull()
      // useSSEEvent must be intercepted by mock, not native EventSource
      // Fails with current impl — ActivityTab does not yet call useSSEEvent
      expect(vi.mocked(useSSEEvent)).toHaveBeenCalled()
    })
  })
})

