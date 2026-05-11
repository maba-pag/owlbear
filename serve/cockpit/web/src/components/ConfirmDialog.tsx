import { useEffect, useMemo, useRef } from 'react'
import { PButton } from '@porsche-design-system/components-react'

export interface ConfirmDialogProps {
  type: 'move-backward' | 'unblock' | 'unclaim'
  targetStatus?: string | null
  blockReason?: string | null
  onCancel: () => void
  onConfirm: () => void
}

export default function ConfirmDialog({
  type,
  targetStatus,
  blockReason,
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  const { description, confirmLabel } = useMemo(() => {
    if (type === 'move-backward') {
      const targetLabel = targetStatus ?? 'previous status'
      return {
        description: `Move to ${targetLabel}?`,
        confirmLabel: `Move to ${targetLabel}`,
      }
    }

    if (type === 'unclaim') {
      return {
        description: 'Release claim?',
        confirmLabel: 'Release claim',
      }
    }

    return {
      description: 'Unblock task?',
      confirmLabel: 'Unblock task',
    }
  }, [type, targetStatus])

  useEffect(() => {
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    dialogRef.current?.focus()

    return () => {
      previousFocusRef.current?.focus()
    }
  }, [])

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      onCancel()
    }
  }

  return (
    <div
      ref={dialogRef}
      data-testid="confirm-dialog"
      role="dialog"
      aria-modal="true"
      aria-label={description}
      tabIndex={-1}
      onKeyDown={handleKeyDown}
    >
      <p>{description}</p>
      {type === 'unblock' && blockReason && <span>{blockReason}</span>}
      <PButton variant="secondary" onClick={onCancel}>Cancel</PButton>
      <PButton onClick={onConfirm}>{confirmLabel}</PButton>
    </div>
  )
}

