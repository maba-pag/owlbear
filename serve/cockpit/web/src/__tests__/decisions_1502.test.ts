/**
 * decisions_1502: api/decisions.ts — AC-1 through AC-5
 *
 * RED reason: api/decisions.ts does not exist yet — all imports fail at
 * module resolution.
 *
 * Proof bundle: behavioral
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { ApiError } from '../api/errors'
import { resolveDR } from '../api/decisions'
import type { ResolveRequest, ResolveResponse } from '../api/decisions'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const RESOLVE_RESPONSE_APPROVED: ResolveResponse = {
  id: 'dr-001',
  response: 'approved',
}

const RESOLVE_RESPONSE_REJECTED: ResolveResponse = {
  id: 'dr-042',
  response: 'rejected',
}

const RESOLVE_RESPONSE_NEEDS_INFO: ResolveResponse = {
  id: 'dr-099',
  response: 'needs-info',
}

function makeSuccessFetch(data: ResolveResponse) {
  return vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(data),
    }),
  )
}

function makeNonOkFetch(
  status: number,
  body: Record<string, unknown> = { detail: 'Server error' },
) {
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

// ─── AC-1 / AC-4 / AC-5: resolveDR() function ────────────────────────────

describe('TestFromAC_ResolveDR', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  const REQUEST_APPROVED: ResolveRequest = { response: 'approved' }
  const REQUEST_WITH_NOTES: ResolveRequest = { response: 'approved', notes: 'LGTM' }

  // ── Happy path ──────────────────────────────────────────────────────────

  it('happy: sends POST to /api/decisions/{id}/resolve', async () => {
    const fetchMock = makeSuccessFetch(RESOLVE_RESPONSE_APPROVED)
    vi.stubGlobal('fetch', fetchMock)
    await resolveDR('dr-001', REQUEST_APPROVED)
    expect(fetchMock).toHaveBeenCalledWith('/api/decisions/dr-001/resolve', expect.anything())
  })

  it('happy: uses HTTP method POST', async () => {
    const fetchMock = makeSuccessFetch(RESOLVE_RESPONSE_APPROVED)
    vi.stubGlobal('fetch', fetchMock)
    await resolveDR('dr-001', REQUEST_APPROVED)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(init.method).toBe('POST')
  })

  it('happy: sends JSON-serialized request body', async () => {
    const fetchMock = makeSuccessFetch(RESOLVE_RESPONSE_APPROVED)
    vi.stubGlobal('fetch', fetchMock)
    await resolveDR('dr-001', REQUEST_APPROVED)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toEqual(REQUEST_APPROVED)
  })

  it('happy: request body includes notes when provided', async () => {
    const fetchMock = makeSuccessFetch(RESOLVE_RESPONSE_APPROVED)
    vi.stubGlobal('fetch', fetchMock)
    await resolveDR('dr-001', REQUEST_WITH_NOTES)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toEqual(REQUEST_WITH_NOTES)
  })

  it('happy: returns parsed ResolveResponse on 2xx', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(RESOLVE_RESPONSE_APPROVED))
    const result = await resolveDR('dr-001', REQUEST_APPROVED)
    expect(result).toEqual(RESOLVE_RESPONSE_APPROVED)
  })

  it('happy: returned response field matches backend value (rejected)', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(RESOLVE_RESPONSE_REJECTED))
    const result = await resolveDR('dr-042', { response: 'rejected' })
    expect(result.response).toBe('rejected')
  })

  it('happy: returned response field matches backend value (needs-info)', async () => {
    vi.stubGlobal('fetch', makeSuccessFetch(RESOLVE_RESPONSE_NEEDS_INFO))
    const result = await resolveDR('dr-099', { response: 'needs-info' })
    expect(result.response).toBe('needs-info')
  })

  // ── Edge cases ──────────────────────────────────────────────────────────

  it('edge: id with dashes is interpolated into URL correctly', async () => {
    const fetchMock = makeSuccessFetch(RESOLVE_RESPONSE_REJECTED)
    vi.stubGlobal('fetch', fetchMock)
    await resolveDR('task-1502', { response: 'rejected' })
    expect(fetchMock).toHaveBeenCalledWith('/api/decisions/task-1502/resolve', expect.anything())
  })

  it('edge: request without notes sends only response field in body', async () => {
    const fetchMock = makeSuccessFetch(RESOLVE_RESPONSE_APPROVED)
    vi.stubGlobal('fetch', fetchMock)
    await resolveDR('dr-001', { response: 'approved' })
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const body = JSON.parse(init.body as string) as Record<string, unknown>
    expect(body.response).toBe('approved')
    expect(body.notes).toBeUndefined()
  })

  // ── Error paths ─────────────────────────────────────────────────────────

  it('error: throws ApiError on 404 response', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(404, { detail: 'Decision not found' }))
    await expect(resolveDR('dr-001', REQUEST_APPROVED)).rejects.toBeInstanceOf(ApiError)
  })

  it('error: ApiError.status matches 404 HTTP status', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(404, { detail: 'Not found' }))
    const err = await resolveDR('dr-001', REQUEST_APPROVED).catch((e: unknown) => e)
    expect((err as ApiError).status).toBe(404)
  })

  it('error: throws ApiError on 409 (ConcurrencyError)', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(409, { code: 'ConcurrencyError', message: 'Already resolved' }))
    await expect(resolveDR('dr-001', REQUEST_APPROVED)).rejects.toBeInstanceOf(ApiError)
  })

  it('error: ApiError.status matches 409 HTTP status', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(409, { message: 'Already resolved' }))
    const err = await resolveDR('dr-001', REQUEST_APPROVED).catch((e: unknown) => e)
    expect((err as ApiError).status).toBe(409)
  })

  it('error: throws ApiError on 422 (validation error)', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(422, { detail: 'Invalid response value' }))
    await expect(resolveDR('dr-001', REQUEST_APPROVED)).rejects.toBeInstanceOf(ApiError)
  })

  it('error: ApiError.status matches 422 HTTP status', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(422, { detail: 'Invalid response value' }))
    const err = await resolveDR('dr-001', REQUEST_APPROVED).catch((e: unknown) => e)
    expect((err as ApiError).status).toBe(422)
  })

  // ── AC-4: error message extraction ─────────────────────────────────────

  it('AC-4: extracts detail field from non-ok response body', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(404, { detail: 'Decision not found: dr-001' }))
    const err = await resolveDR('dr-001', REQUEST_APPROVED).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).message).toBe('Decision not found: dr-001')
  })

  it('AC-4: extracts message field from non-ok response body (ConcurrencyError)', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(409, { code: 'ConcurrencyError', message: 'DR already resolved' }))
    const err = await resolveDR('dr-001', REQUEST_APPROVED).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).message).toBe('DR already resolved')
  })

  it('AC-4: falls back to non-empty message when response body has no detail/message', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(500, {}))
    const err = await resolveDR('dr-001', REQUEST_APPROVED).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect((err as ApiError).message.length).toBeGreaterThan(0)
  })

  it('AC-4: network error propagates unwrapped — not wrapped in ApiError', async () => {
    vi.stubGlobal('fetch', makeNetworkErrorFetch('Network failure'))
    const err = await resolveDR('dr-001', REQUEST_APPROVED).catch((e: unknown) => e)
    expect(err).not.toBeInstanceOf(ApiError)
    expect(err).toBeInstanceOf(Error)
    expect((err as Error).message).toBe('Network failure')
  })

  // ── AC-5: structural import from api/errors.ts ──────────────────────────

  it('AC-5: ApiError imported from api/errors.ts is thrown by resolveDR on non-ok', async () => {
    vi.stubGlobal('fetch', makeNonOkFetch(404, { detail: 'Not found' }))
    const err = await resolveDR('dr-001', REQUEST_APPROVED).catch((e: unknown) => e)
    // ApiError here is imported from api/errors — same class identity as thrown error
    expect(err).toBeInstanceOf(ApiError)
  })
})

// ─── AC-2: ResolveRequest interface ───────────────────────────────────────

describe('TestFromAC_ResolveRequest', () => {
  it('accepts response value: approved', () => {
    const req: ResolveRequest = { response: 'approved' }
    expect(req.response).toBe('approved')
  })

  it('accepts response value: needs-info', () => {
    const req: ResolveRequest = { response: 'needs-info' }
    expect(req.response).toBe('needs-info')
  })

  it('accepts response value: rejected', () => {
    const req: ResolveRequest = { response: 'rejected' }
    expect(req.response).toBe('rejected')
  })

  it('notes field is optional — omitting it produces undefined', () => {
    const req: ResolveRequest = { response: 'approved' }
    expect(req.notes).toBeUndefined()
  })

  it('notes field accepts a non-empty string', () => {
    const req: ResolveRequest = { response: 'approved', notes: 'Looks good, proceeding' }
    expect(req.notes).toBe('Looks good, proceeding')
  })

  it('notes field accepts empty string', () => {
    const req: ResolveRequest = { response: 'rejected', notes: '' }
    expect(req.notes).toBe('')
  })
})

// ─── AC-3: ResolveResponse interface ──────────────────────────────────────

describe('TestFromAC_ResolveResponse', () => {
  it('id field is a string', () => {
    const res: ResolveResponse = { id: 'dr-123', response: 'approved' }
    expect(typeof res.id).toBe('string')
  })

  it('response field accepts: approved', () => {
    const res: ResolveResponse = { id: 'dr-1', response: 'approved' }
    expect(res.response).toBe('approved')
  })

  it('response field accepts: needs-info', () => {
    const res: ResolveResponse = { id: 'dr-2', response: 'needs-info' }
    expect(res.response).toBe('needs-info')
  })

  it('response field accepts: rejected', () => {
    const res: ResolveResponse = { id: 'dr-3', response: 'rejected' }
    expect(res.response).toBe('rejected')
  })

  it('ResolveResponse.response and ResolveRequest.response share identical closed union', () => {
    // Assigning from one to the other must be type-safe
    const reqResponse: ResolveRequest['response'] = 'needs-info'
    const res: ResolveResponse = { id: 'dr-4', response: reqResponse }
    expect(res.response).toBe('needs-info')
  })
})
