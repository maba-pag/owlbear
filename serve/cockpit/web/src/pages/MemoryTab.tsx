import { useEffect, useMemo, useRef, useState } from 'react'
import {
  PButton,
  PInputSearch,
  PMultiSelect,
  PMultiSelectOption,
  PSelect,
  PSelectOption,
  PTag,
} from '@porsche-design-system/components-react'
import type { TagVariant } from '@porsche-design-system/components-react'
import type { KanbanBoardProps } from '../KanbanBoard'
import { usePollingFetch } from '../hooks/usePollingFetch'

type MemoryState = 'pending' | 'curated' | 'approved' | 'deleted'

interface MemoryEntry {
  id: string
  title: string
  content: string
  categories: string[]
  confidence: number
  state: MemoryState
  scope_agents: string[]
  source_agent: string
  created_at: string
  updated_at: string
  approved_at: string | null
}

interface MemoriesResponse {
  entries?: MemoryEntry[]
  parse_errors?: number
}

interface MemoryFilterState {
  states: MemoryState[]
  categories: string[]
  agent: string
  text: string
}

const DEFAULT_STATES: MemoryState[] = ['pending', 'curated', 'approved']
const STATE_PRIORITY: Record<MemoryState, number> = {
  pending: 0,
  curated: 1,
  approved: 2,
  deleted: 3,
}
const STATE_VARIANTS: Record<MemoryState, TagVariant> = {
  pending: 'warning',
  curated: 'info',
  approved: 'success',
  deleted: 'secondary',
}

const INITIAL_FILTER: MemoryFilterState = {
  states: [...DEFAULT_STATES],
  categories: [],
  agent: '',
  text: '',
}

type ControlValueEvent = {
  target?: unknown
  currentTarget?: unknown
  detail?: { value?: unknown }
}

function readStringValue(event: Event): string {
  const customEvent = event as CustomEvent<{ value?: unknown }>
  if (typeof customEvent.detail?.value === 'string') {
    return customEvent.detail.value
  }

  const genericEvent = event as ControlValueEvent
  const target = genericEvent.target as { value?: unknown } | undefined
  if (typeof target?.value === 'string') {
    return target.value
  }

  const currentTarget = genericEvent.currentTarget as { value?: unknown } | undefined
  if (typeof currentTarget?.value === 'string') {
    return currentTarget.value
  }

  return ''
}

function readStringArrayValue(event: Event): string[] {
  const customEvent = event as CustomEvent<{ value?: unknown }>
  const { value } = customEvent.detail ?? {}
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function formatConfidence(value: number): string {
  if (!Number.isFinite(value)) {
    return '0.00'
  }
  return value.toFixed(2)
}

function normalizeTimestamp(value: string): number {
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? Number.POSITIVE_INFINITY : parsed
}

function sortEntries(entries: MemoryEntry[]): MemoryEntry[] {
  return [...entries].sort((left, right) => {
    const stateDelta = STATE_PRIORITY[left.state] - STATE_PRIORITY[right.state]
    if (stateDelta !== 0) {
      return stateDelta
    }
    return normalizeTimestamp(left.created_at) - normalizeTimestamp(right.created_at)
  })
}

function includesText(entry: MemoryEntry, loweredSearch: string): boolean {
  if (!loweredSearch) {
    return true
  }
  return (
    entry.title.toLowerCase().includes(loweredSearch) ||
    entry.content.toLowerCase().includes(loweredSearch)
  )
}

function matchesAgent(entry: MemoryEntry, selectedAgent: string): boolean {
  if (!selectedAgent || entry.scope_agents.length === 0) {
    return true
  }
  return entry.scope_agents.includes(selectedAgent)
}

function toDistinctSortedValues(values: string[]): string[] {
  return [...new Set(values)].sort((left, right) => left.localeCompare(right))
}

function MemoryTab(_props: KanbanBoardProps) {
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [parseErrors, setParseErrors] = useState(0)
  const [filter, setFilter] = useState<MemoryFilterState>(INITIAL_FILTER)

  const stateFilterRef = useRef<HTMLElement | null>(null)
  const categoryFilterRef = useRef<HTMLElement | null>(null)
  const agentFilterRef = useRef<HTMLElement | null>(null)
  const searchFilterRef = useRef<HTMLElement | null>(null)

  const { isFetching, hasFetched, refetch } = usePollingFetch<MemoriesResponse>('/api/memories', {
    paused: true,
    onSuccess: async (payload) => {
      setEntries(Array.isArray(payload.entries) ? payload.entries : [])
      setParseErrors(typeof payload.parse_errors === 'number' ? payload.parse_errors : 0)
    },
    onError: async () => {
      setEntries([])
      setParseErrors(0)
    },
  })

  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        refetch()
      }
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [refetch])

  useEffect(() => {
    const element = stateFilterRef.current
    if (!element) {
      return
    }

    const onUpdate = (event: Event) => {
      const values = readStringArrayValue(event).filter(
        (value): value is MemoryState => value in STATE_PRIORITY,
      )
      setFilter((previous) => ({ ...previous, states: values }))
    }

    element.addEventListener('update', onUpdate)
    return () => {
      element.removeEventListener('update', onUpdate)
    }
  }, [])

  useEffect(() => {
    const element = categoryFilterRef.current
    if (!element) {
      return
    }

    const onUpdate = (event: Event) => {
      setFilter((previous) => ({ ...previous, categories: readStringArrayValue(event) }))
    }

    element.addEventListener('update', onUpdate)
    return () => {
      element.removeEventListener('update', onUpdate)
    }
  }, [])

  useEffect(() => {
    const element = agentFilterRef.current
    if (!element) {
      return
    }

    const onUpdate = (event: Event) => {
      setFilter((previous) => ({ ...previous, agent: readStringValue(event) }))
    }

    element.addEventListener('update', onUpdate)
    element.addEventListener('change', onUpdate)
    return () => {
      element.removeEventListener('update', onUpdate)
      element.removeEventListener('change', onUpdate)
    }
  }, [])

  useEffect(() => {
    const element = searchFilterRef.current
    if (!element) {
      return
    }

    const onUpdate = (event: Event) => {
      setFilter((previous) => ({ ...previous, text: readStringValue(event) }))
    }

    element.addEventListener('input', onUpdate)
    element.addEventListener('change', onUpdate)
    return () => {
      element.removeEventListener('input', onUpdate)
      element.removeEventListener('change', onUpdate)
    }
  }, [])

  const categoryOptions = useMemo(
    () => toDistinctSortedValues(entries.flatMap((entry) => entry.categories)),
    [entries],
  )
  const agentOptions = useMemo(
    () => toDistinctSortedValues(entries.flatMap((entry) => entry.scope_agents)),
    [entries],
  )

  const visibleEntries = useMemo(() => {
    const loweredSearch = filter.text.trim().toLowerCase()

    return sortEntries(entries).filter((entry) => {
      const matchesState = filter.states.length === 0 || filter.states.includes(entry.state)
      const matchesCategory =
        filter.categories.length === 0 || filter.categories.every((category) => entry.categories.includes(category))
      const matchesAgentFilter = matchesAgent(entry, filter.agent)
      const matchesTextSearch = includesText(entry, loweredSearch)

      return matchesState && matchesCategory && matchesAgentFilter && matchesTextSearch
    })
  }, [entries, filter])

  const hasEntries = entries.length > 0
  const hasVisibleEntries = visibleEntries.length > 0

  const resetFilters = () => {
    setFilter(INITIAL_FILTER)
  }

  return (
    <section data-testid="memory-tab">
      <header>
        <h2>Memory</h2>
      </header>

      <div>
        <PMultiSelect
          name="state-filter"
          label="State"
          value={filter.states}
          ref={(element) => {
            stateFilterRef.current = element as unknown as HTMLElement | null
          }}
        >
          <PMultiSelectOption value="pending">pending</PMultiSelectOption>
          <PMultiSelectOption value="curated">curated</PMultiSelectOption>
          <PMultiSelectOption value="approved">approved</PMultiSelectOption>
          <PMultiSelectOption value="deleted">deleted</PMultiSelectOption>
        </PMultiSelect>

        <PMultiSelect
          name="category-filter"
          label="Category"
          value={filter.categories}
          ref={(element) => {
            categoryFilterRef.current = element as unknown as HTMLElement | null
          }}
        >
          {categoryOptions.map((category) => (
            <PMultiSelectOption key={category} value={category}>
              {category}
            </PMultiSelectOption>
          ))}
        </PMultiSelect>

        <PSelect
          name="agent-filter"
          label="Agent"
          value={filter.agent}
          ref={(element) => {
            agentFilterRef.current = element as unknown as HTMLElement | null
          }}
        >
          <PSelectOption value="">All agents</PSelectOption>
          {agentOptions.map((agent) => (
            <PSelectOption key={agent} value={agent}>
              {agent}
            </PSelectOption>
          ))}
        </PSelect>

        <PInputSearch
          name="memory-search"
          label="Search"
          value={filter.text}
          ref={(element) => {
            searchFilterRef.current = element as unknown as HTMLElement | null
          }}
        />
      </div>

      {isFetching ? <div data-testid="memory-loading" /> : null}

      {parseErrors > 0 ? (
        <p data-testid="parse-errors-warning">{parseErrors} entries couldn't be read</p>
      ) : null}

      {!hasEntries && hasFetched && !isFetching ? <p>No memory entries yet</p> : null}

      {hasEntries && !hasVisibleEntries ? (
        <div>
          <p>No entries match your filters</p>
          <PButton data-testid="clear-filters" variant="secondary" compact onClick={resetFilters}>
            Clear filters
          </PButton>
        </div>
      ) : null}

      {hasVisibleEntries ? (
        <ul>
          {visibleEntries.map((entry) => (
            <li key={entry.id} data-testid="memory-entry">
              <strong data-testid="memory-entry-title">{entry.title}</strong>
              <div>
                {entry.categories.map((category) => (
                  <PTag key={`${entry.id}-${category}`} data-testid="memory-entry-category">
                    {category}
                  </PTag>
                ))}
              </div>
              <span data-testid="memory-entry-confidence">{formatConfidence(entry.confidence)}</span>
              <PTag
                data-testid="memory-entry-state"
                variant={STATE_VARIANTS[entry.state]}
              >
                {entry.state}
              </PTag>
              <span data-testid="memory-entry-agents">
                {entry.scope_agents.length > 0 ? entry.scope_agents.join(', ') : 'All agents'}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}

export default MemoryTab
