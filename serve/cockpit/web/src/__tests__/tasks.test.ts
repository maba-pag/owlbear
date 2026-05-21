/**
 * tasks_1501: api/errors.ts + api/tasks.ts — AC-1 through AC-8
 *
 * RED reason: api/errors.ts and api/tasks.ts do not exist yet — all
 * imports fail at module resolution.
 *
 * Proof bundle: behavioral
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { ApiError } from '../api/errors'
import {
  getTask,
  moveTask,
  editTask,
  releaseTask,
} from '../api/tasks'
import type {
  TaskDetail,
  MoveRequest,
  EditRequest,
  ReleaseRequest,
} from '../api/tasks'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const TASK_DETAIL: TaskDetail = {
  id: 42,
  title: 'My task',
  status: 'in-progress',
  priority: 'needed',
  updated: '2026-05-12T00:00:00Z',
  created: '2026-05-01T00:00:00Z',
  body: 'Task body text',
  tags: ['cockpit', 'frontend'],
  blocked: false,
  block_reason: null,
  claimed: true,
  claimed_at: '2026-05-12T00:00:00Z',
  dep_status: null,
  parent: null,
  depends_on: [],
}

const TASK_DETAIL_MINIMAL: TaskDetail = {
  id: 1,
  title: 'Minimal',
  status: 'todo',
  priority: 'normal',
  updated: '2026-01-01T00:00:00Z',
  created: '2026-01-01T00:00:00Z',
  body: null,
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
  claimed_at: null,
  dep_status: null,
  parent: null,
  depends_on: [],
}

function makeSuccessFetch(data: TaskDetail) {
  return vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(data),
    }),
  )
}

function makeNonOkFetch(status: number, body: Record<string, unknown> = { detail: 'Server error' }) {
  return vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve(body),
    }),
  )
}

function makeNetworkErrorFetch(message = 'Network failure') {
  return vi.fn(() => Promise.reject(new Error(message)))
}

// ─── AC-1: ApiError class ──────────────────────────────────────────────────

describe('TestFromAC_ApiError', () => {
  it('constructs with status and message', () => {
    const err = new ApiError(409, 'conflict')
    expect(err.status).toBe(409)
    expect(err.message).toBe('conflict')
  })

  it('status property equals constructor argument', () => {
    const err = new ApiError(404, 'not found')
    expect(err.status).toBe(404)
  })

  it('message property equals constructor argument', () => {
    const err = new ApiError(422, 'unprocessable entity')
    expect(err.message).toBe('unprocessable entity')
  })

  it('extends Error — instanceof Error is true', () => {
    const err = new ApiError(500, 'server error')
    expect(err).toBeInstanceOf(Error)
  })

  it('is instanceof ApiError', () => {
    const err = new ApiError(500, 'server error')
    expect(err).toBeInstanceOf(ApiError)
  })

  it('boundary: status=0 is accepted', () => {
    const err = new ApiError(0, 'zero status')
    expect(err.status).toBe(0)
  })

  it('boundary: empty message string is accepted', () => {
    const err = new ApiError(400, '')
    expect(err.message).toBe('')
  })

  it('boundary: status=599 is accepted', () => {
    const err = new ApiError(599, 'timeout variant')
    expect(err.status).toBe(599)
  })
})

// ─── AC-2: getTask() ───────────────────────────────────────────────────────

describe('TestFromAC_GetTask', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('happy: sends GET to /api/tasks/{id}', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await getTask(42)
    expect(fetchMock).toHaveBeenCalledWith('/api/tasks/42', expect.anything())
  })

  it('happy: uses HTTP method GET', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await getTask(42)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit | undefined]
    const method = init?.method?.toUpperCase() ?? 'GET'
    expect(method).toBe('GET')
  })

  it('happy: returns parsed TaskDetail on 2xx', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await getTask(42)
    expect(result).toEqual(TASK_DETAIL)
  })

  it('happy: returns minimal TaskDetail (null body, empty arrays)', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL_MINIMAL))
    const result = await getTask(1)
    expect(result).toEqual(TASK_DETAIL_MINIMAL)
  })

  it('happy: forwards options.signal to fetch when provided', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController()
    await getTask(42, { signal: controller.signal })
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit | undefined]
    expect(init?.signal).toBe(controller.signal)
  })

  it('edge: does not forward signal when options not provided', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await getTask(42)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit | undefined]
    expect(init?.signal).toBeFalsy()
  })

  it('error: throws ApiError on 404 response', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(404, { detail: 'Not found' }))
    await expect(getTask(99)).rejects.toBeInstanceOf(ApiError)
  })

  it('error: throws ApiError with correct status on 404', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(404, { detail: 'Not found' }))
    const err = await getTask(99).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).status).toBe(404)
  })

  it('error: throws ApiError on 500 response', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(500, { detail: 'Internal error' }))
    await expect(getTask(42)).rejects.toBeInstanceOf(ApiError)
  })

  it('AC-6: extracts detail message from response body via getResponseErrorMessage', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(404, { detail: 'Task not found: 42' }))
    const err = await getTask(42).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).message).toBe('Task not found: 42')
  })

  it('AC-6: extracts message field from response body', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(409, { message: 'Stale update rejected' }))
    const err = await getTask(42).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).message).toBe('Stale update rejected')
  })

  it('AC-6: extracts FastAPI validation detail array messages with field names', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(422, {
      detail: [
        { loc: ['body', 'priority'], msg: 'Input should be a valid string', type: 'string_type' },
        { loc: ['body', 'depends_on', 0], msg: 'Input should be a valid integer', type: 'int_type' },
      ],
    }))
    const err = await getTask(42).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).message).toBe(
      'priority: Input should be a valid string; depends_on: Input should be a valid integer',
    )
  })

  it('AC-6: falls back for empty FastAPI validation detail arrays', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(422, { detail: [] }))
    const err = await getTask(42).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).message).toBe('Get task request failed with status 422')
  })

  it('AC-6: network error propagates unwrapped — not wrapped in ApiError', async () => {
    vi.stubGlobal('fetch', makeNetworkErrorFetch('Network failure'))
    const err = await getTask(42).catch((e: unknown) => e)
    expect(err).not.toBeInstanceOf(ApiError)
    expect(err).toBeInstanceOf(Error)
    expect((err as Error).message).toBe('Network failure')
  })
})

// ─── AC-3: moveTask() ──────────────────────────────────────────────────────

describe('TestFromAC_MoveTask', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  const MOVE_REQUEST: MoveRequest = {
    status: 'done',
    updated: '2026-05-12T00:00:00Z',
    archival_reason: null,
    archival_refs: null,
  }

  it('happy: sends POST to /api/tasks/{id}/move', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await moveTask(42, MOVE_REQUEST)
    expect(fetchMock).toHaveBeenCalledWith('/api/tasks/42/move', expect.anything())
  })

  it('happy: uses HTTP method POST', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await moveTask(42, MOVE_REQUEST)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(init.method).toBe('POST')
  })

  it('happy: sends JSON-serialized request body', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await moveTask(42, MOVE_REQUEST)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toEqual(MOVE_REQUEST)
  })

  it('happy: returns TaskDetail on 2xx', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await moveTask(42, MOVE_REQUEST)
    expect(result).toEqual(TASK_DETAIL)
  })

  it('error: throws ApiError on non-ok response', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(409))
    await expect(moveTask(42, MOVE_REQUEST)).rejects.toBeInstanceOf(ApiError)
  })

  it('error: ApiError status matches HTTP status code', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(409, { detail: 'Stale' }))
    const err = await moveTask(42, MOVE_REQUEST).catch((e: unknown) => e)
    expect((err as ApiError).status).toBe(409)
  })

  it('AC-6: extracts error message from response body', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(409, { detail: 'Task already archived' }))
    const err = await moveTask(42, MOVE_REQUEST).catch((e: unknown) => e)
    expect((err as ApiError).message).toBe('Task already archived')
  })

  it('AC-6: network error propagates unwrapped', async () => {
    vi.stubGlobal('fetch', makeNetworkErrorFetch('Connection refused'))
    const err = await moveTask(42, MOVE_REQUEST).catch((e: unknown) => e)
    expect(err).not.toBeInstanceOf(ApiError)
    expect((err as Error).message).toBe('Connection refused')
  })

  it('boundary: MoveRequest without optional fields is accepted', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    const minimalMove: MoveRequest = { status: 'done', updated: '2026-05-12T00:00:00Z' }
    await moveTask(42, minimalMove)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})

// ─── AC-4: editTask() ──────────────────────────────────────────────────────

describe('TestFromAC_EditTask', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  const EDIT_REQUEST: EditRequest = {
    updated: '2026-05-12T00:00:00Z',
    title: 'New title',
    tags: null,
    priority: null,
    depends_on: null,
    parent: null,
    block_reason: null,
    body: null,
  }

  it('happy: sends POST to /api/tasks/{id}/edit', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await editTask(42, EDIT_REQUEST)
    expect(fetchMock).toHaveBeenCalledWith('/api/tasks/42/edit', expect.anything())
  })

  it('happy: uses HTTP method POST', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await editTask(42, EDIT_REQUEST)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(init.method).toBe('POST')
  })

  it('happy: sends JSON-serialized request body', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await editTask(42, EDIT_REQUEST)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toEqual(EDIT_REQUEST)
  })

  it('happy: returns TaskDetail on 2xx', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await editTask(42, EDIT_REQUEST)
    expect(result).toEqual(TASK_DETAIL)
  })

  it('error: throws ApiError on non-ok response', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(422))
    await expect(editTask(42, EDIT_REQUEST)).rejects.toBeInstanceOf(ApiError)
  })

  it('error: ApiError status matches HTTP status code', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(422, { detail: 'Validation failed' }))
    const err = await editTask(42, EDIT_REQUEST).catch((e: unknown) => e)
    expect((err as ApiError).status).toBe(422)
  })

  it('AC-6: extracts error message from response body', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(422, { detail: 'title must not be empty' }))
    const err = await editTask(42, EDIT_REQUEST).catch((e: unknown) => e)
    expect((err as ApiError).message).toBe('title must not be empty')
  })

  it('AC-6: network error propagates unwrapped', async () => {
    vi.stubGlobal('fetch', makeNetworkErrorFetch('ECONNREFUSED'))
    const err = await editTask(42, EDIT_REQUEST).catch((e: unknown) => e)
    expect(err).not.toBeInstanceOf(ApiError)
    expect((err as Error).message).toBe('ECONNREFUSED')
  })

  it('boundary: EditRequest with only required field (updated) is valid', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    const minimalEdit: EditRequest = { updated: '2026-05-12T00:00:00Z' }
    await editTask(42, minimalEdit)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})

// ─── AC-5: releaseTask() ───────────────────────────────────────────────────

describe('TestFromAC_ReleaseTask', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  const RELEASE_REQUEST: ReleaseRequest = {
    updated: '2026-05-12T00:00:00Z',
  }

  it('happy: sends POST to /api/tasks/{id}/release', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await releaseTask(42, RELEASE_REQUEST)
    expect(fetchMock).toHaveBeenCalledWith('/api/tasks/42/release', expect.anything())
  })

  it('happy: uses HTTP method POST', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await releaseTask(42, RELEASE_REQUEST)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(init.method).toBe('POST')
  })

  it('happy: sends JSON-serialized request body', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await releaseTask(42, RELEASE_REQUEST)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toEqual(RELEASE_REQUEST)
  })

  it('happy: returns TaskDetail on 2xx', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await releaseTask(42, RELEASE_REQUEST)
    expect(result).toEqual(TASK_DETAIL)
  })

  it('error: throws ApiError on non-ok response', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(409))
    await expect(releaseTask(42, RELEASE_REQUEST)).rejects.toBeInstanceOf(ApiError)
  })

  it('error: ApiError status matches HTTP status code', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(409, { detail: 'Stale timestamp' }))
    const err = await releaseTask(42, RELEASE_REQUEST).catch((e: unknown) => e)
    expect((err as ApiError).status).toBe(409)
  })

  it('AC-6: extracts error message from response body', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(409, { detail: 'Updated timestamp mismatch' }))
    const err = await releaseTask(42, RELEASE_REQUEST).catch((e: unknown) => e)
    expect((err as ApiError).message).toBe('Updated timestamp mismatch')
  })

  it('AC-6: network error propagates unwrapped', async () => {
    vi.stubGlobal('fetch', makeNetworkErrorFetch('Request timed out'))
    const err = await releaseTask(42, RELEASE_REQUEST).catch((e: unknown) => e)
    expect(err).not.toBeInstanceOf(ApiError)
    expect((err as Error).message).toBe('Request timed out')
  })
})

// ─── AC-7: Request interfaces ──────────────────────────────────────────────

describe('TestFromAC_RequestInterfaces', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('MoveRequest: status and updated fields are included in POST body', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    const req: MoveRequest = { status: 'done', updated: '2026-05-12T00:00:00Z' }
    await moveTask(42, req)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const body = JSON.parse(init.body as string) as Record<string, unknown>
    expect(body.status).toBe('done')
    expect(body.updated).toBe('2026-05-12T00:00:00Z')
  })

  it('MoveRequest: optional archival_reason and archival_refs are serialized when provided', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    const req: MoveRequest = {
      status: 'archived',
      updated: '2026-05-12T00:00:00Z',
      archival_reason: 'completed',
      archival_refs: [100, 101],
    }
    await moveTask(42, req)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const body = JSON.parse(init.body as string) as Record<string, unknown>
    expect(body.archival_reason).toBe('completed')
    expect(body.archival_refs).toEqual([100, 101])
  })

  it('EditRequest: updated is the only required field', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    const req: EditRequest = { updated: '2026-05-12T00:00:00Z' }
    await editTask(42, req)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const body = JSON.parse(init.body as string) as Record<string, unknown>
    expect(body.updated).toBe('2026-05-12T00:00:00Z')
  })

  it('EditRequest: optional null fields are serialized when explicitly provided', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    const req: EditRequest = {
      updated: '2026-05-12T00:00:00Z',
      title: null,
      tags: null,
      priority: null,
      depends_on: null,
      parent: null,
      block_reason: null,
      body: null,
    }
    await editTask(42, req)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const body = JSON.parse(init.body as string) as Record<string, unknown>
    // null values must be serialized (tri-state: null = clear)
    expect('title' in body).toBe(true)
    expect(body.title).toBeNull()
  })

  it('ReleaseRequest: updated field is included in POST body', async () => {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    const req: ReleaseRequest = { updated: '2026-05-12T00:00:00Z' }
    await releaseTask(42, req)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const body = JSON.parse(init.body as string) as Record<string, unknown>
    expect(body.updated).toBe('2026-05-12T00:00:00Z')
  })
})

// ─── AC-8: TaskDetail interface ────────────────────────────────────────────

describe('TestFromAC_TaskDetailInterface', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('TaskDetail: id is a number', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await getTask(42)
    expect(typeof result.id).toBe('number')
    expect(result.id).toBe(42)
  })

  it('TaskDetail: title is a string', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await getTask(42)
    expect(typeof result.title).toBe('string')
  })

  it('TaskDetail: status and priority are strings', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await getTask(42)
    expect(typeof result.status).toBe('string')
    expect(typeof result.priority).toBe('string')
  })

  it('TaskDetail: updated and created are strings', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await getTask(42)
    expect(typeof result.updated).toBe('string')
    expect(typeof result.created).toBe('string')
  })

  it('TaskDetail: body is string or null', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await getTask(42)
    expect(typeof result.body === 'string' || result.body === null).toBe(true)
  })

  it('TaskDetail: body is null when not present', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL_MINIMAL))
    const result = await getTask(1)
    expect(result.body).toBeNull()
  })

  it('TaskDetail: tags is an array', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await getTask(42)
    expect(Array.isArray(result.tags)).toBe(true)
  })

  it('TaskDetail: blocked is a boolean', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await getTask(42)
    expect(typeof result.blocked).toBe('boolean')
  })

  it('TaskDetail: block_reason is string or null', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL_MINIMAL))
    const result = await getTask(1)
    expect(result.block_reason).toBeNull()
  })

  it('TaskDetail: claimed is a boolean', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL))
    const result = await getTask(42)
    expect(typeof result.claimed).toBe('boolean')
  })

  it('TaskDetail: claimed_at is string or null', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL_MINIMAL))
    const result = await getTask(1)
    expect(result.claimed_at).toBeNull()
  })

  it('TaskDetail: dep_status is string or null', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL_MINIMAL))
    const result = await getTask(1)
    expect(result.dep_status === null || typeof result.dep_status === 'string').toBe(true)
  })

  it('TaskDetail: parent is number or null', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL_MINIMAL))
    const result = await getTask(1)
    expect(result.parent === null || typeof result.parent === 'number').toBe(true)
  })

  it('TaskDetail: depends_on is an array of numbers', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(TASK_DETAIL_MINIMAL))
    const result = await getTask(1)
    expect(Array.isArray(result.depends_on)).toBe(true)
  })
})

// ─── AC-7 (revised): EditRequest per-field serialization semantics ─────────
//
// Revised AC-7 specifies per-field omit/null/empty semantics matching the
// backend _build_edit_kwargs Pydantic model_fields_set logic:
//   - Omit (undefined) → field absent from JSON → backend no-op for that field
//   - null              → field present as null   → field-specific backend behaviour
//   - ""  / []          → field present as empty  → backend "clear" signal
// Tests here document the correct JSON serialisation for each case.
// All pass against current implementation (JSON.stringify behaviour is correct).

describe('TestFromAC_EditRequestFieldSemantics', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  async function captureEditBody(req: EditRequest): Promise<Record<string, unknown>> {
    const fetchMock = makeSuccessFetch(TASK_DETAIL)
    vi.stubGlobal('fetch', fetchMock)
    await editTask(42, req)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    return JSON.parse(init.body as string) as Record<string, unknown>
  }

  // ── Omit = no change: undefined fields must be absent from serialised body ──

  it('AC-7: omitting title (undefined) excludes it from the serialised request body', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z' })
    expect('title' in body).toBe(false)
  })

  it('AC-7: omitting tags (undefined) excludes it from the serialised request body', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z' })
    expect('tags' in body).toBe(false)
  })

  it('AC-7: omitting depends_on (undefined) excludes it from the serialised request body', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z' })
    expect('depends_on' in body).toBe(false)
  })

  it('AC-7: omitting priority (undefined) excludes it from the serialised request body', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z' })
    expect('priority' in body).toBe(false)
  })

  it('AC-7: omitting parent (undefined) excludes it from the serialised request body', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z' })
    expect('parent' in body).toBe(false)
  })

  it('AC-7: omitting block_reason (undefined) excludes it from the serialised request body', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z' })
    expect('block_reason' in body).toBe(false)
  })

  it('AC-7: omitting body field (undefined) excludes it from the serialised request body', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z' })
    expect('body' in body).toBe(false)
  })

  // ── body: ""  = clear signal; body: null = no-op ──────────────────────────

  it('AC-7: body="" serialises as empty string — backend clear-body signal', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z', body: '' })
    expect('body' in body).toBe(true)
    expect(body.body).toBe('')
  })

  it('AC-7: body=null serialises as null — backend no-op (not same as empty string)', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z', body: null })
    expect('body' in body).toBe(true)
    expect(body.body).toBeNull()
  })

  // ── parent: null = clear parent ───────────────────────────────────────────

  it('AC-7: parent=null serialises as null — backend clear-parent signal', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z', parent: null })
    expect('parent' in body).toBe(true)
    expect(body.parent).toBeNull()
  })

  // ── block_reason: null / "" = unblock ─────────────────────────────────────

  it('AC-7: block_reason=null serialises as null — backend unblock signal', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z', block_reason: null })
    expect('block_reason' in body).toBe(true)
    expect(body.block_reason).toBeNull()
  })

  it('AC-7: block_reason="" serialises as empty string — backend unblock signal', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z', block_reason: '' })
    expect('block_reason' in body).toBe(true)
    expect(body.block_reason).toBe('')
  })

  // ── tags: [] = remove all; tags: null = no-op ─────────────────────────────

  it('AC-7: tags=[] serialises as empty array — backend remove-all-tags signal', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z', tags: [] })
    expect('tags' in body).toBe(true)
    expect(body.tags).toEqual([])
  })

  it('AC-7: tags=null serialises as null — backend no-op (distinct from empty array)', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z', tags: null })
    expect('tags' in body).toBe(true)
    expect(body.tags).toBeNull()
  })

  // ── depends_on: [] = remove all; depends_on: null = no-op ─────────────────

  it('AC-7: depends_on=[] serialises as empty array — backend remove-all-deps signal', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z', depends_on: [] })
    expect('depends_on' in body).toBe(true)
    expect(body.depends_on).toEqual([])
  })

  it('AC-7: depends_on=null serialises as null — backend no-op (distinct from empty array)', async () => {
    const body = await captureEditBody({ updated: '2026-05-12T00:00:00Z', depends_on: null })
    expect('depends_on' in body).toBe(true)
    expect(body.depends_on).toBeNull()
  })
})
