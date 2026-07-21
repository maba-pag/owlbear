import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent } from '@testing-library/react'
import {
  TASK_WITH_AC,
  TASK_WITHOUT_AC,
  flushAsyncSave,
  getFetchBody,
  openEditor,
  renderDetail,
  typeIntoPdsField,
} from './DetailTab.testSupport'

describe('DetailTab acceptance criteria', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('renders the task criteria in display mode', () => {
    const { container } = renderDetail(TASK_WITH_AC)
    const items = container.querySelectorAll('[data-testid="task-ac-item"]')

    expect(items).toHaveLength(2)
    expect(items[0]?.textContent).toContain('User can see the acceptance criteria')
    expect(container.querySelector('[data-testid="task-ac-empty-state"]')).toBeNull()
  })

  it('renders an explicit empty state when the task has no criteria', () => {
    const { container } = renderDetail(TASK_WITHOUT_AC)

    expect(container.querySelector('[data-testid="task-ac-list"]')).toBeNull()
    expect(container.querySelector('[data-testid="task-ac-empty-state"]')?.textContent).toContain(
      'No acceptance criteria defined.',
    )
  })

  it('saves edited and pending criteria as a structured list', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(TASK_WITH_AC),
      }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderDetail(TASK_WITH_AC)

    openEditor(container)
    typeIntoPdsField(container, '[data-testid="task-ac-input"][data-ac-index="0"]', 'Updated criterion')
    typeIntoPdsField(container, 'p-input-text[data-field="new-ac"]', 'New criterion')
    fireEvent.click(container.querySelector('[data-testid="save-button"]')!)

    expect(getFetchBody(fetchMock).ac).toEqual([
      'Updated criterion',
      'Missing acceptance criteria has an explicit empty state.',
      'New criterion',
    ])
    await flushAsyncSave()
  })
})
