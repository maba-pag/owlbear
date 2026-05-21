import { useEffect, useRef } from 'react'
import {
  PButton,
  PCheckbox,
  PInputSearch,
  PMultiSelect,
  PMultiSelectOption,
  PSelect,
  PSelectOption,
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

function removeNativeCheckboxInputs(root: ParentNode): void {
  root.querySelectorAll('input[type="checkbox"]').forEach((input) => input.remove())
}

function watchNativeCheckboxInputs(root: ParentNode): () => void {
  const observers: MutationObserver[] = []
  const frameIds: number[] = []

  const cleanup = () => removeNativeCheckboxInputs(root)
  const observe = (scope: ParentNode) => {
    const observer = new MutationObserver(cleanup)
    observer.observe(scope, { childList: true, subtree: true })
    observers.push(observer)
  }

  observe(root)

  let frameCount = 0
  const cleanupFrame = () => {
    cleanup()
    frameCount += 1
    if (frameCount < 10) {
      frameIds.push(window.requestAnimationFrame(cleanupFrame))
    }
  }
  frameIds.push(window.requestAnimationFrame(cleanupFrame))

  return () => {
    observers.forEach((observer) => observer.disconnect())
    frameIds.forEach((frameId) => window.cancelAnimationFrame(frameId))
  }
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
  const blockedRef = useRef<HTMLElement | null>(null)
  const searchRef = useRef<HTMLElement | null>(null)
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
    const blockedElement = blockedRef.current
    if (!blockedElement) {
      return
    }

    const onBlockedChange = (event: Event) => {
      const customEvent = event as CustomEvent<{ checked?: unknown; value?: unknown }>
      const checkedDetail = customEvent.detail?.checked ?? customEvent.detail?.value
      if (typeof checkedDetail === 'boolean') {
        onFilterChange({ ...filter, blocked: checkedDetail })
        return
      }

      const target = event.target as { checked?: unknown } | null
      if (typeof target?.checked === 'boolean') {
        onFilterChange({ ...filter, blocked: target.checked })
        return
      }

      onFilterChange({ ...filter, blocked: !filter.blocked })
    }

    blockedElement.addEventListener('change', onBlockedChange)
    blockedElement.addEventListener('update', onBlockedChange)
    return () => {
      blockedElement.removeEventListener('change', onBlockedChange)
      blockedElement.removeEventListener('update', onBlockedChange)
    }
  }, [filter, onFilterChange, open])

  useEffect(() => {
    if (!open || !panelRef.current) {
      return
    }

    removeNativeCheckboxInputs(panelRef.current)
    return watchNativeCheckboxInputs(panelRef.current)
  }, [open])

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

  useEffect(() => {
    if (!open) {
      return
    }

    const handlePointerDown = (event: PointerEvent) => {
      const panelElement = panelRef.current
      const target = event.target
      if (!(target instanceof Node) || panelElement?.contains(target)) {
        return
      }

      const toggle = document.querySelector('[data-testid="filter-toggle"], [data-testid="filter-toggle-real"]')
      if (toggle?.contains(target)) {
        return
      }

      onClose?.()
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
    }
  }, [onClose, open])

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
      data-testid="filter-panel"
      data-region="filter-panel"
      className="filter-panel"
      role="region"
      aria-label="Task filters"
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          onClose?.()
        }
      }}
    >
      <PInputSearch
        ref={searchRef}
        className="filter-panel__search"
        name="search-filter"
        label="Search tasks"
        role="textbox"
        aria-label="Search tasks"
        tabIndex={0}
      />

      <PSelect
        className="filter-panel__priority"
        name="priority-filter"
        label="Priority"
        value={filter.priority}
        tabIndex={0}
        onChange={(event) => onFilterChange({ ...filter, priority: readStringValue(event as ControlValueEvent) })}
      >
        <PSelectOption value="">All priorities</PSelectOption>
        {priorities.map((priority) => (
          <PSelectOption key={priority} value={priority}>
            {priority}
          </PSelectOption>
        ))}
      </PSelect>

      {availableTags.length > 0 ? (
        <PMultiSelect
          className="filter-panel__tags"
          name="tags-filter"
          label="Tags"
          data-testid="filter-tags"
          value={filter.tags}
          tabIndex={0}
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

      <PCheckbox
        ref={blockedRef}
        className="filter-panel__blocked"
        name="blocked-filter"
        label="Show only blocked tasks"
        checked={filter.blocked}
        tabIndex={0}
        onClick={() => onFilterChange({ ...filter, blocked: !filter.blocked })}
      >
        Show only blocked tasks
      </PCheckbox>

      {isFilterActive ? (
        <PButton
          className="filter-panel__reset"
          data-testid="filter-reset"
          variant="secondary"
          compact
          onClick={() => onFilterChange(EMPTY_FILTER)}
        >
          Clear all
        </PButton>
      ) : null}
    </div>
  )
}
