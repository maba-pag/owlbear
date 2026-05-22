/**
 * Sidecar Detail tab
 *
 * Covers: editable fields, read-only fields, markdown body, edit mode toggle,
 * save with updated snapshot, 409 conflict detection, history subtab, and
 * implements DetailTab.tsx.
 *
 * react-markdown is mocked here (not yet in package.json). The builder installs
 * the real dep during GREEN phase; the mock intercepts the import automatically.
 */
import { beforeAll, describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type TaskDetail } from '../components/DetailTab'
import type { Board } from '../hooks/useBoard'

// Newer jsdom versions expose a partial attachInternals that lacks setFormValue,
// causing PDS Stencil form components (p-input-text, p-textarea, p-select) to
// throw on mount. Unconditionally override for consistent PDS rendering.
beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

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

const BOARD: Board = {
  statuses: [
    { name: 'research' },
    { name: 'backlog' },
    { name: 'todo' },
    { name: 'in-progress' },
    { name: 'review' },
    { name: 'docs' },
    { name: 'done' },
  ],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    research: ['backlog'],
    backlog: ['research', 'todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo', 'review'],
    review: ['in-progress', 'docs'],
    docs: ['review', 'done'],
    done: [],
  },
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

function renderDetailWithBoard(task: TaskDetail = TASK, board: Board | null = BOARD) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} board={board} />
    </PorscheDesignSystemProvider>,
  )
}

function clickConfirm(container: HTMLElement): void {
  const btns = container.querySelectorAll('[data-testid="confirm-dialog"] p-button')
  const confirmBtn = btns[btns.length - 1] as HTMLElement | null
  expect(confirmBtn).not.toBeNull()
  fireEvent.click(confirmBtn!)
}

function typeIntoPdsField(container: HTMLElement, selector: string, value: string): void {
  const field = container.querySelector(selector) as HTMLElement | null
  expect(field).not.toBeNull()
  fireEvent(field!, new CustomEvent('input', { detail: { value }, bubbles: true }))
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
      expect(container.querySelector('p-input-text[data-field="title"]')).not.toBeNull()
    })

    it('title input shows the current task title value', () => {
      const { container } = renderDetail()
      const input = container.querySelector('p-input-text[data-field="title"]') as
        | (HTMLElement & { value?: string })
        | null;
      // PDS PInputText exposes value as a JS property via the Stencil getter
      expect(input?.value ?? input?.getAttribute('value')).toBe('Fix login bug')
    })

    it('renders priority as a select/dropdown control', () => {
      const { container } = renderDetail()
      expect(container.querySelector('[data-field="priority"]')).not.toBeNull()
    })

    it('renders each tag as a dismissible chip element', () => {
      const { container } = renderDetail()
      const chips = container.querySelectorAll('p-tag-dismissible[data-testid="tag-chip"]')
      expect(chips.length).toBe(2)
      expect(container.querySelector('p-tag[data-testid="tag-chip"]')).toBeNull()
      expect(chips[0]).toHaveAttribute('data-tag', 'bug')
    })

    it('removes a tag from the edit surface when its chip is dismissed', () => {
      const { container } = renderDetail()
      const bugChip = container.querySelector('p-tag-dismissible[data-tag="bug"]') as HTMLElement | null
      expect(bugChip).not.toBeNull()

      fireEvent.click(bugChip!)

      expect(container.querySelector('p-tag-dismissible[data-tag="bug"]')).toBeNull()
      expect(container.querySelector('p-tag-dismissible[data-tag="frontend"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="dirty-indicator"]')).not.toBeNull()
    })

    it('renders a field and command to add a tag', () => {
      const { container } = renderDetail()
      expect(container.querySelector('p-input-text[data-field="new-tag"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="add-tag-button"]')).not.toBeNull()
    })

    it('adds a new tag as a dismissible chip', () => {
      const { container } = renderDetail()
      typeIntoPdsField(container, 'p-input-text[data-field="new-tag"]', 'scope:cockpit')
      const addButton = container.querySelector('[data-testid="add-tag-button"]') as HTMLElement | null
      expect(addButton).not.toBeNull()

      fireEvent.click(addButton!)

      expect(container.querySelector('p-tag-dismissible[data-tag="scope:cockpit"]')).not.toBeNull()
      const input = container.querySelector('p-input-text[data-field="new-tag"]') as
        | (HTMLElement & { value?: string })
        | null
      expect(input?.value ?? input?.getAttribute('value')).toBe('')
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
      expect(container.querySelector('p-textarea[data-field="body"]')).not.toBeNull()
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

    it('save request body includes the edited tag list', async () => {
      const updatedTask = { ...TASK, tags: ['frontend', 'scope:cockpit'] }
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(updatedTask) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail()

      const bugChip = container.querySelector('p-tag-dismissible[data-tag="bug"]') as HTMLElement | null
      expect(bugChip).not.toBeNull()
      fireEvent.click(bugChip!)
      typeIntoPdsField(container, 'p-input-text[data-field="new-tag"]', 'scope:cockpit')

      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)

      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body).toHaveProperty('tags')
          expect(body.tags).toEqual(['frontend', 'scope:cockpit'])
        },
        { timeout: 500 },
      )
    })
  })

  // ─── 409 conflict detection ───────────────────────────────────────────────

  describe('409 conflict detection', () => {
    function mockConflictWithRefetchSuccess(): ReturnType<typeof vi.fn> {
      let callCount = 0
      return vi.fn(() => {
        callCount += 1
        if (callCount === 1) {
          return Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) })
        }
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(TASK) })
      })
    }

    it('409 response from save opens a conflict modal', async () => {
      vi.stubGlobal('fetch', mockConflictWithRefetchSuccess())
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
      vi.stubGlobal('fetch', mockConflictWithRefetchSuccess())
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

    it('conflict modal requires acknowledge before showing overwrite (force save) option', async () => {
      vi.stubGlobal('fetch', mockConflictWithRefetchSuccess())
      const { container } = renderDetail()
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          const modal = container.querySelector('[data-testid="conflict-modal"]')
          expect(modal?.querySelector('[data-testid="conflict-overwrite"]')).toBeNull()
          const ack = modal?.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
          expect(ack).not.toBeNull()
          fireEvent.click(ack!)
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
    // TODO(#1381): re-enable when backward-action confirmation dialog wiring is implemented.
    it.skip('backward move action requires a confirmation dialog', () => {
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

  // ─── AC6: body field included in save payload ─────────────────────────────

  describe('save payload includes body (AC6)', () => {
    it('save request body includes the edited body textarea content', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail()

      // Toggle into edit mode so the body p-textarea is rendered
      const toggle = container.querySelector('[data-testid="body-edit-toggle"]') as HTMLElement | null
      expect(toggle).not.toBeNull()
      fireEvent.click(toggle!)

      // Drive p-textarea with CustomEvent matching readControlValue(event.detail?.value)
      const pTextarea = container.querySelector('p-textarea[data-field="body"]') as HTMLElement | null
      expect(pTextarea).not.toBeNull()
      fireEvent(pTextarea!, new CustomEvent('change', { detail: { value: 'edited body content' }, bubbles: true }))

      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)

      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const parsed = JSON.parse(options.body as string) as Record<string, unknown>
          expect(parsed).toHaveProperty('body', 'edited body content')
        },
        { timeout: 500 },
      )
    })
  })

  // ─── AC7: force-save button fires second API call ─────────────────────────

  describe('force-save fires API call (AC7)', () => {
    it('clicking conflict-overwrite sends a second POST to /api/tasks/{id}/edit', async () => {
      let callCount = 0
      const fetchMock = vi.fn(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) })
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) })
      })
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail()

      // Trigger 409
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)

      // Wait for conflict modal to appear
      await waitFor(
        () => {
          expect(container.querySelector('[data-testid="conflict-modal"]')).not.toBeNull()
        },
        { timeout: 500 },
      )

      const acknowledgeBtn = container.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
      expect(acknowledgeBtn).not.toBeNull()
      fireEvent.click(acknowledgeBtn!)

      // Click force-save
      const overwriteBtn = container.querySelector('[data-testid="conflict-overwrite"]') as HTMLElement | null
      expect(overwriteBtn).not.toBeNull()
      fireEvent.click(overwriteBtn!)

      await waitFor(
        () => {
          // Three calls: initial POST (409), refetch GET, force-save POST
          expect(fetchMock).toHaveBeenCalledTimes(3)
          // Call 2 (index 1): refetch GET /api/tasks/{id}
          const [refetchUrl, refetchOpts] = fetchMock.mock.calls[1] as unknown as [string, RequestInit]
          expect(refetchUrl).toContain('/api/tasks/42')
          expect(refetchOpts.method).toBe('GET')
          // Call 3 (index 2): force-save POST /api/tasks/{id}/edit
          const [forceSaveUrl, forceSaveOpts] = fetchMock.mock.calls[2] as unknown as [string, RequestInit]
          expect(forceSaveUrl).toContain('/api/tasks/42/edit')
          expect(forceSaveOpts.method).toBe('POST')
        },
        { timeout: 500 },
      )
    })
  })

  // ─── AC8: Typed save payload proofs ────────────────────────────────────────

  describe('save payload typed fields (AC8)', () => {
    it('save payload includes depends_on as an array of integers', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK_WITH_DEPS) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail(TASK_WITH_DEPS)
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body).toHaveProperty('depends_on')
          const deps = body['depends_on'] as unknown[]
          expect(Array.isArray(deps)).toBe(true)
          expect(deps.every((d) => typeof d === 'number')).toBe(true)
          expect(deps).toContain(10)
          expect(deps).toContain(20)
        },
        { timeout: 500 },
      )
    })

    it('save payload includes parent as integer when task has a parent', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK_WITH_DEPS) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail(TASK_WITH_DEPS)
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body).toHaveProperty('parent')
          expect(typeof body['parent']).toBe('number')
          expect(body['parent']).toBe(5)
        },
        { timeout: 500 },
      )
    })

    it('save payload includes parent as null when task has no parent', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail(TASK)
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body).toHaveProperty('parent')
          expect(body['parent']).toBeNull()
        },
        { timeout: 500 },
      )
    })

    it('save payload includes block_reason string for blocked tasks', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK_BLOCKED) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail(TASK_BLOCKED)
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body).toHaveProperty('block_reason')
          expect(typeof body['block_reason']).toBe('string')
          expect(body['block_reason']).toBe('Waiting for dependency #100')
        },
        { timeout: 500 },
      )
    })
  })

  // ─── AC8: Action endpoint proofs ───────────────────────────────────────────

  describe('action endpoint proofs (AC8)', () => {
    it('unblock confirmation POSTs to edit endpoint with block_reason: null', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...TASK_BLOCKED, blocked: false, block_reason: null }),
        }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail(TASK_BLOCKED)
      const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
      expect(unblockBtn).not.toBeNull()
      fireEvent.click(unblockBtn!)
      await waitFor(
        () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
        { timeout: 500 },
      )
      clickConfirm(container)
      await waitFor(
        () => {
          const editCalls = fetchMock.mock.calls.filter(([url]) =>
            (url as string).includes(`/api/tasks/${TASK_BLOCKED.id}/edit`),
          )
          expect(editCalls.length).toBeGreaterThan(0)
          const [, options] = editCalls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body).toHaveProperty('block_reason', null)
        },
        { timeout: 500 },
      )
    })

    it('unclaim confirmation POSTs to the release endpoint', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail(TASK)
      const unclaimBtn = container.querySelector('[data-testid="unclaim-action"]') as HTMLElement | null
      expect(unclaimBtn).not.toBeNull()
      fireEvent.click(unclaimBtn!)
      await waitFor(
        () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
        { timeout: 500 },
      )
      clickConfirm(container)
      await waitFor(
        () => {
          const releaseCalls = fetchMock.mock.calls.filter(([url]) =>
            (url as string).includes(`/api/tasks/${TASK.id}/release`),
          )
          expect(releaseCalls.length).toBeGreaterThan(0)
        },
        { timeout: 500 },
      )
    })

    it('move-backward sends previous pipeline status in the request body', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      // TASK.status = 'todo'; previous status in BOARD is 'backlog'
      const { container } = renderDetailWithBoard(TASK, BOARD)
      const moveBackBtn = container.querySelector('[data-testid="move-backward"]') as HTMLElement | null
      expect(moveBackBtn).not.toBeNull()
      fireEvent.click(moveBackBtn!)
      await waitFor(
        () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
        { timeout: 500 },
      )
      clickConfirm(container)
      await waitFor(
        () => {
          const moveCalls = fetchMock.mock.calls.filter(([url]) =>
            (url as string).includes(`/api/tasks/${TASK.id}/move`),
          )
          expect(moveCalls.length).toBeGreaterThan(0)
          const [, options] = moveCalls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          // TASK.status = 'todo' → previous status in BOARD is 'backlog'
          expect(body).toHaveProperty('status', 'backlog')
        },
        { timeout: 500 },
      )
    })

    it('404 from mutation calls onTaskCleared callback', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ detail: 'not found' }) }),
        ),
      )
      const onTaskCleared = vi.fn()
      const { container } = render(
        <PorscheDesignSystemProvider>
          <DetailTab task={TASK} onTaskCleared={onTaskCleared} />
        </PorscheDesignSystemProvider>,
      )
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          expect(onTaskCleared).toHaveBeenCalledTimes(1)
        },
        { timeout: 500 },
      )
    })
  })

  // ─── AC8: onTaskUpdated callback ───────────────────────────────────────────

  describe('onTaskUpdated callback (AC8)', () => {
    it('successful save calls onTaskUpdated with the response task', async () => {
      const updatedTask: TaskDetail = { ...TASK, title: 'Updated title from server' }
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(updatedTask) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const onTaskUpdated = vi.fn()
      const { container } = render(
        <PorscheDesignSystemProvider>
          <DetailTab task={TASK} onTaskUpdated={onTaskUpdated} />
        </PorscheDesignSystemProvider>,
      )
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      expect(saveBtn).not.toBeNull()
      fireEvent.click(saveBtn!)
      await waitFor(
        () => {
          expect(onTaskUpdated).toHaveBeenCalledTimes(1)
          expect(onTaskUpdated).toHaveBeenCalledWith(
            expect.objectContaining({ title: 'Updated title from server' }),
          )
        },
        { timeout: 500 },
      )
    })
  })

  // ─── AC4: Live-edit proof — state-driven controlled field values ────────────
  // Reviewer gap: prior AC8 payload tests render seeded state and immediately
  // click save.  These tests drive a live user edit (fire input event) first,
  // proving that the current user-edited value (not the initial prop value)
  // reaches the save payload.

  describe('live field edits reach save payload (AC4)', () => {
    it('typed title overrides seeded value in save payload', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail(TASK)

      const titleInput = container.querySelector('p-input-text[data-field="title"]') as HTMLElement | null
      expect(titleInput).not.toBeNull()
      // Drive live edit via PDS-compatible custom event (detail.value path in readControlValue)
      fireEvent(titleInput!, new CustomEvent('input', { detail: { value: 'User-Typed Title' }, bubbles: true }))

      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      fireEvent.click(saveBtn!)

      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body['title']).toBe('User-Typed Title')
          // Must not echo the seeded value
          expect(body['title']).not.toBe(TASK.title)
        },
        { timeout: 500 },
      )
    })

    it('typed parent id overrides seeded null in save payload', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      // Render with no parent (null) so we can prove that typing "7" into the field
      // causes parent: 7 (not null) to appear in the payload.
      const { container } = renderDetail(TASK)

      const parentInput = container.querySelector('p-input-text[data-field="parent"]') as HTMLElement | null
      expect(parentInput).not.toBeNull()
      fireEvent(parentInput!, new CustomEvent('input', { detail: { value: '7' }, bubbles: true }))

      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      fireEvent.click(saveBtn!)

      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body['parent']).toBe(7)
        },
        { timeout: 500 },
      )
    })

    it('cleared block_reason field sends empty string in save payload when task is blocked', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK_BLOCKED) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail(TASK_BLOCKED)

      const blockReasonInput = container.querySelector('p-input-text[data-field="block_reason"]') as HTMLElement | null
      expect(blockReasonInput).not.toBeNull()
      // Clear the block reason field — user deletes the existing text
      fireEvent(blockReasonInput!, new CustomEvent('input', { detail: { value: '' }, bubbles: true }))

      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      fireEvent.click(saveBtn!)

      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          // block_reason must reflect the live-edited empty value, not the seeded 'Waiting for dependency #100'
          expect(body['block_reason']).not.toBe('Waiting for dependency #100')
          expect(body['block_reason']).toBe('')
        },
        { timeout: 500 },
      )
    })

    it('typed priority value overrides seeded priority in save payload', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail(TASK)

      const prioritySelect = container.querySelector('p-select[data-field="priority"]') as HTMLElement | null
      expect(prioritySelect).not.toBeNull()
      // PSelect uses onChange → React attaches a 'change' listener on the custom element
      fireEvent(prioritySelect!, new CustomEvent('change', { detail: { value: 'critical' }, bubbles: true }))

      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      fireEvent.click(saveBtn!)

      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body['priority']).toBe('critical')
          // Must not echo the seeded 'important' value
          expect(body['priority']).not.toBe(TASK.priority)
        },
        { timeout: 500 },
      )
    })

    it('typed depends_on value overrides seeded value in save payload', async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
      )
      vi.stubGlobal('fetch', fetchMock)
      const { container } = renderDetail(TASK)

      const depsInput = container.querySelector('p-input-text[data-field="depends_on"]') as HTMLElement | null
      expect(depsInput).not.toBeNull()
      // PInputText uses onInput → fire 'input' CustomEvent with detail.value
      fireEvent(depsInput!, new CustomEvent('input', { detail: { value: '10, 20' }, bubbles: true }))

      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
      fireEvent.click(saveBtn!)

      await waitFor(
        () => {
          const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
          const body = JSON.parse(options.body as string) as Record<string, unknown>
          expect(body['depends_on']).toEqual([10, 20])
        },
        { timeout: 500 },
      )
    })
  })
})
