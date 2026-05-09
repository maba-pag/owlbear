/**
 * Failing tests for #1380: P2-05 Test Cockpit task action gating and confirmations
 *
 * RED phase — all tests must fail until builder implements fixes in #1381.
 *
 * AC coverage:
 *   AC1: Action buttons absent from DOM (queryByTestId null) when invalid for task state:
 *        Unclaim absent when claimed=false, Move Backward absent at first pipeline status
 *        or when no board provided. (td:2 → 3 tests)
 *   AC2: Unclaim button absent and no /release mutation fires when claimed=false. (td:2 → 1 test)
 *   AC3: Unblock/Unclaim/Move Backward confirmation shows action-specific text, not generic.
 *        (td:2 → 3 tests)
 *   AC4: Confirm dialog button label names the concrete action, not generic "Confirm".
 *        (td:2 → 2 tests)
 *   AC5: Keyboard/focus: dialog has modal role, Escape dismisses without mutation,
 *        dialog receives focus on open, focus returns to trigger on dismiss. (td:2 → 4 tests)
 *   AC6: Error paths for action mutations use frontend error contract. (td:2 → 3 tests)
 *        NOTE: runMutation error handling is already implemented; AC6 tests use
 *        distinct action/error combinations not covered by DetailTab_1344.test.tsx.
 *   AC7: Suite fails against current always-rendered/generic-confirm behavior. (td:1 — meta)
 *
 * Current gaps (driving failures):
 *   - unclaim-action button always rendered regardless of task.claimed.
 *   - move-backward button always rendered regardless of pipeline position or board.
 *   - ConfirmDialog shows generic "Confirm" button, no action-specific labels or description.
 *   - ConfirmDialog has no role="dialog", no Escape handler, no focus management.
 */

import { beforeAll, describe, it, expect, vi, afterEach } from 'vitest'
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

/** Standard pipeline board — 7 statuses, 'research' is first. */
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

/** Unclaimed, not blocked, mid-pipeline — previousStatus = 'todo'. */
const BASE_TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'in-progress',
  priority: 'important',
  body: '## Body',
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

/** Claimed task — valid state for Unclaim action. */
const TASK_CLAIMED: TaskDetail = {
  ...BASE_TASK,
  claimed: true,
  claimed_at: '2026-05-09T10:00:00+00:00',
}

/** Blocked task — valid state for Unblock action. */
const TASK_BLOCKED: TaskDetail = {
  ...BASE_TASK,
  status: 'todo',
  blocked: true,
  block_reason: 'Waiting for #100',
}

/** Task at the first pipeline status — Move Backward has no valid target. */
const TASK_AT_FIRST_STATUS: TaskDetail = {
  ...BASE_TASK,
  status: 'research',
}

// ─── Render helpers ───────────────────────────────────────────────────────────

function renderDetail(task: TaskDetail, board?: Board | null) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} board={board} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

// ---------------------------------------------------------------------------
// AC1 + AC2: State-based DOM presence/absence of action buttons
// ---------------------------------------------------------------------------

describe('TestFromAC_ActionButtonGating', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('unclaim_button_absent_from_dom_when_task_not_claimed', () => {
    /**
     * AC1: Unclaim must not render when task.claimed is false.
     * Current bug: unclaim-action button always rendered regardless of claimed state.
     */
    const { container } = renderDetail(BASE_TASK, BOARD) // claimed=false
    expect(container.querySelector('[data-testid="unclaim-action"]')).toBeNull()
  })

  it('move_backward_button_absent_when_task_at_first_pipeline_status', () => {
    /**
     * AC1: Move Backward must not render when task is at the first pipeline status
     * (previousStatus returns null → no valid backward target).
     * TASK_AT_FIRST_STATUS.status = 'research' (index 0).
     * Current bug: move-backward always rendered.
     */
    const { container } = renderDetail(TASK_AT_FIRST_STATUS, BOARD)
    expect(container.querySelector('[data-testid="move-backward"]')).toBeNull()
  })

  it('move_backward_button_absent_when_no_board_provided', () => {
    /**
     * AC1: Without a board, previousStatus cannot be computed (returns null).
     * Move Backward must not render when there is no backward target.
     * Current bug: move-backward always rendered even when board is null.
     */
    const { container } = renderDetail(BASE_TASK, null)
    expect(container.querySelector('[data-testid="move-backward"]')).toBeNull()
  })

  it('unblock_button_absent_from_dom_when_task_not_blocked', () => {
    /**
     * AC1 (retry gap): Unblock must not render when task.blocked is false.
     * Implementation: `{t.blocked && <PButton data-testid="unblock-action" ...>}`.
     * This test was absent from the initial RED suite — reviewer identified the gap.
     */
    const { container } = renderDetail(BASE_TASK, BOARD) // blocked=false
    expect(container.querySelector('[data-testid="unblock-action"]')).toBeNull()
  })

  it('unclaim_button_absent_and_no_release_mutation_fires_when_not_claimed', async () => {
    /**
     * AC2: When claimed=false, the unclaim button is absent from the DOM,
     * making it impossible for the /release mutation to fire.
     * Current bug: unclaim-action always rendered; clicking it would trigger /release.
     */
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail(BASE_TASK, BOARD) // claimed=false
    expect(container.querySelector('[data-testid="unclaim-action"]')).toBeNull()
    // No trigger path exists → no /release call
    expect(
      fetchMock.mock.calls.filter((args: unknown[]) =>
        String(args[0]).includes('/release'),
      ),
    ).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// AC3 + AC4: Action-specific confirmation labels
// ---------------------------------------------------------------------------

describe('TestFromAC_ActionSpecificConfirmText', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('unblock_confirm_dialog_shows_action_specific_description', async () => {
    /**
     * AC3: Opening the Unblock confirm dialog must show action-specific text
     * describing the consequence (e.g. "Unblock task?").
     * Current bug: ConfirmDialog shows only blockReason and generic "Confirm" button —
     * no "Unblock task?" description.
     */
    const { container } = renderDetail(TASK_BLOCKED, BOARD)
    const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
    expect(unblockBtn).not.toBeNull()
    fireEvent.click(unblockBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]')!
    expect(dialog.textContent).toMatch(/unblock task\?/i)
  })

  it('unclaim_confirm_dialog_shows_release_claim_description', async () => {
    /**
     * AC3: Opening the Unclaim confirm dialog must show action-specific text
     * describing the consequence (e.g. "Release claim?").
     * Current bug: ConfirmDialog shows no action description.
     * Note: TASK_CLAIMED used so unclaim button is visible after gating.
     * Currently unclaim renders for all tasks — the failure is on the label assertion.
     */
    const { container } = renderDetail(TASK_CLAIMED, BOARD) // claimed=true
    const unclaimBtn = container.querySelector('[data-testid="unclaim-action"]') as HTMLElement | null
    expect(unclaimBtn).not.toBeNull()
    fireEvent.click(unclaimBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]')!
    expect(dialog.textContent).toMatch(/release claim\?/i)
  })

  it('move_backward_confirm_dialog_shows_target_status_name', async () => {
    /**
     * AC3: Move Backward confirm dialog must show the concrete target status
     * (e.g. "Move to todo?"). BASE_TASK.status = 'in-progress'; previousStatus = 'todo'.
     * Current bug: ConfirmDialog shows no target status label.
     */
    const { container } = renderDetail(BASE_TASK, BOARD)
    const moveBackBtn = container.querySelector('[data-testid="move-backward"]') as HTMLElement | null
    expect(moveBackBtn).not.toBeNull()
    fireEvent.click(moveBackBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]')!
    expect(dialog.textContent).toMatch(/move to todo/i)
  })

  it('confirm_button_label_is_not_generic_for_unblock', async () => {
    /**
     * AC4: The primary confirm button in the Unblock dialog must NOT have generic
     * "Confirm" text — it must name the concrete action.
     * Current bug: button text is "Confirm" for all action types.
     */
    const { container } = renderDetail(TASK_BLOCKED, BOARD)
    const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
    expect(unblockBtn).not.toBeNull()
    fireEvent.click(unblockBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]')!
    const pButtons = Array.from(dialog.querySelectorAll('p-button'))
    const primaryBtn = pButtons[pButtons.length - 1] as HTMLElement
    expect(primaryBtn.textContent?.trim()).not.toBe('Confirm')
  })

  it('confirm_button_label_is_not_generic_for_move_backward', async () => {
    /**
     * AC4: The primary confirm button in the Move Backward dialog must NOT have generic
     * "Confirm" text — it must name the concrete target state.
     * Current bug: button text is "Confirm" for all action types.
     */
    const { container } = renderDetail(BASE_TASK, BOARD)
    const moveBackBtn = container.querySelector('[data-testid="move-backward"]') as HTMLElement | null
    expect(moveBackBtn).not.toBeNull()
    fireEvent.click(moveBackBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]')!
    const pButtons = Array.from(dialog.querySelectorAll('p-button'))
    const primaryBtn = pButtons[pButtons.length - 1] as HTMLElement
    expect(primaryBtn.textContent?.trim()).not.toBe('Confirm')
  })

  it('confirm_button_label_exact_unblock_task_for_unblock_action', async () => {
    /**
     * AC4 (retry gap): Confirm button must show the exact label 'Unblock task', not a
     * vague negative check. Reviewer identified that negative-only assertions are
     * insufficient — the contract requires the specific concrete label.
     */
    const { container } = renderDetail(TASK_BLOCKED, BOARD)
    const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
    expect(unblockBtn).not.toBeNull()
    fireEvent.click(unblockBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]')!
    const pButtons = Array.from(dialog.querySelectorAll('p-button'))
    const primaryBtn = pButtons[pButtons.length - 1] as HTMLElement
    expect(primaryBtn.textContent?.trim()).toBe('Unblock task')
  })

  it('confirm_button_label_exact_release_claim_for_unclaim_action', async () => {
    /**
     * AC4 (retry gap): Confirm button must show the exact label 'Release claim'.
     * Also proves the unclaim action-label path — previously untested.
     * Uses TASK_CLAIMED (claimed=true) so the unclaim button is visible.
     */
    const { container } = renderDetail(TASK_CLAIMED, BOARD)
    const unclaimBtn = container.querySelector('[data-testid="unclaim-action"]') as HTMLElement | null
    expect(unclaimBtn).not.toBeNull()
    fireEvent.click(unclaimBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]')!
    const pButtons = Array.from(dialog.querySelectorAll('p-button'))
    const primaryBtn = pButtons[pButtons.length - 1] as HTMLElement
    expect(primaryBtn.textContent?.trim()).toBe('Release claim')
  })

  it('confirm_button_label_exact_move_target_for_move_backward', async () => {
    /**
     * AC4 (retry gap): Confirm button must show the exact label 'Move to {target}'.
     * BASE_TASK.status = 'in-progress' → previousStatus = 'todo'.
     * Label must be 'Move to todo'.
     */
    const { container } = renderDetail(BASE_TASK, BOARD)
    const moveBackBtn = container.querySelector('[data-testid="move-backward"]') as HTMLElement | null
    expect(moveBackBtn).not.toBeNull()
    fireEvent.click(moveBackBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]')!
    const pButtons = Array.from(dialog.querySelectorAll('p-button'))
    const primaryBtn = pButtons[pButtons.length - 1] as HTMLElement
    expect(primaryBtn.textContent?.trim()).toBe('Move to todo')
  })
})

// ---------------------------------------------------------------------------
// AC5: Keyboard / focus semantics
// ---------------------------------------------------------------------------

describe('TestFromAC_ConfirmDialogKeyboard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('confirm_dialog_has_modal_role_or_aria_modal_attribute', async () => {
    /**
     * AC5: ConfirmDialog must expose modal semantics via role="dialog" or aria-modal="true".
     * Current bug: dialog is a plain div with data-testid only — no ARIA attributes.
     */
    const { container } = renderDetail(TASK_BLOCKED, BOARD)
    const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
    expect(unblockBtn).not.toBeNull()
    fireEvent.click(unblockBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]')!
    const hasModalRole = dialog.getAttribute('role') === 'dialog'
    const hasAriaModal = dialog.getAttribute('aria-modal') === 'true'
    expect(hasModalRole || hasAriaModal).toBe(true)
  })

  it('escape_key_dismisses_dialog_without_firing_mutation', async () => {
    /**
     * AC5: Pressing Escape while the confirm dialog is open must dismiss it
     * without triggering any mutation fetch call.
     * Current bug: ConfirmDialog has no keydown handler — Escape does nothing.
     */
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail(TASK_BLOCKED, BOARD)
    const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
    expect(unblockBtn).not.toBeNull()
    fireEvent.click(unblockBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]') as HTMLElement
    fireEvent.keyDown(dialog, { key: 'Escape', code: 'Escape' })
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).toBeNull(),
      { timeout: 500 },
    )
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('confirm_dialog_receives_focus_on_open', async () => {
    /**
     * AC5: When the confirm dialog opens, focus must move into the dialog element
     * (or its first focusable descendant).
     * Current bug: ConfirmDialog performs no focus management — focus stays on body
     * or the last interacted element.
     */
    const { container } = renderDetail(TASK_BLOCKED, BOARD)
    const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
    expect(unblockBtn).not.toBeNull()
    fireEvent.click(unblockBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]') as HTMLElement
    // Dialog (or a descendant) must have received focus
    expect(dialog.contains(document.activeElement)).toBe(true)
  })

  it('focus_returns_to_trigger_button_after_dialog_cancel', async () => {
    /**
     * AC5: After clicking Cancel (or pressing Escape), focus must return to the
     * button that triggered the dialog.
     * Current bug: ConfirmDialog performs no focus restoration on close.
     */
    const { container } = renderDetail(TASK_BLOCKED, BOARD)
    const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
    expect(unblockBtn).not.toBeNull()
    fireEvent.click(unblockBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]')!
    const cancelBtn = dialog.querySelector('p-button') as HTMLElement | null
    expect(cancelBtn).not.toBeNull()
    fireEvent.click(cancelBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).toBeNull(),
      { timeout: 500 },
    )
    // Focus must have returned to the trigger button
    expect(document.activeElement).toBe(unblockBtn)
  })

  it('escape_key_dismisses_dialog_and_restores_focus_to_trigger', async () => {
    /**
     * AC5 (retry gap): The Escape dismiss path must ALSO restore focus to the trigger.
     * Previous tests proved Escape-closes and Cancel-focus-return independently.
     * Reviewer identified the combined Escape+focus-return proof was missing.
     */
    const { container } = renderDetail(TASK_BLOCKED, BOARD)
    const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
    expect(unblockBtn).not.toBeNull()
    fireEvent.click(unblockBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const dialog = container.querySelector('[data-testid="confirm-dialog"]') as HTMLElement
    fireEvent.keyDown(dialog, { key: 'Escape', code: 'Escape' })
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).toBeNull(),
      { timeout: 500 },
    )
    // Focus must return to the trigger button after Escape dismiss
    expect(document.activeElement).toBe(unblockBtn)
  })
})

// ---------------------------------------------------------------------------
// AC6 (retry): Error-contract coverage for action mutations
// ---------------------------------------------------------------------------

describe('TestFromAC_ActionMutationErrorContract', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('unclaim_mutation_404_calls_on_task_cleared', async () => {
    /**
     * AC6 (retry gap): 404 from an action mutation must call onTaskCleared.
     * runMutation: `if (res.status === 404) { onTaskCleared?.(); return }`.
     * No 404 test existed; 1344 only covered unblock 409 and 422.
     * Uses TASK_CLAIMED so the unclaim button is rendered.
     */
    const onTaskCleared = vi.fn()
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: false, status: 404 })))
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={TASK_CLAIMED} board={BOARD} onTaskCleared={onTaskCleared} />
      </PorscheDesignSystemProvider>,
    )
    const unclaimBtn = container.querySelector('[data-testid="unclaim-action"]') as HTMLElement | null
    expect(unclaimBtn).not.toBeNull()
    fireEvent.click(unclaimBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const btns = container.querySelectorAll('[data-testid="confirm-dialog"] p-button')
    fireEvent.click(btns[btns.length - 1] as HTMLElement)
    await waitFor(() => expect(onTaskCleared).toHaveBeenCalledOnce(), { timeout: 500 })
  })

  it('move_backward_mutation_404_calls_on_task_cleared', async () => {
    /**
     * AC6 (retry gap): 404 from move-backward mutation must call onTaskCleared.
     * BASE_TASK.status = 'in-progress' with BOARD → move-backward button is rendered.
     */
    const onTaskCleared = vi.fn()
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: false, status: 404 })))
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={BASE_TASK} board={BOARD} onTaskCleared={onTaskCleared} />
      </PorscheDesignSystemProvider>,
    )
    const moveBackBtn = container.querySelector('[data-testid="move-backward"]') as HTMLElement | null
    expect(moveBackBtn).not.toBeNull()
    fireEvent.click(moveBackBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const btns = container.querySelectorAll('[data-testid="confirm-dialog"] p-button')
    fireEvent.click(btns[btns.length - 1] as HTMLElement)
    await waitFor(() => expect(onTaskCleared).toHaveBeenCalledOnce(), { timeout: 500 })
  })

  it('unclaim_mutation_409_shows_conflict_modal', async () => {
    /**
     * AC6 (retry gap): 409 from unclaim mutation must show conflict modal.
     * Proves the shared 409 contract (refetch + setShowConflict) extends to unclaim,
     * not just the unblock case already in DetailTab_1344.test.tsx.
     */
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({ detail: 'conflict' }) }),
      ),
    )
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={TASK_CLAIMED} board={BOARD} />
      </PorscheDesignSystemProvider>,
    )
    const unclaimBtn = container.querySelector('[data-testid="unclaim-action"]') as HTMLElement | null
    expect(unclaimBtn).not.toBeNull()
    fireEvent.click(unclaimBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const btns = container.querySelectorAll('[data-testid="confirm-dialog"] p-button')
    fireEvent.click(btns[btns.length - 1] as HTMLElement)
    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-modal"]')).not.toBeNull(),
      { timeout: 500 },
    )
  })

  it('move_backward_mutation_422_shows_validation_message', async () => {
    /**
     * AC6 (retry gap): 422 from move-backward mutation must show validation message.
     * runMutation uses getResponseErrorMessage to extract detail from the JSON body.
     * Proves the shared 422 contract extends to move-backward, not just unblock.
     */
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 422,
          json: () => Promise.resolve({ detail: 'invalid status transition' }),
        }),
      ),
    )
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={BASE_TASK} board={BOARD} />
      </PorscheDesignSystemProvider>,
    )
    const moveBackBtn = container.querySelector('[data-testid="move-backward"]') as HTMLElement | null
    expect(moveBackBtn).not.toBeNull()
    fireEvent.click(moveBackBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const btns = container.querySelectorAll('[data-testid="confirm-dialog"] p-button')
    fireEvent.click(btns[btns.length - 1] as HTMLElement)
    await waitFor(
      () => expect(container.querySelector('[data-testid="validation-message"]')).not.toBeNull(),
      { timeout: 500 },
    )
    // AC6 exact-value: textContent must match the seeded server detail, proving
    // getResponseErrorMessage is exercised end-to-end (not a generic fallback).
    const validationEl = container.querySelector('[data-testid="validation-message"]')!
    expect(validationEl.textContent).toContain('invalid status transition')
  })
})
