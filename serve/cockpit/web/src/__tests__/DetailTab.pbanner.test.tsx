/**
 * DetailTab mutation callback wiring (task #1498)
 *
 * Covers:
 *   AC-3 — DetailTab runMutation calls onMutationError(heading, description, state) on
 *           non-409 failures: state='warning' for 422, state='error' for 5xx/network;
 *           heading matches the action verb ('Edit failed', 'Move failed', 'Unblock failed')
 *   AC-4 — 409 retains existing conflict-modal flow (onMutationError NOT called);
 *           409→refetch→404 calls onTaskCleared (not onMutationError)
 *
 * Expected builder changes:
 *   - Add onMutationError prop to DetailTabProps
 *   - runMutation: call onMutationError(heading, description, state) for 422, 5xx, network
 *   - Thread action-verb heading through callers (handleSave, handleForceSave, handleConfirm)
 *   - 409 path: preserve conflict-modal flow; do NOT call onMutationError
 */
import { describe, it, expect, vi, afterEach, beforeAll } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type DetailTabProps, type TaskDetail } from '../components/DetailTab'
import type { Board } from '../hooks/useBoard'

// ─── Mock react-markdown ──────────────────────────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Extended props type (post-implementation shape) ─────────────────────────

interface DetailTabTestProps extends DetailTabProps {
  onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
}

const DetailTabWithCallback = DetailTab as React.ComponentType<DetailTabTestProps>

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: '## Objectives\n\n- item one',
  updated: '2026-04-18T10:00:00+00:00',
  created: '2026-04-17T09:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
  claimed: false,
  claimed_at: null,
  dep_status: null,
}

const TASK_BLOCKED: TaskDetail = {
  ...TASK,
  blocked: true,
  block_reason: 'Waiting for dep',
  claimed: true,
  claimed_at: '2026-04-18T09:00:00+00:00',
}

const TASK_CLAIMED: TaskDetail = {
  ...TASK,
  claimed: true,
  claimed_at: '2026-04-18T09:00:00+00:00',
}

const BOARD: Board = {
  statuses: [
    { name: 'backlog' },
    { name: 'todo' },
    { name: 'in-progress' },
  ],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['backlog', 'in-progress'],
    'in-progress': ['todo'],
  },
}

// A resolved task for 409→refetch response stubs.
const CONFLICT_TASK: TaskDetail = {
  ...TASK,
  updated: '2026-04-18T11:00:00+00:00',
  title: 'Updated by other agent',
}

// ─── Setup ────────────────────────────────────────────────────────────────────

beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

// ─── Fetch helpers ────────────────────────────────────────────────────────────

function stubEditFetch(opts: { status: number; network?: boolean }) {
  const { status, network = false } = opts
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (/\/api\/tasks\/\d+\/edit/.test(url) || /\/api\/tasks\/\d+\/release/.test(url) || /\/api\/tasks\/\d+\/move/.test(url)) {
        if (network) throw new Error('Network failure')
        return {
          ok: status >= 200 && status < 300,
          status,
          json: async () => ({ detail: `Error ${status}` }),
          text: async () => `Error ${status}`,
        } as unknown as Response
      }
      return { ok: true, status: 200, json: async () => CONFLICT_TASK } as unknown as Response
    }),
  )
}

function stub409ThenFetch(refetchResponse: { status: number; body?: object }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      // First call to /edit → 409
      if (/\/api\/tasks\/\d+\/edit/.test(url)) {
        return { ok: false, status: 409, json: async () => ({}), text: async () => '' } as unknown as Response
      }
      // Refetch /api/tasks/{id} → configured response
      if (/\/api\/tasks\/\d+$/.test(url)) {
        return {
          ok: refetchResponse.status < 400,
          status: refetchResponse.status,
          json: async () => refetchResponse.body ?? {},
          text: async () => '',
        } as unknown as Response
      }
      return { ok: true, json: async () => ({}) } as unknown as Response
    }),
  )
}

// ─── Render helpers ───────────────────────────────────────────────────────────

function renderDetail(
  task: TaskDetail,
  extraProps: Pick<DetailTabTestProps, 'onMutationError' | 'onTaskUpdated' | 'onTaskCleared'> = {},
) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTabWithCallback task={task} board={BOARD} {...extraProps} />
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

function clickConfirm(container: HTMLElement) {
  const dialog = container.querySelector('[data-testid="confirm-dialog"]')
  expect(dialog).not.toBeNull()
  const buttons = dialog!.querySelectorAll('p-button')
  const confirmBtn = buttons[buttons.length - 1] as HTMLElement
  fireEvent.click(confirmBtn)
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_DetailTabMutationCallbacks', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ─── AC-3: handleSave → 422 → state='warning' ────────────────────────────

  describe('AC-3: handleSave calls onMutationError with state=warning on 422', () => {
    it('calls onMutationError("Edit failed", description, "warning") on 422 response', async () => {
      stubEditFetch({ status: 422 })
      const spy = vi.fn()
      const { container } = renderDetail(TASK, { onMutationError: spy })

      fireEvent.click(container.querySelector('[data-testid="save-button"]')!)

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Edit failed', expect.any(String), 'warning')
      })
    })
  })

  // ─── AC-3: handleSave → 5xx → state='error' ──────────────────────────────

  describe('AC-3: handleSave calls onMutationError with state=error on 5xx', () => {
    it('calls onMutationError("Edit failed", description, "error") on 500 response', async () => {
      stubEditFetch({ status: 500 })
      const spy = vi.fn()
      const { container } = renderDetail(TASK, { onMutationError: spy })

      fireEvent.click(container.querySelector('[data-testid="save-button"]')!)

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Edit failed', expect.any(String), 'error')
      })
    })

    it('calls onMutationError("Edit failed", description, "error") on network error', async () => {
      stubEditFetch({ status: 500, network: true })
      const spy = vi.fn()
      const { container } = renderDetail(TASK, { onMutationError: spy })

      fireEvent.click(container.querySelector('[data-testid="save-button"]')!)

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Edit failed', expect.any(String), 'error')
      })
    })
  })

  // ─── AC-3: action-specific headings ──────────────────────────────────────

  describe('AC-3: heading matches the action verb', () => {
    it('unblock action uses heading "Unblock failed" on failure', async () => {
      stubEditFetch({ status: 500 })
      const spy = vi.fn()
      const { container } = renderDetail(TASK_BLOCKED, { onMutationError: spy })

      // Open confirm dialog for unblock, then confirm.
      fireEvent.click(container.querySelector('[data-testid="unblock-action"]')!)
      clickConfirm(container)

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Unblock failed', expect.any(String), 'error')
      })
    })

    it('move menu action uses heading "Move failed" on failure', async () => {
      stubEditFetch({ status: 500 })
      const spy = vi.fn()
      // TASK status=todo, board has todo→backlog valid transition → backwardTarget = 'backlog'
      const { container } = renderDetail(TASK, { onMutationError: spy })

      await clickMoveTarget(container, 'backlog')

      await waitFor(() => {
        expect(spy).toHaveBeenCalledWith('Move failed', expect.any(String), 'error')
      })
    })

    it('unclaim action uses heading "Unclaim failed" or similar on failure', async () => {
      stubEditFetch({ status: 500 })
      const spy = vi.fn()
      const { container } = renderDetail(TASK_CLAIMED, { onMutationError: spy })

      fireEvent.click(container.querySelector('[data-testid="unclaim-action"]')!)
      clickConfirm(container)

      await waitFor(() => {
        // Heading must be non-empty and contain a verb (exact string is builder's choice
        // for unclaim/release — AC-3 specifies edit/move/unblock but unclaim follows same rule).
        expect(spy).toHaveBeenCalledWith(
          expect.stringMatching(/failed/i),
          expect.any(String),
          'error',
        )
      })
    })
  })

  // ─── AC-4: 409 retains conflict-modal flow; no onMutationError ───────────

  describe('AC-4: 409 triggers conflict modal and does NOT call onMutationError', () => {
    it('handleSave 409 does not call onMutationError (conflict modal handles UX); ' +
       'while same fetch URL on 500 DOES call onMutationError (differential guard)', async () => {
      // Test differential: 500 must call spy, while 409 must not.
      // This combined test fails in RED because 500→spy call doesn't exist yet.

      // First: 409 path — spy must NOT be called.
      stub409ThenFetch({ status: 200, body: CONFLICT_TASK })
      const spy409 = vi.fn()
      const { container: c1, unmount: u1 } = renderDetail(TASK, { onMutationError: spy409 })
      fireEvent.click(c1.querySelector('[data-testid="save-button"]')!)
      await waitFor(() => {
        expect(c1.querySelector('[data-testid="conflict-modal"]')).not.toBeNull()
      })
      expect(spy409).not.toHaveBeenCalled()
      u1()

      // Second: 500 path — spy MUST be called (fails in RED).
      stubEditFetch({ status: 500 })
      const spy500 = vi.fn()
      const { container: c2 } = renderDetail(TASK, { onMutationError: spy500 })
      fireEvent.click(c2.querySelector('[data-testid="save-button"]')!)
      await waitFor(() => {
        expect(spy500).toHaveBeenCalledWith('Edit failed', expect.any(String), 'error')
      })
    })

  })

  // ─── AC-4: 409→refetch→404 calls onTaskCleared; banner NOT triggered ─────

  describe('AC-4: 409→refetch→404 calls onTaskCleared and does NOT call onMutationError', () => {
    it('handleSave 409→refetch→404 fires onTaskCleared and does NOT call onMutationError', async () => {
      stub409ThenFetch({ status: 404 })
      const mutationErrorSpy = vi.fn()
      const taskClearedSpy = vi.fn()
      const { container } = renderDetail(TASK, {
        onMutationError: mutationErrorSpy,
        onTaskCleared: taskClearedSpy,
      })

      fireEvent.click(container.querySelector('[data-testid="save-button"]')!)

      await waitFor(() => {
        expect(taskClearedSpy).toHaveBeenCalled()
      })
      expect(mutationErrorSpy).not.toHaveBeenCalled()
    })
  })
})
