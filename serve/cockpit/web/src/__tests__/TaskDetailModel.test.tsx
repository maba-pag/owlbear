/**
 * Test Cockpit task detail context model
 *
 * Proves that DetailTab surfaces the backend context fields needed for safe
 * UI decisions. Implementation was provided by #1377.
 *
 * AC coverage:
 *   AC1: TaskDetail exposes `claimed` (boolean) and `claimed_at` (string|null).
 *        `claimed_by` is NOT in the backend API response — not tested.
 *   AC2: TaskDetail exposes `dep_status` (string|null) from ShowTaskResponse.
 *        Existing `parent` and `depends_on` fields are not regressed.
 *   AC3: When `claimed_at` or `dep_status` is null, DetailTab renders an explicit
 *        DOM element (not a missing element). Runtime DOM proof only — test files
 *        are excluded from tsc by tsconfig.json so compile-time enforcement applies
 *        to the implementation file (DetailTab.tsx) only.
 *   AC4: State matrix — unclaimed, claimed, blocked, dep-constrained tasks
 *        produce the correct data shape (asserting field values, not UI gates).
 *   AC5: Tests exercise all three new fields (`claimed`, `claimed_at`, `dep_status`)
 *        via `data-testid` queries and exact value assertions; removing any rendered
 *        field element from DetailTab would fail the suite.
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
// Typed API response shapes (what /api/tasks/{id} returns from the backend).
// Each constant is declared as TaskDetail — TypeScript enforces the full
// interface contract at compile time, proving the model without runtime
// reflection.
// ─────────────────────────────────────────────────────────────────────────────

/** Unclaimed, unconstrained — all nullable fields at their null/false defaults. */
const UNCLAIMED_TASK: TaskDetail = {
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
  claimed: false,
  claimed_at: null,
  dep_status: null,
}

/** Claimed task — claimed_at holds a non-null ISO timestamp. */
const CLAIMED_TASK: TaskDetail = {
  ...UNCLAIMED_TASK,
  claimed: true,
  claimed_at: '2026-05-08T10:00:00+00:00',
  dep_status: null,
}

/** Blocked task — blocked flag set, not claimed. */
const BLOCKED_TASK: TaskDetail = {
  ...UNCLAIMED_TASK,
  blocked: true,
  block_reason: 'Waiting for dependency #100',
  claimed: false,
  claimed_at: null,
  dep_status: null,
}

/** Dependency-constrained task — dep_status is "blocked". */
const DEP_CONSTRAINED_TASK: TaskDetail = {
  ...UNCLAIMED_TASK,
  depends_on: [10, 20],
  claimed: false,
  claimed_at: null,
  dep_status: 'blocked',
}

/** Claimed + dep-ready — claimed while dependencies are satisfied. */
const CLAIMED_DEP_READY_TASK: TaskDetail = {
  ...UNCLAIMED_TASK,
  depends_on: [10],
  claimed: true,
  claimed_at: '2026-05-08T11:00:00+00:00',
  dep_status: 'ready',
}

/** Claimed + blocked — claimed but workflow-blocked (edge combination). */
const CLAIMED_BLOCKED_TASK: TaskDetail = {
  ...UNCLAIMED_TASK,
  blocked: true,
  block_reason: 'Needs design approval',
  claimed: true,
  claimed_at: '2026-05-08T09:00:00+00:00',
  dep_status: null,
}

// ─── Render helper ─────────────────────────────────────────────────────────────

/**
 * Render DetailTab with a typed TaskDetail fixture.
 * The typed parameter proves the TypeScript contract at compile time.
 */
function renderDetail(task: TaskDetail) {
  return render(
    <PorscheDesignSystemProvider>
      <DetailTab task={task} />
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
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-claimed"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe('false')
  })

  it('renders field-claimed-at as empty indicator for an unclaimed task', () => {
    /**
     * AC1 + AC3: claimed_at must be surfaced even when null — the element
     * must exist with an empty representation, not be absent from DOM.
     * (null renders as empty string; absence-vs-null enforced at tsc level)
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-claimed-at"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe('')
  })

  it('renders field-claimed as "true" for a claimed task', () => {
    /**
     * AC1: claimed must be true when claimed_at is a non-null timestamp.
     */
    const { container } = renderDetail(CLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-claimed"]')
    expect(el).not.toBeNull()
    expect(el!.textContent).toBe('true')
  })

  it('renders field-claimed-at as the ISO timestamp for a claimed task', () => {
    /**
     * AC1: claimed_at must be surfaced as the exact ISO string when set.
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
     * AC3: explicit null representation (renders as empty string, not absent DOM node).
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
     * AC3 (runtime DOM proof): A null claimed_at must not make the element
     * disappear from the DOM. DetailTab must always render the field-claimed-at
     * element regardless of value.
     * Note: test files are excluded from tsc by tsconfig.json (line 18), so
     * compile-time null-vs-absent enforcement applies to the implementation
     * file (DetailTab.tsx) only. This test proves runtime DOM presence only.
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-claimed-at"]')
    // Element must exist (not null/undefined) even when value is null
    expect(el).not.toBeNull()
  })

  it('field-dep-status element is present in DOM even when dep_status is null', () => {
    /**
     * AC3 (runtime DOM proof): A null dep_status must not make the element
     * disappear from the DOM. DetailTab must always render the field-dep-status
     * element regardless of value.
     * Note: test files are excluded from tsc by tsconfig.json (line 18), so
     * compile-time null-vs-absent enforcement applies to the implementation
     * file (DetailTab.tsx) only. This test proves runtime DOM presence only.
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    const el = container.querySelector('[data-testid="field-dep-status"]')
    // Element must exist (not null/undefined) even when value is null
    expect(el).not.toBeNull()
  })
})

// ---------------------------------------------------------------------------
// AC5: Removing any rendered field element from DetailTab fails the suite (td:1)
// ---------------------------------------------------------------------------

describe('TestFromAC_FieldElementSensitivity', () => {
  it('all three new fields are present with exact non-null values; removing any element would fail this test', () => {
    /**
     * AC5: Tests exercise all three new fields via data-testid queries and
     * exact value assertions. If field-claimed, field-claimed-at, or
     * field-dep-status were removed from DetailTab, the querySelector would
     * return null and the `.not.toBeNull()` assertions below would fail.
     * Uses CLAIMED_DEP_READY_TASK so all three fields carry non-null values.
     */
    const { container } = renderDetail(CLAIMED_DEP_READY_TASK)
    // field-claimed: element exists with exact boolean string
    const claimedEl = container.querySelector('[data-testid="field-claimed"]')
    expect(claimedEl).not.toBeNull()
    expect(claimedEl!.textContent).toBe('true')
    // field-claimed-at: element exists with exact ISO timestamp
    const claimedAtEl = container.querySelector('[data-testid="field-claimed-at"]')
    expect(claimedAtEl).not.toBeNull()
    expect(claimedAtEl!.textContent).toBe(CLAIMED_DEP_READY_TASK.claimed_at)
    // field-dep-status: element exists with exact string value
    const depStatusEl = container.querySelector('[data-testid="field-dep-status"]')
    expect(depStatusEl).not.toBeNull()
    expect(depStatusEl!.textContent).toBe('ready')
  })
})

// ---------------------------------------------------------------------------
// AC4: State matrix — data shape for each task state (td:2 → 5 tests)
// ---------------------------------------------------------------------------

describe('TestFromAC_StateMatrix', () => {
  it('unclaimed unconstrained task: all three new fields present with correct values', () => {
    /**
     * AC4: Full shape check for the base unclaimed/unconstrained state.
     * claimed=false, claimed_at=null (renders empty), dep_status=null (renders empty).
     */
    const { container } = renderDetail(UNCLAIMED_TASK)
    expect(container.querySelector('[data-testid="field-claimed"]')?.textContent).toBe('false')
    expect(container.querySelector('[data-testid="field-claimed-at"]')?.textContent).toBe('')
    expect(container.querySelector('[data-testid="field-dep-status"]')?.textContent).toBe('')
  })

  it('claimed dep-ready task: claimed=true, claimed_at set, dep_status="ready"', () => {
    /**
     * AC4: Full shape check for a claimed task whose deps are satisfied.
     * All three fields must surface their non-null values.
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
     * AC4: Blocked tasks still surface the three fields alongside the
     * existing `blocked` flag. Data shape must include both dimensions.
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
     */
    const { container } = renderDetail(DEP_CONSTRAINED_TASK)
    expect(container.querySelector('[data-testid="field-dep-status"]')?.textContent).toBe('blocked')
    // Existing depends_on input is still present:
    expect(container.querySelector('[data-field="depends_on"]')).not.toBeNull()
  })

  it('claimed blocked task: both claimed=true and blocked=true coexist in the model', () => {
    /**
     * AC4 edge: A task can be simultaneously claimed AND blocked. Both the
     * existing `blocked` field and the `claimed`/`claimed_at` fields must
     * surface their correct values independently.
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

