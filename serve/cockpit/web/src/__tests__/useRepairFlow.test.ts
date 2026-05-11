/**
 * RF-03 useRepairFlow hook state machine
 *
 * Covers: initial idle state, requestRepair → confirming, confirmRepair → repairing,
 * successful repair → done with grouped outcomes (fixed/quarantined/failed buckets),
 * cancelRepair → idle (from confirming), API error → error state with message,
 * dismissResults → idle (from done and from error), and onSuccess callback triggered
 * after successful repair.
 *
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRepairFlow } from '../hooks/useRepairFlow'
import type { RepairOutcome } from '../api/repair'

vi.mock('../api/repair', () => ({
  repairStorage: vi.fn(),
}))

import { repairStorage } from '../api/repair'

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

const MIXED_OUTCOMES: RepairOutcome[] = [OUTCOME_FIXED, OUTCOME_QUARANTINED, OUTCOME_FAILED]

function mockRepairSuccess(outcomes: RepairOutcome[] = []): void {
  vi.mocked(repairStorage).mockResolvedValueOnce(outcomes)
}

function mockRepairError(message = 'Server error'): void {
  vi.mocked(repairStorage).mockRejectedValueOnce(new Error(message))
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_useRepairFlow', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  // ─── AC1: hook starts in idle state ──────────────────────────────────────

  describe('AC1: hook starts in idle state (no modal, no results)', () => {
    it('initial phase is idle', () => {
      const { result } = renderHook(() => useRepairFlow())
      expect(result.current.phase).toBe('idle')
    })

    it('initial corruptionCount is null', () => {
      const { result } = renderHook(() => useRepairFlow())
      expect(result.current.corruptionCount).toBeNull()
    })

    it('initial results is null', () => {
      const { result } = renderHook(() => useRepairFlow())
      expect(result.current.results).toBeNull()
    })

    it('initial error is null', () => {
      const { result } = renderHook(() => useRepairFlow())
      expect(result.current.error).toBeNull()
    })
  })

  // ─── AC2: requestRepair(count) transitions to confirming state ───────────

  describe('AC2: requestRepair(count) transitions to confirming state with corruption count', () => {
    it('phase becomes confirming after requestRepair', () => {
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(3) })
      expect(result.current.phase).toBe('confirming')
    })

    it('corruptionCount is set to the supplied count', () => {
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(5) })
      expect(result.current.corruptionCount).toBe(5)
    })

    it('corruptionCount reflects the exact count passed in', () => {
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(12) })
      expect(result.current.corruptionCount).toBe(12)
    })

    it('results remain null in confirming state', () => {
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(2) })
      expect(result.current.results).toBeNull()
    })

    it('error remains null in confirming state', () => {
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(2) })
      expect(result.current.error).toBeNull()
    })
  })

  // ─── AC3: confirmRepair() calls repairStorage and transitions to repairing ──

  describe('AC3: confirmRepair() calls repairStorage() and transitions to repairing state', () => {
    it('calls repairStorage() when confirmRepair is invoked', async () => {
      mockRepairSuccess([])
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(1) })
      await act(async () => { result.current.confirmRepair() })
      expect(vi.mocked(repairStorage)).toHaveBeenCalledTimes(1)
    })

    it('phase is repairing immediately after confirmRepair before resolution', async () => {
      // Make repairStorage hang so we can observe the intermediate state
      let resolveRepair!: (v: RepairOutcome[]) => void
      vi.mocked(repairStorage).mockReturnValueOnce(
        new Promise<RepairOutcome[]>((resolve) => { resolveRepair = resolve }),
      )
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(1) })
      act(() => { result.current.confirmRepair() })
      expect(result.current.phase).toBe('repairing')
      // Clean up: resolve to avoid unhandled promise
      await act(async () => { resolveRepair([]) })
    })

    it('repairStorage is called with no arguments', async () => {
      mockRepairSuccess([])
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(1) })
      await act(async () => { result.current.confirmRepair() })
      expect(vi.mocked(repairStorage)).toHaveBeenCalledWith()
    })
  })

  // ─── AC4: successful repair transitions to done with grouped outcomes ─────

  describe('AC4: successful repair transitions to done state with grouped outcomes', () => {
    it('phase becomes done after successful repair', async () => {
      mockRepairSuccess(MIXED_OUTCOMES)
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(3) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.phase).toBe('done')
    })

    it('results.fixed contains outcomes with action=fixed', async () => {
      mockRepairSuccess(MIXED_OUTCOMES)
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(3) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.results?.fixed).toHaveLength(1)
      expect(result.current.results?.fixed[0].action).toBe('fixed')
    })

    it('results.quarantined contains outcomes with action=quarantined', async () => {
      mockRepairSuccess(MIXED_OUTCOMES)
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(3) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.results?.quarantined).toHaveLength(1)
      expect(result.current.results?.quarantined[0].action).toBe('quarantined')
    })

    it('results.failed contains outcomes with action=failed', async () => {
      mockRepairSuccess(MIXED_OUTCOMES)
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(3) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.results?.failed).toHaveLength(1)
      expect(result.current.results?.failed[0].action).toBe('failed')
    })

    it('empty outcome list produces empty groups', async () => {
      mockRepairSuccess([])
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(0) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.phase).toBe('done')
      expect(result.current.results?.fixed).toHaveLength(0)
      expect(result.current.results?.quarantined).toHaveLength(0)
      expect(result.current.results?.failed).toHaveLength(0)
    })

    it('multiple outcomes of the same action all appear in the correct group', async () => {
      const twoFixed: RepairOutcome[] = [
        { ...OUTCOME_FIXED, task_id: 1 },
        { ...OUTCOME_FIXED, task_id: 2 },
      ]
      mockRepairSuccess(twoFixed)
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(2) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.results?.fixed).toHaveLength(2)
    })

    it('error is null in done state after successful repair', async () => {
      mockRepairSuccess(MIXED_OUTCOMES)
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(3) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.error).toBeNull()
    })
  })

  // ─── AC5: cancelRepair() returns to idle from confirming ─────────────────

  describe('AC5: cancelRepair() returns to idle state from confirming', () => {
    it('phase returns to idle after cancelRepair from confirming', () => {
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(2) })
      expect(result.current.phase).toBe('confirming')
      act(() => { result.current.cancelRepair() })
      expect(result.current.phase).toBe('idle')
    })

    it('corruptionCount is reset to null after cancelRepair', () => {
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(4) })
      act(() => { result.current.cancelRepair() })
      expect(result.current.corruptionCount).toBeNull()
    })

    it('repairStorage is NOT called when cancelRepair is used', () => {
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(2) })
      act(() => { result.current.cancelRepair() })
      expect(vi.mocked(repairStorage)).not.toHaveBeenCalled()
    })
  })

  // ─── AC6: API error during repair transitions to error state ─────────────

  describe('AC6: API error during repair transitions to error state with message', () => {
    it('phase becomes error when repairStorage rejects', async () => {
      mockRepairError('Storage failure')
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(1) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.phase).toBe('error')
    })

    it('error field contains the error message', async () => {
      mockRepairError('Storage failure')
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(1) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.error).toBe('Storage failure')
    })

    it('error is a non-empty string in error state', async () => {
      mockRepairError('Something went wrong')
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(1) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.error).toBe('Something went wrong')
    })

    it('results remain null in error state', async () => {
      mockRepairError('Network error')
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(1) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.results).toBeNull()
    })

    it('non-Error rejection produces a non-empty error message', async () => {
      vi.mocked(repairStorage).mockRejectedValueOnce('plain string rejection')
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(1) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.phase).toBe('error')
      expect(result.current.error).toBe('plain string rejection')
    })
  })

  // ─── AC7: dismissResults() returns to idle from done or error ────────────

  describe('AC7: dismissResults() returns to idle from done or error state', () => {
    it('phase returns to idle after dismissResults from done state', async () => {
      mockRepairSuccess([])
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(0) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.phase).toBe('done')
      act(() => { result.current.dismissResults() })
      expect(result.current.phase).toBe('idle')
    })

    it('results is reset to null after dismissResults from done state', async () => {
      mockRepairSuccess(MIXED_OUTCOMES)
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(3) })
      await act(async () => { result.current.confirmRepair() })
      act(() => { result.current.dismissResults() })
      expect(result.current.results).toBeNull()
    })

    it('phase returns to idle after dismissResults from error state', async () => {
      mockRepairError('Oops')
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(1) })
      await act(async () => { result.current.confirmRepair() })
      expect(result.current.phase).toBe('error')
      act(() => { result.current.dismissResults() })
      expect(result.current.phase).toBe('idle')
    })

    it('error is reset to null after dismissResults from error state', async () => {
      mockRepairError('Oops')
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(1) })
      await act(async () => { result.current.confirmRepair() })
      act(() => { result.current.dismissResults() })
      expect(result.current.error).toBeNull()
    })

    it('corruptionCount is reset to null after dismissResults', async () => {
      mockRepairSuccess([])
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(7) })
      await act(async () => { result.current.confirmRepair() })
      act(() => { result.current.dismissResults() })
      expect(result.current.corruptionCount).toBeNull()
    })
  })

  // ─── AC8: hook triggers scan re-poll callback after successful repair ─────

  describe('AC8: hook triggers scan re-poll callback after successful repair', () => {
    it('calls onSuccess callback after successful repair', async () => {
      mockRepairSuccess([])
      const onSuccess = vi.fn()
      const { result } = renderHook(() => useRepairFlow({ onSuccess }))
      act(() => { result.current.requestRepair(0) })
      await act(async () => { result.current.confirmRepair() })
      expect(onSuccess).toHaveBeenCalledTimes(1)
    })

    it('does NOT call onSuccess callback when repair fails', async () => {
      mockRepairError('Fail')
      const onSuccess = vi.fn()
      const { result } = renderHook(() => useRepairFlow({ onSuccess }))
      act(() => { result.current.requestRepair(1) })
      await act(async () => { result.current.confirmRepair() })
      expect(onSuccess).not.toHaveBeenCalled()
    })

    it('does NOT call onSuccess callback when repair is cancelled', () => {
      const onSuccess = vi.fn()
      const { result } = renderHook(() => useRepairFlow({ onSuccess }))
      act(() => { result.current.requestRepair(1) })
      act(() => { result.current.cancelRepair() })
      expect(onSuccess).not.toHaveBeenCalled()
    })

    it('works without onSuccess callback (no error when omitted)', async () => {
      mockRepairSuccess([])
      const { result } = renderHook(() => useRepairFlow())
      act(() => { result.current.requestRepair(0) })
      await expect(
        act(async () => { result.current.confirmRepair() }),
      ).resolves.not.toThrow()
    })
  })
})

