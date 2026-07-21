import { describe, it, expect, vi, afterEach } from 'vitest'
import { act, cleanup, fireEvent } from '@testing-library/react'
import {
  BOARD,
  TASK,
  TASK_REFERENCES,
  TASK_WITH_DEPS,
  TASK_WITH_MISSING_REF,
  openEditor,
  renderDetail,
  renderDetailTab,
  typeIntoPdsField,
} from './DetailTab.testSupport'

describe('DetailTab edit surface', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('mounts the populated edit form only after Edit details is invoked', () => {
    const { container } = renderDetail()

    expect(container.querySelector('[data-testid="task-detail-display"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="edit-details-button"]')).not.toBeNull()
    expect(container.querySelector('[data-region="task-detail-edit-form"]')).toBeNull()
    expect(container.querySelector('p-select[data-field="priority"]')).toBeNull()

    openEditor(container)

    const title = container.querySelector('p-input-text[data-field="title"]') as
      | (HTMLElement & { value?: string })
      | null
    const priority = container.querySelector('p-select[data-field="priority"]') as
      | (HTMLElement & { value?: string })
      | null
    expect(container.querySelector('[data-region="task-detail-edit-form"]')).not.toBeNull()
    expect(title?.value ?? title?.getAttribute('value')).toBe(TASK.title)
    expect(priority?.value ?? priority?.getAttribute('value')).toBe(TASK.priority)
  })

  it('renders edit actions into the supplied modal action host', () => {
    const actionHost = document.createElement('div')
    document.body.appendChild(actionHost)

    try {
      const { container } = renderDetailTab({ task: TASK, actionPortalTarget: actionHost })
      openEditor(container)

      expect(actionHost.querySelector('[data-testid="save-button"]')).not.toBeNull()
      expect(actionHost.querySelector('[data-testid="cancel-edit-button"]')).not.toBeNull()
      expect(container.querySelector('[data-testid="task-detail-edit-actions"]')).toBeNull()
    } finally {
      actionHost.remove()
    }
  })

  it('reports dirty-state changes and restoration to the parent shell', () => {
    const onDirtyChange = vi.fn()
    const { container } = renderDetailTab({ task: TASK, board: BOARD, onDirtyChange })

    openEditor(container)
    act(() => { typeIntoPdsField(container, 'p-input-text[data-field="title"]', 'Changed task title') })
    expect(onDirtyChange).toHaveBeenCalledWith(true)

    act(() => { typeIntoPdsField(container, 'p-input-text[data-field="title"]', TASK.title) })
    expect(onDirtyChange).toHaveBeenLastCalledWith(false)
  })

  it('adds and removes tags from the edit draft', () => {
    const { container } = renderDetail()
    openEditor(container)

    fireEvent.click(container.querySelector('p-tag-dismissible[data-tag="bug"]')!)
    typeIntoPdsField(container, 'p-input-text[data-field="new-tag"]', 'scope:cockpit')
    fireEvent.click(container.querySelector('[data-testid="add-tag-button"]')!)

    expect(container.querySelector('p-tag-dismissible[data-tag="bug"]')).toBeNull()
    expect(container.querySelector('p-tag-dismissible[data-tag="frontend"]')).not.toBeNull()
    expect(container.querySelector('p-tag-dismissible[data-tag="scope:cockpit"]')).not.toBeNull()
    expect(container.querySelector('[data-testid="dirty-indicator"]')).not.toBeNull()
  })

  it('navigates to available task references with their title and status', () => {
    const onSelectTask = vi.fn()
    const { container } = renderDetailTab({
      task: TASK_WITH_DEPS,
      taskReferences: TASK_REFERENCES,
      onSelectTask,
    })

    expect(container.querySelector('[data-reference-kind="parent"][data-reference-id="5"]')?.textContent).toContain('Parent rollout')
    expect(container.querySelector('[data-reference-kind="dependency"][data-reference-id="20"]')?.textContent).toContain('In Progress')
    fireEvent.click(container.querySelector('[data-reference-kind="parent"][data-reference-id="5"]')!)
    expect(onSelectTask).toHaveBeenCalledWith(5)
  })

  it('renders missing task references as unavailable and non-navigable', () => {
    const onSelectTask = vi.fn()
    const { container } = renderDetailTab({
      task: TASK_WITH_MISSING_REF,
      taskReferences: [TASK_REFERENCES[1]],
      onSelectTask,
    })

    const missingParent = container.querySelector('[data-reference-kind="parent"][data-reference-id="999"]')
    const missingDependency = container.querySelector('[data-reference-kind="dependency"][data-reference-id="404"]')
    expect(missingParent?.getAttribute('data-reference-state')).toBe('unavailable')
    expect(missingDependency?.getAttribute('data-reference-state')).toBe('unavailable')

    fireEvent.click(missingParent!)
    fireEvent.click(missingDependency!)
    expect(onSelectTask).not.toHaveBeenCalled()
  })
})
