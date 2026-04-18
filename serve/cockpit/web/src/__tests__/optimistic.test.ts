/**
 * Failing tests for #935: optimistic UI hook
 *
 * Covers: immediate state update on mutation, and rollback to pre-mutation
 * snapshot on API error. All tests are RED (failing) until the builder
 * implements useOptimistic in optimistic.ts.
 */
import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useOptimistic } from '../optimistic'

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_OptimisticUI', () => {
  // ─── Mutation immediately updates local state ─────────────────────────────

  describe('mutation updates state immediately', () => {
    it('mutate applies the updater function to current state', () => {
      const { result } = renderHook(() => useOptimistic({ count: 0 }))
      act(() => {
        result.current.mutate((s) => ({ count: s.count + 1 }))
      })
      expect(result.current.state).toEqual({ count: 1 })
    })

    it('mutate with a replacement value updates state to the new value', () => {
      const { result } = renderHook(() => useOptimistic('original'))
      act(() => {
        result.current.mutate(() => 'mutated')
      })
      expect(result.current.state).toBe('mutated')
    })

    it('successive mutate calls compose on the updated state', () => {
      const { result } = renderHook(() => useOptimistic(0))
      act(() => {
        result.current.mutate((n) => n + 10)
        result.current.mutate((n) => n + 5)
      })
      expect(result.current.state).toBe(15)
    })
  })

  // ─── Rollback to pre-mutation snapshot ───────────────────────────────────

  describe('rollback restores pre-mutation snapshot', () => {
    it('rollback after mutate reverts state to the value before the mutation', () => {
      const { result } = renderHook(() => useOptimistic({ value: 'original' }))
      act(() => {
        result.current.mutate(() => ({ value: 'mutated' }))
      })
      // Verify mutation took effect (fails in RED — stub mutate is noop)
      expect(result.current.state.value).toBe('mutated')
      act(() => {
        result.current.rollback()
      })
      expect(result.current.state.value).toBe('original')
    })

    it('rollback snapshot is the state immediately before the first mutate call', () => {
      const { result } = renderHook(() => useOptimistic(100))
      act(() => {
        result.current.mutate((n) => n + 999)
      })
      // After mutation state should be 1099
      expect(result.current.state).toBe(1099)
      act(() => {
        result.current.rollback()
      })
      // Rollback goes to 100, not 0 or intermediate
      expect(result.current.state).toBe(100)
    })

    it('state after rollback equals the pre-mutation snapshot (not undefined)', () => {
      const { result } = renderHook(() => useOptimistic({ x: 42 }))
      act(() => {
        result.current.mutate((s) => ({ x: s.x * 2 }))
      })
      // Pre-rollback state should be 84
      expect(result.current.state.x).toBe(84)
      act(() => {
        result.current.rollback()
      })
      expect(result.current.state).not.toBeUndefined()
      expect(result.current.state.x).toBe(42)
    })
  })
})
