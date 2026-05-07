import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import {
  PButton,
  PHeading,
  PText,
  PTextarea,
} from '@porsche-design-system/components-react'

import type { PendingDR } from '../hooks/usePendingDRs'
import { getResponseErrorMessage } from '../api/errorMessage'

export interface PendingDRWithBody extends PendingDR {
  body?: string
}

export interface ResolveModalProps {
  dr: PendingDRWithBody | null
  onClose: () => void
  onResolved: () => void
}

type ControlValueEvent = {
  target?: unknown
  detail?: unknown
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

  if (!dr) {
    return null
  }

  function setHeadingTagAttr(element: HTMLElement | null): void {
    element?.setAttribute('tag', 'h3')
  }

  function setHideLabelAttr(element: HTMLElement | null): void {
    element?.setAttribute('hide-label', '')
  }

  function readControlValue(event: ControlValueEvent): string {
    const detailValue = (event.detail as { value?: unknown } | undefined)?.value
    if (typeof detailValue === 'string') {
      return detailValue
    }

    const target = event.target as { value?: unknown } | undefined
    if (typeof target?.value === 'string') {
      return target.value
    }

    return ''
  }

  return (
    <div data-testid="resolve-modal" role="dialog" aria-label="Resolve decision request">
      <PHeading ref={setHeadingTagAttr} tag="h3">{dr.title}</PHeading>
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>{dr.body ?? ''}</ReactMarkdown>

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
        name="resolve-notes"
        ref={setHideLabelAttr}
        data-testid="resolve-notes"
        hideLabel={true}
        value={notes}
        onChange={(event) => setNotes(readControlValue(event))}
      />

      <PButton
        data-testid="resolve-submit"
        onClick={() => {
          void handleSubmit()
        }}
      >
        Submit
      </PButton>
      <PButton data-testid="resolve-cancel" variant="secondary" onClick={onClose}>
        Cancel
      </PButton>

      {error ? <PText data-testid="resolve-error">{error}</PText> : null}
    </div>
  )
}
