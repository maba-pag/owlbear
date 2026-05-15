import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import {
  PButton,
  PHeading,
  PInlineNotification,
  PText,
  PTextarea,
} from '@porsche-design-system/components-react'

import type { PendingDR } from '../hooks/usePendingDRs'
import { resolveDR } from '../api/decisions'
import { ApiError } from '../api/errors'

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
  const [response, setResponse] = useState<ResolveDecision>('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<ResolveErrorState | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const modalRef = useRef<HTMLDivElement | null>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const submitRef = useRef<HTMLElement | null>(null)
  const inlineNotificationRef = useRef<InlineNotificationHost | null>(null)

  async function handleSubmit(retrying = false) {
    if (!dr || isSubmitting) {
      return
    }
    if (!retrying) {
      setError(null)
    }
    setIsSubmitting(true)
    try {
      await resolveDR(dr.id, {
        response: response as 'approved' | 'rejected' | 'needs-info',
        notes,
      })
      setError(null)
      onResolved()
      onClose()
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

  if (!dr) return null

  useEffect(() => {
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    modalRef.current?.focus()

    return () => {
      previousFocusRef.current?.focus()
    }
  }, [])

  useEffect(() => {
    if (response === '') {
      submitRef.current?.setAttribute('disabled', '')
      return
    }
    submitRef.current?.removeAttribute('disabled')
  }, [response])

  useEffect(() => {
    function handleDocumentKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleDocumentKeyDown)
    return () => {
      document.removeEventListener('keydown', handleDocumentKeyDown)
    }
  }, [onClose])

  function getFocusableElements(): HTMLElement[] {
    const root = modalRef.current
    if (!root) {
      return []
    }

    return Array.from(
      root.querySelectorAll<HTMLElement>(
        'p-button:not([disabled]), button:not([disabled]), [href], input:not([disabled]), ' +
          'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    )
  }

  function handleModalKeyDown(event: React.KeyboardEvent<HTMLDivElement>): void {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      onClose()
      return
    }

    if (event.key !== 'Tab') {
      return
    }

    const focusable = getFocusableElements()
    if (focusable.length < 2) {
      return
    }

    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    const active = document.activeElement

    if (event.shiftKey && active === first) {
      event.preventDefault()
      last.focus()
      return
    }

    if (!event.shiftKey && active === last) {
      event.preventDefault()
      first.focus()
    }
  }

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

  return (
    <div
      data-testid="resolve-modal"
      role="dialog"
      aria-modal="true"
      aria-label="Resolve decision request"
      ref={modalRef}
      tabIndex={-1}
      onKeyDown={handleModalKeyDown}
      style={{
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 1000,
        maxWidth: '720px',
      }}
    >
      <PHeading ref={setHeadingTagAttr} tag="h2">{dr.title}</PHeading>
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{dr.body ?? ''}</ReactMarkdown>

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
      <PButton type="button" data-testid="resolve-cancel" variant="secondary" onClick={onClose}>
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
    </div>
  )
}

