import type { WorkItemProjection, WorkItemStage } from '../api/workItems'
import { ATTENTION_LABELS } from '../attentionVocabulary'
import { workItemIdentity, type WorkItemIdentity } from '../hooks/useWorkItems'

interface WorkPortfolioBoardProps {
  items: WorkItemProjection[]
  selected: WorkItemIdentity | null
  onSelect: (identity: WorkItemIdentity) => void
}

/** `emptyLabel` defines what the stage holds, matching the projector's stage rules. */
const GROUPS: Array<{ stage: WorkItemStage; label: string; emptyLabel: string }> = [
  { stage: 'design', label: 'Design', emptyLabel: 'Work waiting on a design decision from you.' },
  { stage: 'planning', label: 'Planning', emptyLabel: 'Accepted design without a published task plan.' },
  { stage: 'implementation', label: 'Implementation', emptyLabel: 'Planned tasks under build and review.' },
  { stage: 'assembly', label: 'Assembly', emptyLabel: 'Reviewed tasks awaiting a composed result.' },
  { stage: 'completed', label: 'Done', emptyLabel: 'Fully reviewed work, ready for Integration.' },
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
      <div className="min-w-0">
        <span className="block truncate text-xs text-contrast-medium">{item.change_id}</span>
        <h3 className="mt-1 line-clamp-2 font-medium">{item.title}</h3>
      </div>
      {item.next_action !== 'Inspect progress' ? (
        <p className={[
          'mt-static-sm line-clamp-2 text-sm leading-snug',
          item.attention === 'user' ? 'font-semibold' : 'font-normal',
        ].join(' ')}>{item.next_action}</p>
      ) : null}
      <p className="mt-static-xs line-clamp-2 text-xs leading-relaxed text-contrast-medium">{item.promise}</p>
      <div className="mt-auto grid gap-1 pt-static-md text-xs">
        <span className={item.attention === 'user' ? 'font-medium text-error' : 'font-medium text-primary'}>{ATTENTION_LABELS[item.attention]}</span>
        <div className="flex items-end justify-between gap-static-sm">
          <span className="whitespace-nowrap text-contrast-medium">
            {item.task_count === 0 ? 'No tasks yet' : `${item.reviewed_task_count}/${item.task_count} reviewed`}
          </span>
          <button
            type="button"
            className="shrink-0 text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            aria-pressed={selected}
            aria-controls="work-item-flyout"
            onClick={onSelect}
          >
            View details
          </button>
        </div>
      </div>
    </article>
  )
}

export default function WorkPortfolioBoard({ items, selected, onSelect }: WorkPortfolioBoardProps) {
  return (
    <section aria-labelledby="work-board-heading" data-testid="work-portfolio-board">
      <div className="grid min-w-0 gap-x-static-md gap-y-static-md md:grid-cols-5 lg:gap-x-static-lg">
        {GROUPS.map((group) => {
          const grouped = items.filter((item) => item.stage === group.stage)
          return (
            <section key={group.stage} aria-labelledby={`work-stage-${group.stage}`} className="min-w-0">
              {/* Scrolls with its column: a pinned label would slice the content passing beneath it.
                  No rule here — the view-header rule above already separates the board. */}
              <div data-stage-heading={group.stage} className="mb-static-sm flex items-baseline gap-static-xs pb-static-xs">
                <h3 id={`work-stage-${group.stage}`} className="min-w-0 truncate text-2xs font-semibold uppercase tracking-[0.08em] text-contrast-high">{group.label}</h3>
                <span className="inline-flex min-w-5 shrink-0 justify-center bg-surface px-1 text-2xs font-semibold text-contrast-high">
                  {grouped.length}
                  <span className="sr-only"> work items</span>
                </span>
              </div>
              <div className="grid gap-static-sm sm:grid-cols-2 md:grid-cols-1">
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
                  <p data-stage-empty={group.stage} className="py-static-sm text-sm text-contrast-medium">{group.emptyLabel}</p>
                ) : null}
              </div>
            </section>
          )
        })}
      </div>
    </section>
  )
}
