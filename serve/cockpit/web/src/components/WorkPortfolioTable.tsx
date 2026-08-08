import { PLinkPure } from '@porsche-design-system/components-react'
import { Link, useNavigate } from 'react-router'
import type {
  ChangeGroupView,
  WorkItemCardView,
} from '../api/workItems'
import { workItemIdentity, type WorkItemIdentity } from '../hooks/useWorkItems'
import { hasOptionalManualAction, PROGRESS_STAGE_LABELS, workItemStatusLabel } from './workItemPresentation'

interface WorkPortfolioTableProps {
  groups: ChangeGroupView[]
  selected: WorkItemIdentity | null
  emptyMessage?: string
  onSelect: (identity: WorkItemIdentity, trigger: HTMLElement) => void
}

type GroupTableProps = Pick<WorkPortfolioTableProps, 'selected' | 'onSelect'> & { group: ChangeGroupView }

function attentionBorder(item: WorkItemCardView): string {
  if (item.needs === 'you') return 'border-l-4 border-l-error'
  if (item.needs === 'repair' || item.activity.state === 'repairing') return 'border-l-4 border-l-warning'
  return 'border-l-4 border-l-contrast-low'
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
      className="block min-w-0 font-semibold text-primary underline-offset-4 after:absolute after:inset-0 after:content-[''] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      aria-current={selected ? 'location' : undefined}
      onClick={(event) => onSelect(identity, event.currentTarget)}
    >
      <span className="block overflow-hidden [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2]">{item.title}</span>
    </Link>
  )
}

function ActionLink({ item, onSelect, subdued = false }: { item: WorkItemCardView; onSelect: WorkPortfolioTableProps['onSelect']; subdued?: boolean }) {
  const navigate = useNavigate()
  if (item.action.kind === 'none' || !item.action.label) return null
  const identity = { changeId: item.change_id, itemKey: item.item_key }
  const path = workItemPath(item)
  return (
    <PLinkPure
      href={path}
      color={subdued ? 'contrast-medium' : 'primary'}
      size="xs"
      className="relative z-[1]"
      onClick={(event) => {
        event.preventDefault()
        onSelect(identity, event.currentTarget as HTMLElement)
        navigate(path)
      }}
    >
      {item.action.label}
    </PLinkPure>
  )
}

function ProgressState({ item }: { item: WorkItemCardView }) {
  if (item.stage === null) return <strong className="block font-medium text-primary">{item.progress.label}</strong>
  if (item.stage === 'completed') return <strong className="block font-medium text-primary">{item.progress.label}</strong>
  const stage = PROGRESS_STAGE_LABELS[item.stage]
  return (
    <span>
      <strong className="block font-medium text-primary">{stage}</strong>
      <span className="mt-0.5 block text-xs text-contrast-medium">{item.progress.label}</span>
    </span>
  )
}

function CurrentState({ item, onSelect }: { item: WorkItemCardView; onSelect: WorkPortfolioTableProps['onSelect'] }) {
  const state = workItemStatusLabel(item)
  const urgent = item.needs === 'you'
  const manualOption = hasOptionalManualAction(item)
  return (
    <span>
      <span className={urgent ? 'block font-semibold text-error' : 'block font-medium text-primary'}>{state}</span>
      {item.activity.task_id ? <span className="mt-0.5 block text-xs text-contrast-medium">Task {item.activity.task_id}</span> : null}
      {item.action.kind !== 'none' ? <span className={manualOption ? 'mt-0.5 block text-xs text-contrast-medium' : 'mt-0.5 block'}>{manualOption ? 'Manual option: ' : null}<ActionLink item={item} onSelect={onSelect} subdued={manualOption} /></span> : null}
    </span>
  )
}

function DesktopTable({ group, selected, onSelect }: GroupTableProps) {
  const outcomes = group.items.filter((item) => item.scope === 'outcome')
  return (
    <div className="hidden overflow-x-auto md:block" data-testid="work-table-scroll">
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
            <th className="px-static-sm py-static-xs" scope="col">Progress</th>
            <th className="px-static-sm py-static-xs" scope="col">Status</th>
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
                <td className={`rounded-l-lg border-y border-contrast-low px-static-sm py-static-sm ${attentionBorder(item)}`}>
                  <ItemLink item={item} selected={isSelected} onSelect={onSelect} />
                  <span className="block text-xs text-contrast-medium">Outcome: <code>{item.work_item_id}</code></span>
                </td>
                <td className="border-y border-contrast-low px-static-sm py-static-sm"><ProgressState item={item} /></td>
                <td className="rounded-r-lg border-y border-r border-contrast-low px-static-sm py-static-sm"><CurrentState item={item} onSelect={onSelect} /></td>
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
    <div className="grid gap-static-sm md:hidden">
      {outcomes.map((item) => {
        const isSelected = selected?.changeId === item.change_id && selected.itemKey === item.item_key
        return (
          <article
            key={workItemIdentity(item)}
            className={['relative grid gap-static-sm rounded-lg border-y border-r border-contrast-low p-static-sm', attentionBorder(item), isSelected ? 'bg-frosted-soft' : 'bg-surface'].join(' ')}
            data-work-item={workItemIdentity(item)}
            aria-label={`${item.title} work item`}
          >
            <ItemLink item={item} selected={isSelected} onSelect={onSelect} />
            <span className="text-xs text-contrast-medium">Outcome: <code>{item.work_item_id}</code></span>
            <div className="grid grid-cols-2 gap-static-sm text-xs">
              <div><span className="mb-1 block text-2xs font-semibold uppercase text-contrast-medium">Progress</span><ProgressState item={item} /></div>
              <div><span className="mb-1 block text-2xs font-semibold uppercase text-contrast-medium">Status</span><CurrentState item={item} onSelect={onSelect} /></div>
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
      className={[
        'relative mt-static-sm rounded-lg border-y border-r border-contrast-low px-static-sm py-static-md md:px-0 md:py-0',
        attentionBorder(item),
        isSelected ? 'bg-frosted-soft' : 'bg-surface hover:bg-frosted-soft',
      ].join(' ')}
      aria-label={`Change Integration for ${group.title}`}
      data-work-item={workItemIdentity(item)}
    >
      <dl className="grid gap-static-sm md:grid-cols-[minmax(0,40fr)_minmax(0,25fr)_minmax(0,35fr)] md:items-start md:gap-0">
        <div className="min-w-0 md:px-static-sm md:py-static-sm">
          <dt className="sr-only">Work</dt>
          <dd>
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
            <span className="text-xs text-contrast-medium">Change: {group.title}</span>
          </dd>
        </div>
        <div className="md:px-static-sm md:py-static-sm">
          <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-medium md:sr-only">Progress</dt>
          <dd><ProgressState item={item} /></dd>
        </div>
        <div className="relative z-[1] md:px-static-sm md:py-static-sm">
          <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-medium md:sr-only">Status</dt>
          <dd><CurrentState item={item} onSelect={onSelect} /></dd>
        </div>
      </dl>
    </section>
  )
}

export default function WorkPortfolioTable({ groups, selected, emptyMessage, onSelect }: WorkPortfolioTableProps) {
  if (groups.length === 0) return <p className="py-static-lg text-sm text-contrast-medium">{emptyMessage ?? 'No current Delivery work.'}</p>
  return (
    <section aria-label="Delivery work" data-testid="work-portfolio-table" className="grid gap-static-lg">
      {groups.map((group) => (
        <section key={group.change_id} className="min-w-0" aria-labelledby={`work-group-${group.change_id}`}>
          <h2 id={`work-group-${group.change_id}`} className="mb-static-xs border-b border-contrast-low px-static-sm pb-static-xs text-md font-semibold text-primary">{group.title}</h2>
          <DesktopTable group={group} selected={selected} onSelect={onSelect} />
          <CompactRows group={group} selected={selected} onSelect={onSelect} />
          <IntegrationGate group={group} selected={selected} onSelect={onSelect} />
        </section>
      ))}
    </section>
  )
}
