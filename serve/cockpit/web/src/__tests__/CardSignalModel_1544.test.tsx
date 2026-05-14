/**
 * Card signal data model tests — task #1544
 *
 * P1-04: impl — card signal data model: type extension, DR cross-reference, signal computation
 *
 * AC coverage:
 *   AC-1: Task interface in src/hooks/useBoard.ts includes dep_status: string | null
 *     — Tested via source-file inspection (readFileSync pattern used in Card.css.test.ts).
 *       FAILS until builder adds the field to the Task interface block.
 *   AC-2: computeSignal() 17 tests pre-satisfied by #1536 (src/__tests__/computeSignal.test.ts).
 *     — No new tests written here; see Test-Writer Notes.
 *   AC-3: PRIORITY_COLORS removed and emoji badge spans (block-badge, running-indicator) removed.
 *     — All tests in TestFromAC_CardBadgesRemoved and TestFromAC_CardPriorityColorsRemoved
 *       FAIL until builder removes these from src/components/Card.tsx.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Card } from '../components/Card'
import type { Task } from '../hooks/useBoard'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const USE_BOARD_PATH = resolve(__dirname, '..', 'hooks', 'useBoard.ts')

// ─── Fixture factory ──────────────────────────────────────────────────────────

function makeTask(overrides: Partial<Task> & { id: number }): Task {
  return {
    title: 'Test task',
    status: 'todo',
    priority: 'important',
    updated: '2026-01-01T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
    ...overrides,
  }
}

function renderCard(task: Task) {
  return render(
    <Card
      task={task}
      onContextMenu={() => {}}
      onDragStart={() => {}}
      onDragEnd={() => {}}
    />,
  )
}

// ─── AC-1: Task interface includes dep_status ─────────────────────────────────
// Source-file inspection: TypeScript interface changes are not enforced by Vitest's
// esbuild transpiler, so a runtime DOM test would pass regardless of the type.
// Reading the source file directly gives a failing test until the builder adds the field.

describe('TestFromAC_TaskDepStatus', () => {
  it('Task interface in useBoard.ts declares dep_status: string | null', () => {
    const source = readFileSync(USE_BOARD_PATH, 'utf-8')
    // Extract Task interface body — relies on the interface closing on its own line.
    const match = source.match(/interface Task\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    const interfaceBody = match![1]
    expect(interfaceBody).toMatch(/dep_status\s*:\s*string\s*\|\s*null/)
  })
})

// ─── AC-3: Emoji badge spans removed from Card.tsx ───────────────────────────
// block-badge and running-indicator spans must be absent from the rendered DOM.
// All tests FAIL until builder removes them from src/components/Card.tsx.

describe('TestFromAC_CardBadgesRemoved', () => {
  it('no block-badge span rendered when task.blocked=true (emoji badge removed)', () => {
    const { container } = renderCard(makeTask({ id: 1, blocked: true, block_reason: null }))
    expect(container.querySelector('[data-testid="block-badge"]')).toBeNull()
  })

  it('no running-indicator span rendered when task.claimed=true (emoji indicator removed)', () => {
    const { container } = renderCard(makeTask({ id: 2, claimed: true }))
    expect(container.querySelector('[data-testid="running-indicator"]')).toBeNull()
  })

  it('neither block-badge nor running-indicator when both blocked=true and claimed=true', () => {
    const { container } = renderCard(makeTask({ id: 3, blocked: true, claimed: true }))
    expect(container.querySelector('[data-testid="block-badge"]')).toBeNull()
    expect(container.querySelector('[data-testid="running-indicator"]')).toBeNull()
  })

  it('no block-badge even when blocked=true with a non-null block_reason string', () => {
    const { container } = renderCard(
      makeTask({ id: 4, blocked: true, block_reason: 'Waiting for upstream API' }),
    )
    expect(container.querySelector('[data-testid="block-badge"]')).toBeNull()
  })
})

// ─── AC-3: PRIORITY_COLORS removed — no inline --card-priority-border style ──
// Card.tsx currently applies --card-priority-border via the PRIORITY_COLORS map.
// After removal, the card element must carry no such inline style property.
// All tests FAIL until builder removes the PRIORITY_COLORS map and cardStyle usage.

describe('TestFromAC_CardPriorityColorsRemoved', () => {
  function expectNoPriorityBorderStyle(priority: string) {
    const { container } = renderCard(makeTask({ id: 10, priority }))
    const card = container.querySelector('[data-testid="task-card"]') as HTMLElement | null
    expect(card).not.toBeNull()
    // getAttribute('style') reads the literal inline style attribute; reliable even when
    // jsdom's CSS custom property support is version-dependent.
    expect(card!.getAttribute('style') ?? '').not.toContain('--card-priority-border')
  }

  it('no --card-priority-border inline style for priority=critical', () => {
    expectNoPriorityBorderStyle('critical')
  })

  it('no --card-priority-border inline style for priority=needed', () => {
    expectNoPriorityBorderStyle('needed')
  })

  it('no --card-priority-border inline style for priority=important', () => {
    expectNoPriorityBorderStyle('important')
  })

  it('no --card-priority-border inline style for priority=nice-to-have', () => {
    expectNoPriorityBorderStyle('nice-to-have')
  })

  it('no --card-priority-border inline style for priority=someday', () => {
    expectNoPriorityBorderStyle('someday')
  })

  it('no --card-priority-border inline style for an unknown priority (was: fallback to contrast-medium)', () => {
    // The old fallback `PRIORITY_COLORS[p] ?? 'var(--pds-theme-light-contrast-medium)'`
    // produced a non-empty style even for unknown priorities. After removal: no style.
    expectNoPriorityBorderStyle('experimental')
  })
})
