/**
 * Card visual treatment tests — task #1615 (AC-1 through AC-7)
 *
 * AC coverage:
 *   AC-1: Status chip renders as <PTag compact> with variant from statusToVariant();
 *         unknown status → variant "secondary"
 *   AC-2: Priority chip renders as <PTag compact> with variant from priorityToVariant();
 *         unknown priority → variant "secondary"
 *   AC-3: Signal icon renders as <p-icon size="xs" aria-label={signal}> for
 *         dr-pending, blocked, claimed, deps-unmet; no p-icon element in DOM when signal is ready
 *   AC-4: Each visible tag (up to TAG_PREVIEW_LIMIT=3) renders as individual
 *         <PTag compact variant="secondary">; overflow count indicator preserved
 *   AC-5: Existing state cue text spans (Blocked, Claimed, Dependencies blocked,
 *         Decision pending) preserved unchanged
 *   AC-6: No inline hex color values in Card output; source imports PTag from PDS
 *   AC-7: KanbanBoard.performance-700.test.tsx DOM_NODE_BUDGET > 6400
 *
 * Failure modes before builder implementation:
 *   AC-1: querySelector('p-tag[data-testid="card-status"]') returns null — no status chip
 *   AC-2: priority chip tagName is 'span' not 'p-tag'
 *   AC-3: querySelector('p-icon[...]') returns null — no PIcon anywhere in Card
 *   AC-4: querySelectorAll('p-tag[compact][variant="secondary"]') returns 0 — tags are in span
 *   AC-5: combined test fails due to missing p-tag status chip (AC-1 anchor)
 *   AC-6: Card.tsx source does not contain 'PTag' import — assertion fails
 *   AC-7: DOM_NODE_BUDGET === 6400 is not > 6400 — assertion fails
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

// ─── Fixture factory ──────────────────────────────────────────────────────────

interface CardTask {
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

function makeTask(overrides: Partial<CardTask> & { id: number }): CardTask {
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

function renderCard(task: CardTask, pendingDRIds: Set<number> = new Set()) {
  return render(
    <Card
      task={task as unknown as Task}
      pendingDRIds={pendingDRIds}
      onContextMenu={() => {}}
      onDragStart={() => {}}
      onDragEnd={() => {}}
    />,
  )
}

// ─── AC-1: Status chip renders as PTag compact ───────────────────────────────

describe('TestFromAC_CardStatusChip', () => {
  it('status chip element has tag name p-tag (not a plain span)', () => {
    // Current Card.tsx has no status chip at all — querySelector returns null,
    // then tagName check fails. FAIL until builder adds <PTag data-testid="card-status">.
    const task = makeTask({ id: 1, status: 'todo' })
    const { container } = renderCard(task)
    const statusChip = container.querySelector('[data-testid="card-status"]')
    expect(statusChip).not.toBeNull()
    expect(statusChip!.tagName.toLowerCase()).toBe('p-tag')
  })

  it('status chip p-tag has compact attribute', () => {
    const task = makeTask({ id: 1, status: 'todo' })
    const { container } = renderCard(task)
    const statusChip = container.querySelector('p-tag[data-testid="card-status"]')
    expect(statusChip).not.toBeNull()
    expect(statusChip!.hasAttribute('compact')).toBe(true)
  })

  it('status chip has a non-empty variant attribute', () => {
    const task = makeTask({ id: 1, status: 'todo' })
    const { container } = renderCard(task)
    const statusChip = container.querySelector('p-tag[data-testid="card-status"]')
    expect(statusChip).not.toBeNull()
    const variant = statusChip!.getAttribute('variant')
    expect(typeof variant).toBe('string')
    expect((variant as string).length).toBeGreaterThan(0)
  })

  it('unknown status string renders status chip with variant="secondary"', () => {
    const task = makeTask({ id: 1, status: 'completely-unknown-status-xyz' })
    const { container } = renderCard(task)
    const statusChip = container.querySelector('p-tag[data-testid="card-status"]')
    expect(statusChip).not.toBeNull()
    expect(statusChip!.getAttribute('variant')).toBe('secondary')
  })

  it('status chip displays the current task status value as text content', () => {
    const task = makeTask({ id: 1, status: 'in-progress' })
    const { container } = renderCard(task)
    const statusChip = container.querySelector('p-tag[data-testid="card-status"]')
    expect(statusChip).not.toBeNull()
    expect(statusChip!.textContent?.trim()).toBe('in-progress')
  })
})

// ─── AC-2: Priority chip renders as PTag compact ──────────────────────────────

describe('TestFromAC_CardPriorityChip', () => {
  it('priority chip element has tag name p-tag (not a plain span)', () => {
    // Current Card.tsx has <span data-testid="card-priority"> — tagName check fails.
    // FAIL until builder migrates to <PTag data-testid="card-priority">.
    const task = makeTask({ id: 1, priority: 'critical' })
    const { container } = renderCard(task)
    const priorityChip = container.querySelector('[data-testid="card-priority"]')
    expect(priorityChip).not.toBeNull()
    expect(priorityChip!.tagName.toLowerCase()).toBe('p-tag')
  })

  it('priority chip p-tag has compact attribute', () => {
    const task = makeTask({ id: 1, priority: 'critical' })
    const { container } = renderCard(task)
    const priorityChip = container.querySelector('p-tag[data-testid="card-priority"]')
    expect(priorityChip).not.toBeNull()
    expect(priorityChip!.hasAttribute('compact')).toBe(true)
  })

  it('priority chip has a non-empty variant attribute', () => {
    const task = makeTask({ id: 1, priority: 'critical' })
    const { container } = renderCard(task)
    const priorityChip = container.querySelector('p-tag[data-testid="card-priority"]')
    expect(priorityChip).not.toBeNull()
    const variant = priorityChip!.getAttribute('variant')
    expect(typeof variant).toBe('string')
    expect((variant as string).length).toBeGreaterThan(0)
  })

  it('unknown priority string renders priority chip with variant="secondary"', () => {
    const task = makeTask({ id: 1, priority: 'completely-unknown-priority-xyz' })
    const { container } = renderCard(task)
    const priorityChip = container.querySelector('p-tag[data-testid="card-priority"]')
    expect(priorityChip).not.toBeNull()
    expect(priorityChip!.getAttribute('variant')).toBe('secondary')
  })

  it('priority chip displays the current task priority value as text content', () => {
    const task = makeTask({ id: 1, priority: 'critical' })
    const { container } = renderCard(task)
    const priorityChip = container.querySelector('p-tag[data-testid="card-priority"]')
    expect(priorityChip).not.toBeNull()
    expect(priorityChip!.textContent?.trim()).toBe('critical')
  })
})

// ─── AC-3: Signal icon renders as PIcon ──────────────────────────────────────

describe('TestFromAC_CardSignalIcon', () => {
  it('dr-pending signal renders p-icon with size="xs" and aria-label="dr-pending"', () => {
    // No PIcon in current Card.tsx — querySelector returns null. FAIL until builder adds it.
    const task = makeTask({ id: 5 })
    const { container } = renderCard(task, new Set([5]))
    const icon = container.querySelector('p-icon[size="xs"][aria-label="dr-pending"]')
    expect(icon).not.toBeNull()
  })

  it('blocked signal renders p-icon with size="xs" and aria-label="blocked"', () => {
    const task = makeTask({ id: 1, blocked: true })
    const { container } = renderCard(task)
    const icon = container.querySelector('p-icon[size="xs"][aria-label="blocked"]')
    expect(icon).not.toBeNull()
  })

  it('claimed signal renders p-icon with size="xs" and aria-label="claimed"', () => {
    const task = makeTask({ id: 1, claimed: true })
    const { container } = renderCard(task)
    const icon = container.querySelector('p-icon[size="xs"][aria-label="claimed"]')
    expect(icon).not.toBeNull()
  })

  it('deps-unmet signal renders p-icon with size="xs" and aria-label="deps-unmet"', () => {
    const task = makeTask({ id: 1, dep_status: 'blocked' })
    const { container } = renderCard(task)
    const icon = container.querySelector('p-icon[size="xs"][aria-label="deps-unmet"]')
    expect(icon).not.toBeNull()
  })

  it('ready signal renders no p-icon element — confirmed by blocked card having p-icon', () => {
    // Anchored to a positive check that FAILS now: blocked card must have p-icon.
    // Both assertions must pass for the test to pass — if p-icon is never rendered,
    // the first assertion fails (correct RED behavior).
    const blockedTask = makeTask({ id: 1, blocked: true })
    const { container: blockedContainer } = renderCard(blockedTask)
    expect(blockedContainer.querySelector('p-icon[aria-label="blocked"]')).not.toBeNull()

    const readyTask = makeTask({ id: 2 })
    const { container: readyContainer } = renderCard(readyTask)
    expect(readyContainer.querySelector('p-icon')).toBeNull()
  })

  it('card with no active signals renders no p-icon element', () => {
    // Positive anchor: blocked variant must have p-icon before we can assert ready has none.
    const blockedTask = makeTask({ id: 99, blocked: true })
    const { container: blockedContainer } = renderCard(blockedTask)
    expect(blockedContainer.querySelector('p-icon')).not.toBeNull()

    // Now verify: no signals → no icon
    const cleanTask = makeTask({ id: 10, status: 'done' })
    const { container } = renderCard(cleanTask, new Set())
    expect(container.querySelector('p-icon')).toBeNull()
  })
})

// ─── AC-4: Tags render as individual PTag elements ───────────────────────────

describe('TestFromAC_CardTagPills', () => {
  // Note: tests use status='in-progress' and priority='critical' — both are known values
  // that the mapping utility must map to non-secondary variants (per AC-1/2 fallback contract).
  // This ensures p-tag[compact][variant="secondary"] selects only tag pills, not chips.

  it('one tag renders as exactly one p-tag[compact][variant="secondary"] pill', () => {
    // Current tags are in a single <span> — querySelectorAll returns 0. FAIL.
    const task = makeTask({ id: 1, status: 'in-progress', priority: 'critical', tags: ['frontend'] })
    const { container } = renderCard(task)
    const tagPills = container.querySelectorAll('p-tag[compact][variant="secondary"]')
    expect(tagPills.length).toBe(1)
  })

  it('three tags render exactly three p-tag[compact][variant="secondary"] pills', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c'],
    })
    const { container } = renderCard(task)
    const tagPills = container.querySelectorAll('p-tag[compact][variant="secondary"]')
    expect(tagPills.length).toBe(3)
  })

  it('four tags render exactly three tag pills (TAG_PREVIEW_LIMIT=3 caps display)', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c', 'd'],
    })
    const { container } = renderCard(task)
    const tagPills = container.querySelectorAll('p-tag[compact][variant="secondary"]')
    expect(tagPills.length).toBe(3)
  })

  it('five tags render three tag pills showing the first three tag names', () => {
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['frontend', 'backend', 'urgent', 'blocked', 'pds'],
    })
    const { container } = renderCard(task)
    const tagPills = container.querySelectorAll('p-tag[compact][variant="secondary"]')
    expect(tagPills.length).toBe(3)
    const texts = Array.from(tagPills).map((el) => el.textContent?.trim())
    expect(texts).toContain('frontend')
    expect(texts).toContain('backend')
    expect(texts).toContain('urgent')
    expect(texts).not.toContain('blocked')
    expect(texts).not.toContain('pds')
  })

  it('zero tags renders no p-tag pill elements with variant="secondary"', () => {
    // Positive anchor: one-tag case must have a pill first.
    const oneTagTask = makeTask({ id: 99, status: 'in-progress', priority: 'critical', tags: ['x'] })
    const { container: oneTagContainer } = renderCard(oneTagTask)
    expect(oneTagContainer.querySelectorAll('p-tag[compact][variant="secondary"]').length).toBe(1)

    // Now verify: zero tags → no pills
    const task = makeTask({ id: 1, status: 'in-progress', priority: 'critical', tags: [] })
    const { container } = renderCard(task)
    expect(container.querySelectorAll('p-tag[compact][variant="secondary"]').length).toBe(0)
  })

  it('overflow count indicator preserved when tags exceed TAG_PREVIEW_LIMIT=3', () => {
    // Anchor: individual tag pills must be p-tags (fails now — tags are still a span).
    // Both the pill assertion and overflow assertion must pass for the test to pass.
    const task = makeTask({
      id: 1,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c', 'd', 'e'],
    })
    const { container } = renderCard(task)
    // AC-4 anchor — fails now (tags still comma-joined in a span, not individual p-tags)
    const pills = container.querySelectorAll('p-tag[compact][variant="secondary"]')
    expect(pills.length).toBe(3)
    // Regression guard: overflow indicator preserved alongside tag pills
    const overflow = container.querySelector('[data-testid="card-tag-overflow"]')
    expect(overflow).not.toBeNull()
    expect(overflow!.textContent).toContain('+2')
  })

  it('overflow indicator absent when tags are within TAG_PREVIEW_LIMIT', () => {
    // Positive anchor: above-limit case must have both pills AND overflow.
    // Pill check fails now (no p-tag pills yet) → whole test fails correctly.
    const manyTask = makeTask({
      id: 99,
      status: 'in-progress',
      priority: 'critical',
      tags: ['a', 'b', 'c', 'd'],
    })
    const { container: manyContainer } = renderCard(manyTask)
    // AC-4 anchor — fails now
    expect(manyContainer.querySelectorAll('p-tag[compact][variant="secondary"]').length).toBe(3)
    expect(manyContainer.querySelector('[data-testid="card-tag-overflow"]')).not.toBeNull()

    // Main assertion: 3 tags → exactly 3 pills, no overflow
    const task = makeTask({ id: 1, status: 'in-progress', priority: 'critical', tags: ['a', 'b', 'c'] })
    const { container } = renderCard(task)
    expect(container.querySelectorAll('p-tag[compact][variant="secondary"]').length).toBe(3)
    expect(container.querySelector('[data-testid="card-tag-overflow"]')).toBeNull()
  })
})

// ─── AC-5: Existing state cue text spans preserved unchanged (regression guard) ─

describe('TestFromAC_CardCueTextPreserved', () => {
  // These are regression guards. Each test is anchored with an AC-1 check
  // (status chip is p-tag) so the test fails RED until BOTH the new PDS chip
  // AND the preserved cue span are present. Without the anchor, the cue tests
  // would pass against the current Card.tsx and not be truly RED.

  it('blocked card retains card-blocked-cue span with text "Blocked" alongside new status chip', () => {
    const task = makeTask({ id: 1, blocked: true, status: 'todo' })
    const { container } = renderCard(task)
    // AC-1 anchor — fails now (no status p-tag yet)
    expect(container.querySelector('p-tag[data-testid="card-status"]')).not.toBeNull()
    // AC-5 regression guard
    const cue = container.querySelector('[data-testid="card-blocked-cue"]')
    expect(cue).not.toBeNull()
    expect(cue!.textContent?.trim()).toBe('Blocked')
  })

  it('claimed card retains card-claimed-cue span with text "Claimed" alongside new status chip', () => {
    const task = makeTask({ id: 1, claimed: true, status: 'in-progress' })
    const { container } = renderCard(task)
    expect(container.querySelector('p-tag[data-testid="card-status"]')).not.toBeNull()
    const cue = container.querySelector('[data-testid="card-claimed-cue"]')
    expect(cue).not.toBeNull()
    expect(cue!.textContent?.trim()).toBe('Claimed')
  })

  it('deps-unmet card retains card-deps-unmet-cue span with text "Dependencies blocked"', () => {
    const task = makeTask({ id: 1, dep_status: 'blocked', status: 'todo' })
    const { container } = renderCard(task)
    expect(container.querySelector('p-tag[data-testid="card-status"]')).not.toBeNull()
    const cue = container.querySelector('[data-testid="card-deps-unmet-cue"]')
    expect(cue).not.toBeNull()
    expect(cue!.textContent?.trim()).toBe('Dependencies blocked')
  })

  it('dr-pending card retains card-dr-pending-cue span with text "Decision pending"', () => {
    const task = makeTask({ id: 7, status: 'todo' })
    const { container } = renderCard(task, new Set([7]))
    expect(container.querySelector('p-tag[data-testid="card-status"]')).not.toBeNull()
    const cue = container.querySelector('[data-testid="card-dr-pending-cue"]')
    expect(cue).not.toBeNull()
    expect(cue!.textContent?.trim()).toBe('Decision pending')
  })
})

// ─── AC-6: No inline hex color values in Card output ─────────────────────────

describe('TestFromAC_CardNoHexColors', () => {
  it('Card.tsx source contains no no-restricted-syntax eslint-disable comment', () => {
    // FAILS until builder removes the /* eslint-disable no-restricted-syntax */ line from Card.tsx
    const cardSrcPath = resolve(__dirname, '../components/Card.tsx')
    const src = readFileSync(cardSrcPath, 'utf-8')
    expect(src).not.toContain('eslint-disable no-restricted-syntax')
  })

  it('Card.tsx source imports PTag from @porsche-design-system/components-react', () => {
    // FAILS now: current Card.tsx has no PTag import.
    const cardSrcPath = resolve(__dirname, '../components/Card.tsx')
    const src = readFileSync(cardSrcPath, 'utf-8')
    expect(src).toContain('PTag')
    expect(src).toContain('@porsche-design-system/components-react')
  })

  it('Card.tsx source contains no inline hex color values', () => {
    // This is a regression guard — hex patterns like #fff or #aabbcc must not appear
    // in JSX style props. Currently passes (no hex in Card.tsx) but anchored below.
    const cardSrcPath = resolve(__dirname, '../components/Card.tsx')
    const src = readFileSync(cardSrcPath, 'utf-8')
    // Anchored to PTag import to ensure test fails until full implementation.
    expect(src).toContain('PTag')
    const hexPattern = /#[0-9a-fA-F]{3,8}\b/g
    const matches = src.match(hexPattern) ?? []
    expect(matches).toHaveLength(0)
  })

  it('rendered Card output has no elements with inline style containing hex color values', () => {
    // AC-1 anchor: status chip must be present (fails now).
    const task = makeTask({ id: 1, status: 'todo', priority: 'critical' })
    const { container } = renderCard(task)
    expect(container.querySelector('p-tag[data-testid="card-status"]')).not.toBeNull()
    // AC-6: no inline hex colors in rendered DOM
    const elementsWithStyle = container.querySelectorAll('[style]')
    for (const el of elementsWithStyle) {
      const style = el.getAttribute('style') ?? ''
      expect(style).not.toMatch(/#[0-9a-fA-F]{3,8}\b/)
    }
  })
})

// ─── AC-7: DOM_NODE_BUDGET adjusted for PDS component nodes ──────────────────

describe('TestFromAC_DOMBudgetAdjusted', () => {
  it('KanbanBoard.performance-700 DOM_NODE_BUDGET constant is > 6400 (increased for PDS nodes)', () => {
    // Current value is 6400. Builder must increase it to accommodate the extra DOM nodes
    // introduced by PTag and PIcon custom elements on each of the 700 cards.
    // This test FAILS until builder adjusts the constant upward.
    const perfTestPath = resolve(__dirname, 'KanbanBoard.performance-700.test.tsx')
    const src = readFileSync(perfTestPath, 'utf-8')
    const match = src.match(/const DOM_NODE_BUDGET\s*=\s*(\d+)/)
    expect(match).not.toBeNull()
    const budget = Number(match![1])
    expect(budget).toBeGreaterThan(6400)
  })
})
