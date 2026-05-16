/**
 * Test Cockpit task conflict resolution workflow
 *
 *
 * AC coverage:
 *   AC1: Local edits (title, priority, body, block_reason, depends_on, parent) are
 *        preserved in the form after a 409 triggers refetch + parent re-render.
 *        StatefulWrapper reproduces the useEffect reset path. (td:2 → 6 tests)
 *   AC2: Conflict modal renders identifiable remote (server) and local (user) values
 *        for differing fields via data-testid patterns: conflict-remote-{field}
 *        and conflict-local-{field}. (td:2 → 4 tests)
 *   AC3: Force-save button is NOT immediately available when the conflict modal first
 *        opens; it appears only after an explicit overwrite acknowledgment step
 *        (conflict-acknowledge). Force-save then sends the user's preserved local form
 *        values (title, priority, body, depends_on, parent, block_reason),
 *        not the server's refreshed values. (td:2 → 8 tests)
 *   AC4: Canceling/dismissing conflict resolution via the available close affordance
 *        (conflict-refresh) closes the modal and leaves the form with the user's
 *        pre-conflict local edits intact — not the server's refreshed values.
 *        (td:2 → 2 tests)
 *   AC5: Mutation errors in the conflict-resolution flow produce user-visible messages
 *        via getResponseErrorMessage(): 409→refetch→404 (task deleted between save and
 *        refresh), force-save 422, and force-save generic error. (td:2 → 3 tests)
 *   AC6: Tests fail against the current reset-then-force behavior (meta — RED gate).
 *        (td:1 — satisfied transitively by all 23 tests failing above)
 *
 * Adjacent suites (not duplicated):
 *   - DetailTab.conflict-nonregression.test.tsx: AC7 guard for action-gating survival
 *   - DetailTab_1380.test.tsx: action-side 409/404/422 paths (unclaim, move-backward)
 *   - ErrorContract.test.tsx: generic error-envelope parsing
 *
 * Harness note:
 *   AC1, AC3, AC4 use StatefulWrapper — wires onTaskUpdated → setState to reproduce
 *   the parent re-render path that triggers useEffect([task?.id, task?.updated]) reset.
 *   Rendering DetailTab standalone without re-rendering on onTaskUpdated would
 *   false-green (form never gets reset by useEffect, making "preservation" trivially true).
 */

import { beforeAll, describe, it, expect, vi, afterEach } from 'vitest'
import { useState } from 'react'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type TaskDetail } from '../components/DetailTab'
import type { Board } from '../hooks/useBoard'

// ─── PDS jsdom patch ──────────────────────────────────────────────────────────

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

/** User-authored task (before any edits). */
const BASE_TASK: TaskDetail = {
  id: 42,
  title: 'Original Title',
  status: 'todo',
  priority: 'important',
  body: 'Original body text',
  updated: '2026-05-01T10:00:00+00:00',
  created: '2026-05-01T09:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
  claimed: false,
  claimed_at: null,
  dep_status: null,
}

/**
 * Server's refreshed task returned by the GET after a 409. Different title,
 * priority, body, AND updated timestamp (useEffect key) so re-render triggers reset.
 */
const SERVER_TASK: TaskDetail = {
  ...BASE_TASK,
  title: 'Server Title (Different)',
  priority: 'critical',
  body: 'Server body (Different)',
  updated: '2026-05-01T11:00:00+00:00',
}

/** Blocked task for block_reason field tests. */
const BLOCKED_TASK: TaskDetail = {
  ...BASE_TASK,
  blocked: true,
  block_reason: 'Original block reason',
}

/** Server's refreshed blocked task — different block_reason + updated timestamp. */
const BLOCKED_SERVER_TASK: TaskDetail = {
  ...BLOCKED_TASK,
  block_reason: 'Server block reason (Different)',
  updated: '2026-05-01T11:00:00+00:00',
}

/**
 * Server task where ONLY body + updated differ from BASE_TASK (title, priority etc. unchanged).
 * Isolates the body field: useEffect fires (updated changes) but only body resets — no
 * title/priority mismatch that would keep isDirty true for unrelated reasons.
 */
const SERVER_TASK_BODY_ONLY: TaskDetail = {
  ...BASE_TASK,
  body: 'Server body (Different)',
  updated: '2026-05-01T11:00:00+00:00',
}


// ─── Stateful wrapper ─────────────────────────────────────────────────────────
//
// Reproduces the parent (Shell) re-render path:
//   onTaskUpdated(latestTask) → setState(latestTask) → DetailTab receives new task prop
//   → useEffect([task?.id, task?.updated]) fires → resets all form fields to server values
//
// Without this wrapper, tests that verify local-edit preservation would false-green:
// DetailTab standalone never re-renders its task prop, so useEffect never resets state.

interface WrapperProps {
  initialTask: TaskDetail
  board?: Board | null
  onTaskUpdated?: (task: TaskDetail) => void
  onTaskCleared?: (message?: string) => void
}

function StatefulWrapper({ initialTask, board, onTaskUpdated, onTaskCleared }: WrapperProps) {
  const [task, setTask] = useState<TaskDetail>(initialTask)
  return (
    <PorscheDesignSystemProvider>
      <DetailTab
        task={task}
        board={board}
        onTaskUpdated={(t) => {
          setTask(t)
          onTaskUpdated?.(t)
        }}
        onTaskCleared={onTaskCleared}
      />
    </PorscheDesignSystemProvider>
  )
}

function StatefulShellConflictWrapper({ initialTask }: { initialTask: TaskDetail }) {
  const [task, setTask] = useState<TaskDetail | null>(initialTask)
  const [message, setMessage] = useState<string | null>(null)

  return (
    <PorscheDesignSystemProvider>
      {task !== null ? (
        <DetailTab
          task={task}
          onTaskUpdated={(nextTask) => {
            setTask(nextTask)
            setMessage(null)
          }}
          onTaskCleared={(nextMessage) => {
            setTask(null)
            setMessage(nextMessage ?? null)
          }}
        />
      ) : null}
      {message !== null ? <div data-testid="validation-message">{message}</div> : null}
    </PorscheDesignSystemProvider>
  )
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function editTitle(container: HTMLElement, value: string): void {
  const input = container.querySelector('p-input-text[data-field="title"]') as HTMLElement | null
  expect(input).not.toBeNull()
  fireEvent(input!, new CustomEvent('change', { detail: { value }, bubbles: true }))
}

function editPriority(container: HTMLElement, value: string): void {
  const select = container.querySelector('[data-field="priority"]') as HTMLElement | null
  expect(select).not.toBeNull()
  fireEvent(select!, new CustomEvent('change', { detail: { value }, bubbles: true }))
}

function editBlockReason(container: HTMLElement, value: string): void {
  const input = container.querySelector('[data-field="block_reason"]') as HTMLElement | null
  expect(input).not.toBeNull()
  fireEvent(input!, new CustomEvent('change', { detail: { value }, bubbles: true }))
}

function editBody(container: HTMLElement, value: string): void {
  const toggle = container.querySelector('[data-testid="body-edit-toggle"]') as HTMLElement | null
  expect(toggle).not.toBeNull()
  fireEvent.click(toggle!)
  const textarea = container.querySelector('[data-field="body"]') as HTMLElement | null
  expect(textarea).not.toBeNull()
  fireEvent(textarea!, new CustomEvent('change', { detail: { value }, bubbles: true }))
}

function editDependsOn(container: HTMLElement, value: string): void {
  const input = container.querySelector('[data-field="depends_on"]') as HTMLElement | null
  expect(input).not.toBeNull()
  fireEvent(input!, new CustomEvent('change', { detail: { value }, bubbles: true }))
}

function editParent(container: HTMLElement, value: string): void {
  const input = container.querySelector('[data-field="parent"]') as HTMLElement | null
  expect(input).not.toBeNull()
  fireEvent(input!, new CustomEvent('change', { detail: { value }, bubbles: true }))
}

function getFieldValue(container: HTMLElement, selector: string): string | null {
  const el = container.querySelector(selector) as (HTMLElement & { value?: string }) | null
  if (!el) return null
  return el.value ?? el.getAttribute('value')
}

function clickSave(container: HTMLElement): void {
  const btn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
  expect(btn).not.toBeNull()
  fireEvent.click(btn!)
}

/** Fetch mock: first call → POST 409, second call → GET 200 with serverTask. */
function mockConflictThenRefetch(serverTask: TaskDetail): ReturnType<typeof vi.fn> {
  let callCount = 0
  return vi.fn(() => {
    callCount++
    if (callCount === 1) {
      return Promise.resolve({
        ok: false,
        status: 409,
        json: () => Promise.resolve({ detail: 'conflict' }),
      })
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(serverTask),
    })
  })
}

/** Fetch mock: POST 409 → GET 200 → force-save POST 200. */
function mockConflictThenForceSaveSuccess(serverTask: TaskDetail): ReturnType<typeof vi.fn> {
  let callCount = 0
  return vi.fn(() => {
    callCount++
    if (callCount === 1) {
      return Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) })
    }
    if (callCount === 2) {
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(serverTask) })
    }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(serverTask) })
  })
}

async function triggerConflictModal(container: HTMLElement): Promise<void> {
  clickSave(container)
  await waitFor(
    () => expect(container.querySelector('[data-testid="conflict-modal"]')).not.toBeNull(),
    { timeout: 500 },
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

// ---------------------------------------------------------------------------
// AC1: Local edits preserved in form after 409 refetch + parent re-render
// ---------------------------------------------------------------------------

describe('TestFromAC_ConflictLocalEditsPreserved', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('title_preserved_in_form_after_409_refetch_and_parent_rerender', async () => {
    /**
     * AC1 (happy path): User edits title → saves → 409 → refetch → parent re-renders
     * DetailTab with SERVER_TASK (different title + updated timestamp). useEffect fires
     * and RESETS title to server value — the bug. After fix, title must retain the
     * user's edited value.
     *
     * StatefulWrapper reproduces the real parent re-render path.
     * Without it: DetailTab never re-renders on onTaskUpdated → false-green.
     * Spy closes the false-green path: a builder who suppresses onTaskUpdated?.(latestTask)
     * avoids the useEffect reset but fails the spy assertion.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const onTaskUpdatedSpy = vi.fn()
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} onTaskUpdated={onTaskUpdatedSpy} />)

    editTitle(container, 'My Local Edit Title')
    await triggerConflictModal(container)

    // Spy proves onTaskUpdated was invoked with server's refreshed task (parent re-render path)
    expect(onTaskUpdatedSpy).toHaveBeenCalledWith(
      expect.objectContaining({ updated: SERVER_TASK.updated }),
    )
    // BUG: useEffect resets title to SERVER_TASK.title ('Server Title (Different)')
    // EXPECTED after fix: user's local title preserved
    expect(getFieldValue(container, 'p-input-text[data-field="title"]')).toBe('My Local Edit Title')
  })

  it('priority_preserved_in_form_after_409_refetch_and_parent_rerender', async () => {
    /**
     * AC1 (edge): Priority (distinct from title) must also be preserved after re-render.
     * User edits priority to 'someday'; SERVER_TASK.priority is 'critical'.
     * Without fix: useEffect resets to 'critical'.
     * Spy closes the false-green path: suppressing onTaskUpdated avoids useEffect reset.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const onTaskUpdatedSpy = vi.fn()
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} onTaskUpdated={onTaskUpdatedSpy} />)

    editPriority(container, 'someday')
    await triggerConflictModal(container)

    expect(onTaskUpdatedSpy).toHaveBeenCalledWith(
      expect.objectContaining({ updated: SERVER_TASK.updated }),
    )
    expect(getFieldValue(container, '[data-field="priority"]')).toBe('someday')
  })

  it('block_reason_preserved_on_blocked_task_after_409_rerender', async () => {
    /**
     * AC1 (boundary): block_reason on a blocked task must survive the useEffect reset.
     * BLOCKED_SERVER_TASK has a different block_reason + updated timestamp.
     * Without fix: useEffect resets block_reason to BLOCKED_SERVER_TASK.block_reason.
     * Spy closes the false-green path: suppressing onTaskUpdated avoids useEffect reset.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(BLOCKED_SERVER_TASK))
    const onTaskUpdatedSpy = vi.fn()
    const { container } = render(<StatefulWrapper initialTask={BLOCKED_TASK} onTaskUpdated={onTaskUpdatedSpy} />)

    editBlockReason(container, 'My local block reason')
    await triggerConflictModal(container)

    expect(onTaskUpdatedSpy).toHaveBeenCalledWith(
      expect.objectContaining({ updated: BLOCKED_SERVER_TASK.updated }),
    )
    expect(getFieldValue(container, '[data-field="block_reason"]')).toBe('My local block reason')
  })

  it('body_preserved_in_form_after_409_refetch_and_parent_rerender', async () => {
    /**
     * AC1 (edge): body field must survive the useEffect reset after parent re-render.
     *
     * Verification strategy: stencil's async DOM updates make getFieldValue unreliable
     * for p-textarea immediately after a re-render. Instead, we verify via the payload
     * of a second save attempt made after dismissing the conflict modal — if body was
     * reset, the payload carries SERVER_TASK.body, not the user's edit.
     *
     * SERVER_TASK_BODY_ONLY: only body + updated differ from BASE_TASK, so title/priority
     * don't introduce extra isDirty false-positives.
     *
     * Without fix: useEffect resets body to 'Server body (Different)' → second save
     *   sends payload.body = 'Server body (Different)' ≠ 'My Local Edit Body' → FAIL.
     * With fix: body preserved → second save sends payload.body = 'My Local Edit Body'.
     */
    let callCount = 0
    const fetchMock = vi.fn(() => {
      callCount++
      if (callCount === 1) {
        // Initial save → 409
        return Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) })
      }
      if (callCount === 2) {
        // Refetch GET → 200 with server task (only body differs)
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(SERVER_TASK_BODY_ONLY) })
      }
      // Third call: second save attempt (after user dismisses conflict modal)
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(SERVER_TASK_BODY_ONLY) })
    })
    const onTaskUpdatedSpy = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} onTaskUpdated={onTaskUpdatedSpy} />)

    editBody(container, 'My Local Edit Body')
    await triggerConflictModal(container)

    // Spy proves onTaskUpdated was invoked with server's refreshed task (parent re-render path)
    expect(onTaskUpdatedSpy).toHaveBeenCalledWith(
      expect.objectContaining({ updated: SERVER_TASK_BODY_ONLY.updated }),
    )

    // Dismiss via the available conflict modal affordance
    const dismissBtn = container.querySelector('[data-testid="conflict-refresh"]') as HTMLElement | null
    expect(dismissBtn).not.toBeNull()
    fireEvent.click(dismissBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-modal"]')).toBeNull(),
      { timeout: 500 },
    )

    // Second save — without fix, body state was reset to SERVER_TASK_BODY_ONLY.body
    clickSave(container)
    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledTimes(3)
        const [, opts] = fetchMock.mock.calls[2] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        // BUG: without fix, payload.body = 'Server body (Different)' (reset by useEffect)
        expect(payload.body).toBe('My Local Edit Body')
      },
      { timeout: 500 },
    )
  })

  it('depends_on_preserved_in_form_after_409_refetch_and_parent_rerender', async () => {
    /**
     * AC1 (edge): depends_on must survive the useEffect reset.
     * User sets depends_on to '1, 2'; SERVER_TASK.depends_on is [] → resets to ''.
     * Without fix: useEffect resets dependsOn to ''.
     * Spy closes the false-green path: suppressing onTaskUpdated avoids useEffect reset.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const onTaskUpdatedSpy = vi.fn()
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} onTaskUpdated={onTaskUpdatedSpy} />)

    editDependsOn(container, '1, 2')
    await triggerConflictModal(container)

    expect(onTaskUpdatedSpy).toHaveBeenCalledWith(
      expect.objectContaining({ updated: SERVER_TASK.updated }),
    )
    // BUG: useEffect resets depends_on to '' (SERVER_TASK.depends_on = [])
    expect(getFieldValue(container, 'p-input-text[data-field="depends_on"]')).toBe('1, 2')
  })

  it('parent_preserved_in_form_after_409_refetch_and_parent_rerender', async () => {
    /**
     * AC1 (edge): parent must survive the useEffect reset.
     * User sets parent to '7'; SERVER_TASK.parent is null → resets to ''.
     * Without fix: useEffect resets parent to ''.
     * Spy closes the false-green path: suppressing onTaskUpdated avoids useEffect reset.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const onTaskUpdatedSpy = vi.fn()
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} onTaskUpdated={onTaskUpdatedSpy} />)

    editParent(container, '7')
    await triggerConflictModal(container)

    expect(onTaskUpdatedSpy).toHaveBeenCalledWith(
      expect.objectContaining({ updated: SERVER_TASK.updated }),
    )
    // BUG: useEffect resets parent to '' (SERVER_TASK.parent = null → '')
    expect(getFieldValue(container, 'p-input-text[data-field="parent"]')).toBe('7')
  })

  it('title_preserved_in_form_after_409_refetch_with_delayed_async_gap', async () => {
    /**
     * AC1 (async-gap): The conflict draft must survive intermediate renders during the
     * async refetch window. Uses a deferred (non-immediately-resolving) GET promise to
     * expose the race between setConflictLocalDraft (fired before await) and
     * setConflictRemoteTask (fired after await).
     *
     * Race mechanism (current bug):
     *   1. POST → 409 → setConflictLocalDraft(draft) called synchronously before await.
     *   2. await fetch(GET) suspends the async function; event loop gets a chance to run.
     *   3. React flushes pending state: conflictLocalDraft=set, conflictRemoteTask=null.
     *   4. useEffect fires: guard (task && conflictLocalDraft && conflictRemoteTask?.id===task.id)
     *      fails because conflictRemoteTask is null → falls through to reset path.
     *   5. Reset path calls setConflictLocalDraft(null) — user draft is lost.
     *   6. Later: deferred GET resolves → setConflictRemoteTask → re-render.
     *   7. useEffect fires again: now conflictLocalDraft=null → guard fails again → draft gone.
     *
     * EXPECTED after fix: setConflictLocalDraft is moved to batch with setConflictRemoteTask
     * in a single synchronous block after GET resolves — no intermediate render, guard passes.
     *
     * This test closes the false-green path of the existing AC1 tests, which all use
     * Promise.resolve() (zero-latency refetch). With zero latency, React 18 batches
     * setConflictLocalDraft and setConflictRemoteTask together before the first render,
     * so the guard passes trivially — the race is never exercised.
     */
    let resolveRefetch!: (value: unknown) => void
    let callCount = 0

    vi.stubGlobal(
      'fetch',
      vi.fn(() => {
        callCount++
        if (callCount === 1) {
          // POST save → 409 conflict
          return Promise.resolve({
            ok: false,
            status: 409,
            json: () => Promise.resolve({ detail: 'conflict' }),
          })
        }
        // GET refetch → deferred; resolveRefetch must be called manually to unblock
        return new Promise(r => {
          resolveRefetch = r
        })
      }),
    )

    const onTaskUpdatedSpy = vi.fn()
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} onTaskUpdated={onTaskUpdatedSpy} />)

    editTitle(container, 'My Local Edit Title')
    clickSave(container)

    // Wait until the GET refetch is initiated (POST 409 has been processed)
    await waitFor(() => expect(callCount).toBeGreaterThanOrEqual(2), { timeout: 500 })

    // Yield to the macrotask queue so React can flush the intermediate state render:
    // conflictLocalDraft is set, conflictRemoteTask is still null at this point.
    await new Promise<void>(r => setTimeout(r, 0))

    // Resolve the deferred GET with the server task
    resolveRefetch({
      ok: true,
      status: 200,
      json: () => Promise.resolve(SERVER_TASK),
    })

    // Wait for the conflict modal to appear (proof that GET resolved and setConflictRemoteTask fired)
    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-modal"]')).not.toBeNull(),
      { timeout: 500 },
    )

    expect(onTaskUpdatedSpy).toHaveBeenCalledWith(
      expect.objectContaining({ updated: SERVER_TASK.updated }),
    )

    // BUG: during the async gap, useEffect reset clears the draft → title resets to BASE_TASK.title
    // EXPECTED after fix: draft survives because setConflictLocalDraft is batched with
    // setConflictRemoteTask in a single synchronous block after GET resolves.
    expect(getFieldValue(container, 'p-input-text[data-field="title"]')).toBe('My Local Edit Title')
  })
})

// ---------------------------------------------------------------------------
// AC2: Conflict modal shows identifiable remote (server) and local (user) values
// ---------------------------------------------------------------------------

describe('TestFromAC_ConflictModalComparison', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('conflict_modal_renders_server_remote_title_with_conflict_remote_testid', async () => {
    /**
     * AC2 (happy path): The conflict modal must include an element with
     * data-testid="conflict-remote-title" showing the server's title.
     * Current: conflict modal has no remote/local comparison elements — FAIL.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editTitle(container, 'My Local Edit Title')
    await triggerConflictModal(container)

    const remoteEl = container.querySelector('[data-testid="conflict-remote-title"]')
    expect(remoteEl).not.toBeNull()
    expect(remoteEl!.textContent).toContain('Server Title (Different)')
  })

  it('conflict_modal_renders_user_local_title_with_conflict_local_testid', async () => {
    /**
     * AC2 (happy path): The conflict modal must include an element with
     * data-testid="conflict-local-title" showing the user's pending local title.
     * Current: no such element — FAIL.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editTitle(container, 'My Local Edit Title')
    await triggerConflictModal(container)

    const localEl = container.querySelector('[data-testid="conflict-local-title"]')
    expect(localEl).not.toBeNull()
    expect(localEl!.textContent).toContain('My Local Edit Title')
  })

  it('conflict_modal_renders_server_remote_priority_with_conflict_remote_testid', async () => {
    /**
     * AC2 (edge — different field): Priority field also gets remote/local comparison.
     * User edits priority to 'someday'; server's priority is 'critical'.
     * conflict-remote-priority must display 'critical'.
     * Current: no such element — FAIL.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editPriority(container, 'someday')
    await triggerConflictModal(container)

    const remoteEl = container.querySelector('[data-testid="conflict-remote-priority"]')
    expect(remoteEl).not.toBeNull()
    expect(remoteEl!.textContent).toContain('critical')
  })

  it('conflict_modal_renders_user_local_priority_with_conflict_local_testid', async () => {
    /**
     * AC2 (edge — different field): The conflict modal must include an element with
     * data-testid="conflict-local-priority" showing the user's pending local priority.
     * User edits priority to 'someday'; after fix, conflict-local-priority must show
     * 'someday' (not 'critical' which is the server's/reset value).
     * Current: no such element — FAIL.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editPriority(container, 'someday')
    await triggerConflictModal(container)

    const localEl = container.querySelector('[data-testid="conflict-local-priority"]')
    expect(localEl).not.toBeNull()
    expect(localEl!.textContent).toContain('someday')
  })
})

// ---------------------------------------------------------------------------
// AC3: Force-save requires explicit acknowledgment step; sends user's local values
// ---------------------------------------------------------------------------

describe('TestFromAC_ForceSaveAcknowledgmentGate', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('force_save_button_absent_when_conflict_modal_first_opens', async () => {
    /**
     * AC3 (happy path): conflict-overwrite must NOT be in the DOM when the conflict
     * modal first appears. An explicit acknowledgment step is required first.
     * Current: conflict-overwrite renders immediately — FAIL.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editTitle(container, 'My Local Edit Title')
    await triggerConflictModal(container)

    expect(container.querySelector('[data-testid="conflict-overwrite"]')).toBeNull()
  })

  it('force_save_button_appears_after_conflict_acknowledge_clicked', async () => {
    /**
     * AC3 (happy path): After the user clicks conflict-acknowledge, the force-save
     * button (conflict-overwrite) must become visible.
     * Current: conflict-acknowledge element does not exist — FAIL.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editTitle(container, 'My Local Edit Title')
    await triggerConflictModal(container)

    const ackEl = container.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
    expect(ackEl).not.toBeNull()
    fireEvent.click(ackEl!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-overwrite"]')).not.toBeNull(),
      { timeout: 500 },
    )
  })

  it('force_save_sends_user_local_title_not_server_refreshed_title', async () => {
    /**
     * AC3 (happy path — payload check): Force-save request payload must carry the
     * user's edited title ('My Local Edit Title'), not SERVER_TASK.title
     * ('Server Title (Different)').
     *
     * Current behavior:
     *   1. 409 → useEffect resets title to SERVER_TASK.title
     *   2. force-save reads reset title → sends 'Server Title (Different)'  ← BUG
     *
     * After fix: local edits preserved; force-save sends 'My Local Edit Title'.
     * Test also fails earlier on missing conflict-acknowledge element.
     */
    const fetchMock = mockConflictThenForceSaveSuccess(SERVER_TASK)
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editTitle(container, 'My Local Edit Title')
    await triggerConflictModal(container)

    const ackEl = container.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
    expect(ackEl).not.toBeNull()
    fireEvent.click(ackEl!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-overwrite"]')).not.toBeNull(),
      { timeout: 500 },
    )
    fireEvent.click(container.querySelector('[data-testid="conflict-overwrite"]') as HTMLElement)

    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledTimes(3)
        const [, opts] = fetchMock.mock.calls[2] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload.title).toBe('My Local Edit Title')
      },
      { timeout: 500 },
    )
  })

  it('force_save_sends_user_local_priority_not_server_refreshed_priority', async () => {
    /**
     * AC3 (edge — different field): Force-save payload carries user's priority
     * ('someday'), not SERVER_TASK.priority ('critical').
     * Test also fails on missing conflict-acknowledge element.
     */
    const fetchMock = mockConflictThenForceSaveSuccess(SERVER_TASK)
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editPriority(container, 'someday')
    await triggerConflictModal(container)

    const ackEl = container.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
    expect(ackEl).not.toBeNull()
    fireEvent.click(ackEl!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-overwrite"]')).not.toBeNull(),
      { timeout: 500 },
    )
    fireEvent.click(container.querySelector('[data-testid="conflict-overwrite"]') as HTMLElement)

    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledTimes(3)
        const [, opts] = fetchMock.mock.calls[2] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload.priority).toBe('someday')
      },
      { timeout: 500 },
    )
  })

  it('force_save_sends_user_local_body_not_server_refreshed_body', async () => {
    /**
     * AC3 (edge — body): Force-save payload carries user's edited body,
     * not SERVER_TASK.body ('Server body (Different)').
     * Test also fails on missing conflict-acknowledge element.
     */
    const fetchMock = mockConflictThenForceSaveSuccess(SERVER_TASK)
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editBody(container, 'My Local Edit Body')
    await triggerConflictModal(container)

    const ackEl = container.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
    expect(ackEl).not.toBeNull()
    fireEvent.click(ackEl!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-overwrite"]')).not.toBeNull(),
      { timeout: 500 },
    )
    fireEvent.click(container.querySelector('[data-testid="conflict-overwrite"]') as HTMLElement)

    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledTimes(3)
        const [, opts] = fetchMock.mock.calls[2] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload.body).toBe('My Local Edit Body')
      },
      { timeout: 500 },
    )
  })

  it('force_save_sends_user_local_depends_on_not_server_refreshed_depends_on', async () => {
    /**
     * AC3 (edge — depends_on): Force-save payload carries user's depends_on ([10, 20]),
     * not SERVER_TASK.depends_on ([] → []).
     * Test also fails on missing conflict-acknowledge element.
     */
    const fetchMock = mockConflictThenForceSaveSuccess(SERVER_TASK)
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editDependsOn(container, '10, 20')
    await triggerConflictModal(container)

    const ackEl = container.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
    expect(ackEl).not.toBeNull()
    fireEvent.click(ackEl!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-overwrite"]')).not.toBeNull(),
      { timeout: 500 },
    )
    fireEvent.click(container.querySelector('[data-testid="conflict-overwrite"]') as HTMLElement)

    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledTimes(3)
        const [, opts] = fetchMock.mock.calls[2] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload.depends_on).toEqual([10, 20])
      },
      { timeout: 500 },
    )
  })

  it('force_save_sends_user_local_parent_not_server_refreshed_parent', async () => {
    /**
     * AC3 (edge — parent): Force-save payload carries user's parent (7),
     * not SERVER_TASK.parent (null → null).
     * Test also fails on missing conflict-acknowledge element.
     */
    const fetchMock = mockConflictThenForceSaveSuccess(SERVER_TASK)
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editParent(container, '7')
    await triggerConflictModal(container)

    const ackEl = container.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
    expect(ackEl).not.toBeNull()
    fireEvent.click(ackEl!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-overwrite"]')).not.toBeNull(),
      { timeout: 500 },
    )
    fireEvent.click(container.querySelector('[data-testid="conflict-overwrite"]') as HTMLElement)

    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledTimes(3)
        const [, opts] = fetchMock.mock.calls[2] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload.parent).toBe(7)
      },
      { timeout: 500 },
    )
  })

  it('force_save_sends_user_local_block_reason_not_server_refreshed_block_reason', async () => {
    /**
     * AC3 (edge — block_reason): On a blocked task, force-save payload carries user's
     * edited block_reason ('My local block reason'), not BLOCKED_SERVER_TASK.block_reason
     * ('Server block reason (Different)').
     * Test also fails on missing conflict-acknowledge element.
     */
    const fetchMock = mockConflictThenForceSaveSuccess(BLOCKED_SERVER_TASK)
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(<StatefulWrapper initialTask={BLOCKED_TASK} />)

    editBlockReason(container, 'My local block reason')
    await triggerConflictModal(container)

    const ackEl = container.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
    expect(ackEl).not.toBeNull()
    fireEvent.click(ackEl!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-overwrite"]')).not.toBeNull(),
      { timeout: 500 },
    )
    fireEvent.click(container.querySelector('[data-testid="conflict-overwrite"]') as HTMLElement)

    await waitFor(
      () => {
        expect(fetchMock).toHaveBeenCalledTimes(3)
        const [, opts] = fetchMock.mock.calls[2] as [string, RequestInit]
        const payload = JSON.parse(opts.body as string) as Record<string, unknown>
        expect(payload.block_reason).toBe('My local block reason')
      },
      { timeout: 500 },
    )
  })
})

// ---------------------------------------------------------------------------
// AC4: Canceling/dismissing conflict modal preserves user's local edits
// ---------------------------------------------------------------------------

describe('TestFromAC_ConflictCancelPreservesEdits', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('conflict_dismiss_closes_modal_and_preserves_user_local_title', async () => {
    /**
     * AC4 (happy path): The available close affordance (conflict-refresh) must close
     * the modal without discarding the user's pending local edits. After dismiss, title
     * must still show the user's value, not the server's.
     *
     * Current failure: useEffect already reset the form to SERVER_TASK.title when
     * onTaskUpdated fired after 409 refetch — form shows server value regardless of
     * which button closes the modal.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editTitle(container, 'My Local Edit Title')
    await triggerConflictModal(container)

    const dismissBtn = container.querySelector('[data-testid="conflict-refresh"]') as HTMLElement | null
    expect(dismissBtn).not.toBeNull()
    fireEvent.click(dismissBtn!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-modal"]')).toBeNull(),
      { timeout: 500 },
    )

    // EXPECTED after fix: user's local title preserved in form
    expect(getFieldValue(container, 'p-input-text[data-field="title"]')).toBe('My Local Edit Title')
  })

  it('conflict_dismiss_preserves_user_local_priority', async () => {
    /**
     * AC4 (edge — different field): Dismissing via the available close affordance
     * (conflict-refresh) must also preserve user's edited priority.
     * Current failure: useEffect already reset priority to SERVER_TASK.priority
     * ('critical') — form shows server value after modal closes.
     */
    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editPriority(container, 'someday')
    await triggerConflictModal(container)

    const dismissBtn = container.querySelector('[data-testid="conflict-refresh"]') as HTMLElement | null
    expect(dismissBtn).not.toBeNull()
    fireEvent.click(dismissBtn!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-modal"]')).toBeNull(),
      { timeout: 500 },
    )

    expect(getFieldValue(container, '[data-field="priority"]')).toBe('someday')
  })
})

// ---------------------------------------------------------------------------
// AC5: Error contract for conflict-resolution flow
// ---------------------------------------------------------------------------

describe('TestFromAC_ConflictErrorContract', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('save_409_then_refetch_404_shows_user_visible_error_message', async () => {
    /**
     * AC5 (error path — 409→refetch→404): When the initial save returns 409 and the
     * follow-up refetch returns 404 (task deleted between save and refresh), a
     * user-visible error message must appear via getResponseErrorMessage().
     *
     * Current: runMutation calls onTaskCleared?.() silently and sets showConflict=true,
     * but no validation-message element is set → FAIL.
     */
    let callCount = 0
    vi.stubGlobal(
      'fetch',
      vi.fn(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) })
        }
        // Refetch GET → 404 (task deleted)
        return Promise.resolve({
          ok: false,
          status: 404,
          json: () => Promise.resolve({ detail: 'No such task: 42' }),
        })
      }),
    )

    const { container } = render(<StatefulShellConflictWrapper initialTask={BASE_TASK} />)

    clickSave(container)

    await waitFor(
      () => expect(container.querySelector('[data-testid="validation-message"]')).not.toBeNull(),
      { timeout: 500 },
    )
    // Discriminating proof: getResponseErrorMessage extracts {detail} from 404 response body
    // (distinct from fallback 'Task not found' so test fails if helper extraction regresses)
    expect(container.querySelector('[data-testid="validation-message"]')!.textContent).toContain('No such task: 42')
  })

  it('force_save_422_shows_server_detail_in_validation_message', async () => {
    /**
     * AC5 (error path — force-save 422): After acknowledging the conflict and clicking
     * force-save, a 422 response must surface the server's detail message via
     * getResponseErrorMessage(). Test uses StatefulWrapper for the re-render path.
     *
     * Primary failure: conflict-acknowledge element does not exist → FAIL immediately.
     * Secondary failure (after ack is added): force-save 422 detail must be displayed.
     */
    let callCount = 0
    vi.stubGlobal(
      'fetch',
      vi.fn(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) })
        }
        if (callCount === 2) {
          return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(SERVER_TASK) })
        }
        // Force-save → 422
        return Promise.resolve({
          ok: false,
          status: 422,
          json: () => Promise.resolve({ detail: 'Conflict: field changed again by another agent' }),
        })
      }),
    )

    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editTitle(container, 'My Local Edit Title')
    await triggerConflictModal(container)

    const ackEl = container.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
    expect(ackEl).not.toBeNull()
    fireEvent.click(ackEl!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-overwrite"]')).not.toBeNull(),
      { timeout: 500 },
    )
    fireEvent.click(container.querySelector('[data-testid="conflict-overwrite"]') as HTMLElement)

    await waitFor(
      () => {
        const msg = container.querySelector('[data-testid="validation-message"]')
        expect(msg).not.toBeNull()
        expect(msg!.textContent).toContain('Conflict: field changed again by another agent')
      },
      { timeout: 500 },
    )
  })

  it('force_save_generic_error_shows_fallback_message_in_validation', async () => {
    /**
     * AC5 (error path — force-save generic 500): An unexpected server error on
     * force-save must display a fallback error message (getResponseErrorMessage fallback)
     * in validation-message — not silently swallow the error.
     *
     * Primary failure: conflict-acknowledge element does not exist → FAIL immediately.
     */
    let callCount = 0
    vi.stubGlobal(
      'fetch',
      vi.fn(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({}) })
        }
        if (callCount === 2) {
          return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(SERVER_TASK) })
        }
        // Force-save → generic 500 with no parseable body
        return Promise.resolve({
          ok: false,
          status: 500,
          json: () => Promise.reject(new Error('no body')),
        })
      }),
    )

    const { container } = render(<StatefulWrapper initialTask={BASE_TASK} />)

    editTitle(container, 'My Local Edit Title')
    await triggerConflictModal(container)

    const ackEl = container.querySelector('[data-testid="conflict-acknowledge"]') as HTMLElement | null
    expect(ackEl).not.toBeNull()
    fireEvent.click(ackEl!)

    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-overwrite"]')).not.toBeNull(),
      { timeout: 500 },
    )
    fireEvent.click(container.querySelector('[data-testid="conflict-overwrite"]') as HTMLElement)

    await waitFor(
      () => {
        const msg = container.querySelector('[data-testid="validation-message"]')
        expect(msg).not.toBeNull()
        // Exact fallback from getResponseErrorMessage when JSON parse fails
        expect(msg!.textContent).toContain('Request failed with status 500')
      },
      { timeout: 500 },
    )
  })
})

// ---------------------------------------------------------------------------
// AC6: ConflictBanner disappears when the active task switches to a different id
// ---------------------------------------------------------------------------

describe('TestFromAC_ConflictBannerTaskSwitch', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('conflict_banner_disappears_when_active_task_switches_to_different_id', async () => {
    /**
     * AC6 (smoke — task-switch cleanup): When a conflict is active for task A
     * (conflict-modal visible), switching the active task to task B (different id)
     * must clear the conflict banner (conflict-modal absent from DOM).
     *
     * Implementation path: TaskFieldsEditor useEffect fires on task.id change →
     * calls clearConflictIfTaskChanged(taskB.id) → hook detects id mismatch vs
     * conflictRemoteTask.id → clears showConflict → ConflictBanner returns null.
     *
     * Verifies the fix in useConflictDraft.ts that was missing in the first builder
     * attempt (clearConflictIfTaskChanged left showConflict true).
     */
    const TASK_B: TaskDetail = {
      ...BASE_TASK,
      id: 99,
      title: 'Task B Title',
      updated: '2026-05-01T12:00:00+00:00',
    }

    function TaskSwitchWrapper() {
      const [task, setTask] = useState<TaskDetail>(BASE_TASK)
      return (
        <PorscheDesignSystemProvider>
          <button data-testid="switch-task" onClick={() => setTask(TASK_B)} />
          <DetailTab
            task={task}
            onTaskUpdated={(t) => setTask(t)}
          />
        </PorscheDesignSystemProvider>
      )
    }

    vi.stubGlobal('fetch', mockConflictThenRefetch(SERVER_TASK))
    const { container } = render(<TaskSwitchWrapper />)

    editTitle(container, 'My Local Edit')
    await triggerConflictModal(container)

    // Precondition: banner is visible for task A
    expect(container.querySelector('[data-testid="conflict-modal"]')).not.toBeNull()

    // Switch to task B (different id) — simulates Shell selecting a new task
    fireEvent.click(container.querySelector('[data-testid="switch-task"]') as HTMLElement)

    // AC6: banner must disappear after task switch
    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-modal"]')).toBeNull(),
      { timeout: 500 },
    )
  })
})
