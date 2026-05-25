import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  PButton,
  PHeading,
  PInputNumber,
  PInputSearch,
  PInputText,
  PModal,
  PMultiSelect,
  PMultiSelectOption,
  PSelect,
  PSelectOption,
  PTag,
  PTagDismissible,
  PTextarea,
} from '@porsche-design-system/components-react'
import type { TagVariant } from '@porsche-design-system/components-react'
import rehypeSanitize from 'rehype-sanitize'
import {
  approveMemory,
  deleteMemory,
  editMemory,
  MemoryMutationError,
  type MemoriesResponse,
  type MemoryEditPayload,
  type MemoryEntry,
  type MemoryState,
  type ValidationMessage,
} from '../api/memories'
import MarkdownPreview from '../components/MarkdownPreview'
import { WorkspaceHeader, WorkspaceHeaderMetric, WorkspaceHeaderPill } from '../components/WorkspaceHeader'
import { MEMORY_PENDING_COUNT_EVENT } from '../hooks/usePendingMemoryCount'
import { usePollingFetch } from '../hooks/usePollingFetch'

interface MemoryFilterState {
  states: MemoryState[]
  categories: string[]
  agent: string
  text: string
}

const DEFAULT_STATES: MemoryState[] = ['pending', 'curated', 'approved']
const ALL_AGENTS_SCOPE = '*'
const STATE_PRIORITY: Record<MemoryState, number> = {
  pending: 0,
  curated: 1,
  approved: 2,
  deleted: 3,
}
const STATE_VARIANTS: Record<MemoryState, TagVariant> = {
  pending: 'warning-frosted',
  curated: 'info-frosted',
  approved: 'success-frosted',
  deleted: 'error-frosted',
}
function syncTagVariantAttr(variant: TagVariant) {
  return (element: HTMLElement | null) => {
    if (!element) {
      return
    }
    element.setAttribute('compact', '')
    element.setAttribute('variant', variant)
  }
}

const INITIAL_FILTER: MemoryFilterState = {
  states: [...DEFAULT_STATES],
  categories: [],
  agent: '',
  text: '',
}

const MEMORY_CONTENT_LIMIT = 1024

export const MEMORY_SANITIZE_SCHEMA = {
  tagNames: ['p', 'br', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'a'],
  attributes: {
    a: ['href'],
  },
  protocols: {
    href: ['http', 'https', 'mailto'],
  },
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

function normalizeConfidence(value: number): number {
  return Number.isFinite(value) ? value : Number.NEGATIVE_INFINITY
}

function compareDescending(left: number, right: number): number {
  if (left === right) {
    return 0
  }
  return left > right ? -1 : 1
}

function compareAscending(left: number, right: number): number {
  if (left === right) {
    return 0
  }
  return left < right ? -1 : 1
}

function sortEntries(entries: MemoryEntry[]): MemoryEntry[] {
  return [...entries].sort((left, right) => {
    const confidenceDelta = compareDescending(normalizeConfidence(left.confidence), normalizeConfidence(right.confidence))
    if (confidenceDelta !== 0) {
      return confidenceDelta
    }

    const stateDelta = STATE_PRIORITY[left.state] - STATE_PRIORITY[right.state]
    if (stateDelta !== 0) {
      return stateDelta
    }

    const createdDelta = compareAscending(normalizeTimestamp(left.created_at), normalizeTimestamp(right.created_at))
    if (createdDelta !== 0) {
      return createdDelta
    }

    return left.id.localeCompare(right.id)
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

function isAllAgentsScope(scopeAgents: string[]): boolean {
  return scopeAgents.length === 0 || scopeAgents.includes(ALL_AGENTS_SCOPE)
}

function formatScopeAgents(scopeAgents: string[]): string {
  return isAllAgentsScope(scopeAgents) ? 'All agents' : scopeAgents.join(', ')
}

function toFilterableScopeAgents(scopeAgents: string[]): string[] {
  return scopeAgents.filter((agent) => agent !== ALL_AGENTS_SCOPE)
}

function matchesAgent(entry: MemoryEntry, selectedAgent: string): boolean {
  if (!selectedAgent || isAllAgentsScope(entry.scope_agents)) {
    return true
  }
  return entry.scope_agents.includes(selectedAgent)
}

function toDistinctSortedValues(values: string[]): string[] {
  return [...new Set(values)].sort((left, right) => left.localeCompare(right))
}

function splitCSV(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

function mergeListValues(existing: string[], additions: string[]): string[] {
  const seen = new Set(existing)
  const merged = [...existing]
  additions.forEach((item) => {
    if (!seen.has(item)) {
      seen.add(item)
      merged.push(item)
    }
  })
  return merged
}

function pendingValue(entry: MemoryEntry | null): number {
  return entry?.state === 'pending' ? 1 : 0
}

function emitPendingCountDelta(before: MemoryEntry, after: MemoryEntry | null): void {
  const delta = pendingValue(after) - pendingValue(before)
  if (delta === 0) {
    return
  }
  window.dispatchEvent(new CustomEvent(MEMORY_PENDING_COUNT_EVENT, { detail: { delta } }))
}

function makeInitialDraft(entry: MemoryEntry): MemoryEditPayload {
  return {
    title: entry.title,
    categories: entry.categories,
    confidence: entry.confidence,
    scope_agents: entry.scope_agents,
    content: entry.content,
    expected_updated_at: entry.updated_at,
  }
}

function MemoryTab() {
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [parseErrors, setParseErrors] = useState(0)
  const [filter, setFilter] = useState<MemoryFilterState>(INITIAL_FILTER)
  const [openEntryId, setOpenEntryId] = useState<string | null>(null)
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<MemoryEditPayload | null>(null)
  const [newCategory, setNewCategory] = useState('')
  const [newScopeAgent, setNewScopeAgent] = useState('')
  const [deleteConfirmEntryId, setDeleteConfirmEntryId] = useState<string | null>(null)
  const [mutationErrorByEntryId, setMutationErrorByEntryId] = useState<Record<string, string>>({})
  const [validationMessages, setValidationMessages] = useState<ValidationMessage[]>([])
  const [promotionMessageByEntryId, setPromotionMessageByEntryId] = useState<Record<string, string>>({})
  const [globalMutationMessage, setGlobalMutationMessage] = useState<string | null>(null)
  const [memoryListCanScrollDown, setMemoryListCanScrollDown] = useState(false)

  const stateFilterRef = useRef<HTMLElement | null>(null)
  const categoryFilterRef = useRef<HTMLElement | null>(null)
  const agentFilterRef = useRef<HTMLElement | null>(null)
  const searchFilterRef = useRef<HTMLElement | null>(null)
  const memoryListRef = useRef<HTMLUListElement | null>(null)
  const accordionRefs = useRef<Record<string, HTMLElement>>({})
  const memoryEditActionsRef = useRef<HTMLDivElement | null>(null)

  const { isFetching, hasFetched, refetch } = usePollingFetch<MemoriesResponse>('/api/memories', {
    paused: true,
    onSuccess: async (payload) => {
      if (Array.isArray(payload.entries)) {
        setEntries(payload.entries)
      }
      setParseErrors(typeof payload.parse_errors === 'number' ? payload.parse_errors : 0)
    },
    onError: async () => {
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
    element.addEventListener('change', onUpdate)
    return () => {
      element.removeEventListener('update', onUpdate)
      element.removeEventListener('change', onUpdate)
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
    element.addEventListener('change', onUpdate)
    return () => {
      element.removeEventListener('update', onUpdate)
      element.removeEventListener('change', onUpdate)
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
  const deleteConfirmEntry = useMemo(
    () => entries.find((entry) => entry.id === deleteConfirmEntryId) ?? null,
    [deleteConfirmEntryId, entries],
  )
  const agentOptions = useMemo(
    () => toDistinctSortedValues(entries.flatMap((entry) => toFilterableScopeAgents(entry.scope_agents))),
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
  const memoryCountMetric = visibleEntries.length === entries.length
    ? <WorkspaceHeaderMetric value={entries.length} label={entries.length === 1 ? 'entry' : 'entries'} />
    : <WorkspaceHeaderMetric value={`${visibleEntries.length} of ${entries.length}`} label="shown" />

  const updateMemoryListScrollCue = useCallback(() => {
    const list = memoryListRef.current
    setMemoryListCanScrollDown(Boolean(list && list.scrollHeight - list.scrollTop - list.clientHeight > 1))
  }, [])

  useEffect(() => {
    updateMemoryListScrollCue()

    const list = memoryListRef.current
    if (!list || typeof ResizeObserver === 'undefined') {
      return
    }

    const observer = new ResizeObserver(updateMemoryListScrollCue)
    observer.observe(list)
    return () => {
      observer.disconnect()
    }
  }, [openEntryId, updateMemoryListScrollCue, visibleEntries.length])

  useEffect(() => {
    if (editingEntryId === null) {
      return
    }

    window.requestAnimationFrame(() => {
      const list = memoryListRef.current
      const editActions = memoryEditActionsRef.current

      if (list && editActions) {
        const listRect = list.getBoundingClientRect()
        const actionsRect = editActions.getBoundingClientRect()
        const top = Math.max(0, list.scrollTop + actionsRect.top - listRect.top)

        if (typeof list.scrollTo === 'function') {
          list.scrollTo({ top, left: 0 })
        } else {
          list.scrollTop = top
          list.scrollLeft = 0
        }
      }
      updateMemoryListScrollCue()
    })
  }, [editingEntryId, updateMemoryListScrollCue])

  useEffect(() => {
    const entriesToBind = Object.entries(accordionRefs.current)
    if (entriesToBind.length === 0) {
      return
    }

    const cleanup = entriesToBind.map(([entryId, element]) => {
      const onUpdate = (event: Event) => {
        const customEvent = event as CustomEvent<{ open?: unknown }>
        const shouldOpen = customEvent.detail?.open === true
        setOpenEntryId((current) => {
          if (shouldOpen) {
            return entryId
          }
          return current === entryId ? null : current
        })
      }

      element.addEventListener('update', onUpdate)
      return () => {
        element.removeEventListener('update', onUpdate)
      }
    })

    return () => {
      cleanup.forEach((dispose) => {
        dispose()
      })
    }
  }, [visibleEntries])

  const applyEntryReplace = (nextEntry: MemoryEntry) => {
    setEntries((previous) => previous.map((entry) => (entry.id === nextEntry.id ? nextEntry : entry)))
  }

  const removeEntry = (entryId: string) => {
    setEntries((previous) => previous.filter((entry) => entry.id !== entryId))
    if (openEntryId === entryId) {
      setOpenEntryId(null)
    }
    if (editingEntryId === entryId) {
      setEditingEntryId(null)
      setEditDraft(null)
    }
    setDeleteConfirmEntryId((current) => (current === entryId ? null : current))
  }

  const clearEntryErrors = (entryId: string) => {
    setMutationErrorByEntryId((previous) => {
      if (!previous[entryId]) {
        return previous
      }
      const next = { ...previous }
      delete next[entryId]
      return next
    })
    setValidationMessages([])
    setGlobalMutationMessage(null)
  }

  const setEntryError = (entryId: string, message: string) => {
    setMutationErrorByEntryId((previous) => ({ ...previous, [entryId]: message }))
  }

  const handleMutationFailure = async (
    entry: MemoryEntry,
    caught: unknown,
  ): Promise<void> => {
    const mutationError = caught instanceof MemoryMutationError ? caught : null
    const apiError = mutationError?.apiError ?? null
    const parsedValidationMessages = mutationError?.validationMessages ?? []

    if (apiError?.status === 409) {
      setEntryError(entry.id, 'Entry was modified — refreshing')
      void refetch()
      return
    }

    if (apiError?.status === 404) {
      removeEntry(entry.id)
      setGlobalMutationMessage('Entry no longer exists')
      return
    }

    if (apiError?.status === 422 && parsedValidationMessages.length > 0) {
      setValidationMessages(parsedValidationMessages)
      return
    }

    setEntryError(entry.id, apiError?.message ?? 'Memory mutation failed')
  }

  const handleApprove = async (entry: MemoryEntry): Promise<void> => {
    clearEntryErrors(entry.id)
    try {
      const payload = await approveMemory(entry.id, entry.updated_at)
      if (payload.entry) {
        applyEntryReplace(payload.entry)
        emitPendingCountDelta(entry, payload.entry)
      }
      void refetch()
    } catch (caught) {
      await handleMutationFailure(entry, caught)
    }
  }

  const handleDelete = async (entry: MemoryEntry): Promise<void> => {
    clearEntryErrors(entry.id)
    try {
      await deleteMemory(entry.id, entry.updated_at)

      if (entry.state === 'pending') {
        removeEntry(entry.id)
        emitPendingCountDelta(entry, null)
      } else {
        const deletedEntry = { ...entry, state: 'deleted' as const }
        applyEntryReplace(deletedEntry)
        emitPendingCountDelta(entry, deletedEntry)
      }
      setDeleteConfirmEntryId(null)
      void refetch()
    } catch (caught) {
      await handleMutationFailure(entry, caught)
    }
  }

  const startEdit = (entry: MemoryEntry) => {
    clearEntryErrors(entry.id)
    setEditingEntryId(entry.id)
    setEditDraft(makeInitialDraft(entry))
    setNewCategory('')
    setNewScopeAgent('')
  }

  const cancelEdit = () => {
    setEditingEntryId(null)
    setEditDraft(null)
    setNewCategory('')
    setNewScopeAgent('')
    setValidationMessages([])
  }

  const addDraftListValues = (field: 'categories' | 'scope_agents', rawValue: string) => {
    const additions = splitCSV(rawValue)
    if (additions.length === 0) {
      return
    }

    setEditDraft((previous) => previous
      ? { ...previous, [field]: mergeListValues(previous[field], additions) }
      : previous)

    if (field === 'categories') {
      setNewCategory('')
    } else {
      setNewScopeAgent('')
    }
  }

  const removeDraftListValue = (field: 'categories' | 'scope_agents', value: string) => {
    setEditDraft((previous) => previous
      ? { ...previous, [field]: previous[field].filter((item) => item !== value) }
      : previous)
  }

  const handleEditSave = async (entry: MemoryEntry): Promise<void> => {
    if (!editDraft) {
      return
    }

    clearEntryErrors(entry.id)
    setValidationMessages([])

    const previousState = entry.state
    try {
      const draftForSave = {
        ...editDraft,
        categories: mergeListValues(editDraft.categories, splitCSV(newCategory)),
        scope_agents: mergeListValues(editDraft.scope_agents, splitCSV(newScopeAgent)),
      }
      const payload = await editMemory(entry.id, draftForSave)
      if (payload.entry) {
        applyEntryReplace(payload.entry)
        emitPendingCountDelta(entry, payload.entry)
        const promoted = previousState === 'pending' && payload.entry.state === 'curated'
        setPromotionMessageByEntryId((previous) => {
          if (!promoted) {
            const next = { ...previous }
            delete next[entry.id]
            return next
          }
          return {
            ...previous,
            [entry.id]: 'Promoted to curated — scope agents assigned',
          }
        })
      }
      setEditingEntryId(null)
      setEditDraft(null)
      setNewCategory('')
      setNewScopeAgent('')
      void refetch()
    } catch (caught) {
      await handleMutationFailure(entry, caught)
    }
  }

  const resetFilters = () => {
    setFilter(INITIAL_FILTER)
  }

  return (
    <section data-testid="memory-tab" className="relative flex h-full min-h-0 w-full flex-col overflow-hidden rounded-lg bg-canvas shadow-sm" aria-labelledby="memory-title">
      <WorkspaceHeader
        title="Memory"
        titleId="memory-title"
        summaryLabel="Memory summary"
        summary={(
          <>
            {memoryCountMetric}
            {parseErrors > 0 ? <WorkspaceHeaderPill tone="error">{parseErrors} unreadable</WorkspaceHeaderPill> : null}
          </>
        )}
      />

      <div className="flex min-h-0 flex-1 flex-col gap-static-md px-static-sm py-static-md sm:p-static-md">
      <div
        className="grid gap-static-xs rounded-md border border-contrast-low bg-canvas px-static-xs py-static-xs sm:grid-cols-2 sm:p-static-xs lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.4fr)]"
        data-testid="memory-filter-panel"
      >
        <PMultiSelect
          name="state-filter"
          label="State"
          compact
          className="block w-full min-w-0 max-w-full"
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
          compact
          className="block w-full min-w-0 max-w-full"
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
          compact
          className="block w-full min-w-0 max-w-full"
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
          compact
          className="block w-full min-w-0 max-w-full"
          value={filter.text}
          ref={(element) => {
            searchFilterRef.current = element as unknown as HTMLElement | null
          }}
        />
      </div>

      {!hasFetched && isFetching ? <div data-testid="memory-loading" role="status">Collecting memory entries...</div> : null}

      {parseErrors > 0 ? (
        <p data-testid="parse-errors-warning" className="rounded-lg border border-warning bg-warning-low p-static-sm text-primary">{parseErrors} entries couldn't be read</p>
      ) : null}

      {globalMutationMessage ? <p className="rounded-lg border border-success bg-success-low p-static-sm text-primary">{globalMutationMessage}</p> : null}

      {!hasEntries && hasFetched && !isFetching ? <p className="rounded-lg border border-contrast-low bg-canvas p-static-lg text-center">No memory entries yet</p> : null}

      {hasEntries && !hasVisibleEntries ? (
        <div className="rounded-lg border border-contrast-low bg-canvas p-static-md text-center">
          <p>No entries match your filters</p>
          <PButton data-testid="clear-filters" variant="secondary" compact onClick={resetFilters}>
            Clear filters
          </PButton>
        </div>
      ) : null}

      {hasVisibleEntries ? (
        <div data-testid="memory-list-scroll-shell" className="relative min-h-0 flex-1 overflow-hidden">
          <ul ref={memoryListRef} onScroll={updateMemoryListScrollCue} className="m-0 flex h-full min-h-0 list-none flex-col gap-static-sm overflow-x-hidden overflow-y-auto p-0 pb-static-lg pr-static-xs">
            {visibleEntries.map((entry) => (
              <li key={entry.id} data-testid="memory-entry" className="rounded-lg border border-contrast-low bg-canvas px-static-sm shadow-sm">
                <p-accordion
                  className="block"
                  open={openEntryId === entry.id ? true : undefined}
                  ref={(element) => {
                    if (element) {
                      accordionRefs.current[entry.id] = element as unknown as HTMLElement
                      return
                    }
                    delete accordionRefs.current[entry.id]
                  }}
                >
                  <div slot="summary" className="grid min-w-0 gap-static-sm py-static-sm lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
                  <div className="min-w-0">
                    <strong data-testid="memory-entry-title" className="block truncate text-base text-primary">{entry.title}</strong>
                    <div className="mt-1 flex min-w-0 flex-wrap items-center gap-x-static-sm gap-y-static-xs">
                      <span data-testid="memory-entry-agents" className="text-sm text-contrast-high">
                        {formatScopeAgents(entry.scope_agents)}
                      </span>
                      <span data-testid="memory-entry-category-group" className="flex min-w-0 flex-wrap items-center gap-static-xs">
                        {entry.categories.map((category) => (
                          <PTag key={`${entry.id}-${category}`} compact data-testid="memory-entry-category" variant="secondary">
                            {category}
                          </PTag>
                        ))}
                      </span>
                    </div>
                  </div>
                  <div data-testid="memory-entry-signal-group" className="flex min-w-0 flex-wrap items-center gap-static-xs text-xs lg:justify-end lg:border-l lg:border-contrast-low lg:pl-static-sm">
                    <PTag compact data-testid="memory-entry-confidence" variant="secondary" aria-label={`Confidence: ${formatConfidence(entry.confidence)}`}>
                      {formatConfidence(entry.confidence)}
                    </PTag>
                    <PTag
                      compact
                      data-testid="memory-entry-state"
                      variant={STATE_VARIANTS[entry.state]}
                      ref={syncTagVariantAttr(STATE_VARIANTS[entry.state])}
                      aria-label={`State: ${entry.state}`}
                    >
                      {entry.state}
                    </PTag>
                  </div>
                </div>

                {openEntryId === entry.id ? (
                  <div data-testid="memory-accordion-detail" className="grid gap-static-md border-t border-contrast-low pb-static-md pt-static-md">
                    <div data-testid="memory-content-panel" className="rounded-md border border-contrast-low bg-surface p-static-md text-base leading-relaxed text-primary shadow-sm">
                      <MarkdownPreview className="text-base" rehypePlugins={[[rehypeSanitize, MEMORY_SANITIZE_SCHEMA]]}>
                        {entry.content}
                      </MarkdownPreview>
                    </div>
                    <section data-testid="memory-metadata-section" className="rounded-lg border border-contrast-low bg-canvas p-static-sm">
                      <div className="mb-static-xs flex min-w-0 items-center justify-between gap-static-sm">
                        <PHeading size="small" tag="h3">Metadata</PHeading>
                      </div>
                      <dl data-testid="memory-metadata-grid" className="grid gap-x-static-lg gap-y-static-xs text-sm text-primary sm:grid-cols-2 lg:grid-cols-3">
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">ID</dt><dd className="m-0 break-words text-primary">{entry.id}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Source agent</dt><dd className="m-0 break-words text-primary">{entry.source_agent}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Scope agents</dt><dd className="m-0 break-words text-primary">{formatScopeAgents(entry.scope_agents)}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Categories</dt><dd className="m-0 break-words text-primary">{entry.categories.join(', ')}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Confidence</dt><dd className="m-0 break-words text-primary">{formatConfidence(entry.confidence)}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">State</dt><dd className="m-0 break-words text-primary">{entry.state}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Created</dt><dd className="m-0 break-words text-primary">{entry.created_at}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Updated</dt><dd className="m-0 break-words text-primary">{entry.updated_at}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Approved</dt><dd className="m-0 break-words text-primary">{entry.approved_at ?? '-'}</dd></div>
                      </dl>
                    </section>

                    {entry.state === 'approved' ? <p className="text-sm text-primary">Editing will require re-approval</p> : null}

                    {mutationErrorByEntryId[entry.id] ? (
                      <p data-testid="memory-occ-banner" className="rounded-lg border border-warning bg-warning-low p-static-sm text-primary">{mutationErrorByEntryId[entry.id]}</p>
                    ) : null}

                    {promotionMessageByEntryId[entry.id] ? <p className="rounded-lg border border-success bg-success-low p-static-sm text-primary">{promotionMessageByEntryId[entry.id]}</p> : null}

                    <div data-testid="memory-detail-actions" className="flex flex-wrap items-center gap-static-xs">
                      {entry.state === 'curated' ? (
                        <PButton type="button" data-testid="memory-approve-btn" compact onClick={() => void handleApprove(entry)}>
                          Approve
                        </PButton>
                      ) : null}

                      {entry.state !== 'deleted' ? (
                        <>
                          <PButton type="button" data-testid="memory-edit-btn" compact variant="secondary" onClick={() => startEdit(entry)}>
                            Edit
                          </PButton>
                          <PButton
                            type="button"
                            data-testid="memory-delete-btn"
                            compact
                            variant="secondary"
                            onClick={() => setDeleteConfirmEntryId(entry.id)}
                          >
                            Delete
                          </PButton>
                        </>
                      ) : null}
                    </div>

                    {editingEntryId === entry.id && editDraft ? (
                      <div data-testid="memory-edit-form" className="grid gap-static-md rounded-lg border border-contrast-low bg-canvas p-static-md">
                        <div
                          ref={memoryEditActionsRef}
                          data-testid="memory-edit-actions"
                          className="sticky top-0 z-20 -mx-static-md -mt-static-md flex min-w-0 flex-wrap items-center justify-between gap-static-sm border-b border-contrast-low bg-canvas px-static-md py-static-sm shadow-lg"
                        >
                          <div className="flex min-w-0 flex-wrap items-center gap-static-sm">
                            <span className="text-sm font-semibold text-primary">Edit memory</span>
                          </div>
                          <div className="flex min-w-0 flex-wrap items-center gap-static-xs">
                            <PButton type="button" data-testid="memory-edit-cancel-btn" compact variant="secondary" onClick={cancelEdit}>
                              Cancel
                            </PButton>
                            <PButton type="button" data-testid="memory-edit-save-btn" compact onClick={() => void handleEditSave(entry)}>
                              Save
                            </PButton>
                          </div>
                        </div>
                        <div className="grid gap-static-sm xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_minmax(0,0.7fr)_minmax(0,1fr)]">
                          <PInputText
                            name="edit-title"
                            data-testid="edit-title"
                            label="Title"
                            compact
                            value={editDraft.title}
                            onChange={(event) => {
                              const value = readStringValue(event)
                              setEditDraft((previous) =>
                                previous ? { ...previous, title: value } : previous,
                              )
                            }}
                            onInput={(event) => {
                              const value = readStringValue(event)
                              setEditDraft((previous) =>
                                previous ? { ...previous, title: value } : previous,
                              )
                            }}
                          />
                          <PInputNumber
                            name="edit-confidence"
                            label="Confidence"
                            compact
                            controls
                            step={0.01}
                            min={0}
                            max={1}
                            value={String(editDraft.confidence)}
                            onChange={(event) => {
                              const value = Number.parseFloat(readStringValue(event))
                              setEditDraft((previous) =>
                                previous
                                  ? {
                                      ...previous,
                                      confidence: Number.isFinite(value) ? value : previous.confidence,
                                    }
                                  : previous,
                              )
                            }}
                            onInput={(event) => {
                              const value = Number.parseFloat(readStringValue(event))
                              setEditDraft((previous) =>
                                previous
                                  ? {
                                      ...previous,
                                      confidence: Number.isFinite(value) ? value : previous.confidence,
                                    }
                                  : previous,
                              )
                            }}
                          />
                        </div>
                        <div className="grid gap-static-sm md:grid-cols-2">
                          <section className="grid min-w-0 gap-static-xs" data-testid="memory-category-editor">
                            <div className="grid min-w-0 gap-static-xs sm:grid-cols-[minmax(0,1fr)_auto]">
                              <PInputText
                                name="new-memory-category"
                                label="Categories"
                                placeholder="Add category"
                                compact
                                className="min-w-0"
                                value={newCategory}
                                onChange={(event) => setNewCategory(readStringValue(event))}
                                onInput={(event) => setNewCategory(readStringValue(event))}
                                onKeyDown={(event) => {
                                  if (event.key === 'Enter') {
                                    event.preventDefault()
                                    addDraftListValues('categories', newCategory)
                                  }
                                }}
                              />
                              <PButton
                                type="button"
                                data-testid="memory-add-category-button"
                                variant="secondary"
                                icon="plus"
                                className="min-w-0 self-end"
                                compact
                                disabled={newCategory.trim().length === 0}
                                onClick={() => addDraftListValues('categories', newCategory)}
                              >
                                Add
                              </PButton>
                            </div>
                            {editDraft.categories.length > 0 ? (
                              <div className="flex min-w-0 flex-wrap items-center gap-static-xs" data-testid="memory-category-chip-list">
                                {editDraft.categories.map((category) => (
                                  <PTagDismissible
                                    key={category}
                                    data-testid="memory-category-chip"
                                    data-category={category}
                                    compact
                                    label={category}
                                    aria={{ 'aria-label': `Remove category ${category}` }}
                                    onClick={() => removeDraftListValue('categories', category)}
                                  />
                                ))}
                              </div>
                            ) : (
                              <span data-testid="memory-no-categories" className="text-sm text-contrast-high">No categories</span>
                            )}
                          </section>

                          <section className="grid min-w-0 gap-static-xs" data-testid="memory-scope-agent-editor">
                            <div className="grid min-w-0 gap-static-xs sm:grid-cols-[minmax(0,1fr)_auto]">
                              <PInputText
                                name="new-memory-scope-agent"
                                label="Scope agents"
                                placeholder="Add scope agent"
                                compact
                                className="min-w-0"
                                value={newScopeAgent}
                                onChange={(event) => setNewScopeAgent(readStringValue(event))}
                                onInput={(event) => setNewScopeAgent(readStringValue(event))}
                                onKeyDown={(event) => {
                                  if (event.key === 'Enter') {
                                    event.preventDefault()
                                    addDraftListValues('scope_agents', newScopeAgent)
                                  }
                                }}
                              />
                              <PButton
                                type="button"
                                data-testid="memory-add-scope-agent-button"
                                variant="secondary"
                                icon="plus"
                                className="min-w-0 self-end"
                                compact
                                disabled={newScopeAgent.trim().length === 0}
                                onClick={() => addDraftListValues('scope_agents', newScopeAgent)}
                              >
                                Add
                              </PButton>
                            </div>
                            {editDraft.scope_agents.length > 0 ? (
                              <div className="flex min-w-0 flex-wrap items-center gap-static-xs" data-testid="memory-scope-agent-chip-list">
                                {editDraft.scope_agents.map((agent) => (
                                  <PTagDismissible
                                    key={agent}
                                    data-testid="memory-scope-agent-chip"
                                    data-scope-agent={agent}
                                    compact
                                    label={agent}
                                    aria={{ 'aria-label': `Remove scope agent ${agent}` }}
                                    onClick={() => removeDraftListValue('scope_agents', agent)}
                                  />
                                ))}
                              </div>
                            ) : (
                              <span data-testid="memory-no-scope-agents" className="text-sm text-contrast-high">No scope agents</span>
                            )}
                          </section>
                        </div>
                        <PTextarea
                          name="edit-content"
                          label="Content"
                          value={editDraft.content}
                          counter
                          maxLength={MEMORY_CONTENT_LIMIT}
                          onChange={(event) => {
                            const value = readStringValue(event).slice(0, MEMORY_CONTENT_LIMIT)
                            setEditDraft((previous) =>
                              previous ? { ...previous, content: value } : previous,
                            )
                          }}
                          onInput={(event) => {
                            const value = readStringValue(event).slice(0, MEMORY_CONTENT_LIMIT)
                            setEditDraft((previous) =>
                              previous ? { ...previous, content: value } : previous,
                            )
                          }}
                        />
                        {validationMessages.length > 0 ? (
                          <ul data-testid="memory-validation-errors" className="m-0 grid list-none gap-static-xs rounded-lg border border-warning bg-warning-low p-static-sm text-sm text-primary">
                            {validationMessages.map(({ field, message }) => (
                              <li
                                key={`${field}:${message}`}
                                data-testid="memory-validation-message"
                                data-field={field}
                              >
                                <strong>{field}</strong>: {message}
                              </li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </p-accordion>
            </li>
          ))}
        </ul>
        {memoryListCanScrollDown && editingEntryId === null ? (
          <div
            aria-hidden="true"
            data-testid="memory-list-scroll-cue"
            className="pointer-events-none absolute inset-x-0 bottom-0 h-10 [background:linear-gradient(to_bottom,transparent,var(--p-color-canvas))]"
          />
        ) : null}
        </div>
      ) : null}

      {deleteConfirmEntry ? (
        <PModal
          data-testid="memory-delete-confirm-dialog"
          open
          tabIndex={-1}
          onDismiss={() => setDeleteConfirmEntryId(null)}
          disableBackdropClick
          dismissButton={false}
          aria-label="Confirm memory deletion"
        >
          <div className="grid max-w-[520px] gap-static-md">
            <div className="grid gap-static-xs rounded-lg bg-frosted-soft p-static-md text-primary">
              <span className="text-xs font-semibold uppercase text-primary">Delete memory</span>
              <p className="m-0 text-sm leading-normal">
                {deleteConfirmEntry.state === 'pending'
                  ? 'This is a permanent hard-delete and cannot be undone.'
                  : 'This will soft-delete the memory and mark it as deleted.'}
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-static-xs">
              <PButton
                type="button"
                data-testid="memory-delete-cancel-btn"
                compact
                variant="secondary"
                onClick={() => setDeleteConfirmEntryId(null)}
              >
                Cancel
              </PButton>
              <PButton
                type="button"
                data-testid="memory-delete-confirm-btn"
                compact
                onClick={() => void handleDelete(deleteConfirmEntry)}
              >
                Confirm delete
              </PButton>
            </div>
          </div>
        </PModal>
      ) : null}
      </div>
    </section>
  )
}

export default MemoryTab
