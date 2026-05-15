import { useEffect, useRef } from 'react'
import {
  PButton,
  PMultiSelect,
  PMultiSelectOption,
} from '@porsche-design-system/components-react'

import './FilterPanel.css'

import type { FilterState } from '../utils/filterTasks'

export interface FilterPanelProps {
  filter: FilterState
  onFilterChange: (filter: FilterState) => void
  priorities: string[]
  availableTags: string[]
  open: boolean
  onClose?: () => void
}

const EMPTY_FILTER: FilterState = { text: '', priority: '', tags: [], blocked: false }

type ControlValueEvent = {
  target?: unknown
  currentTarget?: unknown
  detail?: { value?: unknown }
}

function readStringValue(event: ControlValueEvent): string {
  if (typeof event.detail?.value === 'string') {
    return event.detail.value
  }

  const target = event.target as { value?: unknown } | undefined
  if (typeof target?.value === 'string') {
    return target.value
  }

  const currentTarget = event.currentTarget as { value?: unknown } | undefined
  if (typeof currentTarget?.value === 'string') {
    return currentTarget.value
  }

  return ''
}

function readStringArrayValue(event: Event): string[] {
  const customEvent = event as CustomEvent<{ value?: unknown }>
  const value = customEvent.detail?.value
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

export default function FilterPanel({
  filter,
  onFilterChange,
  priorities,
  availableTags,
  open,
  onClose,
}: FilterPanelProps) {
  const tagsRef = useRef<HTMLElement | null>(null)
  const searchRef = useRef<HTMLElement | null>(null)
  const priorityRef = useRef<HTMLElement | null>(null)
  const panelRef = useRef<HTMLDivElement | null>(null)
  const wasOpenRef = useRef(open)
  const hadFocusInsideRef = useRef(false)

  useEffect(() => {
    const tagsElement = tagsRef.current
    if (!tagsElement) {
      return
    }

    const onUpdate = (event: Event) => {
      onFilterChange({ ...filter, tags: readStringArrayValue(event) })
    }

    tagsElement.addEventListener('update', onUpdate)
    return () => {
      tagsElement.removeEventListener('update', onUpdate)
    }
  }, [filter, onFilterChange, open])

  useEffect(() => {
    const searchElement = searchRef.current
    if (!searchElement) {
      return
    }

    ;(searchElement as { value?: unknown }).value = filter.text

    const onSearchInput = (event: Event) => {
      onFilterChange({ ...filter, text: readStringValue(event as ControlValueEvent) })
    }

    searchElement.addEventListener('input', onSearchInput)
    searchElement.addEventListener('change', onSearchInput)
    return () => {
      searchElement.removeEventListener('input', onSearchInput)
      searchElement.removeEventListener('change', onSearchInput)
    }
  }, [filter, onFilterChange, open])

  useEffect(() => {
    const priorityElement = priorityRef.current
    if (!priorityElement) {
      return
    }

    const onPriorityChange = (event: Event) => {
      onFilterChange({ ...filter, priority: readStringValue(event as ControlValueEvent) })
    }

    priorityElement.addEventListener('input', onPriorityChange)
    priorityElement.addEventListener('change', onPriorityChange)
    return () => {
      priorityElement.removeEventListener('input', onPriorityChange)
      priorityElement.removeEventListener('change', onPriorityChange)
    }
  }, [filter, onFilterChange, open])

  useEffect(() => {
    if (!open) {
      if (wasOpenRef.current && hadFocusInsideRef.current) {
        const toggle = document.querySelector<HTMLElement>(
          '[data-testid="filter-toggle"], [data-testid="filter-toggle-real"]',
        )
        toggle?.focus()
      }

      wasOpenRef.current = false
      hadFocusInsideRef.current = false
      return
    }

    const activeElement = document.activeElement
    const panelElement = panelRef.current
    if (panelElement && activeElement instanceof HTMLElement && panelElement.contains(activeElement)) {
      hadFocusInsideRef.current = true
    }

    if (!panelElement || (activeElement instanceof HTMLElement && panelElement.contains(activeElement))) {
      wasOpenRef.current = true
      return
    }

    searchRef.current?.focus()
    hadFocusInsideRef.current = true
    wasOpenRef.current = true
  }, [open])

  useEffect(() => {
    if (!open || !panelRef.current) {
      return
    }

    const panelElement = panelRef.current
    const onFocusIn = (event: FocusEvent) => {
      if (event.target instanceof Node && panelElement.contains(event.target)) {
        hadFocusInsideRef.current = true
      }
    }

    panelElement.addEventListener('focusin', onFocusIn)
    return () => {
      panelElement.removeEventListener('focusin', onFocusIn)
    }
  }, [open])

  if (!open) {
    return null
  }

  const isFilterActive =
    filter.text !== EMPTY_FILTER.text ||
    filter.priority !== EMPTY_FILTER.priority ||
    filter.tags.length > 0 ||
    filter.blocked !== EMPTY_FILTER.blocked

  return (
    <div
      ref={panelRef}
      id="filter-panel"
      className="filter-panel"
      role="region"
      aria-label="Task filters"
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          onClose?.()
        }
      }}
    >
      <p-input-search
        ref={searchRef}
        name="search-filter"
        aria-label="Search tasks"
        role="textbox"
      />

      <p-select
        ref={priorityRef}
        name="priority-filter"
        aria-label="Priority"
        value={filter.priority}
      >
        <p-select-option value="">All priorities</p-select-option>
        {priorities.map((priority) => (
          <p-select-option key={`pds-${priority}`} value={priority}>
            {priority}
          </p-select-option>
        ))}
      </p-select>

      {availableTags.length > 0 ? (
        <PMultiSelect
          name="tags-filter"
          label="Tags"
          aria-label="Tags"
          data-testid="filter-tags"
          value={filter.tags}
          ref={(element) => {
            tagsRef.current = element as unknown as HTMLElement | null
          }}
        >
          {availableTags.map((tag) => (
            <PMultiSelectOption key={tag} value={tag}>
              {tag}
            </PMultiSelectOption>
          ))}
        </PMultiSelect>
      ) : null}

      <p-checkbox
        name="blocked-filter"
        label="Show only blocked tasks"
        aria-checked={filter.blocked}
        onClick={() => onFilterChange({ ...filter, blocked: !filter.blocked })}
      >
        Show only blocked tasks
      </p-checkbox>

      {isFilterActive ? (
        <PButton data-testid="filter-reset" variant="secondary" onClick={() => onFilterChange(EMPTY_FILTER)}>
          Clear all
        </PButton>
      ) : null}
    </div>
  )
}

