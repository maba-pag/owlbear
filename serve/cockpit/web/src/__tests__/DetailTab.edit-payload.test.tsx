/**
 * Fix Cockpit detail edit workflow contract
 *
 *
 * AC coverage:
 *   AC4: DetailTab controlled inputs; save payload includes depends_on, parent,
 *        and block_reason with correct types (list[int], int|null, str|null).
 *   AC5: Action confirmations call correct endpoints — unblock → POST /edit with
 *        block_reason: null; unclaim → POST /release; move-backward → POST /move
 *        with previous-pipeline-status target. All handle 409 and 422 responses.
 *   AC6: Successful save invokes onTaskUpdated(responseTask) callback.
 *
 * Current bugs (audit evidence):
 *   - handleSave() only sends {updated, title, priority, body} — missing
 *     depends_on, parent, block_reason.
 *   - ConfirmDialog.onConfirm() only calls setConfirmType(null) — no API call.
 *   - onTaskUpdated prop is not destructured from DetailTabProps — never called.
 */

import { beforeAll, describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type TaskDetail } from '../components/DetailTab'
import type { Board } from '../hooks/useBoard'

// ─── PDS jsdom patch ─────────────────────────────────────────────────────────

beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'in-progress',
  priority: 'important',
  body: '## Objectives\n\n- item one',
  updated: '2026-04-18T10:00:00+00:00',
  created: '2026-04-17T09:00:00+00:00',
  tags: ['bug'],
  blocked: false,
  block_reason: null,
  claimed: true,
  claimed_at: '2026-04-18T09:30:00+00:00',
  dep_status: null,
  parent: null,
  depends_on: [],
  proof_bundle: null,
}

const TASK_WITH_DEPS: TaskDetail = {
  ...TASK,
  depends_on: [10, 20],
  parent: 5,
}

const TASK_BLOCKED: TaskDetail = {
  ...TASK,
  blocked: true,
  block_reason: 'Waiting for dependency #100',
}

const TASK_RESEARCH: TaskDetail = {
  ...TASK,
  status: 'research',
  claimed: false,
  claimed_at: null,
}

/** Board fixture matching the default pipeline status order. */
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

// ─── Render helpers ───────────────────────────────────────────────────────────

// Provide references covering dep/parent IDs to avoid resolution hook fetching
const TASK_REFERENCES = [
  { id: 5, title: 'Parent', status: 'done', archival_reason: null },
  { id: 10, title: 'Dep 1', status: 'done', archival_reason: null },
  { id: 20, title: 'Dep 2', status: 'done', archival_reason: null },
]

function renderDetail(task: TaskDetail = TASK) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} taskReferences={TASK_REFERENCES} />
    </PorscheDesignSystemProvider>,
  )
}

/**
 * Render DetailTab with a board prop.
 *
 * The `board` prop does not exist on DetailTabProps yet — the builder adds it.
 * @ts-expect-error is intentional; it will be removed once the prop is added.
 */
function renderDetailWithBoard(task: TaskDetail = TASK, board: Board | null = BOARD) {
  return render(
    <PorscheDesignSystemProvider>
      {/* @ts-expect-error board prop will be added by builder in GREEN phase */}
      <DetailTab task={task} board={board} taskReferences={TASK_REFERENCES} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Click the Confirm button inside an open ConfirmDialog. */
function clickConfirm(container: HTMLElement): void {
  const btns = container.querySelectorAll('[data-testid="confirm-dialog"] p-button')
  const confirmBtn = btns[btns.length - 1] as HTMLElement | null
  expect(confirmBtn).not.toBeNull()
  fireEvent.click(confirmBtn!)
}

function openEditor(container: HTMLElement): void {
  const editButton = container.querySelector('[data-testid="edit-details-button"]') as HTMLElement | null
  expect(editButton).not.toBeNull()
  fireEvent.click(editButton!)
}

function typeIntoField(container: HTMLElement, selector: string, value: string): void {
  const field = container.querySelector(selector) as HTMLElement | null
  expect(field).not.toBeNull()
  fireEvent(field!, new CustomEvent('input', { detail: { value }, bubbles: true }))
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

// ─── Tests ────────────────────────────────────────────────────────────────────

// ---------------------------------------------------------------------------
// AC4: controlled inputs + correct typed save payload
// ---------------------------------------------------------------------------

describe('TestFromAC_DetailTabEditPayload', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('save payload includes depends_on as an array of integers', async () => {
    /**
     * AC4: save sends depends_on with correct type (list[int]).
     *
     * Current bug: handleSave() only sends {updated, title, priority, body} —
     * depends_on is not included.
     */
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(TASK_WITH_DEPS) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail(TASK_WITH_DEPS)
    openEditor(container)

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => {
        const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
        const body = JSON.parse(options.body as string) as Record<string, unknown>
        expect(body).toHaveProperty('updated', TASK_WITH_DEPS.updated)
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

  it('save payload includes parent as an integer when task has a parent', async () => {
    /**
     * AC4: save sends parent with correct type (int), not as a string.
     *
     * Current bug: handleSave() does not include parent in the request body.
     */
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(TASK_WITH_DEPS) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail(TASK_WITH_DEPS)
    openEditor(container)

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
    /**
     * AC4: save sends parent: null (int|null) when task.parent is null.
     * Omitting the field entirely is not equivalent — backend treats omit as
     * "no change" while null signals "clear parent".
     *
     * Current bug: parent field is absent from handleSave() payload.
     */
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail(TASK)
    openEditor(container)

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

  it('save payload includes block_reason when task is blocked', async () => {
    /**
     * AC4: save sends block_reason for blocked tasks.
     *
     * Current bug: handleSave() does not include block_reason.
     */
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(TASK_BLOCKED) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail(TASK_BLOCKED)
    openEditor(container)

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => {
        const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
        const body = JSON.parse(options.body as string) as Record<string, unknown>
        expect(body).toHaveProperty('block_reason')
        expect(body['block_reason']).toBe('Waiting for dependency #100')
      },
      { timeout: 500 },
    )
  })

  it('saves live title, priority, body, tags, and cleared block reason values', async () => {
    const updatedTask: TaskDetail = {
      ...TASK_BLOCKED,
      title: 'User-Typed Title',
      priority: 'critical',
      body: 'edited body content',
      tags: ['scope:cockpit'],
      block_reason: '',
    }
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(updatedTask) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail(TASK_BLOCKED)
    openEditor(container)

    typeIntoField(container, 'p-input-text[data-field="title"]', updatedTask.title)
    fireEvent(
      container.querySelector('p-select[data-field="priority"]')!,
      new CustomEvent('change', { detail: { value: updatedTask.priority }, bubbles: true }),
    )
    fireEvent.click(container.querySelector('[data-testid="body-edit-toggle"]')!)
    typeIntoField(container, 'p-textarea[data-field="body"]', updatedTask.body ?? '')
    fireEvent.click(container.querySelector('p-tag-dismissible[data-tag="bug"]')!)
    typeIntoField(container, 'p-input-text[data-field="new-tag"]', 'scope:cockpit')
    fireEvent.click(container.querySelector('[data-testid="add-tag-button"]')!)
    typeIntoField(container, 'p-input-text[data-field="block_reason"]', '')
    fireEvent.click(container.querySelector('[data-testid="save-button"]')!)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 500 })
    const [, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    const body = JSON.parse(options.body as string) as Record<string, unknown>
    expect(body).toMatchObject({
      title: updatedTask.title,
      priority: updatedTask.priority,
      body: updatedTask.body,
      tags: updatedTask.tags,
      block_reason: '',
    })
  })
})

// ---------------------------------------------------------------------------
// AC5: action confirmations call the correct endpoints
// ---------------------------------------------------------------------------

describe('TestFromAC_DetailTabActions', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('unblock confirmation POSTs to edit endpoint with block_reason: null', async () => {
    /**
     * AC5: unblock → POST /api/tasks/{id}/edit with block_reason: null.
     *
     * Current bug: ConfirmDialog.onConfirm only calls setConfirmType(null) —
     * no API call is made.
     */
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
    expect(container.querySelector('[data-testid="confirm-dialog"]')?.textContent).toContain(
      TASK_BLOCKED.block_reason,
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
    /**
     * AC5: unclaim → POST /api/tasks/{id}/release.
     *
     * Current bug: ConfirmDialog.onConfirm only calls setConfirmType(null) —
     * no API call is made.
     */
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

  it('move menu POSTs to the move endpoint', async () => {
    /**
     * AC5: move-backward → POST /api/tasks/{id}/move.
     *
     * Current bug: ConfirmDialog.onConfirm only calls setConfirmType(null) —
     * no API call is made.
     */
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetailWithBoard(TASK)

    await clickMoveTarget(container, 'todo')

    await waitFor(
      () => {
        const moveCalls = fetchMock.mock.calls.filter(([url]) =>
          (url as string).includes(`/api/tasks/${TASK.id}/move`),
        )
        expect(moveCalls.length).toBeGreaterThan(0)
      },
      { timeout: 500 },
    )
  })

  it('move menu sends the selected pipeline status in the request body', async () => {
    /**
     * AC5: target status derived from pipeline-order (previous status from
     * valid_transitions or board status list).
     *
     * TASK.status = 'in-progress' (index 3 in BOARD.statuses).
     * Previous status = 'todo' (index 2).
     *
     * Current bug: no API call on confirm → never sends move request.
     */
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve(TASK) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetailWithBoard(TASK, BOARD)

    await clickMoveTarget(container, 'todo')

    await waitFor(
      () => {
        const moveCalls = fetchMock.mock.calls.filter(([url]) =>
          (url as string).includes(`/api/tasks/${TASK.id}/move`),
        )
        expect(moveCalls.length).toBeGreaterThan(0)
        const [, options] = moveCalls[0] as unknown as [string, RequestInit]
        const body = JSON.parse(options.body as string) as Record<string, unknown>
        // 'in-progress' previous status in BOARD.statuses order is 'todo'
        expect(body).toHaveProperty('status', 'todo')
      },
      { timeout: 500 },
    )
  })

  it('offers the configured forward move for a research task', async () => {
    const { container } = renderDetailWithBoard(TASK_RESEARCH, BOARD)

    const moveTrigger = container.querySelector('[data-testid="task-detail-move-menu-trigger"]') as HTMLElement | null
    expect(moveTrigger).not.toBeNull()
    fireEvent.click(moveTrigger!)

    expect(container.querySelector('[data-testid="task-detail-move-target"][data-status="backlog"]')).not.toBeNull()
  })

  it('opens the archival flow for an active unclaimed task', () => {
    const { container } = renderDetailWithBoard(TASK_RESEARCH, BOARD)

    fireEvent.click(container.querySelector('[data-testid="task-detail-archive-action"]')!)

    expect(container.querySelector('[data-testid="archival-modal"]')).not.toBeNull()
  })

  it('409 from action confirmation shows a conflict indicator', async () => {
    /**
     * AC5: actions handle 409 (refetch + show conflict).
     *
     * Current bug: no API call is made → 409 is never returned →
     * conflict modal never appears.
     */
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({ detail: 'stale' }) }),
      ),
    )
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
        expect(container.querySelector('[data-testid="conflict-modal"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
  })

  it('422 from action confirmation shows a validation message', async () => {
    /**
     * AC5: actions handle 422 (show validation message).
     *
     * Current bug: no API call is made → 422 is never returned →
     * validation message never shown.
     */
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 422,
          json: () => Promise.resolve({ detail: 'invalid value' }),
        }),
      ),
    )
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
        expect(container.querySelector('[data-testid="validation-message"]')).not.toBeNull()
      },
      { timeout: 500 },
    )
  })
})

// ---------------------------------------------------------------------------
// AC6 (td:1): Successful save invokes onTaskUpdated callback
// ---------------------------------------------------------------------------

describe('TestFromAC_DetailTabTaskUpdated', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('successful save calls onTaskUpdated with the response task', async () => {
    /**
     * AC6 (td:1): DetailTab calls onTaskUpdated(responseTask) callback on success.
     *
     * Current bug: onTaskUpdated is declared in DetailTabProps but not destructured
     * from the component's props — the callback is never invoked.
     */
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
    openEditor(container)

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

  it('calls onTaskCleared when save returns 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 404,
          json: () => Promise.resolve({ detail: 'not found' }),
        }),
      ),
    )
    const onTaskCleared = vi.fn()
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={TASK} onTaskCleared={onTaskCleared} />
      </PorscheDesignSystemProvider>,
    )
    openEditor(container)

    fireEvent.click(container.querySelector('[data-testid="save-button"]')!)

    await waitFor(() => expect(onTaskCleared).toHaveBeenCalledOnce(), { timeout: 500 })
  })
})
