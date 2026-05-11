/**
 * Workflow behavior tests1163: RF-01 repairStorage API client
 *
 * Covers: POST to /api/tasks/repair with no body, typed RepairOutcome[] return,
 * network and HTTP error rejection, and RepairOutcome type schema contract.
 * All tests are RED (failing) until the builder creates src/api/repair.ts.
 *
 * Builder: move this file to serve/cockpit/web/src/__tests__/repairStorage_1163.test.ts
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { repairStorage } from '../api/repair'
import type { RepairOutcome } from '../api/repair'

// --- Fixtures ----------------------------------------------------------------

const OUTCOME_FIXED: RepairOutcome = {
  task_id: 42,
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

function makeSuccessFetch(outcomes: RepairOutcome[]) {
  return vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(outcomes),
    }),
  )
}

function makeNetworkErrorFetch(message = 'Network failure') {
  return vi.fn(() => Promise.reject(new Error(message)))
}

function makeNonOkFetch(status: number) {
  return vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve({ detail: 'Server error' }),
    }),
  )
}

// --- Tests -------------------------------------------------------------------

describe('TestFromAC_repairStorage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // --- AC1: POST to /api/tasks/repair with no body -------------------------

  describe('AC1: sends POST to /api/tasks/repair with no body', () => {
    it('sends a request to /api/tasks/repair', async () => {
      const fetchMock = makeSuccessFetch([])
      vi.stubGlobal('fetch', fetchMock)
      await repairStorage()
      expect(fetchMock).toHaveBeenCalledWith('/api/tasks/repair', expect.anything())
    })

    it('uses HTTP method POST', async () => {
      const fetchMock = makeSuccessFetch([])
      vi.stubGlobal('fetch', fetchMock)
      await repairStorage()
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/tasks/repair',
        expect.objectContaining({ method: 'POST' }),
      )
    })

    it('sends no body in the POST request', async () => {
      const fetchMock = makeSuccessFetch([])
      vi.stubGlobal('fetch', fetchMock)
      await repairStorage()
      const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined
      expect(init?.body).toBeUndefined()
    })

    it('sends exactly one request per call', async () => {
      const fetchMock = makeSuccessFetch([])
      vi.stubGlobal('fetch', fetchMock)
      await repairStorage()
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
  })

  // --- AC2: successful response returns RepairOutcome[] --------------------

  describe('AC2: successful response returns typed RepairOutcome[] array', () => {
    it('returns an array on success', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_FIXED]))
      const result = await repairStorage()
      expect(Array.isArray(result)).toBe(true)
    })

    it('returns an empty array when server returns no outcomes', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([]))
      const result = await repairStorage()
      expect(result).toEqual([])
    })

    it('returns parsed outcome items with correct length', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_FIXED, OUTCOME_QUARANTINED]))
      const result = await repairStorage()
      expect(result).toHaveLength(2)
    })

    it('returns outcome with task_id, file_path, code, action, detail fields', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_FIXED]))
      const result = await repairStorage()
      expect(result[0]).toMatchObject({
        task_id: 42,
        file_path: '/tasks/TASK-001.md',
        code: 'MISSING_STATUS',
        action: 'fixed',
        detail: 'Status field added',
      })
    })

    it('preserves null task_id from backend', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_QUARANTINED]))
      const result = await repairStorage()
      expect(result[0].task_id).toBeNull()
    })

    it('preserves null detail from backend', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_QUARANTINED]))
      const result = await repairStorage()
      expect(result[0].detail).toBeNull()
    })
  })

  // --- AC3: network/server error rejects with meaningful error -------------

  describe('AC3: network or server error rejects with meaningful error', () => {
    it('rejects on network failure', async () => {
      vi.stubGlobal('fetch', makeNetworkErrorFetch('Network failure'))
      await expect(repairStorage()).rejects.toThrow()
    })

    it('rejects with an Error instance on network failure', async () => {
      vi.stubGlobal('fetch', makeNetworkErrorFetch('Network failure'))
      await expect(repairStorage()).rejects.toBeInstanceOf(Error)
    })

    it('rejects with a non-empty message on network failure', async () => {
      vi.stubGlobal('fetch', makeNetworkErrorFetch('Network failure'))
      await expect(repairStorage()).rejects.toMatchObject({
        message: expect.stringMatching(/.+/),
      })
    })

    it('rejects on non-ok HTTP 500 response', async () => {
      vi.stubGlobal('fetch', makeNonOkFetch(500))
      await expect(repairStorage()).rejects.toThrow()
    })

    it('rejects with an Error instance on HTTP error response', async () => {
      vi.stubGlobal('fetch', makeNonOkFetch(500))
      await expect(repairStorage()).rejects.toBeInstanceOf(Error)
    })

    it('rejects with non-empty message on HTTP error response', async () => {
      vi.stubGlobal('fetch', makeNonOkFetch(500))
      await expect(repairStorage()).rejects.toMatchObject({
        message: expect.stringMatching(/.+/),
      })
    })

    it('rejects on non-ok HTTP 422 response', async () => {
      vi.stubGlobal('fetch', makeNonOkFetch(422))
      await expect(repairStorage()).rejects.toThrow()
    })
  })

  // --- AC4: RepairOutcome type matches backend schema ----------------------
  //
  // TypeScript compile-time contract: the OUTCOME_* fixtures above use
  // `RepairOutcome` type annotation — if the exported type doesn't satisfy
  // the schema, compilation fails. Runtime assertions below validate the
  // runtime-level contract (action union, nullable task_id).

  describe('AC4: RepairOutcome schema — action union literal, task_id nullable', () => {
    it('action "fixed" is a valid RepairOutcome action value', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_FIXED]))
      const result = await repairStorage()
      expect(result[0].action).toBe('fixed')
    })

    it('action "quarantined" is a valid RepairOutcome action value', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_QUARANTINED]))
      const result = await repairStorage()
      expect(result[0].action).toBe('quarantined')
    })

    it('action "failed" is a valid RepairOutcome action value', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_FAILED]))
      const result = await repairStorage()
      expect(result[0].action).toBe('failed')
    })

    it('task_id accepts null (nullable contract)', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_QUARANTINED]))
      const result = await repairStorage()
      expect(result[0].task_id).toBeNull()
    })

    it('task_id accepts a positive integer', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_FIXED]))
      const result = await repairStorage()
      expect(typeof result[0].task_id).toBe('number')
    })

    it('file_path is a string', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_FIXED]))
      const result = await repairStorage()
      expect(typeof result[0].file_path).toBe('string')
    })

    it('code is a string', async () => {
      vi.stubGlobal('fetch', makeSuccessFetch([OUTCOME_FIXED]))
      const result = await repairStorage()
      expect(typeof result[0].code).toBe('string')
    })
  })
})
