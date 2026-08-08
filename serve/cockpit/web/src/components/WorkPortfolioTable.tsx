import { PTag } from '@porsche-design-system/components-react'
import { Link } from 'react-router'
import type {
  ChangeGroupView,
  WorkItemActivity,
  WorkItemCardView,
  WorkItemChangeLifecycle,
  WorkItemNeed,
  WorkItemStage,
} from '../api/workItems'
import { workItemIdentity, type WorkItemIdentity } from '../hooks/useWorkItems'

interface WorkPortfolioTableProps {
  groups: ChangeGroupView[]
  selected: WorkItemIdentity | null
  onSelect: (identity: WorkItemIdentity, trigger: HTMLAnchorElement) => void
}

type GroupTableProps = Pick<WorkPortfolioTableProps, 'selected' | 'onSelect'> & { group: ChangeGroupView }

const NEED_LABELS: Record<WorkItemNeed, string> = {
  you: 'You',
  dependency: 'Dependency',
  repair: 'Repair',
  none: 'Nobody',
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

function activityLabel(activity: WorkItemActivity): string {
  if (activity.state === 'working' && activity.worker_role) return `${activity.worker_role} working`
  if (activity.state === 'repairing') return 'Repairing'
  if (activity.state === 'ready') return 'Ready'
  return 'Idle'
}

function Need({ item }: { item: WorkItemCardView }) {
  const urgent = item.needs === 'you' || item.needs === 'repair'
  return (
    <span className={urgent ? 'font-semibold text-error' : 'font-medium text-primary'}>
      {NEED_LABELS[item.needs]}
      {item.needs_headline ? <span className="mt-0.5 block text-xs font-normal text-contrast-medium">{item.needs_headline}</span> : null}
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
      className="block min-w-0 py-1 font-semibold text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      aria-current={selected ? 'location' : undefined}
      onClick={(event) => onSelect(identity, event.currentTarget)}
    >
      <span className="block truncate">{item.title}</span>
      <span className="block text-xs font-normal text-contrast-medium">{item.scope === 'outcome' ? item.work_item_id : 'Change Integration'}</span>
    </Link>
  )
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
      {item.action.label}
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
  return (
    <div className="hidden overflow-x-auto md:block" data-testid="work-table-scroll">
      <table className="w-full min-w-[48rem] table-fixed border-collapse text-left text-sm">
        <caption className="sr-only">Current Work Items for {group.title}</caption>
        <colgroup>
          <col className="w-[13%]" />
          <col className="w-[24%]" />
          <col className="w-[13%]" />
          <col className="w-[21%]" />
          <col className="w-[15%]" />
          <col className="w-[14%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-contrast-low text-2xs font-semibold uppercase text-contrast-high">
            <th className="px-static-sm py-static-xs" scope="col">Needs</th>
            <th className="px-static-sm py-static-xs" scope="col">Work item</th>
            <th className="px-static-sm py-static-xs" scope="col">Stage</th>
            <th className="px-static-sm py-static-xs" scope="col">Progress</th>
            <th className="px-static-sm py-static-xs" scope="col">Activity</th>
            <th className="px-static-sm py-static-xs" scope="col">Action</th>
          </tr>
        </thead>
        <tbody>
          {group.items.map((item) => {
            const isSelected = selected?.changeId === item.change_id && selected.itemKey === item.item_key
            return (
              <tr
                key={workItemIdentity(item)}
                className={['border-b border-contrast-low align-top', isSelected ? 'bg-frosted-soft' : 'hover:bg-surface'].join(' ')}
                data-work-item={workItemIdentity(item)}
              >
                <td className="px-static-sm py-static-sm"><Need item={item} /></td>
                <td className="px-static-sm py-static-xs"><ItemLink item={item} selected={isSelected} onSelect={onSelect} /></td>
                <td className="px-static-sm py-static-sm font-medium">{STAGE_LABELS[item.stage]}</td>
                <td className="px-static-sm py-static-sm text-contrast-medium">{item.progress.label}</td>
                <td className="px-static-sm py-static-sm text-contrast-medium">{activityLabel(item.activity)}</td>
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
  return (
    <div className="md:hidden">
      {group.items.map((item) => {
        const isSelected = selected?.changeId === item.change_id && selected.itemKey === item.item_key
        return (
          <article
            key={workItemIdentity(item)}
            className={['grid gap-static-sm border-b border-contrast-low py-static-md', isSelected ? 'bg-frosted-soft px-static-xs' : ''].join(' ')}
            data-work-item={workItemIdentity(item)}
          >
            <div className="grid grid-cols-[minmax(6rem,0.7fr)_minmax(0,1.5fr)_auto] items-start gap-static-sm">
              <Need item={item} />
              <ItemLink item={item} selected={isSelected} onSelect={onSelect} />
              <span className="text-xs font-medium">{STAGE_LABELS[item.stage]}</span>
            </div>
            <div className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-static-sm text-xs text-contrast-medium">
              <span>{item.progress.label}</span>
              <span>{activityLabel(item.activity)}</span>
              <ActionLink item={item} onSelect={onSelect} />
            </div>
          </article>
        )
      })}
    </div>
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
        </section>
      ))}
    </section>
  )
}
