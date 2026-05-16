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
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} />
    </PorscheDesignSystemProvider>,
  )
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

  it('non-numeric parent input renders a client-side validation error in the DOM', async () => {
    /**
     * AC1: entering "abc" in the parent field must produce a visible
     * client-side validation error element in the DOM.
     *
     * Current bug: parseParent silently returns null for "abc" — no error shown.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', 'abc')

    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
        expect(error!.textContent?.trim()).toBeTruthy()
      },
      { timeout: 500 },
    )
  })

  it('float parent input renders a client-side validation error in the DOM', async () => {
    /**
     * AC1 boundary: "3.14" is not a valid integer parent ID.
     *
     * Current bug: Number("3.14") fails Number.isInteger → parseParent returns
     * null silently, no error element is rendered.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', '3.14')

    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
      },
      { timeout: 500 },
    )
  })

  it('save does not call fetch when parent field contains non-numeric text', async () => {
    /**
     * AC1: when parent validation error is present, save must not proceed.
     * fetch() must not be called at all.
     *
     * Current bug: parseParent("notanumber") silently returns null; handleSave()
     * fires the POST with parent: null, losing the user's invalid-but-intentional input.
     */
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', 'notanumber')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => expect(fetchMock).not.toHaveBeenCalled(),
      { timeout: 500 },
    )
  })

  it('save does not call fetch when parent field contains a float', async () => {
    /**
     * AC1 boundary: "1.5" is not a valid task ID (must be a non-negative integer).
     * Save must refuse rather than silently converting to null.
     *
     * Current bug: parseParent("1.5") → null; POST fires with parent: null.
     */
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', '1.5')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => expect(fetchMock).not.toHaveBeenCalled(),
      { timeout: 500 },
    )
  })

  it('negative parent input renders a client-side validation error in the DOM', async () => {
    /**
     * AC1 boundary: "-5" is not a valid parent task ID (must be a non-negative integer).
     *
     * Current bug: parseParent("-5") silently returns null — no error shown.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', '-5')

    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
        expect(error!.textContent?.trim()).toBeTruthy()
      },
      { timeout: 500 },
    )
  })

  it('save does not call fetch when parent field contains a negative number', async () => {
    /**
     * AC1 boundary: "-5" is not a valid task ID. Save must refuse rather than
     * silently converting to null.
     *
     * Current bug: parseParent("-5") → null; POST fires with parent: null.
     */
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', '-5')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => expect(fetchMock).not.toHaveBeenCalled(),
      { timeout: 500 },
    )
  })

  it('invalid parent text is preserved in the parent field after validation fires', async () => {
    /**
     * AC1 preserved clause: after typing invalid text and validation fires,
     * the raw input must remain in the field — it must not be cleared, nulled,
     * or replaced with the previously-valid value.
     *
     * Readback assertion: field value === the invalid string the user typed.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', 'not-a-number')

    // Wait for validation error to confirm the component processed the input
    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
      },
      { timeout: 500 },
    )

    const el = container.querySelector('[data-field="parent"]') as HTMLInputElement | null
    expect(el).not.toBeNull()
    const fieldValue = (el as HTMLInputElement).value ?? el!.getAttribute('value')
    expect(fieldValue).toBe('not-a-number')
  })

  it('invalid parent text is preserved in the parent field after a blocked save attempt', async () => {
    /**
     * AC1 preserved clause: after a blocked save attempt (fetch not called),
     * the raw invalid text must still be visible in the parent field.
     * The field must not revert to the loaded state or become empty.
     */
    vi.stubGlobal('fetch', vi.fn())
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', 'bad-parent')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
      },
      { timeout: 500 },
    )

    const el = container.querySelector('[data-field="parent"]') as HTMLInputElement | null
    expect(el).not.toBeNull()
    const fieldValue = (el as HTMLInputElement).value ?? el!.getAttribute('value')
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

  it('non-numeric entry in depends_on renders a client-side validation error', async () => {
    /**
     * AC2: "10, abc, 20" contains a non-numeric entry — must produce a visible
     * client-side validation error element.
     *
     * Current bug: parseDependsOn silently drops "abc" → result is [10, 20]
     * with no error rendered.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', '10, abc, 20')

    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
        expect(error!.textContent?.trim()).toBeTruthy()
      },
      { timeout: 500 },
    )
  })

  it('negative number entry in depends_on renders a client-side validation error', async () => {
    /**
     * AC2 boundary: negative IDs are invalid (task IDs are non-negative integers).
     * "-1" must produce a validation error, not be silently filtered out.
     *
     * Current bug: parseDependsOn filters negatives via `value >= 0` with no error.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', '10, -1, 20')

    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
      },
      { timeout: 500 },
    )
  })

  it('float entry in depends_on renders a client-side validation error', async () => {
    /**
     * AC2 boundary: "1.5" is not a valid task ID integer.
     * parseDependsOn rejects it via Number.isInteger — silently with no error.
     *
     * Current bug: float is filtered without surfacing an error to the user.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', '10, 1.5, 20')

    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
      },
      { timeout: 500 },
    )
  })

  it('save does not call fetch when depends_on contains invalid entries among valid ones', async () => {
    /**
     * AC2: "10, notvalid, 20" — save must not proceed. Silent removal of the
     * invalid entry would corrupt the user's depends_on list.
     *
     * Current bug: parseDependsOn drops "notvalid" and handleSave fires POST
     * with depends_on: [10, 20], silently truncating the list.
     */
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', '10, notvalid, 20')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => expect(fetchMock).not.toHaveBeenCalled(),
      { timeout: 500 },
    )
  })

  it('save does not call fetch when depends_on contains a negative entry', async () => {
    /**
     * AC2: "10, -1, 20" — save must not proceed. Silent removal of the negative
     * entry would corrupt the user's intent.
     *
     * Current bug: parseDependsOn filters negatives without validation;
     * handleSave fires POST with depends_on: [10, 20].
     */
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', '10, -1, 20')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => expect(fetchMock).not.toHaveBeenCalled(),
      { timeout: 500 },
    )
  })

  it('save does not call fetch when depends_on contains a float entry', async () => {
    /**
     * AC2: "10, 1.5, 20" — save must not proceed. Float is not a valid task ID;
     * silent removal would corrupt the list.
     *
     * Current bug: parseDependsOn filters floats without validation;
     * handleSave fires POST with depends_on: [10, 20].
     */
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', '10, 1.5, 20')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => expect(fetchMock).not.toHaveBeenCalled(),
      { timeout: 500 },
    )
  })

  it('invalid depends_on text is preserved in the field after validation fires', async () => {
    /**
     * AC2 preserved clause: after typing invalid depends_on text and validation
     * fires, the raw input must remain in the field — the invalid entry must
     * not be silently dropped from the visible field value.
     *
     * Readback assertion: field value === the invalid string the user typed.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', '10, not-valid, 20')

    // Wait for validation error to confirm the component processed the input
    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
      },
      { timeout: 500 },
    )

    const el = container.querySelector('[data-field="depends_on"]') as HTMLInputElement | null
    expect(el).not.toBeNull()
    const fieldValue = (el as HTMLInputElement).value ?? el!.getAttribute('value')
    expect(fieldValue).toBe('10, not-valid, 20')
  })

  it('invalid depends_on text is preserved in the field after a blocked save attempt', async () => {
    /**
     * AC2 preserved clause: after a blocked save attempt (fetch not called),
     * the full raw invalid text must still be visible in the depends_on field.
     * The invalid entry must not be silently removed from the field display.
     */
    vi.stubGlobal('fetch', vi.fn())
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', '5, bad-entry, 15')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => {
        const error = container.querySelector('[data-testid="validation-message"]')
        expect(error).not.toBeNull()
      },
      { timeout: 500 },
    )

    const el = container.querySelector('[data-field="depends_on"]') as HTMLInputElement | null
    expect(el).not.toBeNull()
    const fieldValue = (el as HTMLInputElement).value ?? el!.getAttribute('value')
    expect(fieldValue).toBe('5, bad-entry, 15')
  })
})

// ---------------------------------------------------------------------------
// AC3: Save blocked while client-side validation errors are present (td:2)
// ---------------------------------------------------------------------------

describe('TestFromAC_SaveBlockedOnValidationError', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('save does not call fetch when parent field contains invalid input', async () => {
    /**
     * AC3: mechanism-agnostic save refusal proof. While a client-side validation
     * error is active, save must not proceed regardless of whether the button is
     * disabled or a click-time handler refuses.
     *
     * Proof: fetch is not called after clicking save with invalid parent input.
     *
     * Current bug: no validation state exists; handleSave fires POST with null parent.
     */
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', 'invalid')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => expect(fetchMock).not.toHaveBeenCalled(),
      { timeout: 500 },
    )
  })

  it('save does not call fetch when depends_on contains invalid entries', async () => {
    /**
     * AC3: mechanism-agnostic save refusal proof for invalid depends_on.
     *
     * Proof: fetch is not called after clicking save with invalid depends_on.
     *
     * Current bug: no validation state; handleSave fires POST with silently-filtered list.
     */
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', 'bad, 10')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => expect(fetchMock).not.toHaveBeenCalled(),
      { timeout: 500 },
    )
  })
})

// ---------------------------------------------------------------------------
// AC4: Dirty-state signal testable in DOM (td:2)
// ---------------------------------------------------------------------------

describe('TestFromAC_DirtyStateSignal', () => {
  it('dirty indicator appears in DOM when title is changed from its loaded value', async () => {
    /**
     * AC4: after changing the title field, a dirty-state signal must be
     * visible in the DOM via data-testid="dirty-indicator".
     *
     * Current bug: no dirty-state model exists — no such element is ever rendered.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="title"]', 'New title value')

    await waitFor(
      () => {
        const dirty = container.querySelector('[data-testid="dirty-indicator"]')
        expect(dirty).not.toBeNull()
      },
      { timeout: 500 },
    )
  })

  it('dirty indicator appears when depends_on is changed from its loaded value', async () => {
    /**
     * AC4: changing depends_on from the loaded "10, 20" (TASK_WITH_DEPS) to
     * a different valid value must render the dirty indicator.
     *
     * Current bug: no dirty-state signal.
     */
    const { container } = renderDetail(TASK_WITH_DEPS)
    typeIntoField(container, '[data-field="depends_on"]', '10, 20, 30')

    await waitFor(
      () => {
        const dirty = container.querySelector('[data-testid="dirty-indicator"]')
        expect(dirty).not.toBeNull()
      },
      { timeout: 500 },
    )
  })

  it('dirty indicator appears when parent is changed from its loaded value', async () => {
    /**
     * AC4: changing parent from "5" (loaded from TASK_WITH_DEPS) to a different
     * valid integer must render the dirty indicator.
     *
     * Current bug: no dirty-state signal.
     */
    const { container } = renderDetail(TASK_WITH_DEPS)
    typeIntoField(container, '[data-field="parent"]', '99')

    await waitFor(
      () => {
        const dirty = container.querySelector('[data-testid="dirty-indicator"]')
        expect(dirty).not.toBeNull()
      },
      { timeout: 500 },
    )
  })

  it('dirty indicator is absent when a changed field is restored to its loaded value', async () => {
    /**
     * AC4: restoring a field to its original loaded value must clear the dirty signal.
     * The signal must be absent when fields match the loaded state.
     *
     * Fail path in RED: the first waitFor (dirty indicator appearing) fails —
     * no dirty-state model exists at all.
     */
    const { container } = renderDetail(TASK_WITH_DEPS)

    // Step 1: Change parent away from loaded value — dirty indicator must appear
    typeIntoField(container, '[data-field="parent"]', '99')
    await waitFor(
      () => expect(container.querySelector('[data-testid="dirty-indicator"]')).not.toBeNull(),
      { timeout: 500 },
    )

    // Step 2: Restore to original loaded value "5" — dirty indicator must clear
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
     * AC5: after triggering a client-side validation error (invalid parent),
     * the error must be findable via a stable data-testid query and must have
     * non-empty visible text content.
     *
     * Current bug: no client-side validation element exists in the component.
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
     * AC5 + AC1 boundary: correcting an invalid parent input must remove the
     * validation error from the DOM — the error is not sticky.
     *
     * Fail path in RED: first waitFor (error appearing) fails — no validation
     * error element exists in the current implementation.
     */
    const { container } = renderDetail()

    // Step 1: Enter invalid value — error must appear
    typeIntoField(container, '[data-field="parent"]', 'bad')
    await waitFor(
      () =>
        expect(container.querySelector('[data-testid="validation-message"]')).not.toBeNull(),
      { timeout: 500 },
    )

    // Step 2: Correct to a valid integer — error must disappear
    typeIntoField(container, '[data-field="parent"]', '7')
    await waitFor(
      () =>
        expect(container.querySelector('[data-testid="validation-message"]')).toBeNull(),
      { timeout: 500 },
    )
  })
})
