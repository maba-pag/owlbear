import { useEffect, useId, useMemo, useRef, useState } from 'react'

export const ARCHIVAL_REASONS = [
  'completed',
  'dropped',
  'wontfix',
  'deprecated',
  'duplicate',
] as const

type ArchivalReason = (typeof ARCHIVAL_REASONS)[number]

interface ArchivalModalProps {
  taskId: number
  taskStatus: string
  expectedUpdated: string
  onClose: () => void
  onRefresh: () => void
}

const REASONS_REQUIRING_REFS: ReadonlySet<ArchivalReason> = new Set(['deprecated', 'duplicate'])

function parseRefsInput(refsRaw: string): { values: number[]; invalid: boolean } {
  const parts = refsRaw
    .trim()
    .split(/[\s,]+/)
    .filter((part) => part.length > 0)

  if (parts.length === 0) {
    return { values: [], invalid: false }
  }

  const values: number[] = []
  for (const part of parts) {
    if (!/^\d+$/.test(part)) {
      return { values: [], invalid: true }
    }
    values.push(Number.parseInt(part, 10))
  }

  return { values, invalid: false }
}

export default function ArchivalModal({
  taskId,
  taskStatus,
  expectedUpdated,
  onClose,
  onRefresh,
}: ArchivalModalProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement | null>(null)
  const reasonSelectRef = useRef<HTMLSelectElement | null>(null)

  const [reason, setReason] = useState<ArchivalReason | ''>('')
  const [refsRaw, setRefsRaw] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const requiresRefs = reason !== '' && REASONS_REQUIRING_REFS.has(reason)
  const hasRefs = refsRaw.trim().length > 0

  const submitDisabled = useMemo(() => {
    if (isSubmitting) {
      return true
    }
    if (reason === '') {
      return true
    }
    if (requiresRefs && !hasRefs) {
      return true
    }
    return false
  }, [hasRefs, isSubmitting, reason, requiresRefs])

  useEffect(() => {
    reasonSelectRef.current?.focus()
  }, [])

  function getFocusableElements(): HTMLElement[] {
    const root = dialogRef.current
    if (!root) {
      return []
    }

    return Array.from(
      root.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    )
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
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

  function handleReasonChange(nextReason: string) {
    const parsedReason = nextReason as ArchivalReason | ''
    const wasRefsReason = reason !== '' && REASONS_REQUIRING_REFS.has(reason)
    const isRefsReason = parsedReason !== '' && REASONS_REQUIRING_REFS.has(parsedReason)

    setReason(parsedReason)
    setError(null)

    if (wasRefsReason && !isRefsReason) {
      setRefsRaw('')
    }
  }

  async function handleSubmit() {
    if (submitDisabled || reason === '') {
      return
    }

    const refsResult = parseRefsInput(refsRaw)
    if (refsResult.invalid) {
      setError('Refs must contain only numeric task IDs.')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const response = await fetch(`/api/tasks/${taskId}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'archived',
          updated: expectedUpdated,
          archival_reason: reason,
          archival_refs: refsResult.values,
        }),
      })

      if (response.ok) {
        onRefresh()
        onClose()
        return
      }

      if (response.status === 409) {
        setError('Task snapshot is stale; refresh and try again.')
        return
      }

      if (response.status === 422) {
        const payload = (await response.json()) as { detail?: unknown }
        const detail = typeof payload.detail === 'string' ? payload.detail : 'Validation failed.'
        setError(detail)
        return
      }

      setError(`Archival failed (${response.status}).`)
    } catch {
      setError('Archival failed due to network error.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={titleId} onKeyDown={handleKeyDown}>
      <h3 id={titleId}>Archive task</h3>

      <label>
        Reason
        <select
          ref={reasonSelectRef}
          value={reason}
          onChange={(event) => {
            handleReasonChange(event.target.value)
          }}
        >
          <option value="">Select reason</option>
          {ARCHIVAL_REASONS.map((item) => {
            if (item === 'completed' && taskStatus !== 'done') {
              return null
            }

            return (
              <option key={item} value={item}>
                {item}
              </option>
            )
          })}
        </select>
      </label>

      {requiresRefs ? (
        <label>
          Refs
          <input
            type="text"
            value={refsRaw}
            onChange={(event) => {
              setRefsRaw(event.target.value)
              setError(null)
            }}
          />
          <p>Required — enter at least one task ID</p>
        </label>
      ) : null}

      <button
        data-testid="archival-submit"
        disabled={submitDisabled}
        onClick={() => {
          void handleSubmit()
        }}
      >
        Archive
      </button>
      <button type="button" onClick={onClose}>
        Cancel
      </button>

      {error ? <p data-testid="archival-error">{error}</p> : null}
    </div>
  )
}
