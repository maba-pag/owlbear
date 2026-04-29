/**
 * Failing tests for #1167: RF-05 RepairPanel component
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
})
