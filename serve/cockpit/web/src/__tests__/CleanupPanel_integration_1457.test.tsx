/**
 * Integration tests for #1457: P4-19 Expose maintenance cleanup through Cockpit
 *
 * These tests mount the REAL CleanupPanel with the REAL useCleanupFlow hook,
 * mocking only the cleanupTasks API layer. This exercises full React state
 * transitions within a single render lifecycle, ensuring V8 branch coverage
 * tracks every rendering path in CleanupPanel.tsx (AC 3c/3d).
 *
 * Complement to CleanupPanel_1457.test.tsx (which mocks the hook entirely).
 * Coverage target: raise CleanupPanel.tsx branch coverage to ≥90%.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import CleanupPanel from '../components/CleanupPanel'
import type { CleanupResult } from '../api/cleanup'

// Mock only the API layer — useCleanupFlow runs real code
vi.mock('../api/cleanup', () => ({
  cleanupTasks: vi.fn(),
}))

import { cleanupTasks } from '../api/cleanup'

// ─── Fixtures ──────────────────────────────────────────────────────────────────

const RESULT_EMPTY: CleanupResult = {
  released_claim_ids: [],
  archived_task_ids: [],
  skipped_items: [],
}

const RESULT_WITH_SKIPPED: CleanupResult = {
  released_claim_ids: [1, 2],
  archived_task_ids: [10],
  skipped_items: [{ path: '/tasks/T-001.md', reason: 'File locked' }],
}

const RESULT_FULL: CleanupResult = {
  released_claim_ids: [1, 2, 3],
  archived_task_ids: [10, 20, 30],
  skipped_items: [
    { path: '/tasks/T-099.md', reason: 'File locked' },
    { path: '/tasks/T-100.md', reason: 'Parse error' },
  ],
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

function renderPanel(props: { onSuccess?: () => void } = {}) {
  return render(
    <PorscheDesignSystemProvider>
      <CleanupPanel {...props} />
    </PorscheDesignSystemProvider>,
  )
}

// ─── Tests ─────────────────────────────────────────────────────────────────────

describe('TestFromAC_CleanupPanel_Integration', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  // ─── AC 3c: idle → confirming transition ───────────────────────────────────

  describe('AC 3c: trigger button transitions to confirming (real hook)', () => {
    it('clicking trigger button shows confirmation dialog', () => {
      vi.mocked(cleanupTasks).mockResolvedValue(RESULT_EMPTY)
      const { container } = renderPanel()
      expect(container.querySelector('[data-testid="cleanup-button"]')).not.toBeNull()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      expect(container.querySelector('[data-testid="cleanup-confirm-dialog"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="cleanup-button"]')).toBeNull()
    })

    it('cancel returns from confirming to idle', () => {
      vi.mocked(cleanupTasks).mockResolvedValue(RESULT_EMPTY)
      const { container } = renderPanel()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      expect(container.querySelector('[data-testid="cleanup-confirm-dialog"]')).not.toBeNull()
      fireEvent.click(container.querySelector('[data-testid="cleanup-cancel-btn"]')!)
      expect(container.querySelector('[data-testid="cleanup-button"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="cleanup-confirm-dialog"]')).toBeNull()
    })
  })

  // ─── AC 3c: confirming → running → done lifecycle ──────────────────────────

  describe('AC 3c: full success lifecycle with real hook (real state transitions)', () => {
    it('reaches done state with empty result after confirm', async () => {
      vi.mocked(cleanupTasks).mockResolvedValue(RESULT_EMPTY)
      const { container } = renderPanel()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-released-count"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-testid="cleanup-archived-count"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="cleanup-skipped-count"]')).not.toBeNull()
    })

    it('shows zero counts in done state with empty result', async () => {
      vi.mocked(cleanupTasks).mockResolvedValue(RESULT_EMPTY)
      const { container } = renderPanel()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-released-count"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-testid="cleanup-released-count"]')!.textContent).toMatch(/0/)
      expect(container.querySelector('[data-testid="cleanup-skipped-count"]')!.textContent).toMatch(/0/)
    })

    it('shows counts and skipped list with non-empty result', async () => {
      vi.mocked(cleanupTasks).mockResolvedValue(RESULT_WITH_SKIPPED)
      const { container } = renderPanel()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-skipped-list"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-testid="cleanup-released-count"]')!.textContent).toMatch(/2/)
    })

    it('shows full result with multiple released, archived, and skipped', async () => {
      vi.mocked(cleanupTasks).mockResolvedValue(RESULT_FULL)
      const { container } = renderPanel()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-released-count"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-testid="cleanup-released-count"]')!.textContent).toMatch(/3/)
      expect(container.querySelector('[data-testid="cleanup-archived-count"]')!.textContent).toMatch(/3/)
      expect(container.querySelector('[data-testid="cleanup-skipped-count"]')!.textContent).toMatch(/2/)
    })

    it('skipped list absent when result has no skipped items', async () => {
      vi.mocked(cleanupTasks).mockResolvedValue(RESULT_EMPTY)
      const { container } = renderPanel()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-released-count"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-testid="cleanup-skipped-list"]')).toBeNull()
    })

    it('dismiss button in done state returns to idle', async () => {
      vi.mocked(cleanupTasks).mockResolvedValue(RESULT_EMPTY)
      const { container } = renderPanel()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-dismiss-btn"]')).not.toBeNull()
      })
      fireEvent.click(container.querySelector('[data-testid="cleanup-dismiss-btn"]')!)
      expect(container.querySelector('[data-testid="cleanup-button"]')).not.toBeNull()
    })

    it('onSuccess fires after successful cleanup lifecycle', async () => {
      const onSuccess = vi.fn()
      vi.mocked(cleanupTasks).mockResolvedValue(RESULT_EMPTY)
      const { container } = renderPanel({ onSuccess })
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledOnce()
      })
    })
  })

  // ─── AC 3c: confirming → error lifecycle ───────────────────────────────────

  describe('AC 3c: error lifecycle with real hook (real state transitions)', () => {
    it('reaches error state when API rejects with Error', async () => {
      vi.mocked(cleanupTasks).mockRejectedValue(new Error('Cleanup failed: disk full'))
      const { container } = renderPanel()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-error"]')).not.toBeNull()
      })
      expect(container.querySelector('[data-testid="cleanup-error"]')!.textContent).toContain('Cleanup failed: disk full')
    })

    it('retry button in error state triggers another cleanup attempt', async () => {
      vi.mocked(cleanupTasks)
        .mockRejectedValueOnce(new Error('first failure'))
        .mockResolvedValueOnce(RESULT_EMPTY)
      const { container } = renderPanel()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-retry-btn"]')).not.toBeNull()
      })
      fireEvent.click(container.querySelector('[data-testid="cleanup-retry-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-released-count"]')).not.toBeNull()
      })
    })

    it('dismiss in error state returns to idle', async () => {
      vi.mocked(cleanupTasks).mockRejectedValue(new Error('Cleanup failed'))
      const { container } = renderPanel()
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-dismiss-btn"]')).not.toBeNull()
      })
      fireEvent.click(container.querySelector('[data-testid="cleanup-dismiss-btn"]')!)
      expect(container.querySelector('[data-testid="cleanup-button"]')).not.toBeNull()
    })

    it('onSuccess not called when cleanup errors', async () => {
      const onSuccess = vi.fn()
      vi.mocked(cleanupTasks).mockRejectedValue(new Error('Cleanup failed'))
      const { container } = renderPanel({ onSuccess })
      fireEvent.click(container.querySelector('[data-testid="cleanup-button"]')!)
      fireEvent.click(container.querySelector('[data-testid="cleanup-confirm-btn"]')!)
      await waitFor(() => {
        expect(container.querySelector('[data-testid="cleanup-error"]')).not.toBeNull()
      })
      expect(onSuccess).not.toHaveBeenCalled()
    })
  })
})
