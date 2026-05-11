/**
 * RF-02 repairStorage API client (edge cases + retry strengthening)
 *
 * Context: api/repair.ts was implemented in #1163 builder run — all happy-path
 * and standard error AC lines are GREEN in repairStorage_1163.test.ts.
 *
 * This file covers:
 *   - AC4 edge: non-Error network rejections (existing, GREEN)
 *   - AC3 proof: HTTP error message contains numeric status code (existing, GREEN)
 *   - AC4 proof: native Error is rethrown unchanged (existing, GREEN)
 *   - AC4 proof: non-Error rejections wrapped with descriptive message (existing, GREEN)
 *   - AC4 proof: non-serializable (circular) rejection produces wrapped Error (RETRY v4 — RED)
 *   - AC5 proof: RepairOutcome.action literal-union compile-time guard (existing, GREEN)
 *
 * Retry (reviewer pass 1): Added groups 2–5 per required additions in ## Review Evidence.
 * Retry (reviewer pass 3): Added plain-object message quality tests per refined Test AC line 4.
 * Retry (reviewer pass 4 / loop-breaker cycle 3): Added circular-object group per final AC refinement.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { repairStorage } from '../api/repair'
import type { RepairOutcome } from '../api/repair'

// ---------------------------------------------------------------------------

describe('TestFromAC_repairStorage_1164', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // --- AC4 edge: non-Error network rejection must resolve as Error instance ---
  // Existing tests — GREEN after builder added catch wrapper.

  describe('AC4 edge: non-Error network rejection must resolve as Error instance', () => {
    it('wraps string network rejection in an Error', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject('network timeout')))
      await expect(repairStorage()).rejects.toBeInstanceOf(Error)
    })

    it('wraps numeric network rejection in an Error', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(408)))
      await expect(repairStorage()).rejects.toBeInstanceOf(Error)
    })

    it('wraps plain-object network rejection in an Error', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject({ code: 'ECONNREFUSED' })))
      await expect(repairStorage()).rejects.toBeInstanceOf(Error)
    })
  })

  // --- AC3: HTTP error message contains the numeric status code (Test AC line 41) ---
  // Reviewer: "Test AC line 41 is missing outright; the status-code requirement is
  // implemented but unproven." These tests lock the status code into the message contract.

  describe('AC3: HTTP error message contains the numeric status code', () => {
    it('error message for non-ok 500 response contains "500"', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) })),
      )
      const error = await repairStorage().catch((e: unknown) => e as Error)
      expect(error.message).toContain('500')
    })

    it('error message for non-ok 422 response contains "422"', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.resolve({ ok: false, status: 422, json: () => Promise.resolve({}) })),
      )
      const error = await repairStorage().catch((e: unknown) => e as Error)
      expect(error.message).toContain('422')
    })
  })

  // --- AC4: native Error is rethrown unchanged (same object identity) ---
  // Reviewer: "Assert native Error rejection is rethrown unchanged or preserves
  // original message or identity per the AC intent."

  describe('AC4: native Error rethrown unchanged', () => {
    it('rethrows a native Error as the exact same object (reference identity)', async () => {
      const originalError = new Error('original network error')
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(originalError)))
      const thrown = await repairStorage().catch((e: unknown) => e)
      expect(thrown).toBe(originalError)
    })

    it('rethrown native Error message is preserved unchanged', async () => {
      const originalError = new Error('specific error message abc123')
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(originalError)))
      const thrown = await repairStorage().catch((e: unknown) => e as Error)
      expect(thrown.message).toBe('specific error message abc123')
    })
  })

  // --- AC4: non-Error rejections produce a descriptive wrapped message ---
  // Reviewer: "Assert wrapped non-Error rejections produce a descriptive message,
  // not just an Error instance."

  describe('AC4: non-Error rejection wrapped with descriptive message', () => {
    it('wrapped string rejection message contains original string value', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject('network timeout')))
      const error = await repairStorage().catch((e: unknown) => e as Error)
      expect(error.message).toContain('network timeout')
    })

    it('wrapped numeric rejection message contains numeric value as string', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(408)))
      const error = await repairStorage().catch((e: unknown) => e as Error)
      expect(error.message).toContain('408')
    })

    it('wrapped plain-object rejection preserves original value on cause property', async () => {
      const originalCause = { code: 'ECONNREFUSED' }
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(originalCause)))
      const error = await repairStorage().catch(
        (e: unknown) => e as Error & { cause?: unknown },
      )
      expect(error.cause).toEqual(originalCause)
    })

    it('wrapped plain-object rejection message does not degrade to [object Object]', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject({ code: 'ECONNREFUSED' })))
      const error = await repairStorage().catch((e: unknown) => e as Error)
      expect(error.message).not.toContain('[object Object]')
    })

    it('wrapped plain-object rejection message surfaces object content', async () => {
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject({ code: 'ECONNREFUSED' })))
      const error = await repairStorage().catch((e: unknown) => e as Error)
      expect(error.message).toMatch(/ECONNREFUSED|code/)
    })
  })

  // --- AC4: non-serializable (circular) rejection — loop-breaker cycle 3 AC refinement ---
  // Final AC line 4: non-serializable rejections must still produce a wrapped Error with
  // cause preserved and a non-empty fallback message — the serialization path must not throw.
  //
  // Current gap: repair.ts:22 calls JSON.stringify(error) without a try/catch fallback.
  // For a circular object, JSON.stringify throws TypeError('Converting circular structure to
  // JSON') before wrappedError is created, so:
  //   - error.cause is never set (undefined on the escaped TypeError)
  //   - error.message exposes JSON internals ("Converting circular structure to JSON")
  // Tests 1 and 2 below FAIL against the current implementation.
  // Tests 3 and 4 are regression guards (pass now, must continue to pass after builder fix).

  describe('AC4: non-serializable (circular) rejection produces wrapped Error', () => {
    it('circular-object rejection preserves original value on cause property', async () => {
      const circular: Record<string, unknown> = {}
      circular.self = circular
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(circular)))
      const error = await repairStorage().catch((e: unknown) => e as Error & { cause?: unknown })
      // FAIL: current impl lets JSON.stringify throw; the escaped TypeError has no cause set.
      expect(error.cause).toBe(circular)
    })

    it('circular-object rejection message does not expose JSON.stringify error internals', async () => {
      const circular: Record<string, unknown> = {}
      circular.self = circular
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(circular)))
      const error = await repairStorage().catch((e: unknown) => e as Error)
      // FAIL: current impl rejects with TypeError('Converting circular structure to JSON').
      expect(error.message).not.toMatch(/circular structure|cyclic/i)
    })

    it('circular-object rejection is an Error instance', async () => {
      const circular: Record<string, unknown> = {}
      circular.self = circular
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(circular)))
      // TypeError IS Error — regression guard only (passes currently).
      await expect(repairStorage()).rejects.toBeInstanceOf(Error)
    })

    it('circular-object rejection message is non-empty', async () => {
      const circular: Record<string, unknown> = {}
      circular.self = circular
      vi.stubGlobal('fetch', vi.fn(() => Promise.reject(circular)))
      const error = await repairStorage().catch((e: unknown) => e as Error)
      // Regression guard — passes now (TypeError has non-empty message).
      expect(error.message).toBeTruthy()
    })
  })

  // --- AC5: RepairOutcome.action is a literal union — compile-time guard ---
  // Reviewer: "Add a compile-time or equivalent binding check that fails if
  // RepairOutcome.action widens beyond 'fixed' | 'quarantined' | 'failed'."
  //
  // Mechanism: AssertEqual<T, U> resolves to `true` iff T and U are mutually assignable.
  // If action widens to `string`, AssertEqual resolves to `false` and the assignment
  // `const _guard: false = true` fails to compile, preventing the test suite from running.

  describe('AC5: RepairOutcome.action literal-union compile-time guard', () => {
    it('action type is exactly the literal union — compile error if widened to string', () => {
      type ActionValues = RepairOutcome['action']
      type AssertEqual<T, U> = [T] extends [U] ? ([U] extends [T] ? true : false) : false
      const _guard: AssertEqual<ActionValues, 'fixed' | 'quarantined' | 'failed'> = true
      void _guard
      // Runtime always passes; TypeScript catches widening at compile time.
      expect(true).toBe(true)
    })
  })
})

