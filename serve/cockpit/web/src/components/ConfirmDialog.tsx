import { useEffect, useMemo, useRef } from 'react'
import { PButton, PModal } from '@porsche-design-system/components-react'

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
    document.querySelector<HTMLElement>('[data-testid="confirm-dialog"]')?.focus()

    return () => {
      previousFocusRef.current?.focus()
    }
  }, [])

  function handleModalKeyDown(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      onCancel()
    }
  }

  return (
    <PModal
      data-testid="confirm-dialog"
      tabIndex={-1}
      open
      onDismiss={onCancel}
      onKeyDown={handleModalKeyDown}
      disableBackdropClick
      dismissButton={false}
      aria-label={description}
      aria={{ role: 'alertdialog', 'aria-label': description }}
    >
      <p>{description}</p>
      {type === 'unblock' && blockReason && <span>{blockReason}</span>}
      <PButton variant="secondary" onClick={onCancel}>Cancel</PButton>
      <PButton onClick={onConfirm}>{confirmLabel}</PButton>
    </PModal>
  )
}
