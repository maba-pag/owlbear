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
  }

  function setHideLabelAttr(element: HTMLElement | null): void {
    element?.setAttribute('hide-label', '')
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
      <PHeading ref={setHeadingTagAttr} tag="h2">{snapshotDR.title}</PHeading>
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{snapshotDR.body ?? ''}</ReactMarkdown>

      <fieldset data-testid="response-selector">
        <legend>Response</legend>
        <div data-testid="option-approved">
          <label>
            <input
              type="radio"
              name="resolve-response"
              value="approved"
              checked={response === 'approved'}
              onChange={handleResponseChange}
            />
            approved
          </label>
          <PText>Proceed with approval and continue implementation.</PText>
        </div>
        <div data-testid="option-rejected">
          <label>
            <input
              type="radio"
              name="resolve-response"
              value="rejected"
              checked={response === 'rejected'}
              onChange={handleResponseChange}
            />
            rejected
          </label>
          <PText>Send this request back and stop current progress.</PText>
        </div>
        <div data-testid="option-needs-info">
          <label>
            <input
              type="radio"
              name="resolve-response"
              value="needs-info"
              checked={response === 'needs-info'}
              onChange={handleResponseChange}
            />
            needs-info
          </label>
          <PText>Ask for more details and wait for clarification.</PText>
        </div>
      </fieldset>

      <PTextarea
        label="Resolution notes"
        name="resolve-notes"
        ref={setHideLabelAttr}
        data-testid="resolve-notes"
        value={notes}
        onChange={(event) => setNotes(readControlValue(event))}
      />

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
    </PModal>
  )
}
