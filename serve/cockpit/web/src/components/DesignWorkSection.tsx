import { Link } from 'react-router'
import type { PortfolioChangeLifecycleStatus } from '../api/workItems'
import CopyCommand from './CopyCommand'
import { StatusChip, WorkRow } from './DeliveryPrimitives'
import { designCommand, designWorkTitle } from './designWorkPresentation'

interface DesignWorkSectionProps {
  statuses: PortfolioChangeLifecycleStatus[]
  selectedChangeId: string | null
  onSelect: (identity: { changeId: string; itemKey: string }, trigger: HTMLElement) => void
}

export default function DesignWorkSection({ statuses, selectedChangeId, onSelect }: DesignWorkSectionProps) {
  const designStatuses = statuses.filter((status) => status.admission === 'unadmitted' && status.stage === 'design')
  if (designStatuses.length === 0) return null
  return (
    <section className="min-w-0" aria-labelledby="design-work-heading" data-testid="design-work-section">
      <h2 id="design-work-heading" className="mb-static-sm border-b border-contrast-lower px-static-sm pb-static-xs text-md font-semibold text-primary">Design work</h2>
      <div className="grid gap-static-sm">
        {designStatuses.map((status) => {
          const changeId = status.change_id
          const selected = selectedChangeId === changeId
          return (
            <WorkRow key={changeId} selected={selected} dataWorkItem={changeId} className="px-static-sm py-static-sm text-sm" ariaLabel={`${designWorkTitle(changeId)} Design work`}>
              <dl className="grid gap-static-sm md:grid-cols-[minmax(0,60fr)_minmax(0,40fr)] md:gap-0">
                <div className="min-w-0 md:pr-static-sm">
                  <dt className="sr-only">Work</dt>
                  <dd>
                    <Link
                      to={`/delivery/${encodeURIComponent(changeId)}/design`}
                      data-work-item-primary-trigger
                      data-work-item-identity={`${changeId}:design`}
                      className="block font-semibold text-primary after:absolute after:inset-0 after:content-[''] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
                      aria-current={selected ? 'location' : undefined}
                      onClick={(event) => onSelect({ changeId, itemKey: 'design' }, event.currentTarget)}
                    >
                      {designWorkTitle(changeId)}
                    </Link>
                    <code className="text-xs text-contrast-medium">{changeId}</code>
                  </dd>
                </div>
                <div className="md:pl-static-sm">
                  <dt className="sr-only">State</dt>
                  <dd>
                    <strong className="block font-medium text-primary">Design</strong>
                    <span className="block text-xs text-contrast-medium">Not admitted to Delivery</span>
                    <StatusChip label="Needs design" tone="ready" />
                    <CopyCommand command={designCommand(changeId)} className="mt-1" />
                  </dd>
                </div>
              </dl>
            </WorkRow>
          )
        })}
      </div>
    </section>
  )
}
