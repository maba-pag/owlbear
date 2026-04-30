import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

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

  return (
    <div data-testid="resolve-modal" role="dialog" aria-label="Resolve decision request">
      <h3>{dr.title}</h3>
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

      <textarea
        data-testid="resolve-notes"
        value={notes}
        onChange={(event) => setNotes(event.target.value)}
      />

      <button
        data-testid="resolve-submit"
        onClick={() => {
          void handleSubmit()
        }}
      >
        Submit
      </button>
      <button data-testid="resolve-cancel" onClick={onClose}>
        Cancel
      </button>

      {error ? <p data-testid="resolve-error">{error}</p> : null}
    </div>
  )
}
