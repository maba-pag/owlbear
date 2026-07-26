import { useEffect, useMemo, useRef, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { PButton, PHeading, PIcon, PInputText } from '@porsche-design-system/components-react'
import { useSearchParams } from 'react-router'
import type {
  NativeDeliveryNode,
  NativeGraphDetail,
  NativeNodePlan,
} from '../api/native'

interface DeliveryGraphOutlineProps {
  detail: NativeGraphDetail
}

interface Filters {
  requirement: string
  interfaceId: string
  migration: string
  proof: string
}

const EMPTY_FILTERS: Filters = { requirement: '', interfaceId: '', migration: '', proof: '' }

type FieldValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function eventValue(event: FieldValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function includes(value: string[], query: string): boolean {
  return query === '' || value.some((item) => item.toLowerCase().includes(query.toLowerCase()))
}

function nodeMatches(
  node: NativeDeliveryNode,
  filters: Filters,
  migrationByInterface: Map<string, string | null>,
): boolean {
  const obligations = [...node.owns, ...node.supports]
  const interfaces = [...node.produces, ...node.consumes]
  const migrations = interfaces
    .map((interfaceId) => migrationByInterface.get(interfaceId))
    .filter((migration): migration is string => migration !== null && migration !== undefined)
  return (
    includes(obligations, filters.requirement) &&
    includes(interfaces, filters.interfaceId) &&
    includes(migrations, filters.migration) &&
    (filters.proof === '' || node.proof.toLowerCase().includes(filters.proof.toLowerCase()))
  )
}

function PlanPanel({ plan }: { plan: NativeNodePlan | undefined }) {
  if (!plan) {
    return <p className="text-sm text-contrast-medium">No packet plan is available.</p>
  }
  return (
    <div className="divide-y divide-contrast-low border-y border-contrast-low">
      {plan.packets.map((packet) => (
        <article key={packet.id} className="py-static-sm">
          <strong>{packet.id}</strong>
          <p className="mt-static-xs text-xs text-contrast-medium">
            Paths: {packet.impact_closure.paths.join(', ')}
          </p>
          <p className="mt-1 text-xs text-contrast-medium">Dependencies: {packet.dependencies.join(', ') || 'None'}</p>
          <p className="mt-1 text-xs text-contrast-medium">Authority: {packet.impact_closure.authority_targets.join(', ')}</p>
        </article>
      ))}
    </div>
  )
}

export default function DeliveryGraphOutline({ detail }: DeliveryGraphOutlineProps) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const migrationByInterface = useMemo(
    () => new Map(detail.graph.interfaces.map((item) => [item.id, item.migration])),
    [detail.graph.interfaces],
  )
  const filteredNodes = useMemo(
    () => detail.graph.nodes.filter((node) => nodeMatches(node, filters, migrationByInterface)),
    [detail.graph.nodes, filters, migrationByInterface],
  )
  const requestedNodeId = searchParams.get('node')
  const selectedNode =
    filteredNodes.find((node) => node.id === requestedNodeId) ??
    filteredNodes[0] ??
    null
  const virtualizer = useVirtualizer({
    count: filteredNodes.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 88,
    overscan: 6,
  })

  useEffect(() => {
    if (!selectedNode || selectedNode.id === requestedNodeId) {
      return
    }
    const next = new URLSearchParams(searchParams)
    next.set('node', selectedNode.id)
    setSearchParams(next, { replace: true })
  }, [requestedNodeId, searchParams, selectedNode, setSearchParams])

  useEffect(() => {
    const index = requestedNodeId ? filteredNodes.findIndex((node) => node.id === requestedNodeId) : -1
    if (index >= 0) {
      virtualizer.scrollToIndex(index, { align: 'center' })
    }
  }, [filteredNodes, requestedNodeId, virtualizer])

  const selectNode = (nodeId: string) => {
    const next = new URLSearchParams(searchParams)
    next.set('node', nodeId)
    setSearchParams(next)
  }
  const moveSelection = (direction: -1 | 1) => {
    if (filteredNodes.length === 0) {
      return
    }
    const currentIndex = selectedNode ? filteredNodes.findIndex((node) => node.id === selectedNode.id) : -1
    const nextIndex = Math.min(filteredNodes.length - 1, Math.max(0, currentIndex + direction))
    const nextNode = filteredNodes[nextIndex]
    selectNode(nextNode.id)
    virtualizer.scrollToIndex(nextIndex, { align: 'auto' })
  }
  const updateFilter = (name: keyof Filters, value: string) => {
    setFilters((current) => ({ ...current, [name]: value }))
  }

  return (
    <section aria-labelledby="delivery-graph-heading" className="border-t border-contrast-low pt-static-lg" data-testid="delivery-graph-outline">
      <div className="flex flex-wrap items-end justify-between gap-static-md">
        <div>
          <PHeading id="delivery-graph-heading" tag="h2" size="lg">Delivery graph</PHeading>
          <p className="mt-static-xs text-sm text-contrast-medium">{filteredNodes.length} of {detail.graph.nodes.length} nodes</p>
        </div>
        <PButton type="button" variant="secondary" onClick={() => setFilters(EMPTY_FILTERS)}>Clear filters</PButton>
      </div>

      <div className="mt-static-md grid gap-static-sm sm:grid-cols-2 lg:grid-cols-4" aria-label="Graph filters">
        {([
          ['requirement', 'Requirement'],
          ['interfaceId', 'Interface'],
          ['migration', 'Migration'],
          ['proof', 'Proof'],
        ] as const).map(([name, label]) => (
          <PInputText
            key={name}
            name={`graph-filter-${name}`}
            label={label}
            value={filters[name]}
            compact
            onChange={(event) => updateFilter(name, eventValue(event as FieldValueEvent))}
          />
        ))}
      </div>

      <div className="mt-static-lg grid min-h-0 gap-static-lg lg:grid-cols-[minmax(18rem,0.9fr)_minmax(0,1.1fr)]">
        <div
          ref={scrollRef}
          className="h-[min(55dvh,620px)] min-h-[18rem] overflow-y-auto rounded-sm border border-contrast-low bg-surface"
          role="listbox"
          aria-label="Delivery nodes"
          aria-activedescendant={selectedNode ? `delivery-node-${selectedNode.id}` : undefined}
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault()
              moveSelection(1)
            } else if (event.key === 'ArrowUp') {
              event.preventDefault()
              moveSelection(-1)
            }
          }}
        >
          <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
            {virtualizer.getVirtualItems().map((row) => {
              const node = filteredNodes[row.index]
              const active = selectedNode?.id === node.id
              return (
                <button
                  key={node.id}
                  id={`delivery-node-${node.id}`}
                  type="button"
                  role="option"
                  aria-selected={active}
                  data-node-id={node.id}
                  className={[
                    'absolute left-0 top-0 flex w-full min-w-0 flex-col items-start gap-1 border-b border-contrast-low px-static-md py-static-sm text-left',
                    active ? 'bg-primary text-canvas' : 'bg-surface text-primary hover:bg-canvas',
                  ].join(' ')}
                  style={{ height: `${row.size}px`, transform: `translateY(${row.start}px)` }}
                  onClick={() => selectNode(node.id)}
                >
                  <span className="flex w-full min-w-0 items-center gap-static-xs">
                    <strong>{node.id}</strong>
                    <span className="truncate">{node.title}</span>
                  </span>
                  <span className="line-clamp-2 text-xs opacity-80">{node.outcome}</span>
                </button>
              )
            })}
          </div>
        </div>

        <article className="min-w-0 border-l-4 border-primary pl-static-md" data-testid="node-detail" tabIndex={0}>
          {selectedNode ? (
            <div className="flex min-w-0 flex-col gap-static-md">
              <div>
                <span className="text-xs font-semibold uppercase text-contrast-medium">{selectedNode.id}</span>
                <PHeading tag="h3" size="md">{selectedNode.title}</PHeading>
                <p className="mt-static-sm text-sm leading-relaxed">{selectedNode.outcome}</p>
              </div>
              <dl className="grid gap-static-sm text-sm sm:grid-cols-2">
                <div><dt className="font-semibold">Dependencies</dt><dd>{selectedNode.dependencies.join(', ') || 'None'}</dd></div>
                <div><dt className="font-semibold">Proof</dt><dd>{selectedNode.proof}</dd></div>
                <div><dt className="font-semibold">Owns / supports</dt><dd>{[...selectedNode.owns, ...selectedNode.supports].join(', ') || 'None'}</dd></div>
                <div><dt className="font-semibold">Modules</dt><dd>{selectedNode.modules.join(', ') || 'None'}</dd></div>
                <div><dt className="font-semibold">Produces</dt><dd>{selectedNode.produces.join(', ') || 'None'}</dd></div>
                <div><dt className="font-semibold">Consumes</dt><dd>{selectedNode.consumes.join(', ') || 'None'}</dd></div>
                <div><dt className="font-semibold">Risks</dt><dd>{selectedNode.risks.join(', ') || 'None'}</dd></div>
              </dl>
              <div>
                <PHeading tag="h4" size="sm">Packet plan</PHeading>
                <div className="mt-static-sm"><PlanPanel plan={detail.plans[selectedNode.id]} /></div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-static-sm text-sm text-contrast-medium">
              <PIcon name="search" aria-hidden="true" /> No matching nodes.
            </div>
          )}
        </article>
      </div>
    </section>
  )
}
