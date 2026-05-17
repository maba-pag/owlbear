import { useEffect, useId, useMemo, useRef, useState } from 'react'
import {
  PButton,
  PHeading,
  PInlineNotification,
  PInputText,
  PModal,
  PSelect,
  PText,
} from '@porsche-design-system/components-react'
import { moveTask } from '../api/tasks'
import { ApiError } from '../api/errors'

const TAB_FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'a[href]',
  'p-button:not([disabled])',
  'p-inline-notification',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

const LEGACY_TAB_FOCUSABLE_SELECTOR =
  'p-button:not([disabled]), p-input-text:not([disabled]), p-select:not([disabled]), ' +
  'p-textarea:not([disabled]), button:not([disabled]), [href], input:not([disabled]), ' +
  'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

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
  returnFocusTo?: HTMLElement | null
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

interface ArchivalErrorState {
  message: string
  retryable: boolean
}

interface InlineNotificationHost extends HTMLElement {
  onAction?: () => void
  onDismiss?: () => void
}

export default function ArchivalModal({
  taskId,
  taskStatus,
  expectedUpdated,
  returnFocusTo = null,
  onClose,
  onRefresh,
}: ArchivalModalProps) {
  const titleId = useId()
  const modalRef = useRef<HTMLElement | null>(null)
  const reasonSelectRef = useRef<HTMLElement | null>(null)

  const [reason, setReason] = useState<ArchivalReason | ''>('')
  const [refsRaw, setRefsRaw] = useState('')
  const [error, setError] = useState<ArchivalErrorState | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const closeRequestedRef = useRef(false)
  const inlineNotificationRef = useRef<InlineNotificationHost | null>(null)

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
    const modal = modalRef.current
    const applyDialogAttrs = () => {
      modal?.setAttribute('role', 'dialog')
      modal?.setAttribute('aria-modal', 'true')
      modal?.setAttribute('aria-labelledby', titleId)
    }

    applyDialogAttrs()
    const observer = modal
      ? new MutationObserver(() => {
        applyDialogAttrs()
      })
      : null
    observer?.observe(modal as Node, { attributes: true, attributeFilter: ['role', 'aria-modal'] })

    reasonSelectRef.current?.focus()

    const handleDocumentTab = (nativeEvent: KeyboardEvent) => {
      if (nativeEvent.key !== 'Tab') {
        return
      }
      const root = modalRef.current
      if (!root) {
        return
      }
      const focusable = getFocusableElements(root)
      if (focusable.length === 0) {
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const legacyFocusable = root.querySelectorAll<HTMLElement>(LEGACY_TAB_FOCUSABLE_SELECTOR)
      const legacyFirst = legacyFocusable[0] ?? first
      const legacyLast = legacyFocusable[legacyFocusable.length - 1] ?? last
      const active = document.activeElement instanceof HTMLElement ? document.activeElement : null
      const target = nativeEvent.target instanceof Element
        ? (nativeEvent.target.closest(TAB_FOCUSABLE_SELECTOR) as HTMLElement | null)
        : null
      const current = target ?? active
      const isLastTarget = nativeEvent.target === last || active === last || current === last
      if (!current) {
        return
      }

      if (nativeEvent.shiftKey && (current === first || current === root)) {
        nativeEvent.preventDefault()
        legacyLast.focus()
      } else if (!nativeEvent.shiftKey && isLastTarget) {
        nativeEvent.preventDefault()
        legacyFirst.focus()
      }
    }

    modal?.addEventListener('keydown', handleDocumentTab)
    document.addEventListener('keydown', handleDocumentTab, true)

    return () => {
      observer?.disconnect()
      modal?.removeEventListener('keydown', handleDocumentTab)
      document.removeEventListener('keydown', handleDocumentTab, true)
    }
  }, [titleId])

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

  function handleDismiss() {
    if (closeRequestedRef.current) {
      return
    }
    closeRequestedRef.current = true
    const fallbackTarget =
      returnFocusTo ?? document.querySelector<HTMLElement>(`[data-testid="task-card"][data-id="${taskId}"]`)
    fallbackTarget?.focus()
    onClose()
    setTimeout(() => {
      fallbackTarget?.focus()
    }, 0)
  }

  function handleModalKeyDown(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === 'Tab') {
      const focusable = getFocusableElements(event.currentTarget)
      if (focusable.length === 0) {
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const legacyFocusable = event.currentTarget.querySelectorAll<HTMLElement>(LEGACY_TAB_FOCUSABLE_SELECTOR)
      const legacyFirst = legacyFocusable[0] ?? first
      const legacyLast = legacyFocusable[legacyFocusable.length - 1] ?? last
      const active = document.activeElement instanceof HTMLElement ? document.activeElement : null
      const target = event.target instanceof Element
        ? (event.target.closest(TAB_FOCUSABLE_SELECTOR) as HTMLElement | null)
        : null
      const current = target ?? active
      const isLastTarget = event.target === last || active === last || current === last

      if (event.shiftKey && (current === first || current === event.currentTarget)) {
        event.preventDefault()
        legacyLast.focus()
      } else if (!event.shiftKey && isLastTarget) {
        event.preventDefault()
        legacyFirst.focus()
      }
      return
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      handleDismiss()
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

  async function handleSubmit(retrying = false) {
    if (submitDisabled || reason === '') {
      return
    }

    const refsResult = parseRefsInput(refsRaw)
    if (refsResult.invalid) {
      setError({ message: 'Refs must contain only numeric task IDs.', retryable: false })
      return
    }

    setIsSubmitting(true)
    if (!retrying) {
      setError(null)
    }

    try {
      await moveTask(taskId, {
        status: 'archived',
        updated: expectedUpdated,
        archival_reason: reason,
        archival_refs: refsResult.values,
      })
      setError(null)
      onRefresh()
      onClose()
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 409) {
          setError({ message: 'Task snapshot is stale; refresh and try again.', retryable: false })
          onRefresh()
          return
        }

        if (error.status === 422) {
          setError({ message: error.message, retryable: false })
          return
        }

        const fallback = `Archival failed (${error.status}).`
        const message = error.message === `Move task request failed with status ${error.status}`
          ? fallback
          : error.message
        setError({ message, retryable: error.status >= 500 })
        return
      }

      setError({ message: 'Archival failed due to network error.', retryable: true })
    } finally {
      setIsSubmitting(false)
    }
  }

  const retryArchival = () => {
    void handleSubmit(true)
  }

  const dismissError = () => {
    setError(null)
  }

  return (
    <PModal
      ref={modalRef}
      data-testid="archival-modal"
      open
      onDismiss={handleDismiss}
      onKeyDown={handleModalKeyDown}
      aria-label="Archive task"
    >
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
      <PButton type="button" variant="secondary" onClick={handleDismiss}>
        Cancel
      </PButton>

      {error ? (
        <PInlineNotification
          ref={(element) => {
            inlineNotificationRef.current = element as InlineNotificationHost | null
            if (!inlineNotificationRef.current) {
              return
            }
            inlineNotificationRef.current.onAction = retryArchival
            inlineNotificationRef.current.onDismiss = dismissError
          }}
          data-testid="archival-error"
          state="error"
          description={error.message}
          actionLabel={error.retryable ? 'Retry' : undefined}
          actionIcon={error.retryable ? 'reset' : undefined}
          onAction={error.retryable ? retryArchival : undefined}
          actionLoading={isSubmitting}
          onDismiss={dismissError}
        />
      ) : null}
    </PModal>
  )
}
