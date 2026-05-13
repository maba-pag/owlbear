/**
 * Card signal attribute rendering tests — AC-1
 *
 * Tests that Card renders the correct data-signal attribute for each operational
 * state. Card.tsx currently lacks data-signal and pendingDRIds prop — all tests
 * fail RED until builder #1546 wires signal computation into the Card component.
 *
 * Self-contained: expected signal values are defined inline per brief D10/D14.
 * No import of computeSignal — this test verifies the rendered DOM contract,
 * not the computation logic (tested separately in computeSignal.test.ts).
 *
 * Prerequisites (builder must create before tests reach assertion-failure RED):
 *   src/components/Card.tsx — accept pendingDRIds: Set<number>, render data-signal
 *   src/hooks/useBoard.ts — Task type extended with dep_status: string | null (#1544)
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { Card } from '../components/Card'
import type { Task } from '../hooks/useBoard'

// ─── Local task shape ────────────────────────────────────────────────────────
// Includes dep_status (added by builder #1544) — defined locally to keep
// tests self-contained and not blocked by the type-extension task.

interface SignalTask {
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

function makeTask(overrides: Partial<SignalTask> & { id: number }): SignalTask {
  return {
    title: 'Test task',
    status: 'todo',
    priority: 'important',
    updated: '2026-01-01T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
    dep_status: null,
    ...overrides,
  }
}

function renderCard(task: SignalTask, pendingDRIds: Set<number> = new Set()) {
  // pendingDRIds prop will be added by builder #1546; currently unknown to CardProps.
  // Vitest transpiles without type-checking — extra prop causes no runtime error.
  return render(
    <Card
      task={task as unknown as Task}
      // @ts-expect-error prop added by builder #1546
      pendingDRIds={pendingDRIds}
      onContextMenu={() => {}}
      onDragStart={() => {}}
      onDragEnd={() => {}}
    />,
  )
}

// ─── AC-1: Card renders data-signal attribute per operational state ────────────
// Signal precedence (brief D14): dr-pending > blocked > claimed > deps-unmet > ready
// Each test verifies a single isolated state — no coupling to computeSignal.

describe('TestFromAC_CardSignalAttribute', () => {
  it('renders data-signal="dr-pending" when task.id is in pendingDRIds (highest precedence)', () => {
    const task = makeTask({ id: 42 })
    const { container } = renderCard(task, new Set([42]))
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('dr-pending')
  })

  it('renders data-signal="blocked" when task.blocked=true and task not in pendingDRIds', () => {
    const task = makeTask({ id: 1, blocked: true })
    const { container } = renderCard(task, new Set<number>())
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('blocked')
  })

  it('renders data-signal="claimed" when task.claimed=true, not blocked, no pending DR', () => {
    const task = makeTask({ id: 2, claimed: true })
    const { container } = renderCard(task, new Set<number>())
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('claimed')
  })

  it('renders data-signal="deps-unmet" when dep_status="blocked" and no higher-priority signals active', () => {
    const task = makeTask({ id: 3, dep_status: 'blocked' })
    const { container } = renderCard(task, new Set<number>())
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('deps-unmet')
  })

  it('renders data-signal="ready" when no operational conditions are active (default state)', () => {
    const task = makeTask({ id: 4 })
    const { container } = renderCard(task, new Set<number>())
    const card = container.querySelector('[data-testid="task-card"]')
    expect(card).not.toBeNull()
    expect(card!.getAttribute('data-signal')).toBe('ready')
  })
})
