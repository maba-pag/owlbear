import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import {
  PButton,
  PHeading,
  PInlineNotification,
  PModal,
  PText,
  PTextarea,
} from '@porsche-design-system/components-react'

import type { PendingDR } from '../hooks/usePendingDRs'
import { resolveDR } from '../api/decisions'
import { ApiError } from '../api/errors'
import { formatAge, formatRequestType, getDecisionBodyMarkdown, getDecisionBrief } from '../utils/decisionBrief'

const TAB_FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'a[href]',
  'p-button:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

export type PendingDRWithBody = PendingDR

export interface ResolveModalProps {
  dr: PendingDRWithBody | null
  onClose: () => void
  onResolved: () => void
}

type ControlValueEvent = {
  target?: unknown
  detail?: unknown
}

type ResolveDecision = 'approved' | 'rejected' | 'needs-info' | ''

interface ResolveErrorState {
  message: string
  retryable: boolean
}

interface InlineNotificationHost extends HTMLElement {
  onAction?: () => void
  onDismiss?: () => void
}

export default function ResolveModal({ dr, onClose, onResolved }: ResolveModalProps) {
  const [snapshotDR] = useState<PendingDRWithBody | null>(() => dr)
  const [response, setResponse] = useState<ResolveDecision>('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<ResolveErrorState | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const modalRef = useRef<HTMLElement | null>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const closeRequestedRef = useRef(false)
  const submitRef = useRef<HTMLElement | null>(null)
  const inlineNotificationRef = useRef<InlineNotificationHost | null>(null)

  function requestClose() {
    if (closeRequestedRef.current) {
      return
    }
    closeRequestedRef.current = true
    onClose()
  }

  async function handleSubmit(retrying = false) {
    if (!snapshotDR || isSubmitting) {
      return
    }
    if (!retrying) {
      setError(null)
    }
    setIsSubmitting(true)
    try {
      await resolveDR(snapshotDR.id, {
        response: response as 'approved' | 'rejected' | 'needs-info',
        notes,
      })
      setError(null)
      onResolved()
      requestClose()
    } catch (caught) {
      if (caught instanceof ApiError) {
        const fallback = `Failed to resolve decision request (${caught.status}).`
        const message = caught.message === `Resolve request failed with status ${caught.status}`
          ? fallback
          : caught.message
        setError({ message, retryable: caught.status >= 500 })
        return
      }

      if (caught instanceof Error) {
        setError({ message: caught.message, retryable: true })
        return
      }
      setError({ message: 'Failed to resolve decision request.', retryable: true })
    } finally {
      setIsSubmitting(false)
    }
  }

  const retryResolve = () => {
    void handleSubmit(true)
  }

  const dismissError = () => {
    setError(null)
  }

  if (!snapshotDR) return null

  const brief = getDecisionBrief(snapshotDR)
  const fullRequestBody = getDecisionBodyMarkdown(snapshotDR) || snapshotDR.body || ''

  useEffect(() => {
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const modal = modalRef.current
    const applyDialogAttrs = () => {
      modal?.setAttribute('role', 'dialog')
      modal?.setAttribute('aria-modal', 'true')
      modal?.setAttribute('tabindex', '-1')
    }

    applyDialogAttrs()
    const observer = modal
      ? new MutationObserver(() => {
        applyDialogAttrs()
      })
      : null
    observer?.observe(modal as Node, { attributes: true, attributeFilter: ['role', 'aria-modal'] })

    modal?.focus()

    const handleDocumentEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') {
        return
      }
      if (event.defaultPrevented) {
        return
      }
      event.preventDefault()
      requestClose()
    }
    document.addEventListener('keydown', handleDocumentEscape)

    return () => {
      observer?.disconnect()
      document.removeEventListener('keydown', handleDocumentEscape)
      previousFocusRef.current?.focus()
    }
  }, [])

  function getFocusableElements(root: HTMLElement): HTMLElement[] {
    return Array.from(root.querySelectorAll<HTMLElement>(TAB_FOCUSABLE_SELECTOR)).filter((element) => {
      if (element.hasAttribute('disabled')) {
        return false
      }
      if (element.getAttribute('aria-hidden') === 'true') {
        return false
      }
      return true
    })
  }

  useEffect(() => {
    if (response === '') {
      submitRef.current?.setAttribute('disabled', '')
      return
    }
    submitRef.current?.removeAttribute('disabled')
  }, [response])

  function setHeadingTagAttr(element: HTMLElement | null): void {
    element?.setAttribute('tag', 'h3')
    element?.setAttribute('size', 'small')
  }


  function readControlValue(event: ControlValueEvent): string {
    const detailValue = (event.detail as { value?: unknown } | undefined)?.value
    const target = event.target as { value?: unknown } | undefined
    return typeof target?.value === 'string'
      ? target.value
      : typeof detailValue === 'string'
        ? detailValue
        : ''
  }

  function handleResponseChange(event: ControlValueEvent): void {
    const value = readControlValue(event)
    if (value === 'approved' || value === 'rejected' || value === 'needs-info') {
      setResponse(value)
    }
  }

  function handleModalKeyDown(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === 'Tab') {
      const focusable = getFocusableElements(event.currentTarget)
      if (focusable.length === 0) {
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement instanceof HTMLElement ? document.activeElement : null

      if (event.shiftKey && (active === first || active === event.currentTarget)) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
      return
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      requestClose()
    }
  }

  return (
    <PModal
      data-testid="resolve-modal"
      ref={modalRef}
      tabIndex={-1}
      open
      onDismiss={requestClose}
      onKeyDown={handleModalKeyDown}
      aria={{ 'aria-label': 'Resolve decision request' }}
    >
      <div
        className="grid max-h-[min(84vh,820px)] w-[min(920px,calc(100vw-8rem))] min-w-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-static-md overflow-hidden text-primary"
        data-testid="resolve-modal-surface"
      >
        <header className="grid gap-static-xs border-b border-contrast-low pb-static-sm pr-[4.5rem]">
          <span className="text-xs font-semibold uppercase text-primary">Decision request</span>
          <PHeading ref={setHeadingTagAttr} size="small" tag="h3">{brief.title}</PHeading>
          <div className="flex min-w-0 flex-wrap items-center gap-static-xs text-xs font-semibold text-primary">
            <span className="rounded-full border border-contrast-low bg-canvas px-static-xs py-1">Task #{snapshotDR.task_id}</span>
            <span className="rounded-full border border-contrast-low bg-canvas px-static-xs py-1">{snapshotDR.agent}</span>
            <span className="rounded-full border border-contrast-low bg-canvas px-static-xs py-1">{formatRequestType(snapshotDR.request_type)}</span>
            <span className="text-xs font-semibold text-contrast-high">{formatAge(snapshotDR.created)}</span>
          </div>
        </header>

        <div className="grid min-h-0 gap-static-md overflow-y-auto pr-static-xs">
          <section data-testid="resolve-request-summary" className="grid gap-static-sm rounded-lg border border-contrast-low bg-canvas p-static-md">
            <div className="grid gap-1">
              <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Context</span>
              <p className="m-0 text-sm leading-relaxed text-primary">{brief.context}</p>
            </div>
            {brief.options.length > 0 ? (
              <div className="grid gap-1">
                <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Options</span>
                <ol className="m-0 grid list-none gap-static-xs p-0 text-sm leading-normal text-primary">
                  {brief.options.map((option, optionIndex) => (
                    <li key={option} className="grid min-w-0 grid-cols-[1.5rem_minmax(0,1fr)] gap-static-xs">
                      <span className="inline-flex size-5 items-center justify-center rounded-full border border-contrast-low bg-surface text-xs font-semibold leading-none text-primary">
                        {optionIndex + 1}
                      </span>
                      <span>{option}</span>
                    </li>
                  ))}
                </ol>
              </div>
            ) : null}
            {brief.recommendation || brief.consequence ? (
              <div className="grid gap-static-sm sm:grid-cols-2">
                {brief.recommendation ? (
                  <div className="grid gap-1 border-l-2 border-info pl-static-xs">
                    <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Recommendation</span>
                    <p className="m-0 text-sm leading-normal text-primary">{brief.recommendation}</p>
                  </div>
                ) : null}
                {brief.consequence ? (
                  <div className="grid gap-1 border-l-2 border-contrast-low pl-static-xs">
                    <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Impact</span>
                    <p className="m-0 text-sm leading-normal text-primary">{brief.consequence}</p>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>

          <fieldset data-testid="response-selector" className="m-0 grid gap-static-sm border-0 p-0">
            <legend className="mb-static-xs text-xs font-semibold uppercase text-primary">Response</legend>
            <div className="grid gap-static-sm sm:grid-cols-3">
              <div data-testid="option-approved" className="rounded-lg border border-contrast-low bg-canvas p-static-sm">
                <label className="flex items-center gap-static-xs text-sm font-semibold text-primary">
                  <input
                    type="radio"
                    name="resolve-response"
                    value="approved"
                    checked={response === 'approved'}
                    onChange={handleResponseChange}
                  />
                  Approve
                </label>
                <PText>Proceed with approval and continue implementation.</PText>
              </div>
              <div data-testid="option-rejected" className="rounded-lg border border-contrast-low bg-canvas p-static-sm">
                <label className="flex items-center gap-static-xs text-sm font-semibold text-primary">
                  <input
                    type="radio"
                    name="resolve-response"
                    value="rejected"
                    checked={response === 'rejected'}
                    onChange={handleResponseChange}
                  />
                  Reject
                </label>
                <PText>Send this request back and stop current progress.</PText>
              </div>
              <div data-testid="option-needs-info" className="rounded-lg border border-contrast-low bg-canvas p-static-sm">
                <label className="flex items-center gap-static-xs text-sm font-semibold text-primary">
                  <input
                    type="radio"
                    name="resolve-response"
                    value="needs-info"
                    checked={response === 'needs-info'}
                    onChange={handleResponseChange}
                  />
                  Needs info
                </label>
                <PText>Ask for more details and wait for clarification.</PText>
              </div>
            </div>
          </fieldset>

          <details data-testid="resolve-full-request" className="rounded-lg border border-contrast-low bg-canvas p-static-sm text-primary">
            <summary className="cursor-pointer text-xs font-semibold uppercase leading-tight text-contrast-high">Full request</summary>
            <section className="mt-static-sm text-sm leading-relaxed text-primary [&_h2]:m-0 [&_h2]:mb-static-xs [&_h2]:text-base [&_h2]:font-semibold [&_li]:my-1 [&_p]:my-static-xs [&_ul]:my-static-xs [&_ul]:pl-static-md">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{fullRequestBody}</ReactMarkdown>
            </section>
          </details>

          <PTextarea
            compact
            label="Resolution notes"
            name="resolve-notes"
            rows={2}
            data-testid="resolve-notes"
            value={notes}
            onChange={(event) => setNotes(readControlValue(event))}
          />

          {error ? (
            <PInlineNotification
              ref={(element) => {
                inlineNotificationRef.current = element as InlineNotificationHost | null
                if (!inlineNotificationRef.current) {
                  return
                }
                inlineNotificationRef.current.onAction = retryResolve
                inlineNotificationRef.current.onDismiss = dismissError
              }}
              data-testid="resolve-error"
              state="error"
              description={error.message}
              actionLabel={error.retryable ? 'Retry' : undefined}
              actionIcon={error.retryable ? 'reset' : undefined}
              onAction={error.retryable ? retryResolve : undefined}
              actionLoading={isSubmitting}
              onDismiss={dismissError}
            />
          ) : null}
        </div>

        <footer className="flex flex-wrap items-center justify-end gap-static-xs border-t border-contrast-low pt-static-sm">
          <PButton
            ref={(element) => {
              submitRef.current = element
            }}
            type="button"
            data-testid="resolve-submit"
            variant="primary"
            disabled={response === ''}
            onClick={() => {
              void handleSubmit()
            }}
          >
            Submit Decision
          </PButton>
          <PButton type="button" data-testid="resolve-cancel" variant="secondary" onClick={requestClose}>
            Close Modal
          </PButton>
        </footer>
      </div>
    </PModal>
  )
}
