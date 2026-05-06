import type { RepairOutcome } from '../api/repair'
import { PButton, PSpinner, PText } from '@porsche-design-system/components-react'
import { useRepairFlow } from '../hooks/useRepairFlow'

export interface RepairPanelProps {
  corruptionCount: number
  onSuccess?: () => void
}

function renderOutcomeRows(outcomes: RepairOutcome[]) {
  return outcomes.map((outcome, index) => (
    <li key={`${outcome.file_path}-${outcome.code}-${index}`}>
      <span>{outcome.file_path}</span>
      {outcome.detail !== null ? <span>{outcome.detail}</span> : null}
    </li>
  ))
}

export default function RepairPanel({ corruptionCount, onSuccess }: RepairPanelProps) {
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

  if (phase === 'confirming') {
    return (
      <div
        data-testid="repair-confirm-dialog"
        role="dialog"
        aria-label="Confirm storage repair"
      >
        <PText>
          This will attempt to repair {requestedCount} corrupted files. Fixed files are restored,
          unfixable files are quarantined. Continue?
        </PText>
        <PButton
          data-testid="repair-confirm-btn"
          onClick={() => {
            void confirmRepair()
          }}
        >
          Confirm
        </PButton>
        <PButton data-testid="repair-cancel-btn" variant="secondary" onClick={cancelRepair}>
          Cancel
        </PButton>
      </div>
    )
  }

  if (phase === 'repairing') {
    return (
      <div data-testid="repair-loading">
        <PSpinner aria={{ 'aria-label': 'Repairing storage' }} />
        <PText>Repairing...</PText>
      </div>
    )
  }

  if (phase === 'done') {
    const grouped = results as NonNullable<typeof results>
    return (
      <div>
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
      <div>
        <PText data-testid="repair-error">{error}</PText>
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
      data-testid="repair-button"
      onClick={() => requestRepair(corruptionCount)}
    >
      Repair
    </PButton>
  )
}
