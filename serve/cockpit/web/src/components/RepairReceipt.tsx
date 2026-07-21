import { PButton } from '@porsche-design-system/components-react'
import { createPortal } from 'react-dom'
import type { RepairOutcome, WorkspaceRepairResponse } from '../api/repair'

export interface RepairReceiptProps {
  receipt: WorkspaceRepairResponse
  onDismiss: () => void
}

const COUNTS: Array<{ key: keyof WorkspaceRepairResponse; label: string }> = [
  { key: 'removed_count', label: 'Removed' },
  { key: 'moved_count', label: 'Moved' },
  { key: 'quarantined_count', label: 'Quarantined' },
  { key: 'skipped_count', label: 'Skipped' },
  { key: 'failed_count', label: 'Failed' },
  { key: 'unresolved_count', label: 'Unresolved' },
]

function findingText(finding: Record<string, unknown>, key: string): string | null {
  const value = finding[key]
  return typeof value === 'string' && value.length > 0 ? value : null
}

function findingPath(finding: Record<string, unknown>): string {
  return findingText(finding, 'path') ?? findingText(finding, 'file_path') ?? 'Workspace record'
}

function renderOutcome(outcome: RepairOutcome, index: number) {
  return (
    <li key={`${outcome.file_path}-${outcome.code}-${index}`} className="grid gap-1 border-l-2 border-error pl-static-xs text-xs">
      <span className="break-all font-mono text-primary">{outcome.file_path}</span>
      <span className="font-semibold text-error">{outcome.code}</span>
      {outcome.detail ? <span>{outcome.detail}</span> : null}
    </li>
  )
}

export default function RepairReceipt({ receipt, onDismiss }: RepairReceiptProps) {
  const failedOutcomes = receipt.outcomes.filter((outcome) => outcome.action === 'failed' || outcome.action === 'unresolved')
  const completed = new Date(receipt.completed_at)
  const completedLabel = Number.isNaN(completed.getTime()) ? receipt.completed_at : completed.toLocaleString()

  const content = (
    <section
      data-testid="repair-receipt"
      role="status"
      aria-live="polite"
      className="fixed right-static-md top-[4.5rem] z-[950] grid max-h-[calc(100dvh-6rem)] w-[min(calc(100vw-2rem),30rem)] gap-static-sm overflow-y-auto rounded-lg border border-contrast-medium bg-surface p-static-md text-primary shadow-xl max-sm:left-static-md max-sm:right-static-md max-sm:w-auto"
      data-pds-exception="overlay-surface"
    >
      <header className="flex items-start justify-between gap-static-sm border-b border-contrast-low pb-static-sm">
        <div className="grid gap-1">
          <span className="text-sm font-semibold">Task repair completed</span>
          <time className="text-xs text-[var(--p-color-contrast-medium)]" dateTime={receipt.completed_at}>
            {completedLabel}
          </time>
        </div>
        <PButton compact variant="secondary" onClick={onDismiss}>Dismiss</PButton>
      </header>

      <dl className="m-0 grid grid-cols-3 gap-x-static-md gap-y-static-sm max-sm:grid-cols-2">
        {COUNTS.map(({ key, label }) => (
          <div key={key} className="grid gap-1">
            <dt className="text-xs text-[var(--p-color-contrast-medium)]">{label}</dt>
            <dd className="m-0 text-base font-semibold" data-testid={`repair-count-${key}`}>{String(receipt[key])}</dd>
          </div>
        ))}
      </dl>

      {failedOutcomes.length > 0 || receipt.unresolved_findings.length > 0 ? (
        <div className="grid gap-static-sm border-t border-contrast-low pt-static-sm">
          {failedOutcomes.length > 0 ? (
            <section className="grid gap-static-xs" data-testid="repair-failed-details">
              <span className="text-sm font-semibold">Failed items</span>
              <ul className="m-0 grid list-none gap-static-xs p-0">{failedOutcomes.map(renderOutcome)}</ul>
            </section>
          ) : null}
          {receipt.unresolved_findings.length > 0 ? (
            <section className="grid gap-static-xs" data-testid="repair-unresolved-details">
              <span className="text-sm font-semibold">Unresolved findings</span>
              <ul className="m-0 grid list-none gap-static-xs p-0">
                {receipt.unresolved_findings.map((finding, index) => (
                  <li key={`${findingPath(finding)}-${findingText(finding, 'code') ?? index}`} className="grid gap-1 border-l-2 border-error pl-static-xs text-xs">
                    <span className="break-all font-mono text-primary">{findingPath(finding)}</span>
                    <span className="font-semibold text-error">{findingText(finding, 'code') ?? 'UNRESOLVED'}</span>
                    {findingText(finding, 'detail') ? <span>{findingText(finding, 'detail')}</span> : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}
    </section>
  )

  return typeof document !== 'undefined' && document.body
    ? createPortal(content, document.body)
    : content
}
