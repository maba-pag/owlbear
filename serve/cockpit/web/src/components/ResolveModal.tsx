import { useCallback, useEffect, useRef, useState } from 'react'
import {
  PButton,
  PHeading,
  PInlineNotification,
  PModal,
  PTag,
  PText,
  PTextarea,
} from '@porsche-design-system/components-react'

import type { PendingDR } from '../hooks/usePendingDRs'
import { resolveDR } from '../api/decisions'
import { ApiError } from '../api/errors'
import { formatAge, formatRequestType } from '../utils/decisionBrief'
import { openTaskDetail } from '../utils/openTaskDetail'
import MarkdownPreview from './MarkdownPreview'

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

interface ResolveErrorState {
  message: string
  retryable: boolean
}

interface InlineNotificationHost extends HTMLElement {
  onAction?: () => void
  onDismiss?: () => void
}

interface ResolveMetadataItem {
  label: string
  value: string
  testId: string
  taskId?: number
}

function formatOptionalMetadata(value: string): string {
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : 'Unspecified'
}

function formatCreatedMetadata(created: string): string {
  const trimmed = created.trim()
  return trimmed.length > 0 ? `${trimmed} (${formatAge(trimmed)})` : 'Unspecified'
}

export default function ResolveModal({ dr, onClose, onResolved }: ResolveModalProps) {
  const [snapshotDR] = useState<PendingDRWithBody | null>(() => dr)
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<ResolveErrorState | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [resolveBodyCanScrollDown, setResolveBodyCanScrollDown] = useState(false)
  const modalRef = useRef<HTMLElement | null>(null)
  const resolveBodyRef = useRef<HTMLDivElement | null>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const closeRequestedRef = useRef(false)
  const submitRef = useRef<HTMLElement | null>(null)
  const inlineNotificationRef = useRef<InlineNotificationHost | null>(null)

  const updateResolveBodyScrollCue = useCallback(() => {
    const body = resolveBodyRef.current
    setResolveBodyCanScrollDown(Boolean(body && body.scrollHeight - body.scrollTop - body.clientHeight > 1))
  }, [])

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
    const requestKind = snapshotDR.kind ?? (snapshotDR.request_type === 'action' ? 'action' : 'decision')
    const nextSelectedOptionId = requestKind === 'decision' ? selectedOptionId : null
    if (requestKind === 'decision' && nextSelectedOptionId === null) {
      return
    }

    if (!retrying) {
      setError(null)
    }
    setIsSubmitting(true)
    try {
      await resolveDR(snapshotDR.id, {
        selected_option_id: nextSelectedOptionId,
        free_text: notes.trim().length > 0 ? notes.trim() : null,
        kind: requestKind,
      })
      setError(null)
      onResolved()
      requestClose()
    } catch (caught) {
      if (caught instanceof ApiError) {
        const fallback = `Failed to resolve request (${caught.status}).`
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
      setError({ message: 'Failed to resolve request.', retryable: true })
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

  const requestKind = snapshotDR.kind ?? (snapshotDR.request_type === 'action' ? 'action' : 'decision')
  const requestTitleValue = typeof snapshotDR.title === 'string' ? snapshotDR.title : ''
  const requestSummaryValue = typeof snapshotDR.summary === 'string'
    ? snapshotDR.summary
    : typeof snapshotDR.body_preview === 'string'
      ? snapshotDR.body_preview
      : ''
  const requestTitle = requestTitleValue.trim().length > 0 ? requestTitleValue : `Request #${snapshotDR.id}`
  const requestSummary = requestSummaryValue.trim().length > 0 ? requestSummaryValue : 'No summary provided.'
  const decisionOptions = requestKind === 'decision' && Array.isArray(snapshotDR.options) ? snapshotDR.options : []
  const fullRequestBody = typeof snapshotDR.body === 'string' ? snapshotDR.body : ''
  const canSubmit = !isSubmitting && (requestKind === 'action' || selectedOptionId !== null)

  const metadataItems: ResolveMetadataItem[] = [
    { label: 'Task', value: `#${snapshotDR.task_id}`, testId: 'resolve-metadata-task', taskId: snapshotDR.task_id },
    { label: 'Request type', value: formatRequestType(snapshotDR.request_type), testId: 'resolve-metadata-request-type' },
    { label: 'Created', value: formatCreatedMetadata(snapshotDR.created), testId: 'resolve-metadata-created' },
    { label: 'Agent', value: formatOptionalMetadata(snapshotDR.agent), testId: 'resolve-metadata-agent' },
    { label: 'Source ID', value: formatOptionalMetadata(snapshotDR.id), testId: 'resolve-metadata-source' },
  ]

  useEffect(() => {
    updateResolveBodyScrollCue()
  }, [error, fullRequestBody, selectedOptionId, updateResolveBodyScrollCue])

  useEffect(() => {
    const body = resolveBodyRef.current
    if (!body) {
      return
    }

    updateResolveBodyScrollCue()
    if (typeof ResizeObserver === 'undefined') {
      return
    }

    const observer = new ResizeObserver(updateResolveBodyScrollCue)
    observer.observe(body)
    return () => {
      observer.disconnect()
    }
  }, [updateResolveBodyScrollCue])

  useEffect(() => {
    window.addEventListener('resize', updateResolveBodyScrollCue)
    return () => {
      window.removeEventListener('resize', updateResolveBodyScrollCue)
    }
  }, [updateResolveBodyScrollCue])

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
    if (!canSubmit) {
      submitRef.current?.setAttribute('disabled', '')
      return
    }
    submitRef.current?.removeAttribute('disabled')
  }, [canSubmit])

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
        className="grid max-h-[min(84vh,820px)] w-[min(1280px,calc(100vw-18.5rem))] max-w-full min-w-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-static-md overflow-hidden text-primary"
        data-testid="resolve-modal-surface"
      >
        <header className="grid gap-static-xs border-b border-contrast-low pb-static-sm pr-[4.5rem]">
          <span className="text-xs font-semibold uppercase text-primary">Decision request</span>
          <PHeading ref={setHeadingTagAttr} size="small" tag="h3">{requestTitle}</PHeading>
          <div data-testid="resolve-header-meta" className="flex min-w-0 flex-wrap items-center gap-static-xs text-xs font-semibold text-primary">
            <PButton
              type="button"
              data-testid="resolve-open-task"
              variant="secondary"
              compact
              onClick={() => openTaskDetail(snapshotDR.task_id)}
            >
              Task #{snapshotDR.task_id}
            </PButton>
            <PTag compact variant="secondary">{formatRequestType(snapshotDR.request_type)}</PTag>
            <span className="text-xs font-semibold text-contrast-high">{formatAge(snapshotDR.created)}</span>
          </div>
        </header>

        <div className="relative min-h-0 overflow-hidden">
          <div
            ref={resolveBodyRef}
            data-testid="resolve-scroll-body"
            className="grid h-full min-h-0 gap-static-md overflow-y-auto pb-static-sm pr-static-xs"
            onScroll={updateResolveBodyScrollCue}
          >
            <section data-testid="resolve-request-summary" className="grid gap-static-sm rounded-lg border border-contrast-low bg-canvas p-static-md">
              <div className="grid gap-1">
                <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Summary</span>
                <p className="m-0 text-sm leading-relaxed text-primary">{requestSummary}</p>
              </div>
            {decisionOptions.length > 0 ? (
              <div className="grid gap-1">
                <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Options</span>
                <ol className="m-0 grid list-none gap-static-xs p-0 text-sm leading-normal text-primary">
                  {decisionOptions.map((option, optionIndex) => (
                    <li key={option.option_id} className="grid min-w-0 grid-cols-[1.5rem_minmax(0,1fr)] gap-static-xs">
                      <span className="inline-flex size-5 items-center justify-center rounded-full border border-contrast-low bg-surface text-xs font-semibold leading-none text-primary">
                        {optionIndex + 1}
                      </span>
                      <span>{option.label}</span>
                    </li>
                  ))}
                </ol>
              </div>
            ) : null}
            </section>

            <section data-testid="resolve-decision-metadata" className="rounded-lg border border-contrast-low bg-canvas p-static-sm">
              <div className="mb-static-xs flex min-w-0 items-center justify-between gap-static-sm">
                <PHeading size="small" tag="h3">Metadata</PHeading>
              </div>
              <dl className="m-0 grid min-w-0 gap-x-static-lg gap-y-static-xs text-sm text-primary sm:grid-cols-2 lg:grid-cols-3">
                {metadataItems.map((item) => (
                  <div key={item.testId} data-testid={item.testId} className="min-w-0">
                    <dt className="font-semibold text-contrast-high">{item.label}</dt>
                    <dd className="m-0 min-w-0 break-words text-primary">
                      {typeof item.taskId === 'number' ? (
                        <PButton
                          type="button"
                          data-testid="resolve-metadata-open-task"
                          variant="secondary"
                          compact
                          onClick={() => openTaskDetail(item.taskId!)}
                        >
                          {item.value}
                        </PButton>
                      ) : item.value}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>

            <fieldset data-testid="response-selector" className="m-0 grid gap-static-sm border-0 p-0">
              <legend className="mb-static-xs text-xs font-semibold uppercase text-primary">Response</legend>
              {requestKind === 'decision' ? (
                <div className="grid gap-static-sm">
                  {decisionOptions.map((option) => (
                    <button
                      key={option.option_id}
                      type="button"
                      data-testid={`resolve-option-${option.option_id}`}
                      className="rounded-lg border border-contrast-low bg-canvas p-static-sm text-left text-sm font-semibold text-primary"
                      onClick={() => {
                        setSelectedOptionId(option.option_id)
                      }}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              ) : (
                <PText>Mark this action as complete to resolve it.</PText>
              )}
            </fieldset>

            <details data-testid="resolve-full-request" className="rounded-lg border border-contrast-low bg-canvas p-static-sm text-primary">
              <summary className="cursor-pointer text-xs font-semibold uppercase leading-tight text-contrast-high">Full request</summary>
              <MarkdownPreview className="mt-static-sm text-sm">{fullRequestBody}</MarkdownPreview>
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
          {resolveBodyCanScrollDown ? (
            <div
              aria-hidden="true"
              data-testid="resolve-scroll-cue"
              className="pointer-events-none absolute inset-x-0 bottom-0 h-10 [background:linear-gradient(to_bottom,transparent,var(--p-color-canvas))]"
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
            disabled={!canSubmit}
            onClick={() => {
              void handleSubmit()
            }}
          >
            {requestKind === 'action' ? 'Complete' : 'Submit Decision'}
          </PButton>
          <PButton type="button" data-testid="resolve-cancel" variant="secondary" onClick={requestClose}>
            Close Modal
          </PButton>
        </footer>
      </div>
    </PModal>
  )
}
