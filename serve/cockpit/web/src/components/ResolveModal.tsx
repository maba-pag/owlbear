import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import { PButton, PHeading, PText, PTextarea } from '@porsche-design-system/components-react'

import type { PendingDR } from '../hooks/usePendingDRs'
import { getResponseErrorMessage } from '../api/errorMessage'

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

type ResolveResponse = 'approved' | 'rejected' | 'needs-info' | ''

export default function ResolveModal({ dr, onClose, onResolved }: ResolveModalProps) {
  const [response, setResponse] = useState<ResolveResponse>('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const modalRef = useRef<HTMLDivElement | null>(null)
  const submitRef = useRef<HTMLElement | null>(null)

  async function handleSubmit() {
    if (!dr) {
      return
    }
    setError(null)
    try {
      const res = await fetch(`/api/decisions/${dr.id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ response, notes }),
      })
      if (!res.ok) {
        const errorMessage = await getResponseErrorMessage(res, 'Failed to resolve decision request.')
        setError(errorMessage)
        return
      }
      onResolved()
      onClose()
    } catch (caught) {
      if (caught instanceof Error) {
        setError(caught.message)
        return
      }
      setError('Failed to resolve decision request.')
    }
  }

  if (!dr) return null

  useEffect(() => {
    modalRef.current?.focus()
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

  function handleModalKeyDown(event: { key: string; stopPropagation: () => void }): void {
    if (event.key === 'Escape') {
      event.stopPropagation()
      onClose()
    }
  }

  function setHeadingTagAttr(element: HTMLElement | null): void {
    element?.setAttribute('tag', 'h2')
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

      {error ? <PText data-testid="resolve-error">{error}</PText> : null}
    </div>
  )
}
