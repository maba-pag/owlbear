/**
 * Gap-specific failing tests for #936: G5 — useOptimistic snapshot capture bug
 *
 * The current optimistic.ts sets snapshot.current = initial at mount and never
 * updates it before a mutation. These tests verify that rollback restores the
 * state captured immediately BEFORE the last mutation, not the initial mount
 * state. All tests are RED (failing) until the builder fixes optimistic.ts.
 *
 * Fix pattern (per architecture review):
 *   function mutate(updater: (s: T) => T): void {
 *     setState((prev) => {
 *       snapshot.current = prev  // capture pre-mutation state
 *       return updater(prev)
 *     })
 *   }
 */
import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useOptimistic } from '../hooks/useOptimistic'

describe('TestFromAC_SnapshotCapture', () => {
  // ─── Snapshot captured before each mutation ───────────────────────────────

  describe('snapshot captures state before each mutate call', () => {
    it('rollback after two mutations restores state to after-first-mutate, not initial', () => {
      const { result } = renderHook(() => useOptimistic(0))

      // First mutate (simulates server-driven update arriving before user edits)
      act(() => {
        result.current.mutate(() => 50)
      })
      expect(result.current.state).toBe(50)

      // Second mutate (user action)
      act(() => {
        result.current.mutate((n) => n + 5)
      })
      expect(result.current.state).toBe(55)

      // Rollback must restore to 50 (pre-last-mutation), NOT 0 (initial mount)
      act(() => {
        result.current.rollback()
      })
      expect(result.current.state).toBe(50)
    })

    it('snapshot is the state immediately before the most recent mutate, not mount state', () => {
      const { result } = renderHook(() => useOptimistic({ step: 1, value: 'a' }))

      act(() => {
        result.current.mutate(() => ({ step: 2, value: 'b' }))
      })
      expect(result.current.state).toEqual({ step: 2, value: 'b' })

      act(() => {
        result.current.mutate((s) => ({ ...s, value: 'c' }))
      })
      expect(result.current.state).toEqual({ step: 2, value: 'c' })

      // Rollback: must go to { step: 2, value: 'b' }, NOT { step: 1, value: 'a' }
      act(() => {
        result.current.rollback()
      })
      expect(result.current.state).toEqual({ step: 2, value: 'b' })
    })

    it('snapshot is NOT the initial mount state when a prior mutate has occurred', () => {
      const { result } = renderHook(() => useOptimistic(100))

      // First mutate advances state
      act(() => {
        result.current.mutate(() => 200)
      })
      // Second mutate (user action to be rolled back)
      act(() => {
        result.current.mutate(() => 999)
      })

      act(() => {
        result.current.rollback()
      })
      expect(result.current.state).not.toBe(100) // must NOT revert to mount state
      expect(result.current.state).toBe(200) // must restore intermediate value
    })
  })

  // ─── Boundary: one level of rollback history ──────────────────────────────

  describe('boundary: snapshot stores state before the last mutate only', () => {
    it('rollback after three mutations restores state before the last mutation', () => {
      const { result } = renderHook(() => useOptimistic(0))

      act(() => {
        result.current.mutate(() => 10)
      })
      act(() => {
        result.current.mutate(() => 20)
      })
      act(() => {
        result.current.mutate(() => 30)
      })

      act(() => {
        result.current.rollback()
      })
      // Rollback goes one step back: state before last mutate = 20 (not 0)
      expect(result.current.state).toBe(20)
    })
  })
})
