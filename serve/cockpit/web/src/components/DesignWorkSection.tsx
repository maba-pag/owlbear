import { Link } from 'react-router'
import { designCommand, designWorkTitle } from './designWorkPresentation'

interface DesignWorkSectionProps {
  changeIds: string[]
  selectedChangeId: string | null
  onSelect: (identity: { changeId: string; itemKey: string }, trigger: HTMLAnchorElement) => void
}

export default function DesignWorkSection({ changeIds, selectedChangeId, onSelect }: DesignWorkSectionProps) {
  if (changeIds.length === 0) return null
  return (
    <section className="mt-static-sm min-w-0" aria-labelledby="design-work-heading" data-testid="design-work-section">
      <h2 id="design-work-heading" className="mb-static-xs border-b border-contrast-low px-static-sm pb-static-xs text-md font-semibold text-primary">Design work</h2>
      <div className="hidden grid-cols-[minmax(0,40fr)_minmax(0,25fr)_minmax(0,35fr)] text-2xs font-semibold uppercase text-contrast-medium lg:grid" aria-hidden="true">
        <span className="px-static-sm py-static-xs">Work</span>
        <span className="px-static-sm py-static-xs">Progress</span>
        <span className="px-static-sm py-static-xs">Status</span>
      </div>
      <div className="grid gap-1">
        {changeIds.map((changeId) => {
          const selected = selectedChangeId === changeId
          return (
            <article
              key={changeId}
              className={[
                'relative grid min-w-0 gap-static-sm rounded-lg border border-l-4 border-contrast-low px-static-sm py-static-sm text-sm lg:grid-cols-[minmax(0,40fr)_minmax(0,25fr)_minmax(0,35fr)] lg:gap-0',
                selected ? 'bg-frosted-soft' : 'bg-surface hover:bg-frosted-soft',
              ].join(' ')}
              data-design-work={changeId}
            >
              <div className="min-w-0 lg:pr-static-sm">
                <Link
                  to={`/delivery/${encodeURIComponent(changeId)}/design`}
                  data-work-item-primary-trigger
                  data-work-item-identity={`${changeId}:design`}
                  className="block font-semibold text-primary underline-offset-4 after:absolute after:inset-0 after:content-[''] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
                  aria-current={selected ? 'location' : undefined}
                  onClick={(event) => onSelect({ changeId, itemKey: 'design' }, event.currentTarget)}
                >
                  {designWorkTitle(changeId)}
                </Link>
                <code className="text-xs text-contrast-medium">{changeId}</code>
              </div>
              <div className="lg:px-static-sm">
                <span className="mb-1 block text-2xs font-semibold uppercase text-contrast-medium lg:hidden">Progress</span>
                <strong className="font-medium text-primary">Design</strong>
                <span className="block text-xs text-contrast-medium">Not admitted to Delivery</span>
              </div>
              <div className="lg:pl-static-sm">
                <span className="mb-1 block text-2xs font-semibold uppercase text-contrast-medium lg:hidden">Status</span>
                <span className="block font-medium text-primary">Continue Design</span>
                <code className="mt-1 inline-block rounded-sm border border-contrast-low bg-canvas px-1.5 py-0.5 text-xs text-contrast-medium">{designCommand(changeId)}</code>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
