/**
 * RED phase Vitest tests for #1457: P4-19 Expose maintenance cleanup through Cockpit
 *
 * AC 3c (td:2): CleanupPanel component renders trigger button, confirmation step,
 *               loading indicator, result display with counts per category and
 *               skipped item details (path + reason), and error state with retry/dismiss.
 * AC 3d (td:1): CleanupPanel is a separate control from HealthBadge (cleanup ≠ corruption
 *               scan) — no corruptionCount or repair-domain props required.
 *
 * Hook is fully mocked — only the component's rendering contract is under test.
 *
 * RED reason: src/components/CleanupPanel.tsx does not exist — collection fails with ImportError.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import type { UseCleanupFlowResult, CleanupPhase } from '../hooks/useCleanupFlow'
import type { CleanupResult } from '../api/cleanup'

// ─── Module mock ──────────────────────────────────────────────────────────────

vi.mock('../hooks/useCleanupFlow', () => ({
  useCleanupFlow: vi.fn(),
}))

import { useCleanupFlow } from '../hooks/useCleanupFlow'
import CleanupPanel from '../components/CleanupPanel'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const RESULT_WITH_SKIPPED: CleanupResult = {
  released_claim_ids: [1, 2, 3],
  archived_task_ids: [10, 20],
  skipped_items: [
    { path: '/tasks/TASK-099.md', reason: 'File locked' },
    { path: '/tasks/TASK-100.md', reason: 'Parse error' },
  ],
}

const RESULT_EMPTY: CleanupResult = {
  released_claim_ids: [],
  archived_task_ids: [],
  skipped_items: [],
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function hookDefaults(): UseCleanupFlowResult {
  return {
    phase: 'idle' as CleanupPhase,
    results: null,
    error: null,
    requestCleanup: vi.fn(),
    confirmCleanup: vi.fn(),
    cancelCleanup: vi.fn(),
    dismissResults: vi.fn(),
  }
}

function mockHook(overrides: Partial<UseCleanupFlowResult> = {}): UseCleanupFlowResult {
  const merged = { ...hookDefaults(), ...overrides }
  vi.mocked(useCleanupFlow).mockReturnValue(merged)
  return merged
}

function renderPanel(props: Record<string, unknown> = {}) {
  return render(
    <PorscheDesignSystemProvider>
      <CleanupPanel {...props} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_CleanupPanel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  // ─── AC 3d: CleanupPanel is separate from HealthBadge ────────────────────

  describe('AC 3d: CleanupPanel renders with no HealthBadge-domain props', () => {
    it('renders without corruptionCount prop (not a repair component)', () => {
      mockHook()
      // CleanupPanel should mount without any repair/HealthBadge props
      expect(() => renderPanel()).not.toThrow()
    })

    it('renders the trigger button in idle state without corruptionCount', () => {
      mockHook()
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-button"]')).not.toBeNull()
    })
  })

  // ─── AC 3c: trigger button in idle state ─────────────────────────────────

  describe('AC 3c: trigger button renders in idle state', () => {
    it('renders cleanup trigger button when phase is idle', () => {
      mockHook()
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-button"]')).not.toBeNull()
    })

    it('clicking trigger button calls requestCleanup', () => {
      const hook = mockHook()
      const { container } = renderPanel()
      const btn = container.querySelector('[data-testid="cleanup-button"]')!
      fireEvent.click(btn)
      expect(hook.requestCleanup).toHaveBeenCalledOnce()
    })
  })

  // ─── AC 3c: confirmation step ────────────────────────────────────────────

  describe('AC 3c: confirmation step renders with confirm and cancel controls', () => {
    it('renders a confirmation dialog when phase is confirming', () => {
      mockHook({ phase: 'confirming' })
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-confirm-dialog"]')).not.toBeNull()
    })

    it('confirmation dialog has a confirm button', () => {
      mockHook({ phase: 'confirming' })
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-confirm-btn"]')).not.toBeNull()
    })

    it('confirmation dialog has a cancel button', () => {
      mockHook({ phase: 'confirming' })
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-cancel-btn"]')).not.toBeNull()
    })

    it('clicking confirm button calls confirmCleanup', () => {
      const hook = mockHook({ phase: 'confirming' })
      const { container } = renderPanel()
      const confirmBtn = container.querySelector('[data-testid="cleanup-confirm-btn"]')!
      fireEvent.click(confirmBtn)
      expect(hook.confirmCleanup).toHaveBeenCalledOnce()
    })

    it('clicking cancel button calls cancelCleanup', () => {
      const hook = mockHook({ phase: 'confirming' })
      const { container } = renderPanel()
      const cancelBtn = container.querySelector('[data-testid="cleanup-cancel-btn"]')!
      fireEvent.click(cancelBtn)
      expect(hook.cancelCleanup).toHaveBeenCalledOnce()
    })
  })

  // ─── AC 3c: loading indicator ────────────────────────────────────────────

  describe('AC 3c: loading indicator shown during running phase', () => {
    it('renders loading indicator when phase is running', () => {
      mockHook({ phase: 'running' })
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-loading"]')).not.toBeNull()
    })

    it('does not render trigger button when phase is running', () => {
      mockHook({ phase: 'running' })
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-button"]')).toBeNull()
    })
  })

  // ─── AC 3c: result display with counts per category ──────────────────────

  describe('AC 3c: result display shows counts for released claims, archived tasks, skipped items', () => {
    it('shows released claims count when phase is done', () => {
      mockHook({ phase: 'done', results: RESULT_WITH_SKIPPED })
      const { getByTestId } = renderPanel()
      const el = getByTestId('cleanup-released-count')
      // Must show the count: 3 released claims
      expect(el.textContent).toMatch(/3/)
    })

    it('shows archived tasks count when phase is done', () => {
      mockHook({ phase: 'done', results: RESULT_WITH_SKIPPED })
      const { getByTestId } = renderPanel()
      const el = getByTestId('cleanup-archived-count')
      // Must show the count: 2 archived tasks
      expect(el.textContent).toMatch(/2/)
    })

    it('shows skipped items count when phase is done', () => {
      mockHook({ phase: 'done', results: RESULT_WITH_SKIPPED })
      const { getByTestId } = renderPanel()
      const el = getByTestId('cleanup-skipped-count')
      // Must show the count: 2 skipped items
      expect(el.textContent).toMatch(/2/)
    })

    it('shows zero counts correctly when result has empty arrays', () => {
      mockHook({ phase: 'done', results: RESULT_EMPTY })
      const { getByTestId } = renderPanel()
      expect(getByTestId('cleanup-released-count').textContent).toMatch(/0/)
      expect(getByTestId('cleanup-archived-count').textContent).toMatch(/0/)
      expect(getByTestId('cleanup-skipped-count').textContent).toMatch(/0/)
    })
  })

  // ─── AC 3c: skipped item details (path + reason) ─────────────────────────

  describe('AC 3c: skipped item details show path and reason', () => {
    it('renders skipped item paths', () => {
      mockHook({ phase: 'done', results: RESULT_WITH_SKIPPED })
      const { getByText } = renderPanel()
      expect(getByText('/tasks/TASK-099.md')).toBeTruthy()
      expect(getByText('/tasks/TASK-100.md')).toBeTruthy()
    })

    it('renders skipped item reasons', () => {
      mockHook({ phase: 'done', results: RESULT_WITH_SKIPPED })
      const { getByText } = renderPanel()
      expect(getByText('File locked')).toBeTruthy()
      expect(getByText('Parse error')).toBeTruthy()
    })

    it('skipped items list is absent when skipped_items is empty', () => {
      mockHook({ phase: 'done', results: RESULT_EMPTY })
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-skipped-list"]')).toBeNull()
    })
  })

  // ─── AC 3c: dismiss button in done state ─────────────────────────────────

  describe('AC 3c: done state has a dismiss button', () => {
    it('renders dismiss button when phase is done', () => {
      mockHook({ phase: 'done', results: RESULT_EMPTY })
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-dismiss-btn"]')).not.toBeNull()
    })

    it('clicking dismiss button calls dismissResults', () => {
      const hook = mockHook({ phase: 'done', results: RESULT_EMPTY })
      const { container } = renderPanel()
      const dismissBtn = container.querySelector('[data-testid="cleanup-dismiss-btn"]')!
      fireEvent.click(dismissBtn)
      expect(hook.dismissResults).toHaveBeenCalledOnce()
    })
  })

  // ─── AC 3c: error state with retry and dismiss ───────────────────────────

  describe('AC 3c: error state shows error message with retry and dismiss', () => {
    it('renders error message when phase is error', () => {
      mockHook({ phase: 'error', error: 'Cleanup failed: disk full' })
      const { getByTestId } = renderPanel()
      expect(getByTestId('cleanup-error').textContent).toContain('Cleanup failed: disk full')
    })

    it('renders retry button when phase is error', () => {
      mockHook({ phase: 'error', error: 'Cleanup failed' })
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-retry-btn"]')).not.toBeNull()
    })

    it('renders dismiss button when phase is error', () => {
      mockHook({ phase: 'error', error: 'Cleanup failed' })
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-dismiss-btn"]')).not.toBeNull()
    })

    it('clicking retry calls confirmCleanup', () => {
      const hook = mockHook({ phase: 'error', error: 'Cleanup failed' })
      const { container } = renderPanel()
      const retryBtn = container.querySelector('[data-testid="cleanup-retry-btn"]')!
      fireEvent.click(retryBtn)
      expect(hook.confirmCleanup).toHaveBeenCalledOnce()
    })

    it('clicking dismiss in error state calls dismissResults', () => {
      const hook = mockHook({ phase: 'error', error: 'Cleanup failed' })
      const { container } = renderPanel()
      const dismissBtn = container.querySelector('[data-testid="cleanup-dismiss-btn"]')!
      fireEvent.click(dismissBtn)
      expect(hook.dismissResults).toHaveBeenCalledOnce()
    })
  })
})
