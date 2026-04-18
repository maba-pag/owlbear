/**
 * Failing tests for #935: Sidecar Detail tab
 *
 * Covers: editable fields, read-only fields, markdown body, edit mode toggle,
 * save with updated snapshot, 409 conflict detection, history subtab, and
 * oppose-the-flow confirmations. All tests are RED (failing) until the builder
 * implements DetailTab.tsx.
 *
 * react-markdown is mocked here (not yet in package.json). The builder installs
 * the real dep during GREEN phase; the mock intercepts the import automatically.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type TaskDetail } from '../DetailTab'

// ─── Mock react-markdown ──────────────────────────────────────────────────────
// Factory-based mock works even before the real package is installed.

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: '## Objectives\n\n- item one',
  updated: '2026-04-18T10:00:00+00:00',
  created: '2026-04-17T09:00:00+00:00',
  tags: ['bug', 'frontend'],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
}

const TASK_BLOCKED: TaskDetail = {
  ...TASK,
  blocked: true,
  block_reason: 'Waiting for dependency #100',
}

const TASK_WITH_DEPS: TaskDetail = {
  ...TASK,
  depends_on: [10, 20],
  parent: 5,
}

const SESSIONS_SINGLE = {
  sessions: [
    {
      task_id: 42,
      state: 'released',
      agent: 'builder',
      started_at: '2026-04-18T09:00:00+00:00',
      duration: 120.5,
      outcome: 'success',
    },
  ],
}

const SESSIONS_MIXED = {
  sessions: [
    {
      task_id: 42,
      state: 'released',
      agent: 'builder',
      started_at: '2026-04-18T09:00:00+00:00',
      duration: 120.5,
      outcome: 'success',
    },
    {
      task_id: 99,
      state: 'released',
      agent: 'test-writer',
      started_at: '2026-04-18T08:00:00+00:00',
      duration: 90.0,
      outcome: 'fail',
    },
  ],
}

// ─── Render helper ─────────────────────────────────────────────────────────────

function renderDetail(task: TaskDetail = TASK) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_DetailTab', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── Editable fields ───────────────────────────────────────────────────────

  describe('editable fields', () => {
    it('renders title as an input field', () => {
      const { container } = renderDetail()
      expect(container.querySelector('input[data-field="title"]')).not.toBeNull()
    })

    it('title input shows the current task title value', () => {
      const { container } = renderDetail()
      const input = container.querySelector('input[data-field="title"]') as HTMLInputElement | null
      expect(input?.value).toBe('Fix login bug')
    })

    it('renders priority as a select/dropdown control', () => {
      const { container } = renderDetail()
      expect(container.querySelector('[data-field="priority"]')).not.toBeNull()
    })

    it('renders each tag as a chip element', () => {
      const { container } = renderDetail()
      const chips = container.querySelectorAll('[data-testid="tag-chip"]')
      expect(chips.length).toBe(2)
    })

    it('renders depends_on field control', () => {
      const { container } = renderDetail(TASK_WITH_DEPS)
      expect(container.querySelector('[data-field="depends_on"]')).not.toBeNull()
    })

    it('renders parent field control', () => {
      const { container } = renderDetail(TASK_WITH_DEPS)
      expect(container.querySelector('[data-field="parent"]')).not.toBeNull()
    })

    it('renders block_reason field control when task is blocked', () => {
      const { container } = renderDetail(TASK_BLOCKED)
      expect(container.querySelector('[data-field="block_reason"]')).not.toBeNull()
    })
  })

  // ─── Read-only fields ─────────────────────────────────────────────────────

  describe('read-only fields', () => {
    it('id is shown as static text, not an input', () => {
      const { container } = renderDetail()
      expect(container.querySelector('input[data-field="id"]')).toBeNull()
      expect(container.querySelector('[data-testid="field-id"]')).not.toBeNull()
    })

    it('id field text contains the task id value', () => {
      const { container } = renderDetail()
      expect(container.querySelector('[data-testid="field-id"]')?.textContent).toContain('42')
    })

    it('created is shown as static text, not an input', () => {
      const { container } = renderDetail()
      expect(container.querySelector('input[data-field="created"]')).toBeNull()
      expect(container.querySelector('[data-testid="field-created"]')).not.toBeNull()
    })

    it('status is shown as static text, not an input', () => {
      const { container } = renderDetail()
      expect(container.querySelector('input[data-field="status"]')).toBeNull()
      expect(container.querySelector('[data-testid="field-status"]')).not.toBeNull()
    })
  })

  // ─── Markdown body ─────────────────────────────────────────────────────────

  describe('markdown body rendering', () => {
    it('renders body content through the markdown-body container', () => {
      const { container } = renderDetail()
      expect(container.querySelector('[data-testid="markdown-body"]')).not.toBeNull()
    })

    it('does not inject raw script tags from markdown body (XSS)', () => {
      const xssTask: TaskDetail = { ...TASK, body: '<script>alert("xss")</script>text' }
      const { container } = renderDetail(xssTask)
      // Precondition: body must be rendered at all (fails in RED — stub returns null)
      expect(container.querySelector('[data-testid="markdown-body"]')).not.toBeNull()
      expect(container.querySelector('script')).toBeNull()
    })
  })

  // ─── Edit mode toggle ─────────────────────────────────────────────────────

  describe('edit mode toggle for body', () => {
    it('edit-mode toggle button is present', () => {
      const { container } = renderDetail()
      expect(container.querySelector('[data-testid="body-edit-toggle"]')).not.toBeNull()
    })

    it('clicking edit-mode toggle reveals a textarea for body editing', () => {
      const { container } = renderDetail()
      const toggle = container.querySelector('[data-testid="body-edit-toggle"]') as HTMLElement | null
      expect(toggle).not.toBeNull()
      fireEvent.click(toggle!)
      expect(container.querySelector('textarea[data-field="body"]')).not.toBeNull()
    })
  })

  // ─── Save ─────────────────────────────────────────────────────────────────

  describe('save action', () => {
    it('save button is present', () => {
      const { container } = renderDetail()
      expect(container.querySelector('[data-testid="save-button"]')).not.toBeNull()
    })

    it('clicking save sends POST to /api/tasks/{id}/edit', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail()
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          expect(fetchMock).toHaveBeenCalledWith(
            expect.stringContaining('/api/tasks/42/edit'),
            expect.objectContaining({ method: 'POST' }),
          )
        },
        { timeout: 500 },
      )
    })

    it('save request body includes the updated snapshot field', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail()
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body).toHaveProperty('updated', TASK.updated)
        },
        { timeout: 500 },
      )
    })
  })

  // ─── 409 conflict detection ───────────────────────────────────────────────

  describe('409 conflict detection', () => {
    it('409 response from save opens a conflict modal', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) }),
        ),
      )
      const { container } = renderDetail()
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          expect(container.querySelector('[data-testid="conflict-modal"]')).not.toBeNull()
        },
        { timeout: 500 },
      )
    })

    it('conflict modal offers a refresh (discard local edits) option', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) }),
        ),
      )
      const { container } = renderDetail()
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          const modal = container.querySelector('[data-testid="conflict-modal"]')
          expect(modal?.querySelector('[data-testid="conflict-refresh"]')).not.toBeNull()
        },
        { timeout: 500 },
      )
    })

    it('conflict modal offers an overwrite (force save) option', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) }),
        ),
      )
      const { container } = renderDetail()
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          const modal = container.querySelector('[data-testid="conflict-modal"]')
          expect(modal?.querySelector('[data-testid="conflict-overwrite"]')).not.toBeNull()
        },
        { timeout: 500 },
      )
    })
  })

  // ─── History subtab ───────────────────────────────────────────────────────

  describe('history subtab', () => {
    it('history subtab button is present', () => {
      const { container } = renderDetail()
      expect(container.querySelector('[data-testid="history-tab"]')).not.toBeNull()
    })

    it('clicking history tab fetches GET /api/sessions?filter=all', async () => {
      const fetchMock = vi.fn((url: string) => {
        if (url.includes('/api/sessions')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(SESSIONS_SINGLE) })
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail()
      const historyTab = container.querySelector('[data-testid="history-tab"]') as HTMLElement | null
      expect(historyTab).not.toBeNull()
      fireEvent.click(historyTab!)
      await waitFor(
        () => {
          const sessionUrls = fetchMock.mock.calls
            .map(([url]) => url as string)
            .filter((u) => u.includes('/api/sessions'))
          expect(sessionUrls.length).toBeGreaterThan(0)
          expect(sessionUrls[0]).toContain('filter=all')
        },
        { timeout: 500 },
      )
    })

    it('history shows only sessions matching the selected task_id (client-side filter)', async () => {
      const fetchMock = vi.fn((url: string) => {
        if (url.includes('/api/sessions')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(SESSIONS_MIXED) })
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail()
      const historyTab = container.querySelector('[data-testid="history-tab"]') as HTMLElement | null
      expect(historyTab).not.toBeNull()
      fireEvent.click(historyTab!)
      await waitFor(
        () => {
          // SESSIONS_MIXED has 2 sessions; only 1 belongs to task_id=42
          const rows = container.querySelectorAll('[data-testid="history-session-row"]')
          expect(rows.length).toBe(1)
        },
        { timeout: 500 },
      )
    })

    it('history session row shows agent name', async () => {
      const fetchMock = vi.fn((url: string) => {
        if (url.includes('/api/sessions')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(SESSIONS_SINGLE) })
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail()
      const historyTab = container.querySelector('[data-testid="history-tab"]') as HTMLElement | null
      expect(historyTab).not.toBeNull()
      fireEvent.click(historyTab!)
      await waitFor(
        () => {
          const row = container.querySelector('[data-testid="history-session-row"]')
          expect(row?.querySelector('[data-testid="session-agent"]')?.textContent).toBe('builder')
        },
        { timeout: 500 },
      )
    })

    it('history session row shows duration', async () => {
      const fetchMock = vi.fn((url: string) => {
        if (url.includes('/api/sessions')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(SESSIONS_SINGLE) })
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail()
      const historyTab = container.querySelector('[data-testid="history-tab"]') as HTMLElement | null
      expect(historyTab).not.toBeNull()
      fireEvent.click(historyTab!)
      await waitFor(
        () => {
          const row = container.querySelector('[data-testid="history-session-row"]')
          expect(row?.querySelector('[data-testid="session-duration"]')).not.toBeNull()
        },
        { timeout: 500 },
      )
    })

    it('history session row shows outcome', async () => {
      const fetchMock = vi.fn((url: string) => {
        if (url.includes('/api/sessions')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(SESSIONS_SINGLE) })
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail()
      const historyTab = container.querySelector('[data-testid="history-tab"]') as HTMLElement | null
      expect(historyTab).not.toBeNull()
      fireEvent.click(historyTab!)
      await waitFor(
        () => {
          const row = container.querySelector('[data-testid="history-session-row"]')
          expect(row?.querySelector('[data-testid="session-outcome"]')?.textContent).toBe('success')
        },
        { timeout: 500 },
      )
    })
  })

  // ─── Oppose-the-flow confirmations ────────────────────────────────────────

  describe('oppose-the-flow confirmations', () => {
    it('backward move action requires a confirmation dialog', () => {
      const { container } = renderDetail()
      const btn = container.querySelector('[data-testid="move-backward"]') as HTMLElement | null
      expect(btn).not.toBeNull()
      fireEvent.click(btn!)
      expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull()
    })

    it('unblock action requires a confirmation dialog', () => {
      const { container } = renderDetail(TASK_BLOCKED)
      const btn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
      expect(btn).not.toBeNull()
      fireEvent.click(btn!)
      expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull()
    })

    it('unblock confirmation dialog surfaces the existing block_reason', () => {
      const { container } = renderDetail(TASK_BLOCKED)
      const btn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
      expect(btn).not.toBeNull()
      fireEvent.click(btn!)
      const dialog = container.querySelector('[data-testid="confirm-dialog"]')
      expect(dialog?.textContent).toContain('Waiting for dependency #100')
    })
  })
})

// ─── Builder-discovered tests (AC9: unclaim) ──────────────────────────────────

describe('TestBuilderDiscovered', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('unclaim confirm dialog (AC9)', () => {
    it('unclaim action button is present', () => {
      const { container } = renderDetail()
      expect(container.querySelector('[data-testid="unclaim-action"]')).not.toBeNull()
    })

    it('unclaim action requires a confirmation dialog', () => {
      const { container } = renderDetail()
      const btn = container.querySelector('[data-testid="unclaim-action"]') as HTMLElement | null
      expect(btn).not.toBeNull()
      fireEvent.click(btn!)
      expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull()
    })
  })
})
