/**
 * Failing tests for #1378: P2-03 Test Cockpit task detail edit validation and dirty state
 *
 * RED phase — all tests must fail until the builder implements fixes in #1379.
 *
 * AC coverage:
 *   AC1: Invalid parent input (non-numeric text, floats) produces a client-side
 *        validation error visible in the DOM; save does not proceed with a
 *        null-parent payload derived from the invalid input. (td:2 → 4 tests)
 *   AC2: Invalid dependency entries (non-numeric, negative, floats) among valid
 *        entries produce a client-side validation error visible in the DOM; save
 *        does not proceed with invalid entries silently removed. (td:2 → 4 tests)
 *   AC3: Save button is disabled or save action refuses to proceed while
 *        client-side validation errors are present. (td:2 → 2 tests)
 *   AC4: Dirty-state signal is testable in the DOM when editable field values
 *        differ from loaded task state; signal absent when fields are restored. (td:2 → 4 tests)
 *   AC5: Client-side validation errors render in user-visible, test-queryable
 *        DOM element consistent with existing error display approach. (td:1 → 2 tests)
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
 * Uses fireEvent.input with target.value to trigger the component's onInput
 * handler via readControlValue(event.target.value).
 */
function typeIntoField(container: HTMLElement, selector: string, value: string): void {
  const el = container.querySelector(selector) as HTMLElement | null
  expect(el).not.toBeNull()
  fireEvent.input(el!, { target: { value } })
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
        const error = container.querySelector('[data-testid="client-validation-message"]')
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
        const error = container.querySelector('[data-testid="client-validation-message"]')
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
        const error = container.querySelector('[data-testid="client-validation-message"]')
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
        const error = container.querySelector('[data-testid="client-validation-message"]')
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
        const error = container.querySelector('[data-testid="client-validation-message"]')
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
})

// ---------------------------------------------------------------------------
// AC3: Save blocked while client-side validation errors are present (td:2)
// ---------------------------------------------------------------------------

describe('TestFromAC_SaveBlockedOnValidationError', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('save button is disabled when parent field contains invalid input', async () => {
    /**
     * AC3: while a client-side validation error is active, the save button must
     * be disabled (or save action must be blocked — both satisfy the AC).
     *
     * Current bug: no validation state exists; save button is never disabled.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="parent"]', 'invalid')

    await waitFor(
      () => {
        const saveBtn = container.querySelector('[data-testid="save-button"]') as
          | (HTMLElement & { disabled?: boolean })
          | null
        expect(saveBtn).not.toBeNull()
        // Accept any implementation: disabled attr, aria-disabled, or .disabled property
        const isDisabled =
          saveBtn!.hasAttribute('disabled') ||
          saveBtn!.getAttribute('aria-disabled') === 'true' ||
          saveBtn!.getAttribute('disabled') === 'true' ||
          (saveBtn as HTMLElement & { disabled?: boolean }).disabled === true
        expect(isDisabled).toBe(true)
      },
      { timeout: 500 },
    )
  })

  it('save button is disabled when depends_on contains invalid entries', async () => {
    /**
     * AC3: invalid depends_on must also disable the save action.
     *
     * Current bug: no validation state, save button always enabled.
     */
    const { container } = renderDetail()
    typeIntoField(container, '[data-field="depends_on"]', 'bad, 10')

    await waitFor(
      () => {
        const saveBtn = container.querySelector('[data-testid="save-button"]') as
          | (HTMLElement & { disabled?: boolean })
          | null
        expect(saveBtn).not.toBeNull()
        const isDisabled =
          saveBtn!.hasAttribute('disabled') ||
          saveBtn!.getAttribute('aria-disabled') === 'true' ||
          saveBtn!.getAttribute('disabled') === 'true' ||
          (saveBtn as HTMLElement & { disabled?: boolean }).disabled === true
        expect(isDisabled).toBe(true)
      },
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
        const error = container.querySelector('[data-testid="client-validation-message"]')
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
        expect(container.querySelector('[data-testid="client-validation-message"]')).not.toBeNull(),
      { timeout: 500 },
    )

    // Step 2: Correct to a valid integer — error must disappear
    typeIntoField(container, '[data-field="parent"]', '7')
    await waitFor(
      () =>
        expect(container.querySelector('[data-testid="client-validation-message"]')).toBeNull(),
      { timeout: 500 },
    )
  })
})
