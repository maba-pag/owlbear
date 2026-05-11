/**
 *
 * AC 3b (td:2): A cleanup flow hook manages lifecycle phases
 *               (idle → confirming → running → done → error) and exposes
 *               phase, results, error, and control functions.
 *               Lifecycle shape follows useRepairFlow — result model differs
 *               (CleanupResult vs RepairOutcome).
 *
 * RED reason: src/hooks/useCleanupFlow.ts does not exist — collection fails with ImportError.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCleanupFlow } from '../hooks/useCleanupFlow'
import type { CleanupResult } from '../api/cleanup'

vi.mock('../api/cleanup', () => ({
  cleanupTasks: vi.fn(),
}))

import { cleanupTasks } from '../api/cleanup'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const RESULT_WITH_SKIPPED: CleanupResult = {
  released_claim_ids: [1, 2],
  archived_task_ids: [10, 20, 30],
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

function mockCleanupSuccess(result: CleanupResult = RESULT_EMPTY): void {
  vi.mocked(cleanupTasks).mockResolvedValueOnce(result)
}

function mockCleanupError(message = 'Cleanup failed'): void {
  vi.mocked(cleanupTasks).mockRejectedValueOnce(new Error(message))
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_useCleanupFlow', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  // ─── AC 3b: initial idle state ───────────────────────────────────────────

  describe('AC 3b: hook starts in idle state', () => {
    it('initial phase is idle', () => {
      const { result } = renderHook(() => useCleanupFlow())
      expect(result.current.phase).toBe('idle')
    })

    it('initial results is null', () => {
      const { result } = renderHook(() => useCleanupFlow())
      expect(result.current.results).toBeNull()
    })

    it('initial error is null', () => {
      const { result } = renderHook(() => useCleanupFlow())
      expect(result.current.error).toBeNull()
    })
  })

  // ─── AC 3b: requestCleanup() transitions to confirming ───────────────────

  describe('AC 3b: requestCleanup() transitions to confirming', () => {
    it('phase becomes confirming after requestCleanup', () => {
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      expect(result.current.phase).toBe('confirming')
    })

    it('results remain null in confirming state', () => {
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      expect(result.current.results).toBeNull()
    })

    it('error remains null in confirming state', () => {
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      expect(result.current.error).toBeNull()
    })
  })

  // ─── AC 3b: cancelCleanup() returns to idle from confirming ──────────────

  describe('AC 3b: cancelCleanup() returns to idle from confirming', () => {
    it('phase returns to idle after cancelCleanup', () => {
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      act(() => { result.current.cancelCleanup() })
      expect(result.current.phase).toBe('idle')
    })

    it('results remain null after cancelCleanup', () => {
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      act(() => { result.current.cancelCleanup() })
      expect(result.current.results).toBeNull()
    })
  })

  // ─── AC 3b: confirmCleanup() transitions through running → done ──────────

  describe('AC 3b: confirmCleanup() transitions running → done with CleanupResult', () => {
    it('phase transitions to running then done on success', async () => {
      mockCleanupSuccess(RESULT_EMPTY)
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(result.current.phase).toBe('done')
    })

    it('results contain released_claim_ids on success', async () => {
      mockCleanupSuccess(RESULT_WITH_SKIPPED)
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(result.current.results?.released_claim_ids).toEqual([1, 2])
    })

    it('results contain archived_task_ids on success', async () => {
      mockCleanupSuccess(RESULT_WITH_SKIPPED)
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(result.current.results?.archived_task_ids).toEqual([10, 20, 30])
    })

    it('results contain skipped_items on success', async () => {
      mockCleanupSuccess(RESULT_WITH_SKIPPED)
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(result.current.results?.skipped_items).toHaveLength(2)
      expect(result.current.results?.skipped_items[0].path).toBe('/tasks/TASK-099.md')
      expect(result.current.results?.skipped_items[0].reason).toBe('File locked')
    })

    it('handles empty CleanupResult (all arrays empty)', async () => {
      mockCleanupSuccess(RESULT_EMPTY)
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(result.current.phase).toBe('done')
      expect(result.current.results?.released_claim_ids).toEqual([])
      expect(result.current.results?.archived_task_ids).toEqual([])
      expect(result.current.results?.skipped_items).toEqual([])
    })

    it('error is null after successful cleanup', async () => {
      mockCleanupSuccess(RESULT_EMPTY)
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(result.current.error).toBeNull()
    })
  })

  // ─── AC 3b: onSuccess callback ───────────────────────────────────────────

  describe('AC 3b: onSuccess callback fires after successful cleanup', () => {
    it('calls onSuccess after successful cleanup', async () => {
      mockCleanupSuccess(RESULT_EMPTY)
      const onSuccess = vi.fn()
      const { result } = renderHook(() => useCleanupFlow({ onSuccess }))
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(onSuccess).toHaveBeenCalledOnce()
    })

    it('does not call onSuccess when cleanup errors', async () => {
      mockCleanupError()
      const onSuccess = vi.fn()
      const { result } = renderHook(() => useCleanupFlow({ onSuccess }))
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(onSuccess).not.toHaveBeenCalled()
    })
  })

  // ─── AC 3b: API error → error phase ──────────────────────────────────────

  describe('AC 3b: API error transitions to error phase with message', () => {
    it('phase becomes error when cleanupTasks rejects', async () => {
      mockCleanupError('Cleanup failed: disk full')
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(result.current.phase).toBe('error')
    })

    it('error message is set when cleanupTasks rejects', async () => {
      mockCleanupError('Cleanup failed: disk full')
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(result.current.error).toBe('Cleanup failed: disk full')
    })

    it('results is null in error state', async () => {
      mockCleanupError()
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(result.current.results).toBeNull()
    })
  })

  // ─── AC 3b: dismissResults returns to idle ────────────────────────────────

  describe('AC 3b: dismissResults returns to idle from done or error', () => {
    it('phase returns to idle after dismissResults from done', async () => {
      mockCleanupSuccess(RESULT_EMPTY)
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      act(() => { result.current.dismissResults() })
      expect(result.current.phase).toBe('idle')
    })

    it('results cleared after dismissResults from done', async () => {
      mockCleanupSuccess(RESULT_WITH_SKIPPED)
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      act(() => { result.current.dismissResults() })
      expect(result.current.results).toBeNull()
    })

    it('phase returns to idle after dismissResults from error', async () => {
      mockCleanupError()
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      act(() => { result.current.dismissResults() })
      expect(result.current.phase).toBe('idle')
    })

    it('error cleared after dismissResults from error', async () => {
      mockCleanupError('Some error')
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      act(() => { result.current.dismissResults() })
      expect(result.current.error).toBeNull()
    })
  })

  // ─── AC 3b: running phase is observable before cleanupTasks resolves ─────────
  // Discriminating tests: must fail if setPhase('running') is removed from
  // useCleanupFlow.ts before the cleanupTasks await.

  describe('AC 3b: running phase entered before cleanupTasks resolves (discriminating)', () => {
    it('phase is running while cleanupTasks is in flight', async () => {
      let resolveCleanup!: (value: CleanupResult) => void
      vi.mocked(cleanupTasks).mockImplementationOnce(
        () => new Promise<CleanupResult>((resolve) => { resolveCleanup = resolve }),
      )
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })

      // Start confirmCleanup inside an async act() but do not await the inner promise —
      // setPhase('running') fires synchronously before the cleanupTasks await,
      // and await Promise.resolve() lets React flush that batch.
      await act(async () => {
        void result.current.confirmCleanup()
        await Promise.resolve()
      })

      // If setPhase('running') is removed, this assertion fails because phase
      // would remain 'confirming' until cleanupTasks resolves.
      expect(result.current.phase).toBe('running')

      // Complete the deferred cleanup and verify final transition.
      await act(async () => { resolveCleanup(RESULT_EMPTY) })
      expect(result.current.phase).toBe('done')
    })

    it('results remain null while phase is running', async () => {
      let resolveCleanup!: (value: CleanupResult) => void
      vi.mocked(cleanupTasks).mockImplementationOnce(
        () => new Promise<CleanupResult>((resolve) => { resolveCleanup = resolve }),
      )
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })

      await act(async () => {
        void result.current.confirmCleanup()
        await Promise.resolve()
      })

      expect(result.current.phase).toBe('running')
      expect(result.current.results).toBeNull()

      await act(async () => { resolveCleanup(RESULT_EMPTY) })
    })
  })

  // ─── AC 3b: non-Error rejection (String(caught) branch) ──────────────────
  // Discriminating test: must fail if the `String(caught)` branch on line 52
  // is removed (i.e., if only `Error.message` is used).

  describe('AC 3b: non-Error rejection uses String(caught) for error message', () => {
    it('error message is String(caught) when thrown value is not an Error instance', async () => {
      vi.mocked(cleanupTasks).mockRejectedValueOnce('raw string rejection')
      const { result } = renderHook(() => useCleanupFlow())
      act(() => { result.current.requestCleanup() })
      await act(async () => { await result.current.confirmCleanup() })
      expect(result.current.phase).toBe('error')
      // String('raw string rejection') === 'raw string rejection'
      expect(result.current.error).toBe('raw string rejection')
    })
  })
})

