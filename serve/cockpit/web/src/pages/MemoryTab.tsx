import { useEffect, useMemo, useRef, useState } from 'react'
import {
  PButton,
  PInputSearch,
  PModal,
  PMultiSelect,
  PMultiSelectOption,
  PSelect,
  PSelectOption,
  PTag,
  PTextarea,
} from '@porsche-design-system/components-react'
import type { TagVariant } from '@porsche-design-system/components-react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import type { KanbanBoardProps } from '../KanbanBoard'
import { ApiError } from '../api/errors'
import { getResponseErrorMessage } from '../api/errorMessage'
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

interface MemoryEditPayload {
  title: string
  categories: string[]
  confidence: number
  scope_agents: string[]
  content: string
  expected_updated_at: string
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

function splitCSV(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

function parseValidationErrors(payload: unknown): string[] {
  if (typeof payload !== 'object' || payload === null) {
    return []
  }
  const detail = (payload as { detail?: unknown }).detail
  if (!Array.isArray(detail)) {
    return []
  }
  return detail
    .map((item) => {
      if (typeof item !== 'object' || item === null) {
        return null
      }
      const message = (item as { msg?: unknown }).msg
      return typeof message === 'string' && message.trim().length > 0 ? message.trim() : null
    })
    .filter((message): message is string => message !== null)
}

function parseMutationErrorPayload(payload: unknown): { validationMessages: string[]; message: string | null } {
  const validationMessages = parseValidationErrors(payload)
  if (validationMessages.length > 0) {
    return { validationMessages, message: null }
  }

  if (typeof payload === 'object' && payload !== null) {
    const detail = (payload as { detail?: unknown }).detail
    if (typeof detail === 'string' && detail.trim().length > 0) {
      return { validationMessages: [], message: detail.trim() }
    }

    const message = (payload as { message?: unknown }).message
    if (typeof message === 'string' && message.trim().length > 0) {
      return { validationMessages: [], message: message.trim() }
    }
  }

  return { validationMessages: [], message: null }
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

function MemoryTab(_props: KanbanBoardProps) {
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [parseErrors, setParseErrors] = useState(0)
  const [filter, setFilter] = useState<MemoryFilterState>(INITIAL_FILTER)
  const [openEntryId, setOpenEntryId] = useState<string | null>(null)
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<MemoryEditPayload | null>(null)
  const [deleteConfirmEntryId, setDeleteConfirmEntryId] = useState<string | null>(null)
  const [mutationErrorByEntryId, setMutationErrorByEntryId] = useState<Record<string, string>>({})
  const [validationMessages, setValidationMessages] = useState<string[]>([])
  const [promotionMessageByEntryId, setPromotionMessageByEntryId] = useState<Record<string, string>>({})
  const [globalMutationMessage, setGlobalMutationMessage] = useState<string | null>(null)

  const stateFilterRef = useRef<HTMLElement | null>(null)
  const categoryFilterRef = useRef<HTMLElement | null>(null)
  const agentFilterRef = useRef<HTMLElement | null>(null)
  const searchFilterRef = useRef<HTMLElement | null>(null)
  const accordionRefs = useRef<Record<string, HTMLElement>>({})

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
  const deleteConfirmEntry = useMemo(
    () => entries.find((entry) => entry.id === deleteConfirmEntryId) ?? null,
    [deleteConfirmEntryId, entries],
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

  const mutationFetch = async (url: string, body?: Record<string, unknown>): Promise<unknown> => {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body ?? {}),
    })

    if (!response.ok) {
      let payload: unknown
      try {
        payload = (await response.json()) as unknown
      } catch {
        payload = null
      }

      const parsed = parseMutationErrorPayload(payload)
      const message =
        parsed.message ??
        (await getResponseErrorMessage(response, `Memory mutation failed with status ${response.status}`))
      const error = new ApiError(response.status, message)
      throw { error, payload, validationMessages: parsed.validationMessages }
    }

    return (await response.json()) as unknown
  }

  const handleMutationFailure = async (
    entry: MemoryEntry,
    caught: unknown,
  ): Promise<void> => {
    const result = caught as {
      error?: ApiError
      validationMessages?: string[]
    }
    const apiError = result.error instanceof ApiError ? result.error : null
    const parsedValidationMessages = Array.isArray(result.validationMessages)
      ? result.validationMessages
      : []

    if (apiError?.status === 409) {
      setEntryError(entry.id, 'Entry was modified - refreshing')
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
      const payload = (await mutationFetch(`/api/memories/${entry.id}/approve`)) as { entry?: MemoryEntry }
      if (payload.entry) {
        applyEntryReplace(payload.entry)
      }
      void refetch()
    } catch (caught) {
      await handleMutationFailure(entry, caught)
    }
  }

  const handleDelete = async (entry: MemoryEntry): Promise<void> => {
    clearEntryErrors(entry.id)
    try {
      await mutationFetch(`/api/memories/${entry.id}/delete`, {
        expected_updated_at: entry.updated_at,
      })

      if (entry.state === 'pending') {
        removeEntry(entry.id)
      } else {
        applyEntryReplace({ ...entry, state: 'deleted' })
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
  }

  const cancelEdit = () => {
    setEditingEntryId(null)
    setEditDraft(null)
    setValidationMessages([])
  }

  const handleEditSave = async (entry: MemoryEntry): Promise<void> => {
    if (!editDraft) {
      return
    }

    clearEntryErrors(entry.id)
    setValidationMessages([])

    const previousState = entry.state
    try {
      const payload = (await mutationFetch(`/api/memories/${entry.id}/edit`, editDraft as unknown as Record<string, unknown>)) as {
        entry?: MemoryEntry
      }
      if (payload.entry) {
        applyEntryReplace(payload.entry)
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
      void refetch()
    } catch (caught) {
      await handleMutationFailure(entry, caught)
    }
  }

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

      {!hasFetched && isFetching ? <div data-testid="memory-loading" /> : null}

      {parseErrors > 0 ? (
        <p data-testid="parse-errors-warning">{parseErrors} entries couldn't be read</p>
      ) : null}

      {globalMutationMessage ? <p>{globalMutationMessage}</p> : null}

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
              <p-accordion
                open={openEntryId === entry.id ? true : undefined}
                ref={(element) => {
                  if (element) {
                    accordionRefs.current[entry.id] = element as unknown as HTMLElement
                    return
                  }
                  delete accordionRefs.current[entry.id]
                }}
              >
                <div>
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
                </div>

                {openEntryId === entry.id ? (
                  <div data-testid="memory-accordion-detail">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[[rehypeSanitize, MEMORY_SANITIZE_SCHEMA]]}>
                      {entry.content}
                    </ReactMarkdown>
                    <p>ID: {entry.id}</p>
                    <p>Source agent: {entry.source_agent}</p>
                    <p>Scope agents: {entry.scope_agents.length > 0 ? entry.scope_agents.join(', ') : 'All agents'}</p>
                    <p>Categories: {entry.categories.join(', ')}</p>
                    <p>Confidence: {formatConfidence(entry.confidence)}</p>
                    <p>State: {entry.state}</p>
                    <p>Created: {entry.created_at}</p>
                    <p>Updated: {entry.updated_at}</p>
                    <p>Approved: {entry.approved_at ?? '-'}</p>

                    {entry.state === 'approved' ? <p>Editing will require re-approval</p> : null}

                    {mutationErrorByEntryId[entry.id] ? (
                      <p data-testid="memory-occ-banner">{mutationErrorByEntryId[entry.id]}</p>
                    ) : null}

                    {promotionMessageByEntryId[entry.id] ? <p>{promotionMessageByEntryId[entry.id]}</p> : null}

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

                    {editingEntryId === entry.id && editDraft ? (
                      <div data-testid="memory-edit-form">
                        <label>
                          Title
                          <input
                            name="edit-title"
                            data-testid="edit-title"
                            value={editDraft.title}
                            onChange={(event) => {
                              const value = event.target.value
                              setEditDraft((previous) =>
                                previous ? { ...previous, title: value } : previous,
                              )
                            }}
                          />
                        </label>
                        <label>
                          Categories
                          <input
                            name="edit-categories"
                            value={editDraft.categories.join(', ')}
                            onChange={(event) => {
                              const value = splitCSV(event.target.value)
                              setEditDraft((previous) =>
                                previous ? { ...previous, categories: value } : previous,
                              )
                            }}
                          />
                        </label>
                        <label>
                          Confidence
                          <input
                            name="edit-confidence"
                            type="number"
                            step="0.01"
                            min="0"
                            max="1"
                            value={editDraft.confidence}
                            onChange={(event) => {
                              const value = Number.parseFloat(event.target.value)
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
                        </label>
                        <label>
                          Scope agents
                          <input
                            name="edit-scope-agents"
                            value={editDraft.scope_agents.join(', ')}
                            onChange={(event) => {
                              const value = splitCSV(event.target.value)
                              setEditDraft((previous) =>
                                previous ? { ...previous, scope_agents: value } : previous,
                              )
                            }}
                          />
                        </label>
                        <label>
                          Content
                          <PTextarea
                            name="edit-content"
                            value={editDraft.content}
                            maxLength={MEMORY_CONTENT_LIMIT}
                            onInput={(event) => {
                              const target = event.target as HTMLTextAreaElement
                              const value = target.value.slice(0, MEMORY_CONTENT_LIMIT)
                              setEditDraft((previous) =>
                                previous ? { ...previous, content: value } : previous,
                              )
                            }}
                          />
                        </label>
                        <p data-testid="memory-char-counter">
                          {editDraft.content.length}/{MEMORY_CONTENT_LIMIT}
                        </p>
                        {validationMessages.length > 0 ? (
                          <ul>
                            {validationMessages.map((message) => (
                              <li key={message}>{message}</li>
                            ))}
                          </ul>
                        ) : null}
                        <PButton type="button" data-testid="memory-edit-save-btn" compact onClick={() => void handleEditSave(entry)}>
                          Save
                        </PButton>
                        <PButton type="button" data-testid="memory-edit-cancel-btn" compact variant="secondary" onClick={cancelEdit}>
                          Cancel
                        </PButton>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </p-accordion>
            </li>
          ))}
        </ul>
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
          <p>
            {deleteConfirmEntry.state === 'pending'
              ? 'This is a permanent hard-delete and cannot be undone.'
              : 'This will soft-delete the memory and mark it as deleted (removed from view by default).'}
          </p>
          <PButton
            type="button"
            data-testid="memory-delete-confirm-btn"
            compact
            onClick={() => void handleDelete(deleteConfirmEntry)}
          >
            Confirm delete
          </PButton>
          <PButton
            type="button"
            data-testid="memory-delete-cancel-btn"
            compact
            variant="secondary"
            onClick={() => setDeleteConfirmEntryId(null)}
          >
            Cancel
          </PButton>
        </PModal>
      ) : null}
    </section>
  )
}

export default MemoryTab
