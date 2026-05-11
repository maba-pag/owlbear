/**
 * Workflow behavior tests1167: RF-05 RepairPanel component
 *
 * Covers: button visibility by corruption count, confirmation dialog content,
 * repair execution trigger, cancel/dismiss flows, loading spinner, grouped
 * results display, error state display, and a11y dialog attributes.
 *
 * All tests are RED (failing) until the builder implements RepairPanel.tsx.
 * Hook is fully mocked — component interface is the only contract under test.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { UseRepairFlowResult } from '../hooks/useRepairFlow'
import type { RepairOutcome } from '../api/repair'

// ─── Module mock ──────────────────────────────────────────────────────────────

vi.mock('../hooks/useRepairFlow', () => ({
  useRepairFlow: vi.fn(),
}))

import { useRepairFlow } from '../hooks/useRepairFlow'
import RepairPanel from '../components/RepairPanel'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const OUTCOME_FIXED: RepairOutcome = {
  task_id: 1,
  file_path: '/tasks/TASK-001.md',
  code: 'MISSING_STATUS',
  action: 'fixed',
  detail: 'Status field added',
}

const OUTCOME_QUARANTINED: RepairOutcome = {
  task_id: null,
  file_path: '/tasks/corrupt.md',
  code: 'CORRUPT_YAML',
  action: 'quarantined',
  detail: null,
}

const OUTCOME_FAILED: RepairOutcome = {
  task_id: 7,
  file_path: '/tasks/TASK-007.md',
  code: 'UNRECOGNISED',
  action: 'failed',
  detail: 'Could not determine repair strategy',
}

const GROUPED_RESULTS = {
  fixed: [OUTCOME_FIXED],
  quarantined: [OUTCOME_QUARANTINED],
  failed: [OUTCOME_FAILED],
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function hookDefaults(): UseRepairFlowResult {
  return {
    phase: 'idle',
    corruptionCount: null,
    results: null,
    error: null,
    requestRepair: vi.fn(),
    confirmRepair: vi.fn(),
    cancelRepair: vi.fn(),
    dismissResults: vi.fn(),
  }
}

function mockHook(overrides: Partial<UseRepairFlowResult> = {}): UseRepairFlowResult {
  const merged = { ...hookDefaults(), ...overrides }
  vi.mocked(useRepairFlow).mockReturnValue(merged)
  return merged
}

function renderPanel(corruptionCount: number) {
  return render(
    <PorscheDesignSystemProvider>
      <RepairPanel corruptionCount={corruptionCount} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_RepairPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  // ─── AC1: Repair button renders when corruptionCount > 0 ─────────────────

  describe('AC1: Repair button renders when corruptionCount > 0', () => {
    it('renders a Repair button when corruptionCount is 1', () => {
      mockHook()
      const { container } = renderPanel(1)
      expect(container.querySelector('[data-testid="repair-button"]')).not.toBeNull()
    })

    it('renders a Repair button when corruptionCount is large', () => {
      mockHook()
      const { container } = renderPanel(99)
      expect(container.querySelector('[data-testid="repair-button"]')).not.toBeNull()
    })
  })

  // ─── AC2: Repair button hidden when corruptionCount is 0 ─────────────────

  describe('AC2: Repair button hidden when corruptionCount is 0', () => {
    it('does not render a Repair button when corruptionCount is 0', () => {
      mockHook()
      const { container } = renderPanel(0)
      expect(container.querySelector('[data-testid="repair-button"]')).toBeNull()
    })
  })

  // ─── AC3: Clicking Repair shows confirmation dialog with count ────────────

  describe('AC3: clicking Repair calls requestRepair and shows dialog with count', () => {
    it('clicking Repair button calls requestRepair with corruptionCount prop value', () => {
      const hook = mockHook()
      const { container } = renderPanel(3)
      const btn = container.querySelector('[data-testid="repair-button"]')!
      fireEvent.click(btn)
      expect(hook.requestRepair).toHaveBeenCalledWith(3)
    })

    it('clicking Repair button calls requestRepair with the exact prop value', () => {
      const hook = mockHook()
      const { container } = renderPanel(7)
      const btn = container.querySelector('[data-testid="repair-button"]')!
      fireEvent.click(btn)
      expect(hook.requestRepair).toHaveBeenCalledWith(7)
    })

    it('shows confirmation dialog when phase is confirming', () => {
      mockHook({ phase: 'confirming', corruptionCount: 3 })
      const { container } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-confirm-dialog"]')).not.toBeNull()
    })

    it('includes corruptionCount in confirmation dialog message', () => {
      mockHook({ phase: 'confirming', corruptionCount: 5 })
      const { getByText } = renderPanel(5)
      // The message must contain the count so user understands scope
      expect(getByText(/5/)).toBeTruthy()
    })
  })

  // ─── AC4: Confirming dialog triggers repair execution ────────────────────

  describe('AC4: confirming dialog triggers repair execution', () => {
    it('confirmation dialog has a confirm button', () => {
      mockHook({ phase: 'confirming', corruptionCount: 2 })
      const { container } = renderPanel(2)
      expect(container.querySelector('[data-testid="repair-confirm-btn"]')).not.toBeNull()
    })

    it('clicking confirm button calls confirmRepair', () => {
      const hook = mockHook({ phase: 'confirming', corruptionCount: 2 })
      const { container } = renderPanel(2)
      const confirmBtn = container.querySelector('[data-testid="repair-confirm-btn"]')!
      fireEvent.click(confirmBtn)
      expect(hook.confirmRepair).toHaveBeenCalledOnce()
    })
  })

  // ─── AC5: Cancelling dialog returns to button state ──────────────────────

  describe('AC5: cancelling dialog calls cancelRepair', () => {
    it('confirmation dialog has a cancel button', () => {
      mockHook({ phase: 'confirming', corruptionCount: 2 })
      const { container } = renderPanel(2)
      expect(container.querySelector('[data-testid="repair-cancel-btn"]')).not.toBeNull()
    })

    it('clicking cancel button calls cancelRepair', () => {
      const hook = mockHook({ phase: 'confirming', corruptionCount: 2 })
      const { container } = renderPanel(2)
      const cancelBtn = container.querySelector('[data-testid="repair-cancel-btn"]')!
      fireEvent.click(cancelBtn)
      expect(hook.cancelRepair).toHaveBeenCalledOnce()
    })

    it('repair button reappears and dialog disappears when hook returns to idle after cancel', () => {
      // Prove the confirming → idle UI transition at the component boundary.
      // A mutation that calls cancelRepair but fails to restore button state would FAIL this test.
      mockHook({ phase: 'confirming', corruptionCount: 2 })
      const { container, rerender } = renderPanel(2)
      // Confirming state: dialog visible, button absent
      expect(container.querySelector('[data-testid="repair-confirm-dialog"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-button"]')).toBeNull()
      // Hook transitions back to idle (as cancelRepair implementation would do)
      mockHook()
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={2} />
        </PorscheDesignSystemProvider>,
      )
      // Idle state restored: dialog gone, repair button visible
      expect(container.querySelector('[data-testid="repair-confirm-dialog"]')).toBeNull()
      expect(container.querySelector('[data-testid="repair-button"]')).not.toBeNull()
    })
  })

  // ─── AC6: Loading spinner shown during repair execution ──────────────────

  describe('AC6: loading spinner shown during repair execution', () => {
    it('renders a loading indicator when phase is repairing', () => {
      mockHook({ phase: 'repairing' })
      const { container } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-loading"]')).not.toBeNull()
    })

    it('does not render the Repair button while repairing', () => {
      mockHook({ phase: 'repairing' })
      const { container } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-button"]')).toBeNull()
    })
  })

  // ─── AC7: Results grouped by action ──────────────────────────────────────

  describe('AC7: results display groups outcomes by action', () => {
    it('renders a fixed section when there are fixed outcomes', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { container } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-results-fixed"]')).not.toBeNull()
    })

    it('renders a quarantined section when there are quarantined outcomes', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { container } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-results-quarantined"]')).not.toBeNull()
    })

    it('renders a failed section when there are failed outcomes', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { container } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-results-failed"]')).not.toBeNull()
    })

    it('renders all three sections when results has items in each bucket', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { container } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-results-fixed"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-results-quarantined"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-results-failed"]')).not.toBeNull()
    })
  })

  // ─── AC8: Each outcome row shows file path and detail ────────────────────

  describe('AC8: outcome rows show file path and detail when present', () => {
    it('renders file_path for a fixed outcome row', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { getByText } = renderPanel(3)
      expect(getByText('/tasks/TASK-001.md')).toBeTruthy()
    })

    it('renders detail text for an outcome that has detail', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { getByText } = renderPanel(3)
      expect(getByText('Status field added')).toBeTruthy()
    })

    it('renders file_path for a failed outcome row', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { getByText } = renderPanel(3)
      expect(getByText('/tasks/TASK-007.md')).toBeTruthy()
    })

    it('renders file_path even when detail is null (quarantined outcome)', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { getByText } = renderPanel(3)
      expect(getByText('/tasks/corrupt.md')).toBeTruthy()
    })
  })

  // ─── AC9: Dismiss button in results view clears results ──────────────────

  describe('AC9: dismiss button in results view returns to button state', () => {
    it('renders a dismiss button in the done phase', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { container } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-dismiss-btn"]')).not.toBeNull()
    })

    it('clicking dismiss button calls dismissResults', () => {
      const hook = mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { container } = renderPanel(3)
      const dismissBtn = container.querySelector('[data-testid="repair-dismiss-btn"]')!
      fireEvent.click(dismissBtn)
      expect(hook.dismissResults).toHaveBeenCalledOnce()
    })
  })

  // ─── AC10: Error message displayed when repair fails ─────────────────────

  describe('AC10: error message displayed when repair execution fails', () => {
    it('renders an error message element when phase is error', () => {
      mockHook({ phase: 'error', error: 'Server unreachable' })
      const { container } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-error"]')).not.toBeNull()
    })

    it('error element contains the error string from hook', () => {
      mockHook({ phase: 'error', error: 'Server unreachable' })
      const { getByText } = renderPanel(3)
      expect(getByText(/Server unreachable/)).toBeTruthy()
    })
  })

  // ─── AC11: Dismiss from error state clears error ─────────────────────────

  describe('AC11: dismiss from error state calls dismissResults', () => {
    it('renders a dismiss button in the error phase', () => {
      mockHook({ phase: 'error', error: 'oops' })
      const { container } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-dismiss-btn"]')).not.toBeNull()
    })

    it('clicking dismiss in error phase calls dismissResults', () => {
      const hook = mockHook({ phase: 'error', error: 'oops' })
      const { container } = renderPanel(3)
      const dismissBtn = container.querySelector('[data-testid="repair-dismiss-btn"]')!
      fireEvent.click(dismissBtn)
      expect(hook.dismissResults).toHaveBeenCalledOnce()
    })
  })

  // ─── AC12: Confirmation dialog a11y attributes ────────────────────────────

  describe('AC12: confirmation dialog has role="dialog" and accessible label', () => {
    it('confirmation dialog element has role="dialog"', () => {
      mockHook({ phase: 'confirming', corruptionCount: 2 })
      const { container } = renderPanel(2)
      const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
      expect(dialog?.getAttribute('role')).toBe('dialog')
    })

    it('confirmation dialog element has an aria-label attribute', () => {
      mockHook({ phase: 'confirming', corruptionCount: 2 })
      const { container } = renderPanel(2)
      const dialog = container.querySelector('[data-testid="repair-confirm-dialog"]')
      expect(dialog?.getAttribute('aria-label')).toBeTruthy()
    })
  })

  // ─── AC8-ext: conditional detail rendering ("when present") ──────────────
  // AC8 specifies "shows file path and detail when present".
  // "When present" means detail must NOT appear in the DOM when detail is null.
  // Current implementation renders <span>{outcome.detail}</span> unconditionally
  // (i.e. an empty span when detail is null) — these tests expose that contract gap.

  describe('AC8-ext: detail element absent when outcome detail is null', () => {
    it('outcome row with null detail contains exactly one span (file path only)', () => {
      // OUTCOME_QUARANTINED has detail: null
      mockHook({ phase: 'done', results: { fixed: [], quarantined: [OUTCOME_QUARANTINED], failed: [] } })
      const { container } = renderPanel(1)
      const li = container.querySelector('[data-testid="repair-results-quarantined"] li')!
      // Only the file-path span should render; no empty detail span
      expect(li.querySelectorAll('span')).toHaveLength(1)
    })

    it('mixed outcomes: null-detail row has 1 span, non-null-detail row has 2 spans', () => {
      mockHook({
        phase: 'done',
        results: { fixed: [OUTCOME_FIXED], quarantined: [OUTCOME_QUARANTINED], failed: [] },
      })
      const { container } = renderPanel(2)
      const fixedLi = container.querySelector('[data-testid="repair-results-fixed"] li')!
      expect(fixedLi.querySelectorAll('span')).toHaveLength(2) // non-null detail → 2 spans
      const quarantinedLi = container.querySelector('[data-testid="repair-results-quarantined"] li')!
      expect(quarantinedLi.querySelectorAll('span')).toHaveLength(1) // null detail → 1 span
    })

    it('null-detail failed outcome: row contains exactly one span', () => {
      const FAILED_NO_DETAIL: RepairOutcome = {
        task_id: 9,
        file_path: '/tasks/TASK-009.md',
        code: 'UNRECOGNISED',
        action: 'failed',
        detail: null,
      }
      mockHook({ phase: 'done', results: { fixed: [], quarantined: [], failed: [FAILED_NO_DETAIL] } })
      const { container } = renderPanel(1)
      const li = container.querySelector('[data-testid="repair-results-failed"] li')!
      expect(li.querySelectorAll('span')).toHaveLength(1)
    })
  })
})

// ─── Re-render coverage (React Compiler memoisation cache-hit branches) ───────
//
// The React Compiler (babel-plugin-react-compiler) wraps each JSX block in a
// useMemoCache() check. A single render only exercises the cache-miss branch.
// These tests re-render the component (same or changed props/state) to exercise
// the cache-hit and cache-invalidation branches, driving branch coverage to ≥90%.
//
// All tests in this suite are GREEN (pass with any correct implementation);
// they are required for coverage, not for RED-phase failure evidence.

const OUTCOME_FIXED_2: RepairOutcome = {
  task_id: 2,
  file_path: '/tasks/TASK-002.md',
  code: 'MISSING_TITLE',
  action: 'fixed',
  detail: 'Title field added',
}

describe('TestFromAC_RepairPanel_RenderCoverage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  // ─── Re-render idempotency (cache-hit path per phase) ────────────────────

  describe('re-render idempotency — same props/state produces same output', () => {
    it('idle phase: repair button still present after re-render with identical props', () => {
      mockHook()
      const { container, rerender } = renderPanel(3)
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={3} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="repair-button"]')).not.toBeNull()
    })

    it('confirming phase: dialog still present after re-render', () => {
      mockHook({ phase: 'confirming', corruptionCount: 2 })
      const { container, rerender } = renderPanel(2)
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={2} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="repair-confirm-dialog"]')).not.toBeNull()
    })

    it('repairing phase: loading indicator still present after re-render', () => {
      mockHook({ phase: 'repairing' })
      const { container, rerender } = renderPanel(3)
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={3} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="repair-loading"]')).not.toBeNull()
    })

    it('done phase: all result sections still present after re-render', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { container, rerender } = renderPanel(3)
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={3} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="repair-results-fixed"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-results-quarantined"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-results-failed"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-dismiss-btn"]')).not.toBeNull()
    })

    it('error phase: error element still present after re-render', () => {
      mockHook({ phase: 'error', error: 'Network timeout' })
      const { container, rerender } = renderPanel(3)
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={3} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="repair-error"]')).not.toBeNull()
    })

    it('idle with count=0: null output stable after re-render', () => {
      mockHook()
      const { container, rerender } = renderPanel(0)
      expect(container.firstChild).toBeNull()
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={0} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.firstChild).toBeNull()
    })
  })

  // ─── Phase transitions (cache-invalidation on state change) ─────────────

  describe('phase transitions — component updates when hook phase changes', () => {
    it('idle → confirming: dialog replaces repair button on phase change', () => {
      mockHook()
      const { container, rerender } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-button"]')).not.toBeNull()
      mockHook({ phase: 'confirming', corruptionCount: 3 })
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={3} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="repair-confirm-dialog"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-button"]')).toBeNull()
    })

    it('confirming → repairing: loading replaces dialog', () => {
      mockHook({ phase: 'confirming', corruptionCount: 3 })
      const { container, rerender } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-confirm-dialog"]')).not.toBeNull()
      mockHook({ phase: 'repairing' })
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={3} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="repair-loading"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-confirm-dialog"]')).toBeNull()
    })

    it('repairing → done: results replace loading indicator', () => {
      mockHook({ phase: 'repairing' })
      const { container, rerender } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-loading"]')).not.toBeNull()
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={3} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="repair-results-fixed"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-loading"]')).toBeNull()
    })

    it('done → idle: repair button reappears after dismiss (phase reset)', () => {
      mockHook({ phase: 'done', results: GROUPED_RESULTS })
      const { container, rerender } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-dismiss-btn"]')).not.toBeNull()
      mockHook()
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={3} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="repair-button"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-results-fixed"]')).toBeNull()
    })

    it('error → idle: repair button reappears after error dismiss', () => {
      mockHook({ phase: 'error', error: 'oops' })
      const { container, rerender } = renderPanel(3)
      expect(container.querySelector('[data-testid="repair-error"]')).not.toBeNull()
      mockHook()
      rerender(
        <PorscheDesignSystemProvider>
          <RepairPanel corruptionCount={3} />
        </PorscheDesignSystemProvider>,
      )
      expect(container.querySelector('[data-testid="repair-button"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="repair-error"]')).toBeNull()
    })
  })

  // ─── Multiple outcomes per section (map-callback loop coverage) ──────────

  describe('multiple outcomes per section', () => {
    it('renders 2 list items in fixed section when 2 fixed outcomes provided', () => {
      mockHook({
        phase: 'done',
        results: { fixed: [OUTCOME_FIXED, OUTCOME_FIXED_2], quarantined: [], failed: [] },
      })
      const { container } = renderPanel(2)
      const fixedSection = container.querySelector('[data-testid="repair-results-fixed"]')!
      expect(fixedSection.querySelectorAll('li')).toHaveLength(2)
    })

    it('renders all file paths when multiple outcomes in a section', () => {
      mockHook({
        phase: 'done',
        results: { fixed: [OUTCOME_FIXED, OUTCOME_FIXED_2], quarantined: [], failed: [] },
      })
      const { getByText } = renderPanel(2)
      expect(getByText('/tasks/TASK-001.md')).toBeTruthy()
      expect(getByText('/tasks/TASK-002.md')).toBeTruthy()
    })

    it('renders items across all three non-empty sections correctly', () => {
      mockHook({
        phase: 'done',
        results: {
          fixed: [OUTCOME_FIXED, OUTCOME_FIXED_2],
          quarantined: [OUTCOME_QUARANTINED],
          failed: [OUTCOME_FAILED],
        },
      })
      const { container } = renderPanel(4)
      expect(
        container.querySelector('[data-testid="repair-results-fixed"]')!.querySelectorAll('li'),
      ).toHaveLength(2)
      expect(
        container.querySelector('[data-testid="repair-results-quarantined"]')!.querySelectorAll('li'),
      ).toHaveLength(1)
      expect(
        container.querySelector('[data-testid="repair-results-failed"]')!.querySelectorAll('li'),
      ).toHaveLength(1)
    })
  })
})
