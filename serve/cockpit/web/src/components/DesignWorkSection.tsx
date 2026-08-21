import { Link } from 'react-router'
import type { PortfolioChangeLifecycleStatus } from '../api/workItems'
import CopyCommand from './CopyCommand'
import { designCommand, designWorkTitle } from './designWorkPresentation'
import { workItemStatusClassName } from './workItemPresentation'

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
      <div className="mb-static-sm hidden grid-cols-[minmax(0,44fr)_minmax(0,24fr)_minmax(0,32fr)] text-2xs font-semibold uppercase text-contrast-high md:grid" aria-hidden="true">
        <span className="px-static-sm py-static-xs">Work</span>
        <span className="px-static-sm py-static-xs">Progress</span>
        <span className="px-static-sm py-static-xs">Status</span>
      </div>
      <div className="grid gap-static-sm">
        {designStatuses.map((status) => {
          const changeId = status.change_id
          const selected = selectedChangeId === changeId
          return (
            <article
              key={changeId}
              className={[
                'relative min-w-0 rounded-lg border border-l-4 border-contrast-lower px-static-sm py-static-sm text-sm',
                selected ? 'bg-canvas' : 'bg-frosted-soft hover:bg-canvas',
              ].join(' ')}
              data-design-work={changeId}
            >
              <dl className="grid gap-static-sm md:grid-cols-[minmax(0,44fr)_minmax(0,24fr)_minmax(0,32fr)] md:gap-0">
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
                <div className="md:px-static-sm">
                  <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-high md:sr-only">Progress</dt>
                  <dd>
                    <strong className="font-medium text-primary">Design</strong>
                    <span className="block text-xs text-contrast-medium">Not admitted to Delivery</span>
                  </dd>
                </div>
                <div className="md:pl-static-sm">
                  <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-high md:sr-only">Status</dt>
                  <dd>
                    <span className={`inline-flex items-center rounded-sm border px-static-xs py-1 text-xs font-semibold leading-none ${workItemStatusClassName('ready')}`} data-status-tone="ready">Needs design</span>
                    <CopyCommand command={designCommand(changeId)} className="mt-1" />
                  </dd>
                </div>
              </dl>
            </article>
          )
        })}
      </div>
    </section>
  )
}
