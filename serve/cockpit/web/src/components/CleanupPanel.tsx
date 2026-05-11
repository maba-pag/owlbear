import { PButton, PSpinner, PText } from '@porsche-design-system/components-react'
import { useCleanupFlow } from '../hooks/useCleanupFlow'

export interface CleanupPanelProps {
  onSuccess?: () => void
}

function renderSkippedItems(skippedItems: Array<{ path: string; reason: string }>) {
  return skippedItems.map((item, index) => (
    <li key={`${item.path}-${item.reason}-${index}`}>
      <span>{item.path}</span>
      <span>{item.reason}</span>
    </li>
  ))
}

export default function CleanupPanel({ onSuccess }: CleanupPanelProps) {
  const {
    phase,
    results,
    error,
    requestCleanup,
    confirmCleanup,
    cancelCleanup,
    dismissResults,
  } = useCleanupFlow({ onSuccess })

  if (phase === 'confirming') {
    return (
      <div data-testid="cleanup-confirm-dialog" role="dialog" aria-label="Confirm task cleanup">
        <PText>
          This will run maintenance cleanup to release stale claims and archive completed tasks.
        </PText>
        <PButton
          data-testid="cleanup-confirm-btn"
          onClick={() => {
            void confirmCleanup()
          }}
        >
          Confirm
        </PButton>
        <PButton data-testid="cleanup-cancel-btn" variant="secondary" onClick={cancelCleanup}>
          Cancel
        </PButton>
      </div>
    )
  }

  if (phase === 'running') {
    return (
      <div data-testid="cleanup-loading">
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

  return (
    <PButton data-testid="cleanup-button" onClick={requestCleanup}>
      Cleanup
    </PButton>
  )
}