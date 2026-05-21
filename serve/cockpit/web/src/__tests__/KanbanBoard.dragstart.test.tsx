import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import KanbanBoard from '../KanbanBoard'

vi.mock('../components/ArchivalModal', () => ({
  default: vi.fn(() => null),
}))

const BOARD = {
  statuses: [{ name: 'backlog' }, { name: 'todo' }],
  priorities: ['someday', 'nice-to-have', 'important', 'needed', 'critical'],
  valid_transitions: {
    backlog: ['todo'],
    todo: ['backlog'],
  } as Record<string, string[]>,
}

const TASK_ONE = {
  id: 7,
  title: 'Move this task explicitly',
  status: 'backlog',
  priority: 'needed',
  updated: '2026-04-30T12:00:00+00:00',
  tags: [],
  blocked: false,
  block_reason: null,
  claimed: false,
}

function stubMoveFetch() {
  const mockFetch = vi.fn((url: string) => {
    if (/\/api\/tasks\/\d+\/move/.test(url)) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ ...TASK_ONE, status: 'todo' }),
      })
    }

    return Promise.reject(new Error(`Unexpected fetch URL in no-drag suite: ${url}`))
  })
  vi.stubGlobal('fetch', mockFetch)
  return mockFetch
}

function renderBoard(
  refetchTasks = vi.fn(),
  onMutationError = vi.fn(),
  onMutationSuccess = vi.fn(),
) {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter>
        <KanbanBoard
          board={BOARD}
          tasks={[TASK_ONE]}
          loading={false}
          error={null}
          refetchTasks={refetchTasks}
          onMutationError={onMutationError}
          onMutationSuccess={onMutationSuccess}
        />
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

async function getTaskCard(container: HTMLElement) {
  await waitFor(() => {
    expect(container.querySelector('[data-testid="task-card"][data-id="7"]')).not.toBeNull()
  })
  return container.querySelector('[data-testid="task-card"][data-id="7"]') as HTMLElement
}

describe('KanbanBoard no-drag move contract', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders task cards as non-draggable click targets', async () => {
    const { container } = renderBoard()
    const card = await getTaskCard(container)

    expect(card.draggable).toBe(false)
    expect(card.getAttribute('data-dragging')).toBeNull()
  })

  it('does not send move requests or activate drop targets for drag/drop gestures', async () => {
    const mockFetch = stubMoveFetch()
    const mutationErrorSpy = vi.fn()
    const mutationSuccessSpy = vi.fn()
    const { container } = renderBoard(vi.fn(), mutationErrorSpy, mutationSuccessSpy)
    const card = await getTaskCard(container)
    const todoColumn = container.querySelector('[data-column="todo"]') as HTMLElement

    fireEvent.dragStart(card)
    fireEvent.dragOver(todoColumn)
    fireEvent.drop(todoColumn)

    expect(mockFetch).not.toHaveBeenCalled()
    expect(mutationErrorSpy).not.toHaveBeenCalled()
    expect(mutationSuccessSpy).not.toHaveBeenCalled()
    expect(todoColumn.getAttribute('data-drag-over')).toBeNull()
  })

  it('keeps explicit context-menu moves available', async () => {
    const mockFetch = stubMoveFetch()
    const { container } = renderBoard()
    const card = await getTaskCard(container)

    fireEvent.contextMenu(card)
    await waitFor(() => {
      expect(container.querySelector('[data-testid="context-menu"]')).not.toBeNull()
    })

    fireEvent.click(container.querySelector('[data-testid="transition-item"][data-status="todo"]')!)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/tasks/7/move',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ status: 'todo', updated: TASK_ONE.updated }),
        }),
      )
    })
  })
})
