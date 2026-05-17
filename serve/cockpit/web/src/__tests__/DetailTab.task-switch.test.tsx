/**
 * AC-6 regression test — TaskActions confirm dialog resets on task identity change.
 *
 * Mechanism under test: DetailTab renders `<TaskActions key={`${t.id}:${t.updated}`}>`.
 * When either t.id or t.updated changes, React destroys and remounts the TaskActions
 * subtree, resetting confirmType state to null and closing any open ConfirmDialog.
 *
 * If the key attribute were removed, both tests below would fail: the dialog would
 * remain open after the task switch because confirmType state persists across re-renders
 * without a key change.
 *
 * AC coverage:
 *   AC-6 (B2): TaskActions confirm dialog resets on task identity change.
 *     - Task id change: dialog opened on task A (id=42), switch to task B (id=99) → gone.
 *     - Task updated change: same id, different updated timestamp → gone.
 */

import { beforeAll, describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type TaskDetail } from '../components/DetailTab'

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

const BLOCKED_TASK_A: TaskDetail = {
  id: 42,
  title: 'Task A',
  status: 'in-progress',
  priority: 'important',
  body: 'body A',
  updated: '2026-05-01T10:00:00+00:00',
  created: '2026-05-01T09:00:00+00:00',
  tags: [],
  blocked: true,
  block_reason: 'Waiting on external dep',
  parent: null,
  depends_on: [],
  claimed: true,
  claimed_at: '2026-05-01T09:30:00+00:00',
  dep_status: null,
}

/** Different task — same structure, different id and title. */
const BLOCKED_TASK_B: TaskDetail = {
  ...BLOCKED_TASK_A,
  id: 99,
  title: 'Task B',
}

/** Same task id as A but different updated timestamp (simulates server-side edit). */
const BLOCKED_TASK_A_REFRESHED: TaskDetail = {
  ...BLOCKED_TASK_A,
  updated: '2026-05-01T11:00:00+00:00',
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_TaskActionsConfirmReset', () => {
  it('confirm_dialog_resets_when_task_id_changes', () => {
    /**
     * AC-6 (boundary — id change): User opens the unblock confirm dialog on task A,
     * then the parent switches to task B (different id). DetailTab re-renders with
     * task B; the `key={`${t.id}:${t.updated}`}` attribute on TaskActions changes,
     * React remounts the subtree, confirmType resets to null, and the dialog disappears.
     *
     * Without the key: TaskActions receives new props but retains confirmType state,
     * so the dialog remains visible — this test would fail.
     */
    const { container, rerender } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={BLOCKED_TASK_A} />
      </PorscheDesignSystemProvider>,
    )

    // Open the unblock confirm dialog on task A
    const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
    expect(unblockBtn).not.toBeNull()
    fireEvent.click(unblockBtn!)
    expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull()

    // Parent switches to task B (different id → key changes → TaskActions remounts)
    rerender(
      <PorscheDesignSystemProvider>
        <DetailTab task={BLOCKED_TASK_B} />
      </PorscheDesignSystemProvider>,
    )

    // Confirm dialog must be gone — confirmType was reset by remount
    expect(container.querySelector('[data-testid="confirm-dialog"]')).toBeNull()
  })

  it('confirm_dialog_resets_when_task_updated_changes', () => {
    /**
     * AC-6 (boundary — updated change): Same task id, but the updated timestamp
     * changes (e.g. after a concurrent mutation on the server). The key
     * `${t.id}:${t.updated}` changes, React remounts TaskActions, dialog disappears.
     *
     * Without the key: same id → same key → no remount → dialog stays open.
     */
    const { container, rerender } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={BLOCKED_TASK_A} />
      </PorscheDesignSystemProvider>,
    )

    // Open the unblock confirm dialog on task A (original updated timestamp)
    const unblockBtn = container.querySelector('[data-testid="unblock-action"]') as HTMLElement | null
    expect(unblockBtn).not.toBeNull()
    fireEvent.click(unblockBtn!)
    expect(container.querySelector('[data-testid="confirm-dialog"]')).not.toBeNull()

    // Same task id, but updated changes (server-side version bump)
    rerender(
      <PorscheDesignSystemProvider>
        <DetailTab task={BLOCKED_TASK_A_REFRESHED} />
      </PorscheDesignSystemProvider>,
    )

    // Confirm dialog must be gone — confirmType was reset by remount
    expect(container.querySelector('[data-testid="confirm-dialog"]')).toBeNull()
  })
})
