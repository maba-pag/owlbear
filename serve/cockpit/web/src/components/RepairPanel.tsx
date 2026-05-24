import type { RepairOutcome } from '../api/repair'
import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { PButton, PModal, PSpinner, PText } from '@porsche-design-system/components-react'
import { useRepairFlow } from '../hooks/useRepairFlow'
import './RepairPanel.css'

export interface RepairPanelProps {
  corruptionCount: number
  onSuccess?: () => void
  files?: Array<Pick<RepairOutcome, 'file_path' | 'code'>>
  portalConfirmDialog?: boolean
}

function renderOutcomeRows(outcomes: RepairOutcome[]) {
  return outcomes.map((outcome, index) => (
    <li key={`${outcome.file_path}-${outcome.code}-${index}`}>
      <span>{outcome.file_path}</span>
      {outcome.detail !== null ? <span>{outcome.detail}</span> : null}
    </li>
  ))
}

export default function RepairPanel({ corruptionCount, onSuccess, files = [], portalConfirmDialog = false }: RepairPanelProps) {
  const modalRef = useRef<HTMLElement | null>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const {
    phase,
    corruptionCount: requestedCount,
    results,
    error,
    requestRepair,
    confirmRepair,
    cancelRepair,
    dismissResults,
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
            <span className="text-xs font-semibold uppercase text-primary">Storage repair</span>
            <h2 className="m-0 text-xl font-semibold leading-tight text-primary">Repair {requestedCount} corrupted files?</h2>
            <PText className="m-0 text-sm leading-normal text-primary">
              Fixed files are restored, quarantined files move to .owlbear/kanban/quarantine, and failed files remain corrupted. This action can be irreversible.
            </PText>
          </div>
          {files.length > 0 ? (
            <ul className="m-0 grid max-h-[min(32vh,220px)] gap-static-xs overflow-y-auto p-0">
              {files.map((file, index) => (
                <li key={`${file.file_path}-${file.code}-${index}`} className="grid gap-1 rounded-lg border border-contrast-low bg-surface p-static-sm">
                  <span className="break-all font-mono text-xs leading-normal text-primary">{file.file_path}</span>
                  <span className="w-fit rounded-full border border-error bg-error px-static-xs py-1 text-xs font-semibold leading-none text-canvas">{file.code}</span>
                </li>
              ))}
            </ul>
          ) : null}
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

  if (phase === 'done') {
    const grouped = results as NonNullable<typeof results>
    return (
      <div className="repair-overlay">
        <section data-testid="repair-results-fixed">
          <PText weight="semibold">Fixed</PText>
          <ul>{renderOutcomeRows(grouped.fixed)}</ul>
        </section>
        <section data-testid="repair-results-quarantined">
          <PText weight="semibold">Quarantined</PText>
          <ul>{renderOutcomeRows(grouped.quarantined)}</ul>
        </section>
        <section data-testid="repair-results-failed">
          <PText weight="semibold">Failed</PText>
          <ul>{renderOutcomeRows(grouped.failed)}</ul>
        </section>
        <PButton data-testid="repair-dismiss-btn" variant="secondary" onClick={dismissResults}>
          Dismiss
        </PButton>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="repair-overlay">
        <PText data-testid="repair-error">{error}</PText>
        <PButton
          data-testid="repair-retry-btn"
          onClick={() => {
            void confirmRepair()
          }}
        >
          Retry
        </PButton>
        <PButton data-testid="repair-dismiss-btn" variant="secondary" onClick={dismissResults}>
          Dismiss
        </PButton>
      </div>
    )
  }

  if (corruptionCount <= 0) {
    return null
  }

  return (
    <PButton
      type="button"
      data-testid="repair-button"
      compact
      onClick={() => requestRepair(corruptionCount)}
    >
      Repair
    </PButton>
  )
}
