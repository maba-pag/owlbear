import { PLinkPure } from '@porsche-design-system/components-react'
import { Link, useNavigate } from 'react-router'
import type {
  ChangeGroupView,
  WorkItemCardView,
} from '../api/workItems'
import { workItemIdentity, type WorkItemIdentity } from '../hooks/useWorkItems'
import CopyCommand from './CopyCommand'
import {
  PROGRESS_STAGE_LABELS,
  workItemStatus,
  workItemStatusClassName,
} from './workItemPresentation'

interface WorkPortfolioTableProps {
  groups: ChangeGroupView[]
  selected: WorkItemIdentity | null
  emptyMessage?: string
  onSelect: (identity: WorkItemIdentity, trigger: HTMLElement) => void
}

type GroupTableProps = Pick<WorkPortfolioTableProps, 'selected' | 'onSelect'> & { group: ChangeGroupView }

function attentionBorder(item: WorkItemCardView): string {
  if (item.needs === 'you') return 'border-l-4 border-l-error'
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
      className="block min-w-0 font-semibold text-primary after:absolute after:inset-0 after:content-[''] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
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
  if (item.action.command) {
    return <CopyCommand command={item.action.command} />
  }
  const identity = { changeId: item.change_id, itemKey: item.item_key }
  const path = workItemPath(item)
  return (
    <PLinkPure
      href={path}
      color={subdued ? 'contrast-medium' : 'primary'}
      size="xs"
      className="relative z-[1]"
      onClick={(event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
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
  const stage = item.stage === null ? null : PROGRESS_STAGE_LABELS[item.stage]
  const quantified = item.progress.done !== null && item.progress.total !== null && item.progress.total > 0
  const percentage = quantified
    ? Math.min(100, Math.round((item.progress.done as number / (item.progress.total as number)) * 100))
    : null
  return (
    <span>
      {stage ? <strong className="block font-medium text-primary">{stage}</strong> : null}
      {percentage !== null ? (
        <span
          className="mt-1 block h-1.5 w-full max-w-40 overflow-hidden rounded-full bg-contrast-low"
          role="progressbar"
          aria-label={`${item.progress.label} progress`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percentage}
        >
          <span className="block h-full rounded-full bg-primary" style={{ width: `${percentage}%` }} />
        </span>
      ) : null}
      <span className="mt-0.5 block text-xs text-contrast-medium">{item.progress.label}</span>
    </span>
  )
}

function CurrentState({ item, onSelect }: { item: WorkItemCardView; onSelect: WorkPortfolioTableProps['onSelect'] }) {
  const state = workItemStatus(item)
  return (
    <span>
      <span className={`inline-flex items-center rounded-sm border px-static-xs py-1 text-xs font-semibold leading-none ${workItemStatusClassName(state.tone)}`} data-status-tone={state.tone}>{state.label}</span>
      {state.detail ? <span className="mt-1 block text-xs text-contrast-medium">{state.detail}</span> : null}
      {item.activity.task_id ? <span className="mt-0.5 block text-xs text-contrast-medium">Task {item.activity.task_id}</span> : null}
      {item.action.kind !== 'none' ? <span className="mt-0.5 block"><ActionLink item={item} onSelect={onSelect} /></span> : null}
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
          <col className="w-[44%]" />
          <col className="w-[24%]" />
          <col className="w-[32%]" />
        </colgroup>
        <thead>
          <tr className="text-2xs font-semibold uppercase text-contrast-high">
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
              <div><span className="mb-1 block text-2xs font-semibold uppercase text-contrast-high">Progress</span><ProgressState item={item} /></div>
              <div><span className="mb-1 block text-2xs font-semibold uppercase text-contrast-high">Status</span><CurrentState item={item} onSelect={onSelect} /></div>
            </div>
          </article>
        )
      })}
    </div>
  )
}

function PublicationGate({ group, selected, onSelect }: GroupTableProps) {
  const item = group.items.find((candidate) => candidate.scope === 'change-publication')
  if (!item) return null
  const isSelected = selected?.changeId === item.change_id && selected.itemKey === item.item_key
  const identity = { changeId: item.change_id, itemKey: item.item_key }
  const path = workItemPath(item)
  return (
    <section
      className={[
        'relative mt-static-sm rounded-lg border-y border-r border-contrast-low px-static-sm py-static-md md:px-0 md:py-0',
        attentionBorder(item),
        isSelected ? 'bg-frosted-soft' : 'bg-surface hover:bg-frosted-soft',
      ].join(' ')}
      aria-label={`Change publication for ${group.title}`}
      data-work-item={workItemIdentity(item)}
    >
      <dl className="grid gap-static-sm md:grid-cols-[minmax(0,44fr)_minmax(0,24fr)_minmax(0,32fr)] md:items-start md:gap-0">
        <div className="min-w-0 md:px-static-sm md:py-static-sm">
          <dt className="sr-only">Work</dt>
          <dd>
            <Link
              to={path}
              data-work-item-primary-trigger
              data-work-item-identity={`${item.change_id}:${item.item_key}`}
              className="block font-semibold text-primary after:absolute after:inset-0 after:content-[''] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
              aria-current={isSelected ? 'location' : undefined}
              onClick={(event) => onSelect(identity, event.currentTarget)}
            >
              Publication
            </Link>
            <span className="text-xs text-contrast-medium">Change: {group.title}</span>
          </dd>
        </div>
        <div className="md:px-static-sm md:py-static-sm">
          <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-high md:sr-only">Progress</dt>
          <dd><ProgressState item={item} /></dd>
        </div>
        <div className="md:px-static-sm md:py-static-sm">
          <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-high md:sr-only">Status</dt>
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
          <PublicationGate group={group} selected={selected} onSelect={onSelect} />
        </section>
      ))}
    </section>
  )
}
