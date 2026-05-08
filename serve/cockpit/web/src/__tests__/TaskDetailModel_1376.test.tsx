/**
 * RED phase tests for #1376: P2-01 Test Cockpit task detail context model
 *
 * All tests FAIL until #1377 implements the extended TaskDetail interface and
 * renders the new fields in DetailTab.
 *
 * AC coverage:
 *   AC1: TaskDetail exposes `claimed` (boolean) and `claimed_at` (string|null).
 *        `claimed_by` is NOT in the backend API response — not tested.
 *   AC2: TaskDetail exposes `dep_status` (string|null) from ShowTaskResponse.
 *        Existing `parent` and `depends_on` fields are not regressed.
 *   AC3: Absent optional context (`claimed_at: null`, `dep_status: null`) is
 *        represented as an explicit rendered element (not field absence).
 *   AC4: State matrix — unclaimed, claimed, blocked, dep-constrained tasks
 *        produce the correct data shape (asserting field values, not UI gates).
 *
 * Current fail reason: DetailTab does not render field-claimed, field-claimed-at,
 * or field-dep-status data-testid elements because those fields are absent from
 * the TaskDetail interface. All queries for those elements return null → FAIL.
 */
import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import DetailTab, { type TaskDetail } from '../components/DetailTab'

// ─── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── Fixtures ─────────────────────────────────────────────────────────────────
//
// Raw API response shapes (what /api/tasks/{id} returns from the backend).
// These include the new fields that #1377 will add to the TaskDetail interface:
//   claimed (bool), claimed_at (string|null), dep_status (string|null).
//
// Using untyped objects + cast at render-time to avoid TypeScript errors on
// excess properties while preserving full runtime field access.
// ─────────────────────────────────────────────────────────────────────────────

/** Unclaimed, unconstrained — all new fields at their null/false defaults. */
const UNCLAIMED_TASK = {
  id: 42,
  title: 'Fix login bug',
  status: 'todo',
  priority: 'important',
  body: '## Objectives\n\n- item one',
  updated: '2026-05-08T10:00:00+00:00',
  created: '2026-05-07T09:00:00+00:00',
  tags: ['backend'],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
  // Fields that #1377 will add to TaskDetail:
  claimed: false,
  claimed_at: null,
  dep_status: null,
}

/** Claimed task — claimed_at holds a non-null ISO timestamp. */
const CLAIMED_TASK = {
  ...UNCLAIMED_TASK,
  claimed: true,
  claimed_at: '2026-05-08T10:00:00+00:00',
  dep_status: null,
}

/** Blocked task — blocked flag set, not claimed. */
const BLOCKED_TASK = {
  ...UNCLAIMED_TASK,
  blocked: true,
  block_reason: 'Waiting for dependency #100',
  claimed: false,
  claimed_at: null,
  dep_status: null,
}

/** Dependency-constrained task — dep_status is "blocked". */
const DEP_CONSTRAINED_TASK = {
  ...UNCLAIMED_TASK,
  depends_on: [10, 20],
  claimed: false,
  claimed_at: null,
  dep_status: 'blocked',
}

/** Claimed + dep-ready — claimed while dependencies are satisfied. */
const CLAIMED_DEP_READY_TASK = {
  ...UNCLAIMED_TASK,
  depends_on: [10],
  claimed: true,
  claimed_at: '2026-05-08T11:00:00+00:00',
  dep_status: 'ready',
}

/** Claimed + blocked — claimed but workflow-blocked (edge combination). */
const CLAIMED_BLOCKED_TASK = {
  ...UNCLAIMED_TASK,
  blocked: true,
  block_reason: 'Needs design approval',
  claimed: true,
  claimed_at: '2026-05-08T09:00:00+00:00',
  dep_status: null,
}

// ─── Render helper ─────────────────────────────────────────────────────────────

/**
 * Render DetailTab with a raw API response fixture.
 *
 * Cast through `unknown` because the new fields are not yet on TaskDetail —
 * #1377 will extend the interface, removing the need for this cast.
 */
function renderDetail(task: Record<string, unknown>) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task as unknown as TaskDetail} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

// ---------------------------------------------------------------------------
// AC1: TaskDetail exposes `claimed` and `claimed_at`  (td:2 → 4 tests)
// ---------------------------------------------------------------------------

describe('TestFromAC_ClaimFieldsOnModel', () => {
  it('renders field-claimed as "false" for an unclaimed task', () => {
    /**
     * AC1: DetailTab must surface the `claimed` boolean from TaskDetail so
     * consumers can read claim state without re-deriving it from claimed_at.
     *
     * FAIL reason: DetailTab has no data-testid="field-claimed" element.
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-claimed"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe('false')
  })

  it('renders field-claimed-at as empty indicator for an unclaimed task', () => {
    /**
     * AC1 + AC3: claimed_at must be surfaced even when null — the element
     * must exist with an empty/null representation, not be absent from DOM.
     *
     * FAIL reason: DetailTab has no data-testid="field-claimed-at" element.
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-claimed-at"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe('')
  })

  it('renders field-claimed as "true" for a claimed task', () => {
    /**
     * AC1: claimed must be true when claimed_at is a non-null timestamp.
     *
     * FAIL reason: DetailTab has no data-testid="field-claimed" element.
     */
    const { container } = renderDetail(CLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-claimed"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe('true')
  })

  it('renders field-claimed-at as the ISO timestamp for a claimed task', () => {
    /**
     * AC1: claimed_at must be surfaced as the exact ISO string when set.
     *
     * FAIL reason: DetailTab has no data-testid="field-claimed-at" element.
     */
    const { container } = renderDetail(CLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-claimed-at"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe(CLAIMED_TASK.claimed_at)
  })
})

// ---------------------------------------------------------------------------
// AC2: TaskDetail exposes `dep_status`; parent/depends_on not regressed (td:2 → 4 tests)
// ---------------------------------------------------------------------------

describe('TestFromAC_DepStatusOnModel', () => {
  it('renders field-dep-status as empty indicator for an unconstrained task', () => {
    /**
     * AC2: dep_status must be surfaced even when null — the element must exist.
     * AC3: explicit null representation, not field absence.
     *
     * FAIL reason: DetailTab has no data-testid="field-dep-status" element.
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-dep-status"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe('')
  })

  it('renders field-dep-status as "blocked" for a dependency-constrained task', () => {
    /**
     * AC2: dep_status='blocked' when task dependencies are in earlier pipeline
     * stages. Must be surfaced on the detail model.
     *
     * FAIL reason: DetailTab has no data-testid="field-dep-status" element.
     */
    const { container } = renderDetail(DEP_CONSTRAINED_TASK)
    const el = container.querySelector('[data-testid="field-dep-status"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe('blocked')
  })

  it('renders field-dep-status as "ready" when dependencies are satisfied', () => {
    /**
     * AC2: dep_status='ready' when all dependency tasks have reached the
     * required pipeline stage.
     *
     * FAIL reason: DetailTab has no data-testid="field-dep-status" element.
     */
    const { container } = renderDetail(CLAIMED_DEP_READY_TASK)
    const el = container.querySelector('[data-testid="field-dep-status"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe('ready')
  })
})

// ---------------------------------------------------------------------------
// AC3: Absent optional context is explicit null, not field absence (td:1 → 2 tests)
// ---------------------------------------------------------------------------

describe('TestFromAC_ExplicitNullRepresentation', () => {
  it('field-claimed-at element is present in DOM even when claimed_at is null', () => {
    /**
     * AC3: A null claimed_at must not make the element disappear from the DOM.
     * Missing context must be represented as an explicit empty value so that
     * a consumer can distinguish "field absent" from "field present, null".
     *
     * FAIL reason: DetailTab has no data-testid="field-claimed-at" element at all.
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-claimed-at"]')
    // Element must exist (not null/undefined) even when value is null
    expect(el).not.toBeNull()
  })

  it('field-dep-status element is present in DOM even when dep_status is null', () => {
    /**
     * AC3: A null dep_status must not make the element disappear from the DOM.
     * Builder must render an always-present element, not a conditional render.
     *
     * FAIL reason: DetailTab has no data-testid="field-dep-status" element at all.
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-dep-status"]')
    // Element must exist (not null/undefined) even when value is null
    expect(el).not.toBeNull()
  })
})

// ---------------------------------------------------------------------------
// AC4: State matrix — data shape for each task state (td:2 → 5 tests)
// ---------------------------------------------------------------------------

describe('TestFromAC_StateMatrix', () => {
  it('unclaimed unconstrained task: all three new fields present with correct values', () => {
    /**
     * AC4: Full shape check for the base unclaimed/unconstrained state.
     * claimed=false, claimed_at=null (empty), dep_status=null (empty).
     *
     * FAIL reason: none of the three field-* elements exist in DetailTab.
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    expect(container.querySelector('[data-testid="field-claimed"]')?.textContent).toBe('false')
    expect(container.querySelector('[data-testid="field-claimed-at"]')?.textContent).toBe('')
    expect(container.querySelector('[data-testid="field-dep-status"]')?.textContent).toBe('')
  })

  it('claimed dep-ready task: claimed=true, claimed_at set, dep_status="ready"', () => {
    /**
     * AC4: Full shape check for a claimed task whose deps are satisfied.
     * All three new fields must surface their non-null values.
     *
     * FAIL reason: none of the three field-* elements exist in DetailTab.
     */
    const { container } = renderDetail(CLAIMED_DEP_READY_TASK)
    expect(container.querySelector('[data-testid="field-claimed"]')?.textContent).toBe('true')
    expect(container.querySelector('[data-testid="field-claimed-at"]')?.textContent).toBe(
      CLAIMED_DEP_READY_TASK.claimed_at,
    )
    expect(container.querySelector('[data-testid="field-dep-status"]')?.textContent).toBe('ready')
  })

  it('blocked task: blocked=true with claim state fields present', () => {
    /**
     * AC4: Blocked tasks still surface the three new fields alongside the
     * existing `blocked` flag. Data shape must include both dimensions.
     *
     * FAIL reason: none of the three field-* elements exist in DetailTab.
     */
    const { container } = renderDetail(BLOCKED_TASK)
    // Existing blocked rendering is not regressed:
    expect(container.querySelector('[data-field="block_reason"]')).not.toBeNull()
    // New fields are also present:
    expect(container.querySelector('[data-testid="field-claimed"]')?.textContent).toBe('false')
    expect(container.querySelector('[data-testid="field-claimed-at"]')?.textContent).toBe('')
  })

  it('dependency-constrained task: dep_status="blocked" alongside depends_on list', () => {
    /**
     * AC4: A task whose dependencies are unresolved has dep_status='blocked'
     * AND retains the existing depends_on field.
     *
     * FAIL reason: field-dep-status element does not exist in DetailTab.
     */
    const { container } = renderDetail(DEP_CONSTRAINED_TASK)
    expect(container.querySelector('[data-testid="field-dep-status"]')?.textContent).toBe('blocked')
    // Existing depends_on input is still present:
    expect(container.querySelector('[data-field="depends_on"]')).not.toBeNull()
  })

  it('claimed blocked task: both claimed=true and blocked=true coexist in the model', () => {
    /**
     * AC4 edge: A task can be simultaneously claimed AND blocked. Both the
     * existing `blocked` field and the new `claimed`/`claimed_at` fields must
     * surface their correct values independently.
     *
     * FAIL reason: field-claimed and field-claimed-at elements do not exist.
     */
    const { container } = renderDetail(CLAIMED_BLOCKED_TASK)
    expect(container.querySelector('[data-testid="field-claimed"]')?.textContent).toBe('true')
    expect(container.querySelector('[data-testid="field-claimed-at"]')?.textContent).toBe(
      CLAIMED_BLOCKED_TASK.claimed_at,
    )
    // Blocked state is also still surfaced:
    expect(container.querySelector('[data-field="block_reason"]')).not.toBeNull()
  })
})
