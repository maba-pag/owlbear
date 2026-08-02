import type { WorkItemProjection, WorkItemStage } from '../api/workItems'
import { workItemIdentity, type WorkItemIdentity } from '../hooks/useWorkItems'

interface WorkPortfolioBoardProps {
  items: WorkItemProjection[]
  selected: WorkItemIdentity | null
  onSelect: (identity: WorkItemIdentity) => void
}

const GROUPS: Array<{ stage: WorkItemStage; label: string; optional?: boolean }> = [
  { stage: 'design', label: 'Design' },
  { stage: 'planning', label: 'Planning' },
  { stage: 'implementation', label: 'Implementation' },
  { stage: 'assembly', label: 'Assembly', optional: true },
  { stage: 'completed', label: 'Completed', optional: true },
]

function WorkItemCard({
  item,
  selected,
  onSelect,
}: {
  item: WorkItemProjection
  selected: boolean
  onSelect: () => void
}) {
  return (
    <article
      className={[
        'flex min-h-56 min-w-0 flex-col border-l-4 bg-surface p-static-md',
        selected ? 'border-primary' : 'border-contrast-low',
      ].join(' ')}
      data-work-item={workItemIdentity(item)}
    >
      <div className="flex min-w-0 items-start justify-between gap-static-sm">
        <div className="min-w-0">
          <span className="block truncate text-xs font-semibold text-contrast-medium">{item.change_id}</span>
          <h3 className="mt-1 line-clamp-2 font-semibold">{item.title}</h3>
        </div>
        <span className="border border-contrast-low px-static-xs py-1 text-xs">{item.scope}</span>
      </div>
      <p className="mt-static-xs line-clamp-3 text-sm leading-relaxed text-contrast-medium">{item.promise}</p>
      <dl className="mt-static-sm grid gap-1 text-xs">
        <div className="flex justify-between gap-static-sm">
          <dt>Attention</dt>
          <dd className="font-semibold">{item.attention}</dd>
        </div>
        <div className="flex justify-between gap-static-sm">
          <dt>Progress</dt>
          <dd>{item.reviewed_task_count} / {item.task_count}</dd>
        </div>
      </dl>
      <p className="mt-static-sm line-clamp-2 text-xs text-contrast-medium">{item.next_action}</p>
      <div className="mt-auto pt-static-md">
        <button
          type="button"
          className="min-h-10 border border-primary px-static-sm py-static-xs text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          aria-pressed={selected}
          onClick={onSelect}
        >
          {selected ? 'Selected' : 'Inspect'}
        </button>
      </div>
    </article>
  )
}

export default function WorkPortfolioBoard({ items, selected, onSelect }: WorkPortfolioBoardProps) {
  const visibleGroups = GROUPS.filter(
    (group) => !group.optional || items.some((item) => item.stage === group.stage),
  )

  return (
    <section aria-labelledby="work-board-heading" data-testid="work-portfolio-board">
      <h2 id="work-board-heading" className="sr-only">Work stages</h2>
      <div className="grid min-w-0 gap-static-md lg:grid-cols-4">
        {visibleGroups.map((group) => {
          const grouped = items.filter((item) => item.stage === group.stage)
          return (
            <section key={group.stage} aria-labelledby={`work-stage-${group.stage}`} className="min-w-0">
              <div className="mb-static-sm flex items-center justify-between border-b border-contrast-low pb-static-xs">
                <h3 id={`work-stage-${group.stage}`} className="font-semibold">{group.label}</h3>
                <span className="text-xs text-contrast-medium">{grouped.length}</span>
              </div>
              <div className="grid gap-static-sm sm:grid-cols-2 lg:grid-cols-1">
                {grouped.map((item) => {
                  const isSelected = selected?.changeId === item.change_id && selected.workItemId === item.work_item_id
                  return (
                    <WorkItemCard
                      key={workItemIdentity(item)}
                      item={item}
                      selected={isSelected}
                      onSelect={() => onSelect({ changeId: item.change_id, workItemId: item.work_item_id })}
                    />
                  )
                })}
                {grouped.length === 0 ? (
                  <p className="py-static-sm text-sm text-contrast-medium">No work in {group.label.toLowerCase()}.</p>
                ) : null}
              </div>
            </section>
          )
        })}
      </div>
    </section>
  )
}
