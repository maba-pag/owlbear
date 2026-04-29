import type { RepairOutcome } from '../api/repair'
import { useRepairFlow } from '../hooks/useRepairFlow'

export interface RepairPanelProps {
  corruptionCount: number
}

function renderOutcomeRows(outcomes: RepairOutcome[]) {
  return outcomes.map((outcome, index) => (
    <li key={`${outcome.file_path}-${outcome.code}-${index}`}>
      <span>{outcome.file_path}</span>
      {outcome.detail !== null ? <span>{outcome.detail}</span> : null}
    </li>
  ))
}

export default function RepairPanel({ corruptionCount }: RepairPanelProps) {
  const {
    phase,
    corruptionCount: requestedCount,
    results,
    error,
    requestRepair,
    confirmRepair,
    cancelRepair,
    dismissResults,
  } = useRepairFlow()

  if (phase === 'confirming') {
    return (
      <div
        data-testid="repair-confirm-dialog"
        role="dialog"
        aria-label="Confirm storage repair"
      >
        <p>Repair {requestedCount} corrupted items?</p>
        <button
          type="button"
          data-testid="repair-confirm-btn"
          onClick={() => {
            void confirmRepair()
          }}
        >
          Confirm
        </button>
        <button type="button" data-testid="repair-cancel-btn" onClick={cancelRepair}>
          Cancel
        </button>
      </div>
    )
  }

  if (phase === 'repairing') {
    return <div data-testid="repair-loading">Repairing...</div>
  }

  if (phase === 'done') {
    const grouped = results as NonNullable<typeof results>
    return (
      <div>
        <section data-testid="repair-results-fixed">
          <h3>Fixed</h3>
          <ul>{renderOutcomeRows(grouped.fixed)}</ul>
        </section>
        <section data-testid="repair-results-quarantined">
          <h3>Quarantined</h3>
          <ul>{renderOutcomeRows(grouped.quarantined)}</ul>
        </section>
        <section data-testid="repair-results-failed">
          <h3>Failed</h3>
          <ul>{renderOutcomeRows(grouped.failed)}</ul>
        </section>
        <button type="button" data-testid="repair-dismiss-btn" onClick={dismissResults}>
          Dismiss
        </button>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div>
        <p data-testid="repair-error">{error}</p>
        <button type="button" data-testid="repair-dismiss-btn" onClick={dismissResults}>
          Dismiss
        </button>
      </div>
    )
  }

  if (corruptionCount <= 0) {
    return null
  }

  return (
    <button
      type="button"
      data-testid="repair-button"
      onClick={() => requestRepair(corruptionCount)}
    >
      Repair
    </button>
  )
}