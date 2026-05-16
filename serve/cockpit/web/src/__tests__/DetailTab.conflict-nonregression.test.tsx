/**
 * Implement Cockpit task action gating and confirmations
 *
 * AC1–AC6 coverage is provided by DetailTab_1380.test.tsx (22 tests).
 * This file provides the AC7 non-regression guard only.
 *
 * AC coverage:
 *   AC7: Save → 409 → conflict-modal path must survive the action-gating and
 *        confirmation changes; unclaim button must remain absent for claimed=false
 *        tasks when the conflict path is exercised. (td:1 → 1 test)
 *
 * Note: Implementation was pre-committed during #1380's pipeline cycle (commit
 * b899bbb2). This test is a non-regression guard — it PASSES against the current
 * codebase and serves as the builder's verification target.
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

/**
 * Fully-typed task fixture with all fields required by the updated TaskDetail
 * interface (claimed, claimed_at, dep_status). claimed=false so unclaim button
 * must be absent under the action-gating contract.
 */
const TASK_UNCLAIMED: TaskDetail = {
  id: 99,
  title: 'Auth service refactor',
  status: 'in-progress',
  priority: 'needed',
  body: '## Work',
  updated: '2026-05-09T08:00:00+00:00',
  created: '2026-05-09T07:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  parent: null,
  depends_on: [],
  claimed: false,
  claimed_at: null,
  dep_status: null,
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_ConflictResolutionNonRegression', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('save_409_opens_conflict_modal_and_unclaim_absent_for_unclaimed_task', async () => {
    /**
     * AC7 non-regression guard: The save → 409 → conflict-modal path must not be
     * broken by the action-gating changes introduced in this task.
     *
     * Two assertions combined (both required by the AC7 contract):
     *   1. unclaim button is absent for claimed=false task (gating survives into save path)
     *   2. clicking Save after 409 response shows the conflict modal
     *
     * Exercises DetailTab.tsx paths shared between the save edit handler and the
     * new action-gating logic to prove neither branch pollutes the other.
     */
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 409,
          json: () => Promise.resolve({ detail: 'conflict' }),
        }),
      ),
    )
    const { container } = render(
      <PorscheDesignSystemProvider>
        <DetailTab task={TASK_UNCLAIMED} />
      </PorscheDesignSystemProvider>,
    )
    // Gating non-regression: unclaim button must be absent for claimed=false
    expect(container.querySelector('[data-testid="unclaim-action"]')).toBeNull()
    // Conflict-resolution non-regression: save → 409 → conflict modal appears
    const saveBtn = container.querySelector('[data-testid="save-button"]') as HTMLElement | null
    expect(saveBtn).not.toBeNull()
    fireEvent.click(saveBtn!)
    await waitFor(
      () => expect(container.querySelector('[data-testid="conflict-modal"]')).not.toBeNull(),
      { timeout: 500 },
    )
  })
})
