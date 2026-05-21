import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { PButton, PButtonPure, PModal, PSpinner, PText } from '@porsche-design-system/components-react'
import { useCleanupFlow } from '../hooks/useCleanupFlow'

export interface CleanupPanelProps {
  compact?: boolean
  onSuccess?: () => void
  portalConfirmDialog?: boolean
}

function renderSkippedItems(skippedItems: Array<{ path: string; reason: string }>) {
  return skippedItems.map((item, index) => (
    <li key={`${item.path}-${item.reason}-${index}`}>
      <span>{item.path}</span>
      <span>{item.reason}</span>
    </li>
  ))
}

export default function CleanupPanel({ compact = false, onSuccess, portalConfirmDialog = false }: CleanupPanelProps) {
  const modalRef = useRef<HTMLElement | null>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const {
    phase,
    results,
    error,
    requestCleanup,
    confirmCleanup,
    cancelCleanup,
    dismissResults,
  } = useCleanupFlow({ onSuccess })

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

    return () => {
      observer?.disconnect()
    }
  }, [phase])

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
      cancelCleanup()
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
        data-testid="cleanup-confirm-dialog"
        aria-label="Confirm task cleanup"
        aria={{ role: 'alertdialog', 'aria-label': 'Confirm task cleanup' }}
        tabIndex={-1}
        open
        onDismiss={cancelCleanup}
        onKeyDown={handleConfirmDialogKeyDown}
        disableBackdropClick
        dismissButton={false}
      >
        <div className="grid max-w-[560px] gap-static-md text-primary">
          <div className="grid gap-static-xs rounded-lg border border-contrast-low bg-canvas p-static-md">
            <span className="text-xs font-semibold uppercase text-primary">Workspace cleanup</span>
            <h2 className="m-0 text-xl font-semibold leading-tight text-primary">Run maintenance cleanup?</h2>
            <p className="m-0 text-sm leading-normal text-primary">
              This releases stale claims and archives completed tasks so the board starts from a clean operational state.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-static-xs">
            <PButton data-testid="cleanup-cancel-btn" variant="secondary" onClick={cancelCleanup}>
              Cancel
            </PButton>
            <PButton
              data-testid="cleanup-confirm-btn"
              onClick={() => {
                void confirmCleanup()
              }}
            >
              Run cleanup
            </PButton>
          </div>
        </div>
      </PModal>
    )

    return portalConfirmDialog && typeof document !== 'undefined'
      ? createPortal(dialog, document.body)
      : dialog
  }

  if (phase === 'running') {
    return (
      <div data-testid="cleanup-loading" role="status" aria-live="polite">
        <PSpinner aria={{ 'aria-label': 'Running cleanup' }} />
        <PText>Running cleanup...</PText>
      </div>
    )
  }

  if (phase === 'done') {
    const cleanupResults = results as NonNullable<typeof results>

    return (
      <div>
        <PText data-testid="cleanup-released-count">
          Released claims: {cleanupResults.released_claim_ids.length}
        </PText>
        <PText data-testid="cleanup-archived-count">
          Archived tasks: {cleanupResults.archived_task_ids.length}
        </PText>
        <PText data-testid="cleanup-skipped-count">
          Skipped items: {cleanupResults.skipped_items.length}
        </PText>
        {cleanupResults.skipped_items.length > 0 ? (
          <ul data-testid="cleanup-skipped-list">
            {renderSkippedItems(cleanupResults.skipped_items)}
          </ul>
        ) : null}
        <PButton data-testid="cleanup-dismiss-btn" variant="secondary" onClick={dismissResults}>
          Dismiss
        </PButton>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div>
        <PText data-testid="cleanup-error">{error}</PText>
        <PButton
          data-testid="cleanup-retry-btn"
          onClick={() => {
            void confirmCleanup()
          }}
        >
          Retry
        </PButton>
        <PButton data-testid="cleanup-dismiss-btn" variant="secondary" onClick={dismissResults}>
          Dismiss
        </PButton>
      </div>
    )
  }

  if (compact) {
    return (
      <PButtonPure
        type="button"
        icon="delete"
        hideLabel
        data-testid="cleanup-button"
        aria-label="Cleanup"
        onClick={requestCleanup}
      >
        Cleanup
      </PButtonPure>
    )
  }

  return (
    <PButton
      type="button"
      data-testid="cleanup-button"
      variant="secondary"
      compact
      onClick={requestCleanup}
    >
      Cleanup
    </PButton>
  )
}
