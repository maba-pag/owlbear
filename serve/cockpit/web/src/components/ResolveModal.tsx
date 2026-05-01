import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  PButton,
  PHeading,
  PText,
  PTextarea,
} from '@porsche-design-system/components-react'

import type { PendingDR } from '../hooks/usePendingDRs'

export interface PendingDRWithBody extends PendingDR {
  body: string
}

export interface ResolveModalProps {
  dr: PendingDRWithBody | null
  onClose: () => void
  onResolved: () => void
}

export default function ResolveModal({ dr, onClose, onResolved }: ResolveModalProps) {
  const [response, setResponse] = useState('approved')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)

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
        setError('Failed to resolve decision request.')
        return
      }
      onResolved()
      onClose()
    } catch {
      setError('Failed to resolve decision request.')
    }
  }

  if (!dr) {
    return null
  }

  function setHeadingTagAttr(element: HTMLElement | null): void {
    element?.setAttribute('tag', 'h3')
  }

  function setHideLabelAttr(element: HTMLElement | null): void {
    element?.setAttribute('hide-label', '')
  }

  function readControlValue(
    event: {
      target?: { value?: unknown }
      detail?: { value?: unknown }
    },
  ): string {
    if (typeof event.detail?.value === 'string') {
      return event.detail.value
    }

    if (typeof event.target?.value === 'string') {
      return event.target.value
    }

    return ''
  }

  return (
    <div data-testid="resolve-modal" role="dialog" aria-label="Resolve decision request">
      <PHeading ref={setHeadingTagAttr} tag="h3">{dr.title}</PHeading>
      <ReactMarkdown>{dr.body}</ReactMarkdown>

      <fieldset data-testid="response-selector">
        <legend>Response</legend>
        <label>
          <input
            type="radio"
            name="resolve-response"
            value="approved"
            checked={response === 'approved'}
            onChange={() => setResponse('approved')}
          />
          approved
        </label>
        <label>
          <input
            type="radio"
            name="resolve-response"
            value="rejected"
            checked={response === 'rejected'}
            onChange={() => setResponse('rejected')}
          />
          rejected
        </label>
        <label>
          <input
            type="radio"
            name="resolve-response"
            value="needs-info"
            checked={response === 'needs-info'}
            onChange={() => setResponse('needs-info')}
          />
          needs-info
        </label>
      </fieldset>

      <PTextarea
        ref={setHideLabelAttr}
        data-testid="resolve-notes"
        hideLabel={true}
        value={notes}
        onChange={(event) => setNotes(readControlValue(event))}
        onInput={(event) => setNotes(readControlValue(event))}
      />

      <PButton
        data-testid="resolve-submit"
        onClick={() => {
          void handleSubmit()
        }}
      >
        Submit
      </PButton>
      <PButton data-testid="resolve-cancel" variant="tertiary" onClick={onClose}>
        Cancel
      </PButton>

      {error ? <PText data-testid="resolve-error">{error}</PText> : null}
    </div>
  )
}
