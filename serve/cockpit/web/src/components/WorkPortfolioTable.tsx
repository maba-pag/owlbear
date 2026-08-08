import { Link } from 'react-router'
import type {
  ChangeGroupView,
  DeliveryWorkerRole,
  WorkItemCardView,
  WorkItemStage,
} from '../api/workItems'
import { workItemIdentity, type WorkItemIdentity } from '../hooks/useWorkItems'

interface WorkPortfolioTableProps {
  groups: ChangeGroupView[]
  selected: WorkItemIdentity | null
  emptyMessage?: string
  onSelect: (identity: WorkItemIdentity, trigger: HTMLAnchorElement) => void
}

type GroupTableProps = Pick<WorkPortfolioTableProps, 'selected' | 'onSelect'> & { group: ChangeGroupView }

const STAGE_LABELS: Record<WorkItemStage, string> = {
  design: 'Design',
  planning: 'Planning',
  implementation: 'Implementation',
  assembly: 'Assembly',
  completed: 'Complete',
}

const WORKER_LABELS: Record<DeliveryWorkerRole, string> = {
  planner: 'Planner',
  builder: 'Builder',
  'assembly-reviewer': 'Assembly reviewer',
  'integration-repairer': 'Integration repairer',
}

function workItemPath(item: WorkItemCardView): string {
  return `/delivery/${encodeURIComponent(item.change_id)}/${encodeURIComponent(item.item_key)}`
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
    </Link>
  )
}

function ActionLink({ item, onSelect }: { item: WorkItemCardView; onSelect: WorkPortfolioTableProps['onSelect'] }) {
  if (item.action.kind === 'none' || !item.action.label) return null
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

function PipelineState({ item }: { item: WorkItemCardView }) {
  if (item.stage === null) return <strong className="block font-medium text-primary">{item.progress.label}</strong>
  const stage = STAGE_LABELS[item.stage]
  const showProgress = item.stage !== 'completed'
  return (
    <span>
      <strong className="block font-medium text-primary">{stage}</strong>
      {showProgress ? <span className="mt-0.5 block text-xs text-contrast-medium">{item.progress.label}</span> : null}
    </span>
  )
}

function CurrentState({ item, onSelect }: { item: WorkItemCardView; onSelect: WorkPortfolioTableProps['onSelect'] }) {
  let state = item.next_step
  if (item.needs === 'you') state = item.needs_headline ?? 'Needs your intervention'
  else if (item.needs === 'dependency') state = item.needs_headline ?? 'Waiting on a dependency'
  else if (item.needs === 'repair') state = 'Waiting for an Integration repair'
  else if (item.activity.state === 'working' || item.activity.state === 'repairing') {
    state = `${item.activity.worker_role ? WORKER_LABELS[item.activity.worker_role] : 'Agent'} working`
  } else if (item.activity.state === 'ready') {
    state = item.next_actor === 'agent-or-you' ? 'Ready for Orchestration or your action' : 'Waiting for Orchestration'
  }
  else if (item.stage === 'completed') state = 'Done'
  const urgent = item.needs === 'you'
  return (
    <span>
      <span className={urgent ? 'block font-semibold text-error' : 'block font-medium text-primary'}>{state}</span>
      {item.activity.task_id ? <span className="mt-0.5 block text-xs text-contrast-medium">Task {item.activity.task_id}</span> : null}
      {item.action.kind !== 'none' ? <span className="mt-static-xs block"><ActionLink item={item} onSelect={onSelect} /></span> : null}
    </span>
  )
}

function DesktopTable({ group, selected, onSelect }: GroupTableProps) {
  const outcomes = group.items.filter((item) => item.scope === 'outcome')
  return (
    <div className="hidden overflow-x-auto lg:block" data-testid="work-table-scroll">
      <table className="w-full min-w-[48rem] table-fixed border-separate border-spacing-y-1 text-left text-sm">
        <caption className="sr-only">Current Outcomes for {group.title}</caption>
        <colgroup>
          <col className="w-[40%]" />
          <col className="w-[25%]" />
          <col className="w-[35%]" />
        </colgroup>
        <thead>
          <tr className="text-2xs font-semibold uppercase text-contrast-medium">
            <th className="px-static-sm py-static-xs" scope="col">Work</th>
            <th className="px-static-sm py-static-xs" scope="col">Pipeline</th>
            <th className="px-static-sm py-static-xs" scope="col">Current state</th>
          </tr>
        </thead>
        <tbody>
          {outcomes.map((item) => {
            const isSelected = selected?.changeId === item.change_id && selected.itemKey === item.item_key
            return (
              <tr
                key={workItemIdentity(item)}
                className={['relative align-top', isSelected ? 'bg-frosted-soft' : 'bg-surface hover:bg-frosted-soft'].join(' ')}
                data-work-item={workItemIdentity(item)}
              >
                <td className="rounded-l-sm px-static-sm py-static-xs">
                  <ItemLink item={item} selected={isSelected} onSelect={onSelect} />
                  <span className="block text-xs text-contrast-medium">Outcome {item.work_item_id}</span>
                </td>
                <td className="px-static-sm py-static-sm"><PipelineState item={item} /></td>
                <td className="rounded-r-sm px-static-sm py-static-sm"><CurrentState item={item} onSelect={onSelect} /></td>
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
    <div className="lg:hidden">
      {outcomes.map((item) => {
        const isSelected = selected?.changeId === item.change_id && selected.itemKey === item.item_key
        return (
          <article
            key={workItemIdentity(item)}
            className={['relative mb-1 grid gap-static-sm rounded-sm p-static-sm', isSelected ? 'bg-frosted-soft' : 'bg-surface'].join(' ')}
            data-work-item={workItemIdentity(item)}
            aria-label={`${item.title} work item`}
          >
            <ItemLink item={item} selected={isSelected} onSelect={onSelect} />
            <span className="text-xs text-contrast-medium">Outcome {item.work_item_id}</span>
            <div className="grid grid-cols-2 gap-static-sm text-xs">
              <div><span className="mb-1 block text-2xs font-semibold uppercase text-contrast-medium">Pipeline</span><PipelineState item={item} /></div>
              <div><span className="mb-1 block text-2xs font-semibold uppercase text-contrast-medium">Current state</span><CurrentState item={item} onSelect={onSelect} /></div>
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
      className={['relative grid gap-static-sm rounded-sm px-static-sm py-static-md lg:grid-cols-[minmax(0,40fr)_minmax(0,25fr)_minmax(0,35fr)] lg:items-start lg:gap-0 lg:px-0 lg:py-0', isSelected ? 'bg-frosted-soft' : 'bg-surface'].join(' ')}
      aria-label={`Change Integration for ${group.title}`}
      data-work-item={workItemIdentity(item)}
    >
      <div className="min-w-0 lg:px-static-sm lg:py-static-sm">
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
        <span className="text-xs text-contrast-medium">Change</span>
      </div>
      <div className="lg:px-static-sm lg:py-static-sm"><span className="mb-1 block text-2xs font-semibold uppercase text-contrast-medium lg:hidden">Pipeline</span><PipelineState item={item} /></div>
      <div className="relative z-[1] lg:px-static-sm lg:py-static-sm"><span className="mb-1 block text-2xs font-semibold uppercase text-contrast-medium lg:hidden">Current state</span><CurrentState item={item} onSelect={onSelect} /></div>
    </section>
  )
}

export default function WorkPortfolioTable({ groups, selected, emptyMessage, onSelect }: WorkPortfolioTableProps) {
  if (groups.length === 0) return <p className="py-static-lg text-sm text-contrast-medium">{emptyMessage ?? 'No current Delivery work.'}</p>
  return (
    <section aria-label="Delivery work" data-testid="work-portfolio-table" className="grid gap-static-xl">
      {groups.map((group) => (
        <section key={group.change_id} className="min-w-0" aria-labelledby={`work-group-${group.change_id}`}>
          <h2 id={`work-group-${group.change_id}`} className="mb-static-xs px-static-sm text-xs font-semibold text-contrast-medium">{group.title}</h2>
          <DesktopTable group={group} selected={selected} onSelect={onSelect} />
          <CompactRows group={group} selected={selected} onSelect={onSelect} />
          <IntegrationGate group={group} selected={selected} onSelect={onSelect} />
        </section>
      ))}
    </section>
  )
}
