import { useEffect, useMemo, useRef } from 'react'
import { PButton, PModal } from '@porsche-design-system/components-react'

const TAB_FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'a[href]',
  'p-button:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

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
  const modalRef = useRef<HTMLElement | null>(null)

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
    const modal = modalRef.current
    const applyDialogAttrs = () => {
      modal?.setAttribute('role', 'dialog')
      modal?.setAttribute('aria-modal', 'true')
    }

    applyDialogAttrs()
    const observer = modal
      ? new MutationObserver(() => {
        applyDialogAttrs()
      })
      : null
    observer?.observe(modal as Node, { attributes: true, attributeFilter: ['role', 'aria-modal'] })

    modal?.focus()

    return () => {
      observer?.disconnect()
      previousFocusRef.current?.focus()
    }
  }, [])

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

  function handleModalKeyDown(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === 'Tab') {
      const focusable = getFocusableElements(event.currentTarget)
      if (focusable.length === 0) {
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement instanceof HTMLElement ? document.activeElement : null

      if (event.shiftKey && (active === first || active === event.currentTarget)) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
      return
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      onCancel()
    }
  }

  return (
    <PModal
      ref={modalRef}
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
      <div className="grid max-w-[520px] gap-static-md">
        <div className="grid gap-static-xs rounded-lg bg-frosted-soft p-static-md text-primary">
          <span className="text-xs font-semibold uppercase text-primary">Confirm action</span>
          <p className="m-0 text-sm leading-normal">{description}</p>
          {type === 'unblock' && blockReason ? (
            <span className="rounded-md border border-contrast-low bg-surface p-static-xs text-sm text-primary">{blockReason}</span>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center justify-end gap-static-xs">
          <PButton variant="secondary" onClick={onCancel}>Cancel</PButton>
          <PButton onClick={onConfirm}>{confirmLabel}</PButton>
        </div>
      </div>
    </PModal>
  )
}
