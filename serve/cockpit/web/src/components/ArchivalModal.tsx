import { useEffect, useId, useMemo, useRef, useState } from 'react'
import {
  PButton,
  PHeading,
  PInputText,
  PSelect,
  PText,
} from '@porsche-design-system/components-react'
import { getResponseErrorMessage } from '../api/errorMessage'

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

type ControlValueEvent = {
  target?: unknown
  detail?: unknown
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
  const reasonSelectRef = useRef<HTMLElement | null>(null)

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

  function setHeadingTagAttr(element: HTMLElement | null): void {
    element?.setAttribute('tag', 'h3')
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

  function getFocusableElements(): HTMLElement[] {
    const root = dialogRef.current
    if (!root) {
      return []
    }

    return Array.from(
      root.querySelectorAll<HTMLElement>(
        'p-button:not([disabled]), p-input-text:not([disabled]), p-select:not([disabled]), ' +
          'p-textarea:not([disabled]), button:not([disabled]), [href], input:not([disabled]), ' +
          'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
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
        onRefresh()
        return
      }

      if (response.status === 422) {
        setError(await getResponseErrorMessage(response, 'Validation failed.'))
        return
      }

      setError(
        await getResponseErrorMessage(response, `Archival failed (${response.status}).`),
      )
    } catch {
      setError('Archival failed due to network error.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={titleId} onKeyDown={handleKeyDown}>
      <PHeading ref={setHeadingTagAttr} id={titleId} tag="h2">Archive task</PHeading>

      <label>
        Reason
        <PSelect
          name="archival-reason"
          ref={reasonSelectRef}
          value={reason}
          onChange={(event) => {
            handleReasonChange(readControlValue(event))
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
        </PSelect>
      </label>

      {requiresRefs ? (
        <label>
          Refs
          <PInputText
            name="archival-refs"
            placeholder="e.g., 1230, 1229"
            value={refsRaw}
            onChange={(event) => {
              setRefsRaw(readControlValue(event))
              setError(null)
            }}
          />
          <PText>Required — enter at least one task ID</PText>
        </label>
      ) : null}

      <PButton
        data-testid="archival-submit"
        disabled={submitDisabled}
        onClick={() => {
          void handleSubmit()
        }}
      >
        Archive
      </PButton>
      <PButton type="button" variant="secondary" onClick={onClose}>
        Cancel
      </PButton>

      {error ? <PText data-testid="archival-error">{error}</PText> : null}
    </div>
  )
}

