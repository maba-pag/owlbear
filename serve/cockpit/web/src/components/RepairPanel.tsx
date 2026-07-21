import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { PButton, PModal, PSpinner, PText } from '@porsche-design-system/components-react'
import { useRepairFlow } from '../hooks/useRepairFlow'
import type { WorkspaceRepairResponse } from '../api/repair'
import './RepairPanel.css'

export interface RepairPanelProps {
  repairableCount: number
  onSuccess?: (repair: WorkspaceRepairResponse) => void
  portalConfirmDialog?: boolean
}

export default function RepairPanel({ repairableCount, onSuccess, portalConfirmDialog = false }: RepairPanelProps) {
  const modalRef = useRef<HTMLElement | null>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const {
    phase,
    repairableCount: requestedCount,
    error,
    requestRepair,
    confirmRepair,
    cancelRepair,
    dismissError,
  } = useRepairFlow({ onSuccess })

  useEffect(() => {
    if (phase !== 'confirming') {
      previousFocusRef.current?.focus()
      return
    }

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

    function handleDocumentKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape') {
        return
      }
      event.preventDefault()
      cancelRepair()
    }

    document.addEventListener('keydown', handleDocumentKeyDown)
    return () => {
      observer?.disconnect()
      document.removeEventListener('keydown', handleDocumentKeyDown)
    }
  }, [cancelRepair, phase])

  function getFocusableElements(): HTMLElement[] {
    const root = modalRef.current
    if (!root) {
      return []
    }

    return Array.from(
      root.querySelectorAll<HTMLElement>(
        'p-button:not([disabled]), button:not([disabled]), [href], input:not([disabled]), ' +
          'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    )
  }

  function handleConfirmDialogKeyDown(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      cancelRepair()
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

    if (event.shiftKey && (active === first || active === event.currentTarget)) {
      event.preventDefault()
      last.focus()
      return
    }

    if (!event.shiftKey && active === last) {
      event.preventDefault()
      first.focus()
    }
  }

  if (phase === 'confirming') {
    const dialog = (
      <PModal
        ref={modalRef}
        data-testid="repair-confirm-dialog"
        data-workspace-status-overlay=""
        aria-label="Confirm storage repair"
        aria={{ role: 'alertdialog', 'aria-label': 'Confirm storage repair' }}
        tabIndex={-1}
        open
        onDismiss={cancelRepair}
        onKeyDown={handleConfirmDialogKeyDown}
        disableBackdropClick
        dismissButton={false}
      >
        <div className="grid max-w-[640px] gap-static-md text-primary">
          <div className="grid gap-static-xs rounded-lg border border-contrast-low bg-canvas p-static-md">
            <span className="text-xs font-semibold uppercase text-primary">Task health repair</span>
            <h2 className="m-0 text-xl font-semibold leading-tight text-primary">
              Repair {requestedCount} task {requestedCount === 1 ? 'finding' : 'findings'}?
            </h2>
            <PText className="m-0 text-sm leading-normal text-primary">
              OwlBear will apply every currently discoverable deterministic repair. Ambiguous findings remain unchanged and will be reported in the receipt.
            </PText>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-static-xs">
            <PButton data-testid="repair-cancel-btn" variant="secondary" onClick={cancelRepair}>
              Cancel
            </PButton>
            <PButton
              data-testid="repair-confirm-button"
              onClick={() => {
                void confirmRepair()
              }}
            >
              Run repair
            </PButton>
          </div>
        </div>
      </PModal>
    )

    return (
      <>
        <div className="repair-button-placeholder" aria-hidden="true" />
        {portalConfirmDialog && typeof document !== 'undefined'
          ? createPortal(dialog, document.body)
          : dialog}
      </>
    )
  }

  if (phase === 'repairing') {
    return (
      <div className="repair-overlay" data-testid="repair-loading" role="status" aria-live="polite">
        <PSpinner aria={{ 'aria-label': 'Repairing storage' }} />
        <PText>Repairing...</PText>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="repair-overlay" role="alert">
        <PText data-testid="repair-error">{error}</PText>
        <PButton
          data-testid="repair-retry-btn"
          onClick={() => {
            void confirmRepair()
          }}
        >
          Retry
        </PButton>
        <PButton data-testid="repair-dismiss-btn" variant="secondary" onClick={dismissError}>
          Dismiss
        </PButton>
      </div>
    )
  }

  if (repairableCount <= 0) {
    return null
  }

  return (
    <PButton
      type="button"
      data-testid="repair-button"
      compact
      onClick={() => requestRepair(repairableCount)}
    >
      Repair tasks
    </PButton>
  )
}
