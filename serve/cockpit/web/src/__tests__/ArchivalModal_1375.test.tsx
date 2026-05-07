/**
 * RED phase tests for #1375: P1-12 Implement Cockpit frontend error-contract adoption
 *
 * ArchivalModal.tsx gaps — handleSubmit reads only payload.detail for 422 errors
 * and uses a status-only fallback for all other non-ok statuses:
 *
 *   422 path: `const detail = typeof payload.detail === 'string' ? payload.detail : 'Validation failed.'`
 *             → {code, message} body silently falls back to "Validation failed."
 *
 *   Other non-ok path: `setError(\`Archival failed (${response.status}).\`)`
 *             → no body read; {code, message} or {detail} body always discarded.
 *
 * After #1375, getResponseErrorMessage() is adopted in handleArchive so both
 * {code, message} and {detail} shapes surface in the archival-error element.
 *
 * All tests FAIL until #1375 replaces the partial/missing body parsing.
 */
import { describe, it, expect, vi, beforeAll, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ArchivalModal from '../components/ArchivalModal'

// ─── PDS jsdom polyfill ────────────────────────────────────────────────────────

beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

// ─── Helpers ──────────────────────────────────────────────────────────────────

function renderModal({
  taskId = 42,
  taskStatus = 'in-progress',
  expectedUpdated = '2026-05-01T10:00:00+00:00',
  onClose = vi.fn(),
  onRefresh = vi.fn(),
}: {
  taskId?: number
  taskStatus?: string
  expectedUpdated?: string
  onClose?: ReturnType<typeof vi.fn>
  onRefresh?: ReturnType<typeof vi.fn>
} = {}) {
  const utils = render(
    <PorscheDesignSystemProvider>
      <ArchivalModal
        taskId={taskId}
        taskStatus={taskStatus}
        expectedUpdated={expectedUpdated}
        onClose={onClose}
        onRefresh={onRefresh}
      />
    </PorscheDesignSystemProvider>,
  )
  return { ...utils, onClose, onRefresh }
}

function getSelect(container: HTMLElement): HTMLElement {
  const el = container.querySelector('p-select') as HTMLElement | null
  if (!el) throw new Error('reason p-select not found')
  return el
}

function getSubmitBtn(container: HTMLElement): HTMLElement {
  const el = container.querySelector('[data-testid="archival-submit"]') as HTMLElement | null
  if (!el) throw new Error('archival-submit button not found')
  return el
}

function selectReason(container: HTMLElement, reason: string): void {
  fireEvent(
    getSelect(container),
    new CustomEvent('change', { detail: { value: reason }, bubbles: true }),
  )
}

function makeJsonFetch(status: number, body: unknown) {
  return vi.fn(() =>
    Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    } as Response),
  )
}

// ─── AC1/AC2/AC3: ArchivalModal handleSubmit body extraction ──────────────────
//
// Tests cover the two remaining gaps:
//   1. 422 with {code, message} body — current code reads only .detail → fallback
//   2. Non-409/422 (e.g. 500) — current code uses status-only string, no body read.

describe('TestFromAC_ArchivalModalErrorBodyParsing', () => {
  // FAILS: handleSubmit 422 path reads `payload.detail` only.
  // When body is {code, message}, payload.detail is undefined → falls back to
  // "Validation failed." — the body message field is never shown.
  // After fix, getResponseErrorMessage() reads .message → archival-error contains it.
  it('handleSubmit 422 {code,message}: archival-error contains body message field, not "Validation failed."', async () => {
    const errorBody = { code: 'VALIDATION_ERROR', message: 'priority field is required' }
    vi.stubGlobal('fetch', makeJsonFetch(422, errorBody))

    const { container } = renderModal()
    selectReason(container, 'dropped')
    fireEvent.click(getSubmitBtn(container))

    await waitFor(
      () => {
        const errEl = container.querySelector('[data-testid="archival-error"]')
        expect(errEl).not.toBeNull()
        // FAILS: current text is "Validation failed." — body message not read for 422
        expect(errEl!.textContent).toContain('priority field is required')
      },
      { timeout: 1000 },
    )
  })

  // FAILS: same 422 root cause — current text is "Validation failed.", not.toBe passes
  // only after fix when body message appears in the text.
  it('handleSubmit 422 {code,message}: archival-error is not the "Validation failed." fallback', async () => {
    const errorBody = { code: 'SCHEMA_ERROR', message: 'archival_reason must be one of the allowed values' }
    vi.stubGlobal('fetch', makeJsonFetch(422, errorBody))

    const { container } = renderModal()
    selectReason(container, 'wontfix')
    fireEvent.click(getSubmitBtn(container))

    await waitFor(
      () => {
        const errEl = container.querySelector('[data-testid="archival-error"]')
        expect(errEl).not.toBeNull()
        // FAILS: current text IS "Validation failed."
        expect(errEl!.textContent).not.toBe('Validation failed.')
      },
      { timeout: 1000 },
    )
  })

  // FAILS: non-409/422 path uses `setError(\`Archival failed (${response.status}).\`)`.
  // Body is never read. After fix, getResponseErrorMessage() reads .message →
  // archival-error contains body message field.
  it('handleSubmit 500 {code,message}: archival-error contains body message field', async () => {
    const errorBody = { code: 'STORAGE_ERROR', message: 'archival failed: disk quota exceeded' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))

    const { container } = renderModal()
    selectReason(container, 'dropped')
    fireEvent.click(getSubmitBtn(container))

    await waitFor(
      () => {
        const errEl = container.querySelector('[data-testid="archival-error"]')
        expect(errEl).not.toBeNull()
        // FAILS: current text is "Archival failed (500)." — body not read
        expect(errEl!.textContent).toContain('archival failed: disk quota exceeded')
      },
      { timeout: 1000 },
    )
  })

  // FAILS: same non-422/409 path discards {detail} shape too.
  // After fix, getResponseErrorMessage() reads .detail → archival-error shows body detail.
  it('handleSubmit 500 {detail}: archival-error contains body detail field', async () => {
    const errorBody = { detail: 'service temporarily unavailable: storage backend offline' }
    vi.stubGlobal('fetch', makeJsonFetch(503, errorBody))

    const { container } = renderModal()
    selectReason(container, 'wontfix')
    fireEvent.click(getSubmitBtn(container))

    await waitFor(
      () => {
        const errEl = container.querySelector('[data-testid="archival-error"]')
        expect(errEl).not.toBeNull()
        // FAILS: current text is "Archival failed (503)." — body not read
        expect(errEl!.textContent).toContain('service temporarily unavailable: storage backend offline')
      },
      { timeout: 1000 },
    )
  })

  // FAILS: non-422/409 path text IS "Archival failed (500)." which is the status-only string.
  // not.toBe fails because current text exactly equals the status-only fallback.
  // After fix, body message appears in text, making not.toBe pass.
  it('handleSubmit 500: archival-error text is not the bare status-only fallback string', async () => {
    const errorBody = { code: 'ENGINE_ERROR', message: 'task engine timed out during archival' }
    vi.stubGlobal('fetch', makeJsonFetch(500, errorBody))

    const { container } = renderModal()
    selectReason(container, 'dropped')
    fireEvent.click(getSubmitBtn(container))

    await waitFor(
      () => {
        const errEl = container.querySelector('[data-testid="archival-error"]')
        expect(errEl).not.toBeNull()
        // FAILS: current text IS "Archival failed (500)."
        expect(errEl!.textContent).not.toBe('Archival failed (500).')
      },
      { timeout: 1000 },
    )
  })
})
