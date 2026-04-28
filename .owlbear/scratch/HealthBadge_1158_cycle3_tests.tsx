/**
 * Cycle 3 test additions for #1158: HealthBadge component.
 *
 * BUILDER INSTRUCTION:
 * Append these tests inside the existing `describe('TestFromAC_HealthBadge', () => { ... })`
 * block in serve/cockpit/web/src/__tests__/HealthBadge.test.tsx,
 * immediately before the closing `})` of the describe block.
 *
 * These tests strengthen AC 2 (exact badge text) and AC 4 (per-<li> row binding)
 * per Architecture Review Cycle 3 directives. The implementation is already correct;
 * these assertions raise the mutation-resistance bar from toContain → toBe for text
 * and from aggregate popover.textContent → per-row li.textContent for field binding.
 */

  // ── Cycle 3 AC 2 refinements: exact badge textContent using toBe(), not toContain() ──

  it('badge textContent is exactly "Health OK" when items is empty (exact toBe)', () => {
    const { container } = renderBadge([])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    expect(badge.textContent).toBe('Health OK')
  })

  it('badge textContent is exactly "Health 1 issues" for single item (exact toBe)', () => {
    const { container } = renderBadge([ITEM_A])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    expect(badge.textContent).toBe('Health 1 issues')
  })

  it('badge textContent is exactly "Health 2 issues" for two items (exact toBe)', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    const badge = container.querySelector('[data-testid="health-badge"]')!
    expect(badge.textContent).toBe('Health 2 issues')
  })

  // ── Cycle 3 AC 4 refinements: per-<li> row field binding, not aggregate popover.textContent ──

  it('first list row textContent contains ITEM_A file_path, code, and detail (per-row)', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    const rows = popover.querySelectorAll('li')
    expect(rows[0].textContent).toContain(ITEM_A.file_path)
    expect(rows[0].textContent).toContain(ITEM_A.code)
    expect(rows[0].textContent).toContain(ITEM_A.detail)
  })

  it('second list row textContent contains ITEM_B file_path, code, and detail (per-row)', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    const rows = popover.querySelectorAll('li')
    expect(rows[1].textContent).toContain(ITEM_B.file_path)
    expect(rows[1].textContent).toContain(ITEM_B.code)
    expect(rows[1].textContent).toContain(ITEM_B.detail)
  })

  it('each list row contains only its own item fields — no cross-row field leakage', () => {
    const { container } = renderBadge([ITEM_A, ITEM_B])
    fireEvent.click(container.querySelector('[data-testid="health-badge"]')!)
    const popover = container.querySelector('[data-testid="health-badge-popover"]')!
    const rows = popover.querySelectorAll('li')
    // Row 0 has ITEM_A data, must not contain ITEM_B data
    expect(rows[0].textContent).not.toContain(ITEM_B.file_path)
    expect(rows[0].textContent).not.toContain(ITEM_B.code)
    expect(rows[0].textContent).not.toContain(ITEM_B.detail)
    // Row 1 has ITEM_B data, must not contain ITEM_A data
    expect(rows[1].textContent).not.toContain(ITEM_A.file_path)
    expect(rows[1].textContent).not.toContain(ITEM_A.code)
    expect(rows[1].textContent).not.toContain(ITEM_A.detail)
  })
