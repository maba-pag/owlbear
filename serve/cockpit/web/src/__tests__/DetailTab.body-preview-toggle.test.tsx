/**
 * AC-4 regression: edit body → toggle out of edit mode → readonly preview shows unsaved local body.
 *
 * Proof bundle: smoke — one regression assertion for the preview-after-toggle path
 * introduced by #1508 (TaskFieldsEditor body state ownership).
 *
 * Repaired defect: TaskFieldsEditor.tsx line ~242 now renders local `body` state in the
 * readonly ReactMarkdown branch instead of persisted `task.body`. This test would fail if
 * the source were reverted to rendering `task.body` in that branch.
 *
 * AC coverage:
 *   AC-1 / AC-4 (B2): body edit → toggle out → readonly preview shows unsaved local body,
 *                      NOT the persisted task.body value.
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

const TASK: TaskDetail = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: 'persisted body text',
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
  proof_bundle: null,
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_BodyPreviewToggle', () => {
  /**
   * AC-1 / AC-4 regression:
   * Input:  user edits body textarea to a new value, then toggles editBody to false
   * Output: readonly markdown preview renders the unsaved local body state (not persisted task.body)
   *
   * Would fail if TaskFieldsEditor.tsx reverted to passing `task.body` to ReactMarkdown
   * instead of the local `body` state variable.
   */
  it('readonly markdown preview shows unsaved local body after toggling out of edit mode', () => {
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={TASK} />
      </PorscheDesignSystemProvider>,
    )

    const editDetails = container.querySelector('[data-testid="edit-details-button"]') as HTMLElement | null
    expect(editDetails).not.toBeNull()
    fireEvent.click(editDetails!)

    // Step 1: enter edit mode — body-edit-toggle click sets editBody = true
    const toggle = container.querySelector('[data-testid="body-edit-toggle"]') as HTMLElement | null
    expect(toggle).not.toBeNull()
    fireEvent.click(toggle!)

    // Step 2: simulate user typing a different value into the PDS textarea via CustomEvent,
    // matching the readControlValue(event.detail.value) path in TaskFieldsEditor
    const textarea = container.querySelector('p-textarea[data-field="body"]') as
      | (HTMLElement & { hideLabel?: boolean; label?: string })
      | null
    expect(textarea).not.toBeNull()
    expect(textarea?.label ?? textarea?.getAttribute('label')).toBe('Body')
    expect(textarea?.hideLabel ?? textarea?.hasAttribute('hide-label')).toBe(true)
    fireEvent(
      textarea!,
      new CustomEvent('input', { detail: { value: 'unsaved local body' }, bubbles: true }),
    )

    // Step 3: toggle back to preview mode — body-edit-toggle click sets editBody = false
    fireEvent.click(toggle!)

    // Step 4: readonly markdown preview must render the LOCAL body state, not persisted task.body
    const preview = container.querySelector('[data-testid="markdown-body"]')
    expect(preview).not.toBeNull()
    expect(preview!.textContent).toBe('unsaved local body')
  })
})
