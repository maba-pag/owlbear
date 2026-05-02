import { useEffect, useRef } from 'react'
import {
  PButton,
  PMultiSelect,
  PMultiSelectOption,
  PSelect,
} from '@porsche-design-system/components-react'

import type { FilterState } from '../utils/filterTasks'

export interface FilterPanelProps {
  filter: FilterState
  onFilterChange: (filter: FilterState) => void
  priorities: string[]
  availableTags: string[]
  open: boolean
}

const EMPTY_FILTER: FilterState = { text: '', priority: '', tags: [], blocked: false }

function readStringValue(
  event: {
    target?: { value?: unknown }
    detail?: { value?: unknown }
  },
): string {
  if (typeof event.detail?.value === 'string') {
    return event.detail.value
  }

  if (typeof event.target?.value === 'string') {
    return event.target.value
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
}: FilterPanelProps) {
  const tagsRef = useRef<HTMLElement | null>(null)

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
  }, [filter, onFilterChange])

  if (!open) {
    return null
  }

  const isFilterActive =
    filter.text !== EMPTY_FILTER.text ||
    filter.priority !== EMPTY_FILTER.priority ||
    filter.tags.length > 0 ||
    filter.blocked !== EMPTY_FILTER.blocked

  return (
    <div>
      <input
        type="text"
        placeholder="Search by title…"
        value={filter.text}
        onChange={(event) => onFilterChange({ ...filter, text: readStringValue(event) })}
        onInput={(event) => onFilterChange({ ...filter, text: readStringValue(event) })}
      />

      <PSelect
        value={filter.priority}
        onChange={(event) => onFilterChange({ ...filter, priority: readStringValue(event) })}
        onInput={(event) => onFilterChange({ ...filter, priority: readStringValue(event) })}
      >
        <option value="">All priorities</option>
        {priorities.map((priority) => (
          <option key={priority} value={priority}>
            {priority}
          </option>
        ))}
      </PSelect>

      {availableTags.length > 0 ? (
        <PMultiSelect
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

      <label>
        <input
          type="checkbox"
          role="switch"
          checked={filter.blocked}
          onChange={() => onFilterChange({ ...filter, blocked: !filter.blocked })}
        />
        Show only blocked tasks
      </label>

      {isFilterActive ? (
        <PButton data-testid="filter-reset" variant="tertiary" onClick={() => onFilterChange(EMPTY_FILTER)}>
          Clear all
        </PButton>
      ) : null}
    </div>
  )
}
