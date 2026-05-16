/**
 * Implement Cockpit task detail edit validation and dirty state
 *
 * AC1–AC4 are covered by DetailTab_1378.test.tsx (written during #1378 test-writer
 * cycle per architect annotation "Test-writer: tests already written by #1378").
 * This file covers the remaining AC lines.
 *
 * AC coverage:
 *   AC5: Existing valid parent and dependency edits continue to save correctly.
 *        (td:1 → 2 tests)
 *   AC6: The implementation does not add action-gating or conflict-resolution
 *        behavior owned by later tasks. (td:1 → 2 tests)
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

const BASE_TASK: TaskDetail = {
  id: 99,
  title: 'Base task',
  status: 'todo',
  priority: 'needed',
  body: 'Body text',
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

const TASK_WITH_DEPS: TaskDetail = {
  ...BASE_TASK,
  parent: 5,
  depends_on: [10, 20],
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function renderDetail(task: TaskDetail = BASE_TASK) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} />
    </PorscheDesignSystemProvider>,
  )
}

/**
 * Simulate a user typing into a PDS input field via CustomEvent — the
 * authoritative path used by readControlValue() in DetailTab.
 */
function typeIntoField(container: HTMLElement, selector: string, value: string): void {
  const el = container.querySelector(selector) as HTMLElement | null
  expect(el).not.toBeNull()
  fireEvent(el!, new CustomEvent('input', { detail: { value }, bubbles: true }))
}

// ─── Tests ────────────────────────────────────────────────────────────────────

// ---------------------------------------------------------------------------
// AC5: Valid parent and dependency edits continue to save correctly (td:1)
// ---------------------------------------------------------------------------

describe('TestFromAC_ValidEditsStillSave', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('valid parent change triggers fetch with the updated parent value in payload', async () => {
    /**
     * AC5: changing parent from "5" to "6" (both valid non-negative integers)
     * must call fetch with parent=6 in the POST body. The validation path must
     * not refuse valid input.
     */
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...TASK_WITH_DEPS, parent: 6 }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { container } = renderDetail(TASK_WITH_DEPS)
    typeIntoField(container, '[data-field="parent"]', '6')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 500 })

    const call = fetchMock.mock.calls[0] as [string, { body: string }]
    const payload = JSON.parse(call[1].body) as Record<string, unknown>
    expect(payload.parent).toBe(6)
  })

  it('valid depends_on change triggers fetch with the updated depends_on list in payload', async () => {
    /**
     * AC5: changing depends_on from "10, 20" to "10, 20, 30" (all valid integers)
     * must call fetch with depends_on=[10,20,30]. The validation path must not
     * refuse valid input or silently strip entries.
     */
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...TASK_WITH_DEPS, depends_on: [10, 20, 30] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { container } = renderDetail(TASK_WITH_DEPS)
    typeIntoField(container, '[data-field="depends_on"]', '10, 20, 30')

    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce(), { timeout: 500 })

    const call = fetchMock.mock.calls[0] as [string, { body: string }]
    const payload = JSON.parse(call[1].body) as Record<string, unknown>
    expect(payload.depends_on).toEqual([10, 20, 30])
  })
})

// ---------------------------------------------------------------------------
// AC6: No action-gating or conflict-resolution behavior added (td:1)
// ---------------------------------------------------------------------------

describe('TestFromAC_NoExtraActionGating', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('save button renders without a disabled attribute on a clean valid form', () => {
    /**
     * AC6: the save button must not be disabled by extra action-gating added
     * beyond what is described in the AC. A disabled save button would indicate
     * an unintended claim-gate or dirty-gate beyond scope.
     */
    const { container } = renderDetail(BASE_TASK)
    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    expect(saveBtn!.getAttribute('disabled')).toBeNull()
  })

  it('standard save does not trigger a confirmation dialog before calling fetch', async () => {
    /**
     * AC6: a standard title edit + save must reach fetch directly — no confirm
     * dialog (action-gate) should intercept the save. Conflict-resolution dialogs
     * are owned by later tasks and must not be present in this implementation.
     */
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => BASE_TASK,
    })
    vi.stubGlobal('fetch', fetchMock)

    const { container } = renderDetail(BASE_TASK)

    // No confirm dialog before interacting
    expect(container.querySelector('[data-testid="confirm-dialog"]')).toBeNull()

    typeIntoField(container, '[data-field="title"]', 'Updated title')
    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)

    await waitFor(
      () => {
        // No confirm dialog appeared — save went straight to fetch
        expect(container.querySelector('[data-testid="confirm-dialog"]')).toBeNull()
        expect(fetchMock).toHaveBeenCalledOnce()
      },
      { timeout: 500 },
    )
  })
})
