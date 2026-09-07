import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  PButton,
  PButtonPure,
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
import rehypeSanitize from 'rehype-sanitize'
import { getResponseErrorMessage } from '../api/errorMessage'
import {
  approveMemory,
  deleteMemory,
  editMemory,
  MemoryMutationError,
  resolveMemory,
  type MemoriesResponse,
  type MemoryEditPayload,
  type MemoryEntry,
  type MemoryState,
  type ValidationMessage,
} from '../api/memories'
import MarkdownPreview from '../components/MarkdownPreview'
import { WorkspaceHeader, WorkspaceHeaderMetric, WorkspaceHeaderPill } from '../components/WorkspaceHeader'
import { useMemoryPurgeFlow } from '../hooks/useCleanupFlow'
import { MEMORY_PENDING_COUNT_EVENT } from '../hooks/usePendingMemoryCount'
import { usePollingFetch } from '../hooks/usePollingFetch'

type AgentFilter =
  | { mode: 'any' }
  | { mode: 'all' }
  | { mode: 'unscoped' }
  | { mode: 'named'; agent: string }

interface MemoryFilterState {
  states: MemoryState[]
  categories: string[]
  agent: AgentFilter
  text: string
}

type MemoryConflictStatus = 'refreshing' | 'ready' | 'error'

interface MemoryConflictState {
  entryId: string
  baseEntry: MemoryEntry
  status: MemoryConflictStatus
  message: string
  currentEntry: MemoryEntry | null
  refreshError: string | null
}

const DEFAULT_STATES: MemoryState[] = ['pending', 'curated', 'approved', 'contested', 'disputed', 'stale']
const ALL_AGENTS_SCOPE = '*'
const AGENT_FILTER_VALUES = {
  any: 'mode:any',
  all: 'mode:all',
  unscoped: 'mode:unscoped',
  namedPrefix: 'agent:',
} as const
const STATE_PRIORITY: Record<MemoryState, number> = {
  pending: 0,
  curated: 1,
  approved: 2,
  contested: 3,
  disputed: 4,
  stale: 5,
  deleted: 6,
}
const STATE_BORDERS: Record<MemoryState, string> = {
  pending: 'border-l-warning',
  curated: 'border-l-info',
  approved: 'border-l-success',
  contested: 'border-l-warning',
  disputed: 'border-l-warning',
  stale: 'border-l-error',
  deleted: 'border-l-error',
}

const INITIAL_FILTER: MemoryFilterState = {
  states: [...DEFAULT_STATES],
  categories: [],
  agent: { mode: 'any' },
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
    const scoreDelta = compareDescending(normalizeConfidence(left.score), normalizeConfidence(right.score))
    if (scoreDelta !== 0) {
      return scoreDelta
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

function formatScopeAgents(scopeAgents: string[]): string {
  if (scopeAgents.length === 0) {
    return 'Unscoped'
  }
  if (scopeAgents.includes(ALL_AGENTS_SCOPE)) {
    return 'All agents'
  }
  return scopeAgents.join(', ')
}

function agentFilterValue(filter: AgentFilter): string {
  if (filter.mode === 'named') {
    return `${AGENT_FILTER_VALUES.namedPrefix}${encodeURIComponent(filter.agent)}`
  }
  return AGENT_FILTER_VALUES[filter.mode]
}

function parseAgentFilterValue(value: string): AgentFilter {
  if (value === AGENT_FILTER_VALUES.any) {
    return { mode: 'any' }
  }
  if (value === AGENT_FILTER_VALUES.all) {
    return { mode: 'all' }
  }
  if (value === AGENT_FILTER_VALUES.unscoped) {
    return { mode: 'unscoped' }
  }
  if (value.startsWith(AGENT_FILTER_VALUES.namedPrefix)) {
    try {
      return { mode: 'named', agent: decodeURIComponent(value.slice(AGENT_FILTER_VALUES.namedPrefix.length)) }
    } catch {
      return { mode: 'any' }
    }
  }
  return { mode: 'any' }
}

function toFilterableScopeAgents(scopeAgents: string[]): string[] {
  return scopeAgents.filter((agent) => agent !== ALL_AGENTS_SCOPE)
}

function matchesAgent(entry: MemoryEntry, filter: AgentFilter): boolean {
  if (filter.mode === 'any') {
    return true
  }
  if (filter.mode === 'all') {
    return entry.scope_agents.includes(ALL_AGENTS_SCOPE)
  }
  if (filter.mode === 'unscoped') {
    return entry.scope_agents.length === 0
  }
  return entry.scope_agents.includes(ALL_AGENTS_SCOPE) || entry.scope_agents.includes(filter.agent)
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

async function parseMemoriesResponse(response: Response): Promise<MemoriesResponse> {
  const payload = (await response.json()) as Partial<MemoriesResponse>
  if (!Array.isArray(payload.entries) || typeof payload.parse_errors !== 'number') {
    throw new Error('Malformed memory response')
  }
  return payload as MemoriesResponse
}

function MemoryTab() {
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [parseErrors, setParseErrors] = useState(0)
  const [loadError, setLoadError] = useState<Error | null>(null)
  const [filter, setFilter] = useState<MemoryFilterState>(INITIAL_FILTER)
  const [openEntryId, setOpenEntryId] = useState<string | null>(null)
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<MemoryEditPayload | null>(null)
  const [newCategory, setNewCategory] = useState('')
  const [newScopeAgent, setNewScopeAgent] = useState('')
  const [deleteConfirmEntryId, setDeleteConfirmEntryId] = useState<string | null>(null)
  const [mutationErrorByEntryId, setMutationErrorByEntryId] = useState<Record<string, string>>({})
  const [memoryConflict, setMemoryConflict] = useState<MemoryConflictState | null>(null)
  const [mutationPendingByEntryId, setMutationPendingByEntryId] = useState<Record<string, boolean>>({})
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
  const conflictPanelRef = useRef<HTMLElement | null>(null)
  const restoreConflictFocusRef = useRef<string | null>(null)
  const pendingMutationIdsRef = useRef(new Set<string>())

  const { isFetching, hasFetched, refetch } = usePollingFetch<MemoriesResponse>('/api/memories', {
    paused: true,
    parse: parseMemoriesResponse,
    onSuccess: async (payload) => {
      setLoadError(null)
      setEntries(payload.entries)
      setParseErrors(payload.parse_errors)
    },
    onError: async (error) => {
      setLoadError(error)
    },
  })

  const refreshConflictEntry = async (entryId: string): Promise<void> => {
    try {
      const response = await fetch('/api/memories')
      if (!response.ok) {
        const message = await getResponseErrorMessage(
          response,
          `Memory refresh failed with status ${response.status}`,
        )
        throw new Error(message)
      }

      const payload = await parseMemoriesResponse(response)
      setLoadError(null)
      setEntries(payload.entries)
      setParseErrors(payload.parse_errors)
      setMemoryConflict((current) => {
        if (!current || current.entryId !== entryId) {
          return current
        }

        const currentEntry = payload.entries.find((entry) => entry.id === entryId) ?? null
        if (!currentEntry) {
          return {
            ...current,
            status: 'error',
            currentEntry: null,
            refreshError: 'The memory entry no longer exists on the server.',
          }
        }

        return {
          ...current,
          status: 'ready',
          currentEntry,
          refreshError: null,
        }
      })
    } catch (caught) {
      const error = caught instanceof Error ? caught : new Error('Memory refresh failed')
      setLoadError(error)
      setMemoryConflict((current) => current && current.entryId === entryId ? {
        ...current,
        status: 'error',
        refreshError: error.message,
      } : current)
    }
  }

  const purgeFlow = useMemoryPurgeFlow({ onSuccess: () => void refetch() })

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
    if (!memoryConflict || memoryConflict.status === 'refreshing') {
      return
    }
    conflictPanelRef.current?.focus()
  }, [memoryConflict?.entryId, memoryConflict?.status])

  useEffect(() => {
    const entryId = restoreConflictFocusRef.current
    if (memoryConflict || !entryId || editingEntryId !== entryId) {
      return
    }

    restoreConflictFocusRef.current = null
    memoryEditActionsRef.current
      ?.querySelector<HTMLElement>('[data-testid="memory-edit-save-btn"]')
      ?.focus()
  }, [editingEntryId, memoryConflict])

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
      setFilter((previous) => ({ ...previous, agent: parseAgentFilterValue(readStringValue(event)) }))
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

  const activeConflictEntry = useMemo(() => {
    if (!memoryConflict || editingEntryId !== memoryConflict.entryId) {
      return null
    }
    return entries.find((entry) => entry.id === memoryConflict.entryId) ?? memoryConflict.baseEntry
  }, [editingEntryId, entries, memoryConflict])

  const visibleEntries = useMemo(() => {
    const loweredSearch = filter.text.trim().toLowerCase()

    const filteredEntries = sortEntries(entries).filter((entry) => {
      const matchesState = filter.states.length === 0 || filter.states.includes(entry.state)
      const matchesCategory =
        filter.categories.length === 0 || filter.categories.every((category) => entry.categories.includes(category))
      const matchesAgentFilter = matchesAgent(entry, filter.agent)
      const matchesTextSearch = includesText(entry, loweredSearch)

      return matchesState && matchesCategory && matchesAgentFilter && matchesTextSearch
    })
    if (!activeConflictEntry || filteredEntries.some((entry) => entry.id === activeConflictEntry.id)) {
      return filteredEntries
    }
    return sortEntries([...filteredEntries, activeConflictEntry])
  }, [activeConflictEntry, entries, filter])

  const totalEntryCount = entries.length + (activeConflictEntry && !entries.some((entry) => entry.id === activeConflictEntry.id) ? 1 : 0)
  const hasEntries = totalEntryCount > 0
  const hasVisibleEntries = visibleEntries.length > 0
  const deletedCount = entries.filter((entry) => entry.state === 'deleted').length
  const memoryCountMetric = visibleEntries.length === totalEntryCount
    ? <WorkspaceHeaderMetric value={totalEntryCount} label={totalEntryCount === 1 ? 'entry' : 'entries'} />
    : <WorkspaceHeaderMetric value={`${visibleEntries.length} of ${totalEntryCount}`} label="shown" />

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
    setMemoryConflict((current) => current?.entryId === entryId ? null : current)
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

  const beginMutation = (entryId: string): boolean => {
    if (pendingMutationIdsRef.current.has(entryId)) {
      return false
    }
    pendingMutationIdsRef.current.add(entryId)
    setMutationPendingByEntryId((previous) => ({ ...previous, [entryId]: true }))
    return true
  }

  const finishMutation = (entryId: string): void => {
    pendingMutationIdsRef.current.delete(entryId)
    setMutationPendingByEntryId((previous) => {
      if (!previous[entryId]) {
        return previous
      }
      const next = { ...previous }
      delete next[entryId]
      return next
    })
  }

  const isMutationPending = (entryId: string): boolean => Boolean(mutationPendingByEntryId[entryId])

  const retryConflictRefresh = (): void => {
    const entryId = memoryConflict?.entryId
    if (!entryId) {
      return
    }
    setMemoryConflict((current) => current ? {
      ...current,
      status: 'refreshing',
      refreshError: null,
    } : current)
    void refreshConflictEntry(entryId)
  }

  const reloadConflictEntry = (entryId: string): void => {
    if (memoryConflict?.entryId !== entryId || !memoryConflict.currentEntry) {
      return
    }
    restoreConflictFocusRef.current = entryId
    setEditDraft(makeInitialDraft(memoryConflict.currentEntry))
    clearEntryErrors(entryId)
    setMemoryConflict(null)
  }

  const reapplyConflictDraft = (entryId: string): void => {
    if (memoryConflict?.entryId !== entryId || !memoryConflict.currentEntry) {
      return
    }
    restoreConflictFocusRef.current = entryId
    const currentUpdatedAt = memoryConflict.currentEntry.updated_at
    setEditDraft((previous) => previous ? { ...previous, expected_updated_at: currentUpdatedAt } : previous)
    clearEntryErrors(entryId)
    setMemoryConflict(null)
  }

  const handleMutationFailure = async (
    entry: MemoryEntry,
    caught: unknown,
  ): Promise<void> => {
    const mutationError = caught instanceof MemoryMutationError ? caught : null
    const apiError = mutationError?.apiError ?? null
    const parsedValidationMessages = mutationError?.validationMessages ?? []

    if (apiError?.status === 409) {
      if (editingEntryId === entry.id && editDraft) {
        setMemoryConflict({
          entryId: entry.id,
          baseEntry: entry,
          status: 'refreshing',
          message: 'Entry was modified on the server. Review the latest version before saving again.',
          currentEntry: null,
          refreshError: null,
        })
        void refreshConflictEntry(entry.id)
      } else {
        setEntryError(entry.id, 'Entry was modified — refreshing')
        void refetch()
      }
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
    if (!beginMutation(entry.id)) {
      return
    }
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
    } finally {
      finishMutation(entry.id)
    }
  }

  const handleResolve = async (entry: MemoryEntry): Promise<void> => {
    if (!beginMutation(entry.id)) {
      return
    }
    clearEntryErrors(entry.id)
    try {
      const payload = await resolveMemory(entry.id, entry.updated_at)
      if (payload.entry) {
        applyEntryReplace(payload.entry)
      }
      void refetch()
    } catch (caught) {
      await handleMutationFailure(entry, caught)
    } finally {
      finishMutation(entry.id)
    }
  }

  const handleDelete = async (entry: MemoryEntry): Promise<void> => {
    if (!beginMutation(entry.id)) {
      return
    }
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
    } finally {
      finishMutation(entry.id)
    }
  }

  const startEdit = (entry: MemoryEntry) => {
    clearEntryErrors(entry.id)
    setEditingEntryId(entry.id)
    setEditDraft(makeInitialDraft(entry))
    setMemoryConflict(null)
    setNewCategory('')
    setNewScopeAgent('')
  }

  const cancelEdit = () => {
    setEditingEntryId(null)
    setEditDraft(null)
    setMemoryConflict(null)
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
    if (!editDraft || memoryConflict?.entryId === entry.id || !beginMutation(entry.id)) {
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
    } finally {
      finishMutation(entry.id)
    }
  }

  const resetFilters = () => {
    setFilter(INITIAL_FILTER)
  }

  return (
    <section data-testid="memory-tab" className="relative flex h-full min-h-0 w-full flex-col overflow-hidden bg-canvas" aria-labelledby="memory-title">
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

      {purgeFlow.receipt ? (
        <div className="mx-static-lg mt-static-md flex flex-wrap items-center justify-between gap-static-sm rounded-lg border border-success bg-success-low p-static-sm text-sm text-primary" data-testid="memory-purge-receipt">
          <span>
            Purged {purgeFlow.receipt.purged}; skipped {purgeFlow.receipt.skipped}; failed {purgeFlow.receipt.failed}
          </span>
          <PButton type="button" compact variant="secondary" data-testid="memory-purge-receipt-dismiss" onClick={purgeFlow.cancelPurge}>
            Dismiss
          </PButton>
        </div>
      ) : null}

      <div className="flex min-h-0 flex-1 flex-col gap-static-lg px-static-lg py-static-lg">
      <div
        className="grid gap-static-md rounded-md border border-contrast-low bg-surface p-static-md sm:grid-cols-2 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.4fr)]"
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
          <PMultiSelectOption value="contested">contested</PMultiSelectOption>
          <PMultiSelectOption value="disputed">disputed</PMultiSelectOption>
          <PMultiSelectOption value="stale">stale</PMultiSelectOption>
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
          value={agentFilterValue(filter.agent)}
          ref={(element) => {
            agentFilterRef.current = element as unknown as HTMLElement | null
          }}
        >
          <PSelectOption value={AGENT_FILTER_VALUES.any}>Any agent</PSelectOption>
          <PSelectOption value={AGENT_FILTER_VALUES.all}>All agents</PSelectOption>
          <PSelectOption value={AGENT_FILTER_VALUES.unscoped}>Unscoped</PSelectOption>
          {agentOptions.map((agent) => (
            <PSelectOption key={agent} value={agentFilterValue({ mode: 'named', agent })}>
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

      {/* Tombstone cleanup belongs with the entries it removes, so it rides the top edge of the
          entries region — not the page identity, and not the filter panel it deliberately ignores. */}
      {!hasFetched && isFetching ? <div data-testid="memory-loading" role="status">Collecting memory entries...</div> : null}

      {loadError ? (
        <div data-testid="memory-load-error" className="flex flex-wrap items-center justify-between gap-static-sm rounded-lg border border-error bg-error-low p-static-sm text-primary">
          <span role="alert">{entries.length > 0 ? `Memory entries may be stale: ${loadError.message}` : `Memory entries could not be loaded: ${loadError.message}`}</span>
          <PButton type="button" compact variant="secondary" data-testid="memory-retry" disabled={isFetching} aria-busy={isFetching} onClick={() => void refetch()}>
            Retry
          </PButton>
        </div>
      ) : null}

      {parseErrors > 0 ? (
        <p data-testid="parse-errors-warning" className="rounded-lg border border-warning bg-warning-low p-static-sm text-primary">{parseErrors} entries couldn't be read</p>
      ) : null}

      {globalMutationMessage ? <p className="rounded-lg border border-success bg-success-low p-static-sm text-primary">{globalMutationMessage}</p> : null}

      <section
        data-testid="memory-entries-region"
        aria-label="Memory entries"
        className="flex min-h-0 flex-1 flex-col gap-static-md"
      >
        <div
          data-testid="memory-entries-toolbar"
          className="flex min-w-0 flex-wrap items-center justify-end gap-static-sm border-b border-contrast-low pb-static-xs pr-static-sm"
        >
          <PButtonPure
            type="button"
            size="small"
            icon="delete"
            data-testid="memory-purge-open-button"
            disabled={deletedCount === 0}
            onClick={() => void purgeFlow.requestPreview()}
          >
            Purge deleted ({deletedCount})
          </PButtonPure>
        </div>

        {!hasEntries && hasFetched && !isFetching && !loadError ? (
          <section className="grid min-h-40 place-items-center border border-dashed border-contrast-low bg-canvas px-static-lg py-static-xl text-center" data-testid="memory-empty-state">
            <div className="grid max-w-[44rem] gap-static-xs">
              <PHeading tag="h2" size="small">No memory entries yet</PHeading>
              <p className="text-sm leading-relaxed text-contrast-medium">Entries saved to Memory will appear here for review and curation.</p>
            </div>
          </section>
        ) : null}

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
          <ul ref={memoryListRef} onScroll={updateMemoryListScrollCue} className="m-0 flex h-full min-h-0 list-none flex-col gap-static-md overflow-x-hidden overflow-y-auto p-0 pb-static-lg pr-static-sm">
            {visibleEntries.map((entry) => (
              <li key={entry.id} data-testid="memory-entry" className={`rounded-lg border border-l-4 border-contrast-low bg-canvas px-static-md shadow-sm ${STATE_BORDERS[entry.state]}`}>
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
                  <div slot="summary" className="grid min-w-0 gap-static-sm py-static-sm md:grid-cols-[minmax(0,1fr)_auto] md:items-start">
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
                  <div data-testid="memory-entry-signal-group" className="flex min-w-0 flex-wrap items-center gap-static-xs text-xs md:justify-end md:border-l md:border-contrast-low md:pl-static-sm">
                    <PTag compact data-testid="memory-entry-score" variant="secondary" aria-label={`Score: ${formatConfidence(entry.score)}`}>
                      {formatConfidence(entry.score)}
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
                        <PHeading size="sm" tag="h3">Metadata</PHeading>
                      </div>
                      <dl data-testid="memory-metadata-grid" className="grid gap-x-static-lg gap-y-static-xs text-sm text-primary sm:grid-cols-2 lg:grid-cols-3">
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">ID</dt><dd className="m-0 break-words text-primary">{entry.id}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Source agent</dt><dd className="m-0 break-words text-primary">{entry.source_agent}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Scope agents</dt><dd className="m-0 break-words text-primary">{formatScopeAgents(entry.scope_agents)}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Categories</dt><dd className="m-0 break-words text-primary">{entry.categories.join(', ')}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Confidence</dt><dd className="m-0 break-words text-primary">{formatConfidence(entry.confidence)}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">State</dt><dd data-testid="memory-entry-state" className="m-0 break-words text-primary">{entry.state}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Outstanding marks</dt><dd className="m-0 break-words text-primary">★ {entry.outstanding_count}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Score</dt><dd className="m-0 break-words text-primary">{formatConfidence(entry.score)}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Contested task</dt><dd className="m-0 break-words text-primary">
                          {entry.contested_by_task ?? '—'}
                        </dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Created</dt><dd className="m-0 break-words text-primary">{entry.created_at}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Updated</dt><dd className="m-0 break-words text-primary">{entry.updated_at}</dd></div>
                        <div className="min-w-0"><dt className="font-semibold text-contrast-high">Approved</dt><dd className="m-0 break-words text-primary">{entry.approved_at ?? '-'}</dd></div>
                      </dl>
                    </section>

                    {entry.state === 'approved' ? <p className="text-sm text-primary">Editing will require re-approval</p> : null}

                    {mutationErrorByEntryId[entry.id] ? (
                      <p data-testid="memory-occ-banner" className="rounded-lg border border-warning bg-warning-low p-static-sm text-primary">{mutationErrorByEntryId[entry.id]}</p>
                    ) : null}

                    {memoryConflict?.entryId === entry.id ? (
                      <section
                        data-testid="memory-conflict-panel"
                        ref={(element) => {
                          conflictPanelRef.current = element as unknown as HTMLElement | null
                        }}
                        role="region"
                        aria-labelledby={`memory-conflict-title-${entry.id}`}
                        tabIndex={-1}
                        className="grid gap-static-sm rounded-lg border border-warning bg-warning-low p-static-md text-primary"
                      >
                        <div className="grid gap-static-xs">
                          <h3 id={`memory-conflict-title-${entry.id}`} className="m-0 text-base font-semibold">This memory changed while you were editing.</h3>
                          <p className="m-0 text-sm">Your draft is preserved. Review the latest server version before saving again.</p>
                          <p className="m-0 break-words text-sm">{memoryConflict.message}</p>
                        </div>
                        <span className="sr-only" role="status" aria-live="polite">
                          {memoryConflict.status === 'refreshing'
                            ? 'Loading the latest server version.'
                            : memoryConflict.status === 'error'
                              ? memoryConflict.refreshError ?? 'The latest server version could not be loaded.'
                              : 'The latest server version is ready. Choose whether to discard the draft or reapply it.'}
                        </span>
                        {memoryConflict.status === 'refreshing' ? (
                          <p data-testid="memory-conflict-refreshing" className="m-0 text-sm">Loading the latest server version...</p>
                        ) : null}
                        {memoryConflict.status === 'error' ? (
                          <div className="flex min-w-0 flex-wrap items-center gap-static-xs">
                            <p data-testid="memory-conflict-refresh-error" className="m-0 min-w-0 flex-1 break-words text-sm">
                              {memoryConflict.refreshError ?? 'The latest server version could not be loaded.'}
                            </p>
                            <PButton type="button" data-testid="memory-conflict-retry" compact variant="secondary" onClick={retryConflictRefresh}>
                              Retry latest
                            </PButton>
                          </div>
                        ) : null}
                        {memoryConflict.status === 'ready' && memoryConflict.currentEntry ? (
                          <>
                            <dl className="grid min-w-0 gap-static-sm text-sm sm:grid-cols-2">
                              <div className="min-w-0">
                                <dt className="font-semibold">Latest server title</dt>
                                <dd data-testid="memory-conflict-current-title" className="m-0 break-words">{memoryConflict.currentEntry.title}</dd>
                              </div>
                              <div className="min-w-0">
                                <dt className="font-semibold">Your draft title</dt>
                                <dd data-testid="memory-conflict-draft-title" className="m-0 break-words">{editDraft?.title ?? ''}</dd>
                              </div>
                              <div className="min-w-0">
                                <dt className="font-semibold">Latest server content</dt>
                                <dd data-testid="memory-conflict-current-content" className="m-0 whitespace-pre-wrap break-words">{memoryConflict.currentEntry.content}</dd>
                              </div>
                              <div className="min-w-0">
                                <dt className="font-semibold">Your draft content</dt>
                                <dd data-testid="memory-conflict-draft-content" className="m-0 whitespace-pre-wrap break-words">{editDraft?.content ?? ''}</dd>
                              </div>
                            </dl>
                            <div className="flex min-w-0 flex-wrap items-center gap-static-xs">
                              <PButton
                                type="button"
                                data-testid="memory-conflict-reload"
                                compact
                                variant="secondary"
                                disabled={isMutationPending(entry.id)}
                                onClick={() => reloadConflictEntry(entry.id)}
                              >
                                Discard draft and load latest
                              </PButton>
                              <PButton
                                type="button"
                                data-testid="memory-conflict-reapply"
                                compact
                                disabled={isMutationPending(entry.id)}
                                onClick={() => reapplyConflictDraft(entry.id)}
                              >
                                Reapply draft
                              </PButton>
                            </div>
                          </>
                        ) : null}
                      </section>
                    ) : null}

                    {promotionMessageByEntryId[entry.id] ? <p className="rounded-lg border border-success bg-success-low p-static-sm text-primary">{promotionMessageByEntryId[entry.id]}</p> : null}

                    <div data-testid="memory-detail-actions" className="flex flex-wrap items-center gap-static-xs">
                      {entry.state === 'contested' || entry.state === 'disputed' || entry.state === 'stale' ? (
                        <PButton type="button" data-testid="memory-resolve-btn" compact disabled={isMutationPending(entry.id)} aria-busy={isMutationPending(entry.id)} onClick={() => void handleResolve(entry)}>
                          Resolve
                        </PButton>
                      ) : null}
                      {entry.state === 'curated' ? (
                        <PButton type="button" data-testid="memory-approve-btn" compact disabled={isMutationPending(entry.id)} aria-busy={isMutationPending(entry.id)} onClick={() => void handleApprove(entry)}>
                          Approve
                        </PButton>
                      ) : null}

                      {entry.state !== 'deleted' ? (
                        <>
                          <PButton type="button" data-testid="memory-edit-btn" compact variant="secondary" disabled={isMutationPending(entry.id)} onClick={() => startEdit(entry)}>
                            Edit
                          </PButton>
                          <PButton
                            type="button"
                            data-testid="memory-delete-btn"
                            compact
                            disabled={isMutationPending(entry.id)}
                            aria-busy={isMutationPending(entry.id)}
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
                            <PButton type="button" data-testid="memory-edit-cancel-btn" compact variant="secondary" disabled={isMutationPending(entry.id)} onClick={cancelEdit}>
                              Cancel
                            </PButton>
                            <PButton
                              type="button"
                              data-testid="memory-edit-save-btn"
                              compact
                              disabled={isMutationPending(entry.id) || memoryConflict?.entryId === entry.id}
                              aria-busy={isMutationPending(entry.id)}
                              onClick={() => void handleEditSave(entry)}
                            >
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
      </section>

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
                disabled={deleteConfirmEntry ? isMutationPending(deleteConfirmEntry.id) : false}
                aria-busy={deleteConfirmEntry ? isMutationPending(deleteConfirmEntry.id) : false}
                onClick={() => void handleDelete(deleteConfirmEntry)}
              >
                Confirm delete
              </PButton>
            </div>
          </div>
        </PModal>
      ) : null}
      {purgeFlow.phase !== 'idle' && purgeFlow.phase !== 'done' ? (
        <PModal
          data-testid="memory-purge-dialog"
          open
          tabIndex={-1}
          onDismiss={purgeFlow.cancelPurge}
          disableBackdropClick
          dismissButton={false}
          aria-label="Purge deleted memories"
        >
          <div className="grid max-w-[520px] gap-static-md">
            <div className="grid gap-static-xs">
              <PHeading tag="h2" size="small">Purge deleted memories</PHeading>
              <p className="m-0 text-sm text-contrast-high">This action ignores active filters and applies across the project.</p>
            </div>
            <PInputNumber
              name="memory-purge-threshold"
              label="Minimum age (days)"
              controls
              min={0}
              step={1}
              value={purgeFlow.threshold}
              state={purgeFlow.error ? 'error' : undefined}
              message={purgeFlow.error ?? undefined}
              onChange={(event) => purgeFlow.setThreshold(readStringValue(event))}
              onInput={(event) => purgeFlow.setThreshold(readStringValue(event))}
            />
            {purgeFlow.preview ? (
              <dl className="grid grid-cols-3 gap-static-sm rounded-lg border border-contrast-low bg-surface p-static-sm text-sm" data-testid="memory-purge-preview">
                <div><dt className="text-contrast-high">Total deleted</dt><dd className="m-0 font-semibold">{purgeFlow.preview.deleted_total}</dd></div>
                <div><dt className="text-contrast-high">Eligible</dt><dd className="m-0 font-semibold">{purgeFlow.preview.eligible}</dd></div>
                <div><dt className="text-contrast-high">Too recent</dt><dd className="m-0 font-semibold">{purgeFlow.preview.too_recent}</dd></div>
              </dl>
            ) : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" compact variant="secondary" onClick={purgeFlow.cancelPurge}>Cancel</PButton>
              {purgeFlow.phase === 'confirming' ? (
                <PButton type="button" compact onClick={() => void purgeFlow.confirmPurge()}>Purge</PButton>
              ) : (
                <PButton type="button" compact disabled={purgeFlow.phase === 'previewing' || purgeFlow.phase === 'running'} onClick={() => void purgeFlow.requestPreview()}>
                  Preview
                </PButton>
              )}
            </div>
          </div>
        </PModal>
      ) : null}
      </div>
    </section>
  )
}

export default MemoryTab
