import { PTag } from '@porsche-design-system/components-react'
import { Link } from 'react-router'
import type {
  ChangeGroupView,
  WorkItemCardView,
  WorkItemChangeLifecycle,
  WorkItemNextActor,
  WorkItemStage,
} from '../api/workItems'
import { workItemIdentity, type WorkItemIdentity } from '../hooks/useWorkItems'

interface WorkPortfolioTableProps {
  groups: ChangeGroupView[]
  selected: WorkItemIdentity | null
  onSelect: (identity: WorkItemIdentity, trigger: HTMLAnchorElement) => void
}

type GroupTableProps = Pick<WorkPortfolioTableProps, 'selected' | 'onSelect'> & { group: ChangeGroupView }

const NEXT_ACTOR_LABELS: Record<WorkItemNextActor, string> = {
  you: 'You',
  agent: 'Agent',
  'agent-or-you': 'Agent or you',
  dependency: 'Dependency',
  repair: 'Repair workflow',
  none: 'No action',
}

const STAGE_LABELS: Record<WorkItemStage, string> = {
  design: 'Design',
  planning: 'Planning',
  implementation: 'Implementation',
  assembly: 'Assembly',
  completed: 'Complete',
}

const LIFECYCLE_LABELS: Record<WorkItemChangeLifecycle, string> = {
  'in-delivery': 'In delivery',
  integration: 'Integration',
}

function workItemPath(item: WorkItemCardView): string {
  return `/delivery/${encodeURIComponent(item.change_id)}/${encodeURIComponent(item.item_key)}`
}

function NextStep({ item }: { item: WorkItemCardView }) {
  const urgent = item.next_actor === 'you' || item.next_actor === 'repair'
  return (
    <span className={urgent ? 'font-semibold text-error' : 'font-medium text-primary'}>
      {NEXT_ACTOR_LABELS[item.next_actor]}
      <span className="mt-0.5 block text-xs font-normal text-contrast-medium">{item.next_step}</span>
    </span>
  )
}

function ItemLink({
  item,
  selected,
  onSelect,
}: {
  item: WorkItemCardView
  selected: boolean
  onSelect: WorkPortfolioTableProps['onSelect']
}) {
  const identity = { changeId: item.change_id, itemKey: item.item_key }
  return (
    <Link
      to={workItemPath(item)}
      data-work-item-primary-trigger
      data-work-item-identity={`${item.change_id}:${item.item_key}`}
      className="block min-w-0 py-1 font-semibold text-primary underline-offset-4 after:absolute after:inset-0 after:content-[''] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      aria-current={selected ? 'location' : undefined}
      onClick={(event) => onSelect(identity, event.currentTarget)}
    >
      <span className="block overflow-hidden [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2]">{item.title}</span>
      <span className="block text-xs font-normal text-contrast-medium">Outcome {item.work_item_id}</span>
    </Link>
  )
}

function reviewLabel(item: WorkItemCardView): string {
  if (item.action.kind === 'answer-request') return 'Review request'
  if (item.action.kind === 'clear-block') return 'Review block'
  if (item.action.kind === 'recover-claim') return 'Review recovery'
  if (item.action.kind === 'run-repair-command') return 'Review repair'
  return 'Review Integration'
}

function ActionLink({ item, onSelect }: { item: WorkItemCardView; onSelect: WorkPortfolioTableProps['onSelect'] }) {
  if (item.action.kind === 'none' || !item.action.label) return <span className="text-contrast-medium">—</span>
  const identity = { changeId: item.change_id, itemKey: item.item_key }
  return (
    <Link
      to={workItemPath(item)}
      className="relative z-[1] inline-flex min-h-8 items-center font-semibold text-primary underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      onClick={(event) => onSelect(identity, event.currentTarget)}
    >
      {reviewLabel(item)}
    </Link>
  )
}

function ChangeHeader({ group }: { group: ChangeGroupView }) {
  const showId = group.title.toLocaleLowerCase() !== group.change_id.toLocaleLowerCase()
  return (
    <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-static-lg gap-y-static-xs">
      <div className="min-w-0">
        <h3 className="truncate text-sm font-semibold">{group.title}</h3>
        {showId ? <p className="truncate text-xs text-contrast-medium">{group.change_id}</p> : null}
      </div>
      <div className="flex shrink-0 items-center gap-static-sm text-xs text-contrast-medium">
        <PTag compact>{LIFECYCLE_LABELS[group.lifecycle]}</PTag>
        <span>{group.outcome_completed} of {group.outcome_total} Outcomes complete</span>
      </div>
    </div>
  )
}

function DesktopTable({ group, selected, onSelect }: GroupTableProps) {
  const outcomes = group.items.filter((item) => item.scope === 'outcome')
  return (
    <div className="hidden overflow-x-auto md:block" data-testid="work-table-scroll">
      <table className="w-full min-w-[48rem] table-fixed border-collapse text-left text-sm">
        <caption className="sr-only">Current Outcomes for {group.title}</caption>
        <colgroup>
          <col className="w-[22%]" />
          <col className="w-[34%]" />
          <col className="w-[14%]" />
          <col className="w-[20%]" />
          <col className="w-[10%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-contrast-low text-2xs font-semibold uppercase text-contrast-high">
            <th className="px-static-sm py-static-xs" scope="col">Next</th>
            <th className="px-static-sm py-static-xs" scope="col">Outcome</th>
            <th className="px-static-sm py-static-xs" scope="col">Stage</th>
            <th className="px-static-sm py-static-xs" scope="col">Progress</th>
            <th className="px-static-sm py-static-xs" scope="col">Review</th>
          </tr>
        </thead>
        <tbody>
          {outcomes.map((item) => {
            const isSelected = selected?.changeId === item.change_id && selected.itemKey === item.item_key
            return (
              <tr
                key={workItemIdentity(item)}
                className={['relative border-b border-contrast-low align-top', isSelected ? 'bg-frosted-soft' : 'hover:bg-surface'].join(' ')}
                data-work-item={workItemIdentity(item)}
              >
                <td className="px-static-sm py-static-sm"><NextStep item={item} /></td>
                <td className="px-static-sm py-static-xs"><ItemLink item={item} selected={isSelected} onSelect={onSelect} /></td>
                <td className="px-static-sm py-static-sm font-medium">{item.stage ? STAGE_LABELS[item.stage] : '—'}</td>
                <td className="px-static-sm py-static-sm text-contrast-medium">{item.progress.label}</td>
                <td className="px-static-sm py-static-xs"><ActionLink item={item} onSelect={onSelect} /></td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function CompactRows({ group, selected, onSelect }: GroupTableProps) {
  const outcomes = group.items.filter((item) => item.scope === 'outcome')
  return (
    <div className="md:hidden">
      {outcomes.map((item) => {
        const isSelected = selected?.changeId === item.change_id && selected.itemKey === item.item_key
        return (
          <article
            key={workItemIdentity(item)}
            className={['relative grid gap-static-sm border-b border-contrast-low py-static-md', isSelected ? 'bg-frosted-soft px-static-xs' : ''].join(' ')}
            data-work-item={workItemIdentity(item)}
            aria-label={`${item.title} work item`}
          >
            <div className="grid grid-cols-[minmax(7rem,0.8fr)_minmax(0,1.5fr)_auto] items-start gap-static-sm">
              <div className="grid gap-1"><span className="text-2xs font-semibold uppercase text-contrast-medium">Next</span><NextStep item={item} /></div>
              <div className="grid min-w-0 gap-1"><span className="text-2xs font-semibold uppercase text-contrast-medium">Outcome</span><ItemLink item={item} selected={isSelected} onSelect={onSelect} /></div>
              <div className="grid gap-1"><span className="text-2xs font-semibold uppercase text-contrast-medium">Stage</span><span className="text-xs font-medium">{item.stage ? STAGE_LABELS[item.stage] : '—'}</span></div>
            </div>
            <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-static-sm text-xs text-contrast-medium">
              <div className="grid gap-1"><span className="text-2xs font-semibold uppercase">Progress</span><span>{item.progress.label}</span></div>
              <div className="grid gap-1"><span className="text-2xs font-semibold uppercase">Review</span><ActionLink item={item} onSelect={onSelect} /></div>
            </div>
          </article>
        )
      })}
    </div>
  )
}

function IntegrationGate({ group, selected, onSelect }: GroupTableProps) {
  const item = group.items.find((candidate) => candidate.scope === 'change-integration')
  if (!item) return null
  const isSelected = selected?.changeId === item.change_id && selected.itemKey === item.item_key
  return (
    <section
      className={['relative grid gap-static-sm border-b border-contrast-low bg-surface px-static-sm py-static-md md:grid-cols-[minmax(12rem,1.25fr)_minmax(12rem,1fr)_minmax(12rem,1fr)_auto] md:items-center', isSelected ? 'bg-frosted-soft' : ''].join(' ')}
      aria-label={`Change Integration for ${group.title}`}
      data-work-item={workItemIdentity(item)}
    >
      <div className="min-w-0">
        <span className="text-2xs font-semibold uppercase text-contrast-medium">Change-level step</span>
        <Link
          to={workItemPath(item)}
          data-work-item-primary-trigger
          data-work-item-identity={`${item.change_id}:${item.item_key}`}
          className="block font-semibold text-primary underline-offset-4 after:absolute after:inset-0 after:content-[''] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          aria-current={isSelected ? 'location' : undefined}
          onClick={(event) => onSelect({ changeId: item.change_id, itemKey: item.item_key }, event.currentTarget)}
        >
          Integration
        </Link>
        <span className="text-xs text-contrast-medium">Publishes the reviewed Change</span>
      </div>
      <div><span className="block text-2xs font-semibold uppercase text-contrast-medium">Next</span><NextStep item={item} /></div>
      <div><span className="block text-2xs font-semibold uppercase text-contrast-medium">Status</span><span className="text-sm text-contrast-medium">{item.progress.label}</span></div>
      <div className="relative z-[1]"><span className="block text-2xs font-semibold uppercase text-contrast-medium">Review</span><ActionLink item={item} onSelect={onSelect} /></div>
    </section>
  )
}

export default function WorkPortfolioTable({ groups, selected, onSelect }: WorkPortfolioTableProps) {
  if (groups.length === 0) return <p className="py-static-lg text-sm text-contrast-medium">No current Delivery work.</p>
  return (
    <section aria-labelledby="work-board-heading" data-testid="work-portfolio-table" className="grid gap-static-xl">
      {groups.map((group) => (
        <section key={group.change_id} className="min-w-0" aria-labelledby={`change-${group.change_id}`}>
          <div id={`change-${group.change_id}`} className="border-b border-contrast-medium pb-static-sm">
            <ChangeHeader group={group} />
          </div>
          <DesktopTable group={group} selected={selected} onSelect={onSelect} />
          <CompactRows group={group} selected={selected} onSelect={onSelect} />
          <IntegrationGate group={group} selected={selected} onSelect={onSelect} />
        </section>
      ))}
    </section>
  )
}
