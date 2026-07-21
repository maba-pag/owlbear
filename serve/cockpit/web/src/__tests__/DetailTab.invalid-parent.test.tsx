/**
 * Test Cockpit task detail edit validation and dirty state
 *
 *
 * AC coverage:
 *   AC1: Invalid parent input (non-numeric text, negative numbers, floats) produces a
 *        client-side validation error visible via data-testid="validation-message";
 *        save does not proceed (fetch not called) for each invalid-input category. (td:2 → 6 tests)
 *   AC2: Each category of invalid dependency entry (non-numeric, negative, floats)
 *        individually produces a validation error AND proves save refusal (fetch not
 *        called per category). (td:2 → 6 tests)
 *   AC3: Save does not proceed while validation errors are present — proven via
 *        fetch-mock assertion (mechanism-agnostic). (td:2 → 2 tests)
 *   AC4: Dirty-state signal is testable in the DOM when editable field values
 *        differ from loaded task state; signal absent when fields are restored. (td:2 → 4 tests)
 *   AC5: Client-side validation errors render in the existing data-testid="validation-message"
 *        element with non-empty visible text content. (td:1 → 2 tests)
 *   AC6: Tests fail against current parseDependsOn/parseParent silent-transform
 *        behavior and are designed for #1379 to satisfy. (meta — verified by RED run)
 *
 * Current bugs driving failures:
 *   - parseDependsOn silently drops invalid entries via
 *     `.filter(v => Number.isInteger(v) && v >= 0)` with no validation error.
 *   - parseParent turns invalid input into null via
 *     `Number.isInteger(parsed) ? parsed : null` with no validation error.
 *   - No client-side validation state or error element exists in the component.
 *   - No dirty-state model or indicator element exists in the component.
 */

import { beforeAll, describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type TaskDetail } from '../components/DetailTab'
import { openEditor } from './DetailTab.testSupport'

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
  status: 'in-progress',
  priority: 'important',
  body: '## Objectives\n\n- item one',
  updated: '2026-04-18T10:00:00+00:00',
  created: '2026-04-17T09:00:00+00:00',
  tags: ['bug'],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
  claimed: false,
  claimed_at: null,
  dep_status: null,
}

/** Task with parent and depends_on set — used for dirty-state and dep tests. */
const TASK_WITH_DEPS: TaskDetail = {
  ...TASK,
  depends_on: [10, 20],
  parent: 5,
}

// ─── Render helpers ───────────────────────────────────────────────────────────

function renderDetail(task: TaskDetail = TASK) {
  const result = render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} />
    </PorscheDesignSystemProvider>,
  )
  openEditor(result.container)
  return result
}

// ─── Input simulation ─────────────────────────────────────────────────────────

/**
 * Simulate a user typing into a PDS input field.
 * Uses CustomEvent with detail.value — readControlValue() checks detail.value first,
 * so this is the authoritative path (target.value is the fragile fallback).
 */
function typeIntoField(container: HTMLElement, selector: string, value: string): void {
  const el = container.querySelector(selector) as HTMLElement | null
  expect(el).not.toBeNull()
  fireEvent(el!, new CustomEvent('input', { detail: { value }, bubbles: true }))
}

// ─── Tests ────────────────────────────────────────────────────────────────────

// ---------------------------------------------------------------------------
// AC1: Invalid parent input → client-side validation error + save blocked (td:2)
// ---------------------------------------------------------------------------

describe('TestFromAC_InvalidParentValidation', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('non-numeric_float_and_negative_parent_inputs_all_render_validation_error', async () => {
    /**
     * AC1: All invalid parent categories (non-numeric text, float, negative)
     * must produce a visible client-side validation error element.
     */
    for (const value of ['abc', '3.14', '-5']) {
      const { container, unmount } = renderDetail()
      typeIntoField(container, '[data-field="parent"]', value)
      await waitFor(
        () => {
          const error = container.querySelector('[data-testid="validation-message"]')
          expect(error, `expected error for parent="${value}"`).not.toBeNull()
          expect(error!.textContent?.trim()).toBeTruthy()
        },
        { timeout: 500 },
      )
      unmount()
    }
  })

  it('save_does_not_call_fetch_for_any_invalid_parent_category', async () => {
    /**
     * AC1+AC3: Save must not proceed for non-numeric, float, or negative parent.
     */
    for (const value of ['notanumber', '1.5', '-5']) {
      const fetchMock = vi.fn()
      vi.stubGlobal('fetch', fetchMock)
      const { container, unmount } = renderDetail()
      typeIntoField(container, '[data-field="parent"]', value)
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement
      fireEvent.click(saveBtn)
      await waitFor(
        () => expect(fetchMock, `fetch called for parent="${value}"`).not.toHaveBeenCalled(),
        { timeout: 500 },
      )
      unmount()
      vi.unstubAllGlobals()
    }
  })

  it('invalid_parent_text_preserved_after_validation_fires', async () => {
    /**
     * AC1 preserved clause: raw invalid input must remain in the field.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', 'not-a-number')
    await waitFor(
      () => expect(container.querySelector('[data-testid="validation-message"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const el = container.querySelector('[data-field="parent"]') as HTMLInputElement
    const fieldValue = el.value ?? el.getAttribute('value')
    expect(fieldValue).toBe('not-a-number')
  })

  it('invalid_parent_text_preserved_after_blocked_save_attempt', async () => {
    /**
     * AC1 preserved clause: after blocked save, raw invalid text still visible.
     */
    vi.stubGlobal('fetch', vi.fn())
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', 'bad-parent')
    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement
    fireEvent.click(saveBtn)
    await waitFor(
      () => expect(container.querySelector('[data-testid="validation-message"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const el = container.querySelector('[data-field="parent"]') as HTMLInputElement
    const fieldValue = el.value ?? el.getAttribute('value')
    expect(fieldValue).toBe('bad-parent')
  })
})

// ---------------------------------------------------------------------------
// AC2: Invalid depends_on entries → client-side validation error + save blocked (td:2)
// ---------------------------------------------------------------------------

describe('TestFromAC_InvalidDependsOnValidation', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('non-numeric_float_and_negative_depends_on_entries_all_render_validation_error', async () => {
    /**
     * AC2: All invalid depends_on categories (non-numeric, float, negative)
     * must produce a visible client-side validation error.
     */
    for (const value of ['10, abc, 20', '10, 1.5, 20', '10, -1, 20']) {
      const { container, unmount } = renderDetail()
      typeIntoField(container, '[data-field="depends_on"]', value)
      await waitFor(
        () => {
          const error = container.querySelector('[data-testid="validation-message"]')
          expect(error, `expected error for depends_on="${value}"`).not.toBeNull()
          expect(error!.textContent?.trim()).toBeTruthy()
        },
        { timeout: 500 },
      )
      unmount()
    }
  })

  it('save_does_not_call_fetch_for_any_invalid_depends_on_category', async () => {
    /**
     * AC2+AC3: Save must not proceed for non-numeric, float, or negative depends_on.
     */
    for (const value of ['10, notvalid, 20', '10, -1, 20', '10, 1.5, 20']) {
      const fetchMock = vi.fn()
      vi.stubGlobal('fetch', fetchMock)
      const { container, unmount } = renderDetail()
      typeIntoField(container, '[data-field="depends_on"]', value)
      const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement
      fireEvent.click(saveBtn)
      await waitFor(
        () => expect(fetchMock, `fetch called for depends_on="${value}"`).not.toHaveBeenCalled(),
        { timeout: 500 },
      )
      unmount()
      vi.unstubAllGlobals()
    }
  })

  it('invalid_depends_on_text_preserved_after_validation_fires', async () => {
    /**
     * AC2 preserved clause: raw invalid input must remain in the field.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', '10, not-valid, 20')
    await waitFor(
      () => expect(container.querySelector('[data-testid="validation-message"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const el = container.querySelector('[data-field="depends_on"]') as HTMLInputElement
    const fieldValue = el.value ?? el.getAttribute('value')
    expect(fieldValue).toBe('10, not-valid, 20')
  })

  it('invalid_depends_on_text_preserved_after_blocked_save_attempt', async () => {
    /**
     * AC2 preserved clause: after blocked save, raw invalid text still visible.
     */
    vi.stubGlobal('fetch', vi.fn())
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', '5, bad-entry, 15')
    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement
    fireEvent.click(saveBtn)
    await waitFor(
      () => expect(container.querySelector('[data-testid="validation-message"]')).not.toBeNull(),
      { timeout: 500 },
    )
    const el = container.querySelector('[data-field="depends_on"]') as HTMLInputElement
    const fieldValue = el.value ?? el.getAttribute('value')
    expect(fieldValue).toBe('5, bad-entry, 15')
  })
})

// ---------------------------------------------------------------------------
// AC4: Dirty-state signal testable in DOM (td:2)
// ---------------------------------------------------------------------------

describe('TestFromAC_DirtyStateSignal', () => {
  it('dirty_indicator_appears_when_any_editable_field_changes_from_loaded_value', async () => {
    /**
     * AC4: Changing title, depends_on, or parent from loaded values must all
     * produce a dirty-state signal via data-testid="dirty-indicator".
     */
    // title
    const r1 = renderDetail()
    typeIntoField(r1.container, '[data-field="title"]', 'New title value')
    await waitFor(
      () => expect(r1.container.querySelector('[data-testid="dirty-indicator"]')).not.toBeNull(),
      { timeout: 500 },
    )
    r1.unmount()

    // depends_on
    const r2 = renderDetail(TASK_WITH_DEPS)
    typeIntoField(r2.container, '[data-field="depends_on"]', '10, 20, 30')
    await waitFor(
      () => expect(r2.container.querySelector('[data-testid="dirty-indicator"]')).not.toBeNull(),
      { timeout: 500 },
    )
    r2.unmount()

    // parent
    const r3 = renderDetail(TASK_WITH_DEPS)
    typeIntoField(r3.container, '[data-field="parent"]', '99')
    await waitFor(
      () => expect(r3.container.querySelector('[data-testid="dirty-indicator"]')).not.toBeNull(),
      { timeout: 500 },
    )
    r3.unmount()
  })

  it('dirty_indicator_absent_when_changed_field_restored_to_loaded_value', async () => {
    /**
     * AC4: Restoring a field to its loaded value must clear the dirty signal.
     */
    const { container } = renderDetail(TASK_WITH_DEPS)
    typeIntoField(container, '[data-field="parent"]', '99')
    await waitFor(
      () => expect(container.querySelector('[data-testid="dirty-indicator"]')).not.toBeNull(),
      { timeout: 500 },
    )
    typeIntoField(container, '[data-field="parent"]', '5')
    await waitFor(
      () => expect(container.querySelector('[data-testid="dirty-indicator"]')).toBeNull(),
      { timeout: 500 },
    )
  })
})

// ---------------------------------------------------------------------------
// AC5: Client-side validation errors render in user-visible, queryable DOM (td:1)
// ---------------------------------------------------------------------------

describe('TestFromAC_ValidationErrorVisibility', () => {
  it('client-side validation error renders in a DOM element queryable by data-testid', async () => {
    /**
     * AC5: Error must be findable via data-testid with non-empty text.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', 'notvalid')
    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
        expect(error!.textContent?.trim()).toBeTruthy()
      },
      { timeout: 500 },
    )
  })

  it('client-side validation error disappears when invalid input is corrected', async () => {
    /**
     * AC5 + AC1: Correcting invalid input must remove the validation error.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', 'bad')
    await waitFor(
      () => expect(container.querySelector('[data-testid="validation-message"]')).not.toBeNull(),
      { timeout: 500 },
    )
    typeIntoField(container, '[data-field="parent"]', '7')
    await waitFor(
      () => expect(container.querySelector('[data-testid="validation-message"]')).toBeNull(),
      { timeout: 500 },
    )
  })
})
