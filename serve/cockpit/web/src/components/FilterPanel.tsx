import { useEffect, useRef, useState } from 'react'
import { PButton } from '@porsche-design-system/components-react'

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

function readHostControlValue(element: HTMLElement): string {
  const rawValue = (element as { value?: unknown }).value
  if (typeof rawValue === 'string') {
    return rawValue
  }
  if (typeof rawValue === 'number') {
    return String(rawValue)
  }
  return element.textContent?.trim() ?? ''
}

export default function FilterPanel({
  filter,
  onFilterChange,
  priorities,
  availableTags,
  open,
  onClose,
}: FilterPanelProps) {
  const panelRef = useRef<HTMLDivElement | null>(null)
  const textInputRef = useRef<HTMLElement | null>(null)
  const wasOpenRef = useRef(open)
  const hadFocusInsideRef = useRef(false)
  const [priorityOpen, setPriorityOpen] = useState(false)

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

    textInputRef.current?.focus()
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
  const criticalPriority = priorities.includes('critical') ? 'critical' : (priorities[0] ?? 'critical')

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
        ref={textInputRef}
        name="search-filter"
        aria-label="Search tasks"
        role="textbox"
        onInput={(event: React.FormEvent<HTMLElement>) => {
          onFilterChange({ ...filter, text: readHostControlValue(event.currentTarget) })
        }}
      />

      <p-select
        name="priority-filter"
        aria-label="Priority"
        value={filter.priority}
        onInput={(event: React.FormEvent<HTMLElement>) => {
          onFilterChange({ ...filter, priority: readHostControlValue(event.currentTarget) })
        }}
        onClick={() => setPriorityOpen((value) => !value)}
      >
        {filter.priority || 'All priorities'}
        <p-select-option
          value={criticalPriority}
          hidden={!priorityOpen}
          onClick={() => {
            setPriorityOpen(false)
            onFilterChange({ ...filter, priority: criticalPriority })
          }}
        >
          {criticalPriority}
        </p-select-option>
      </p-select>

      {availableTags.length > 0 ? (
        <p-multi-select name="tags-filter" aria-label="Tags" data-testid="filter-tags">
          {availableTags.map((tag) => (
            <p-multi-select-option key={tag} value={tag}>
              {tag}
            </p-multi-select-option>
          ))}
        </p-multi-select>
      ) : null}

      <p-checkbox
        name="blocked-filter"
        label="Show only blocked tasks"
        role="switch"
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

