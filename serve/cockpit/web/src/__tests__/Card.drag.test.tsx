/**
 * Card drag-attribute behavior tests — task #1546 (AC-4 JSX side)
 *
 * Tests verify Card.tsx sets data-dragging="true" when a drag starts and
 * resets it to "false" when the drag ends.
 *
 * All tests fail RED until builder #1546:
 *   - Adds local drag state (useState) to Card.tsx
 *   - Sets data-dragging={dragging ? 'true' : 'false'} on the card element
 *   - Updates onDragStart to set dragging=true (and call the prop callback)
 *   - Updates onDragEnd to set dragging=false (and call the prop callback)
 *
 * Currently Card.tsx has no data-dragging attribute → getAttribute returns null
 * for all tests below → all fail RED.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent, act } from '@testing-library/react'
import { Card } from '../components/Card'

// ─── Minimal task shape ───────────────────────────────────────────────────────

interface MinimalTask {
  id: number
  title: string
  status: string
  priority: string
  updated: string
  tags: string[]
  blocked: boolean
  block_reason: string | null
  claimed: boolean
  dep_status: string | null
}

function makeTask(id: number): MinimalTask {
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

// ─── AC-4: data-dragging attribute lifecycle ──────────────────────────────────

describe('TestFromAC_CardDragAttribute', () => {
  it('card element has data-dragging="false" when not dragging (initial render)', () => {
    const { container } = render(
      <Card
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        task={makeTask(1) as any}
        onContextMenu={() => {}}
        onDragStart={() => {}}
        onDragEnd={() => {}}
      />,
    )
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    // Builder sets data-dragging="false" initially — currently absent → null → FAIL RED.
    expect(card!.getAttribute('data-dragging')).toBe('false')
  })

  it('card element sets data-dragging="true" when dragStart event fires (AC-4)', () => {
    const onDragStart = vi.fn()
    const { container } = render(
      <Card
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        task={makeTask(2) as any}
        onContextMenu={() => {}}
        onDragStart={onDragStart}
        onDragEnd={() => {}}
      />,
    )
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    act(() => {
      fireEvent.dragStart(card!)
    })
    // Builder updates dragging state → data-dragging="true" — currently absent → FAIL RED.
    expect(card!.getAttribute('data-dragging')).toBe('true')
  })

  it('card element resets data-dragging to "false" after dragEnd event fires (AC-4)', () => {
    const { container } = render(
      <Card
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        task={makeTask(3) as any}
        onContextMenu={() => {}}
        onDragStart={() => {}}
        onDragEnd={() => {}}
      />,
    )
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    act(() => {
      fireEvent.dragStart(card!)
    })
    expect(card!.getAttribute('data-dragging')).toBe('true')
    act(() => {
      fireEvent.dragEnd(card!)
    })
    // Builder resets dragging state → data-dragging="false" — currently absent → FAIL RED.
    expect(card!.getAttribute('data-dragging')).toBe('false')
  })

  it('onDragStart prop callback is invoked AND data-dragging becomes "true" simultaneously (AC-4)', () => {
    const onDragStart = vi.fn()
    const task = makeTask(42)
    const { container } = render(
      <Card
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        task={task as any}
        onContextMenu={() => {}}
        onDragStart={onDragStart}
        onDragEnd={() => {}}
      />,
    )
    const card = container.querySelector('[data-testid="task-card"]')
    act(() => {
      fireEvent.dragStart(card!)
    })
    // Both conditions must hold: prop callback fired AND drag state is reflected in DOM.
    expect(onDragStart).toHaveBeenCalledWith(42, '2026-01-01T00:00:00+00:00')
    expect(card!.getAttribute('data-dragging')).toBe('true')
  })
})
