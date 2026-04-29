/**
 * Failing tests for #1164: RF-02 repairStorage API client (Test AC - edge cases)
 *
 * Context: api/repair.ts was implemented in #1163 builder run — all happy-path
 * and standard error AC lines are GREEN in repairStorage_1163.test.ts.
 *
 * This file targets the ONE remaining gap: non-Error network rejections.
 * AC4 says "network error rejects with Error (td:2)". At td:2, edge cases
 * include non-Error rejection values (strings, numbers, plain objects). The
 * current implementation does NOT wrap these — they propagate as-is, failing
 * `rejects.toBeInstanceOf(Error)`.
 *
 * Covered by this file:
 *   - AC4 edge: string rejection → must be an Error instance (FAIL)
 *   - AC4 edge: numeric rejection → must be an Error instance (FAIL)
 *   - AC4 edge: plain-object rejection → must be an Error instance (FAIL)
 *
 * AC1/AC2/AC3/AC5 happy paths are already covered by repairStorage_1163.test.ts.
 *
 * Builder action required: move this file to
 *   serve/cockpit/web/src/__tests__/repairStorage_1164.test.ts
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { repairStorage } from '../api/repair'

// ---------------------------------------------------------------------------

describe('TestFromAC_repairStorage_1164', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // AC4: network error rejects with Error — non-Error rejection edge cases
  // The implementation currently lacks a catch wrapper that normalises
  // non-Error values to Error instances; these three tests all FAIL.

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
})
