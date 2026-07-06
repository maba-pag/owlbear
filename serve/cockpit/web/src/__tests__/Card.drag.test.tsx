import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { Card } from '../components/Card'
import type { Task } from '../hooks/useBoard'

function makeTask(id: number): Task {
  return {
    id,
    title: 'Test task',
    status: 'todo',
    priority: 'important',
    updated: '2026-01-01T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
    dep_status: null,
  }
}

describe('Card no-drag interaction contract', () => {
  it('renders as a non-draggable task button without drag state chrome', () => {
    const { container } = render(
      <Card
        task={makeTask(1)}
        onContextMenu={() => {}}
      />,
    )
    const card = container.querySelector('[data-testid="task-card"]') as HTMLElement | null

    expect(card).not.toBeNull()
    expect(card!.draggable).toBe(false)
    expect(card!.getAttribute('data-dragging')).toBeNull()
    expect(card!.className).not.toContain('opacity-50')
  })

  it('keeps primary click selection separate from removed drag behavior', () => {
    const onSelect = vi.fn()
    const { container } = render(
      <Card
        task={makeTask(2)}
        onSelect={onSelect}
        onContextMenu={() => {}}
      />,
    )
    const card = container.querySelector('[data-testid="task-card"]') as HTMLElement

    fireEvent.dragStart(card)
    expect(onSelect).not.toHaveBeenCalled()

    fireEvent.click(card)
    expect(onSelect).toHaveBeenCalledWith(2)
  })
})
