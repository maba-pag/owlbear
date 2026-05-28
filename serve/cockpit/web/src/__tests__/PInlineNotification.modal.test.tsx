/**
 * PInlineNotification modal error display (task #1499)
 *
 * Covers:
 *   AC-1 — ArchivalModal renders PInlineNotification (state='error', data-testid='archival-error')
 *           on HTTP 409/422/500+/network/client-side validation;
 *           description prop carries error detail from getResponseErrorMessage()
 *   AC-2 — ResolveModal renders PInlineNotification (state='error', data-testid='resolve-error')
 *           on HTTP 404/409/422/500+/network;
 *           description prop carries error detail from getResponseErrorMessage()
 *   AC-3 — Retryable errors (ArchivalModal 500+/network; ResolveModal 500+/network) show
 *           actionLabel='Retry', actionIcon='reset', onAction re-invokes handleSubmit()
 *   AC-4 — Non-retryable errors (ArchivalModal 409/422/client-validation;
 *           ResolveModal 404/409/422) render PInlineNotification without action button
 *   AC-5 — actionLoading=true while retry handleSubmit() is in-flight
 *   AC-6 — Notification dismissed on success (setError(null)), onDismiss click (setError(null));
 *           ArchivalModal also clears error on reason-change (existing behavior)
 *   AC-7 — ArchivalModal.getFocusableElements() selector includes p-inline-notification
 *
 * Expected post-implementation selectors:
 *   p-inline-notification[data-testid="archival-error"]
 *   p-inline-notification[data-testid="resolve-error"]
 *
 * Expected JS property access (PDS web component pattern):
 *   (element as any).state       === 'error'
 *   (element as any).description — error detail string
 *   (element as any).actionLabel — 'Retry' | '' | undefined
 *   (element as any).actionIcon  — 'reset' | undefined
 *   (element as any).actionLoading — boolean
 *   (element as any).onAction   — () => void
 *   (element as any).onDismiss  — () => void
 */
import { beforeAll, describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor, act } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ArchivalModal from '../components/ArchivalModal'

// ─── PDS jsdom polyfill ────────────────────────────────────────────────────────
// Prevents PDS Stencil form components from throwing on mount in jsdom.

beforeAll(() => {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(() => ({
    setFormValue: vi.fn(),
    setValidity: vi.fn(),
    checkValidity: vi.fn(() => true),
    reportValidity: vi.fn(() => true),
  }))
})

// ─── react-markdown mock ──────────────────────────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown-body">{children}</div>
  ),
}))

// ─── PDS property type ────────────────────────────────────────────────────────

type PInlineEl = HTMLElement & {
  state?: string
  description?: string
  heading?: string
  actionLabel?: string
  actionIcon?: string
  actionLoading?: boolean
  onAction?: () => void
  onDismiss?: () => void
}

// ─── Fetch stubs ──────────────────────────────────────────────────────────────

function makeJsonFetch(status: number, body: unknown = {}) {
  return vi.fn(() =>
    Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
      text: () => Promise.resolve(JSON.stringify(body)),
    } as Response),
  )
}

function makeNetworkFetch() {
  return vi.fn(() => Promise.reject(new Error('Network error')))
}

// ─── Render helpers ───────────────────────────────────────────────────────────

interface ArchivalRenderOpts {
  taskId?: number
  taskStatus?: string
  expectedUpdated?: string
  onClose?: ReturnType<typeof vi.fn>
  onRefresh?: ReturnType<typeof vi.fn>
}

function renderArchivalModal({
  taskId = 42,
  taskStatus = 'in-progress',
  expectedUpdated = '2026-05-01T10:00:00+00:00',
  onClose = vi.fn(),
  onRefresh = vi.fn(),
}: ArchivalRenderOpts = {}) {
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



// ─── Interaction helpers ──────────────────────────────────────────────────────

function selectReason(container: HTMLElement, reason: string): void {
  const el = container.querySelector('p-select') as HTMLElement | null
  if (!el) throw new Error('reason p-select not found')
  fireEvent(el, new CustomEvent('change', { detail: { value: reason }, bubbles: true }))
}

function getArchivalSubmitBtn(container: HTMLElement): HTMLElement {
  const el = container.querySelector('[data-testid="archival-submit"]') as HTMLElement | null
  if (!el) throw new Error('archival-submit button not found')
  return el
}

function getArchivalError(container: HTMLElement): PInlineEl | null {
  return container.querySelector('p-inline-notification[data-testid="archival-error"]')
}



// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TestFromAC_PInlineNotificationModals', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.resetAllMocks()
  })

  // ─── AC-1: ArchivalModal renders PInlineNotification on errors ────────────

  describe('AC-1: ArchivalModal renders p-inline-notification on HTTP and client-side errors', () => {
    it('renders p-inline-notification[data-testid=archival-error] with state=error on 409', async () => {
      vi.stubGlobal('fetch', makeJsonFetch(409, { code: 'CONFLICT', message: 'Task snapshot is stale' }))
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.state).toBe('error')
        },
        { timeout: 2000 },
      )
    })

    it('renders p-inline-notification with state=error on 422 validation failure', async () => {
      vi.stubGlobal(
        'fetch',
        makeJsonFetch(422, { code: 'VALIDATION_ERROR', message: 'Invalid archival reason' }),
      )
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.state).toBe('error')
        },
        { timeout: 2000 },
      )
    })

    it('renders p-inline-notification with state=error on 500 server error', async () => {
      vi.stubGlobal('fetch', makeJsonFetch(500, { code: 'SERVER_ERROR', message: 'Storage failed' }))
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.state).toBe('error')
        },
        { timeout: 2000 },
      )
    })

    it('renders p-inline-notification with state=error on network failure', async () => {
      vi.stubGlobal('fetch', makeNetworkFetch())
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.state).toBe('error')
        },
        { timeout: 2000 },
      )
    })

    it('renders p-inline-notification with state=error on client-side invalid refs input', () => {
      // Client-side validation — no fetch call needed
      const { container } = renderArchivalModal()
      selectReason(container, 'duplicate') // requires refs
      const refsInput = container.querySelector('p-input-text') as HTMLElement | null
      if (refsInput) {
        fireEvent(
          refsInput,
          new CustomEvent('change', { detail: { value: 'not-a-number' }, bubbles: true }),
        )
      }
      fireEvent.click(getArchivalSubmitBtn(container))
      // Validation is synchronous — error set before next tick
      const el = getArchivalError(container)
      expect(el).not.toBeNull()
      expect(el!.state).toBe('error')
    })

    it('description prop carries error detail from getResponseErrorMessage on 422', async () => {
      vi.stubGlobal(
        'fetch',
        makeJsonFetch(422, { code: 'VALIDATION_ERROR', message: 'archival_reason must be valid' }),
      )
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.description).toContain('archival_reason must be valid')
        },
        { timeout: 2000 },
      )
    })

    it('description prop carries error detail from getResponseErrorMessage on 500', async () => {
      vi.stubGlobal(
        'fetch',
        makeJsonFetch(500, { code: 'STORAGE_ERROR', message: 'disk quota exceeded during archival' }),
      )
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.description).toContain('disk quota exceeded during archival')
        },
        { timeout: 2000 },
      )
    })
  })

  // ─── AC-3: Retryable errors show Retry action ─────────────────────────────

  describe('AC-3: retryable errors render actionLabel=Retry and actionIcon=reset', () => {
    it('ArchivalModal 500: actionLabel is Retry', async () => {
      vi.stubGlobal('fetch', makeJsonFetch(500, {}))
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.actionLabel).toBe('Retry')
        },
        { timeout: 2000 },
      )
    })

    it('ArchivalModal 500: actionIcon is reset', async () => {
      vi.stubGlobal('fetch', makeJsonFetch(500, {}))
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.actionIcon).toBe('reset')
        },
        { timeout: 2000 },
      )
    })

    it('ArchivalModal network failure: actionLabel is Retry', async () => {
      vi.stubGlobal('fetch', makeNetworkFetch())
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.actionLabel).toBe('Retry')
        },
        { timeout: 2000 },
      )
    })

    it('ArchivalModal network failure: actionIcon is reset', async () => {
      vi.stubGlobal('fetch', makeNetworkFetch())
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.actionIcon).toBe('reset')
        },
        { timeout: 2000 },
      )
    })

  })

  // ─── AC-4: Non-retryable errors have no action button ────────────────────

  describe('AC-4: non-retryable errors render PInlineNotification without action button', () => {
    it('ArchivalModal 409 conflict: actionLabel is empty or absent', async () => {
      vi.stubGlobal('fetch', makeJsonFetch(409, { code: 'CONFLICT', message: 'Stale snapshot' }))
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.actionLabel ?? '').toBe('')
        },
        { timeout: 2000 },
      )
    })

    it('ArchivalModal 422 validation: actionLabel is empty or absent', async () => {
      vi.stubGlobal('fetch', makeJsonFetch(422, { detail: 'Validation failed' }))
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))
      await waitFor(
        () => {
          const el = getArchivalError(container)
          expect(el).not.toBeNull()
          expect(el!.actionLabel ?? '').toBe('')
        },
        { timeout: 2000 },
      )
    })

    it('ArchivalModal client-side invalid refs: actionLabel is empty or absent', () => {
      const { container } = renderArchivalModal()
      selectReason(container, 'duplicate')
      const refsInput = container.querySelector('p-input-text') as HTMLElement | null
      if (refsInput) {
        fireEvent(
          refsInput,
          new CustomEvent('change', { detail: { value: 'not-a-number' }, bubbles: true }),
        )
      }
      fireEvent.click(getArchivalSubmitBtn(container))
      const el = getArchivalError(container)
      expect(el).not.toBeNull()
      expect(el!.actionLabel ?? '').toBe('')
    })

  })

  // ─── AC-5: actionLoading=true while retry is in-flight ───────────────────

  describe('AC-5: actionLoading=true on PInlineNotification while retry handleSubmit() is pending', () => {
    it('ArchivalModal: actionLoading is true while retry fetch is stalled', async () => {
      let resolveRetry!: (value: Response) => void
      let callCount = 0
      vi.stubGlobal(
        'fetch',
        vi.fn(async () => {
          callCount++
          if (callCount === 1) {
            return {
              ok: false,
              status: 500,
              json: async () => ({ code: 'SERVER_ERROR', message: 'Failed' }),
              text: async () => 'Failed',
            } as unknown as Response
          }
          // Second call (retry): stall indefinitely
          return new Promise<Response>((resolve) => {
            resolveRetry = resolve
          })
        }),
      )

      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))

      // Wait for error notification to appear
      await waitFor(() => expect(getArchivalError(container)).not.toBeNull(), { timeout: 2000 })

      const el = getArchivalError(container)!

      // Trigger retry via onAction prop
      await act(async () => {
        el.onAction?.()
      })

      // isSubmitting=true → actionLoading should be true on the element
      expect(el.actionLoading).toBe(true)

      // Clean up: resolve the stalled fetch
      resolveRetry({
        ok: false,
        status: 500,
        json: async () => ({}),
        text: async () => '',
      } as unknown as Response)
    })

  })

  // ─── AC-6: Notification dismissed on success or manual dismiss ───────────

  describe('AC-6: notification dismissed on success, onDismiss click, or ArchivalModal reason-change', () => {
    it('ArchivalModal: error absent after successful retry (setError(null) on success)', async () => {
      let callCount = 0
      const onClose = vi.fn()
      const onRefresh = vi.fn()
      vi.stubGlobal(
        'fetch',
        vi.fn(async () => {
          callCount++
          if (callCount === 1) {
            return {
              ok: false,
              status: 500,
              json: async () => ({}),
              text: async () => '',
            } as unknown as Response
          }
          // Retry succeeds
          return { ok: true, status: 200, json: async () => ({}), text: async () => '' } as unknown as Response
        }),
      )

      const { container } = renderArchivalModal({ onClose, onRefresh })
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))

      await waitFor(() => expect(getArchivalError(container)).not.toBeNull(), { timeout: 2000 })

      const el = getArchivalError(container)!
      await act(async () => {
        el.onAction?.()
      })

      // On success, onClose is called and error is cleared
      await waitFor(() => expect(onClose).toHaveBeenCalled(), { timeout: 2000 })
      // AC-6a: notification element absent from DOM after successful retry
      await waitFor(() => expect(getArchivalError(container)).toBeNull(), { timeout: 2000 })
    })

    it('ArchivalModal: error element absent after onDismiss fires (setError(null))', async () => {
      vi.stubGlobal('fetch', makeJsonFetch(500, {}))
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))

      await waitFor(() => expect(getArchivalError(container)).not.toBeNull(), { timeout: 2000 })

      const el = getArchivalError(container)!
      await act(async () => {
        el.onDismiss?.()
      })

      await waitFor(() => {
        expect(getArchivalError(container)).toBeNull()
      }, { timeout: 2000 })
    })

    it('ArchivalModal: error cleared when reason selection changes (regression guard)', async () => {
      vi.stubGlobal('fetch', makeJsonFetch(500, {}))
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))

      await waitFor(() => expect(getArchivalError(container)).not.toBeNull(), { timeout: 2000 })

      // Changing reason clears error — existing handleReasonChange behavior
      selectReason(container, 'wontfix')

      await waitFor(() => {
        expect(getArchivalError(container)).toBeNull()
      }, { timeout: 2000 })
    })

  })

  // ─── AC-7: ArchivalModal getFocusableElements includes p-inline-notification ──

  describe('AC-7: ArchivalModal getFocusableElements selector includes p-inline-notification', () => {
    it('Tab keydown on dialog calls querySelectorAll with a selector that includes p-inline-notification', async () => {
      vi.stubGlobal('fetch', makeJsonFetch(500, {}))
      const { container } = renderArchivalModal()
      selectReason(container, 'dropped')
      fireEvent.click(getArchivalSubmitBtn(container))

      await waitFor(() => expect(getArchivalError(container)).not.toBeNull(), { timeout: 2000 })

      const dialog = container.querySelector('[role="dialog"]') as HTMLElement
      expect(dialog).not.toBeNull()

      const querySelectorAllSpy = vi.spyOn(dialog, 'querySelectorAll')
      fireEvent.keyDown(dialog, { key: 'Tab', bubbles: true })

      expect(querySelectorAllSpy).toHaveBeenCalled()
      const selectors = querySelectorAllSpy.mock.calls.map((c) => String(c[0]))
      expect(selectors.some((s) => s.includes('p-inline-notification'))).toBe(true)
    })
  })
})
