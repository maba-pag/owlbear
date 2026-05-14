import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const SRC_DIR = resolve(__dirname, '..')
const COMPONENTS_DIR = resolve(SRC_DIR, 'components')

const FILTER_PANEL_TSX = resolve(COMPONENTS_DIR, 'FilterPanel.tsx')
const FILTER_PANEL_CSS = resolve(COMPONENTS_DIR, 'FilterPanel.css')
const KANBAN_BOARD_TSX = resolve(SRC_DIR, 'KanbanBoard.tsx')
const STYLES_TS = resolve(SRC_DIR, 'utils', 'styles.ts')

describe('TestFromAC_FilterPanelCSS_1550', () => {
  it('AC-1: FilterPanel.css exists in src/components/', () => {
    expect(existsSync(FILTER_PANEL_CSS), `FilterPanel.css must exist at ${FILTER_PANEL_CSS}`).toBe(true)
  })

  it('AC-1: FilterPanel.tsx imports FilterPanel.css', () => {
    const source = readFileSync(FILTER_PANEL_TSX, 'utf-8')
    expect(source, 'FilterPanel.tsx must import ./FilterPanel.css').toMatch(
      /import\s+['"]\.\/FilterPanel\.css['"]/,
    )
  })

  it('AC-1: FilterPanel.tsx root container element has a className attribute', () => {
    const source = readFileSync(FILTER_PANEL_TSX, 'utf-8')
    // The root element contains id="filter-panel"; className must appear in the same JSX element
    expect(
      source,
      'FilterPanel.tsx root div (id="filter-panel") must have a className attribute for CSS targeting',
    ).toMatch(
      /id="filter-panel"[\s\S]{0,300}className=|className=[\s\S]{0,300}id="filter-panel"/,
    )
  })

  it('AC-1: FilterPanel.css applies var(--pds-background-surface) for background', () => {
    const css = readFileSync(FILTER_PANEL_CSS, 'utf-8')
    expect(css, 'FilterPanel.css must apply var(--pds-background-surface) as background').toMatch(
      /background[^:]*:\s*[^;]*var\(--pds-background-surface\)/,
    )
  })

  it('AC-1: FilterPanel.css applies var(--pds-border-default) for border', () => {
    const css = readFileSync(FILTER_PANEL_CSS, 'utf-8')
    expect(css, 'FilterPanel.css must apply var(--pds-border-default) for border').toMatch(
      /border[^:]*:\s*[^;]*var\(--pds-border-default\)/,
    )
  })

  it('AC-1: FilterPanel.css applies var(--pds-spacing-md) for padding', () => {
    const css = readFileSync(FILTER_PANEL_CSS, 'utf-8')
    expect(css, 'FilterPanel.css must apply var(--pds-spacing-md) for padding').toMatch(
      /padding[^:]*:\s*[^;]*var\(--pds-spacing-md\)/,
    )
  })
})

describe('TestFromAC_StylesTsDeletion_1550', () => {
  it('AC-2: utils/styles.ts is deleted (file must not exist)', () => {
    expect(
      existsSync(STYLES_TS),
      `utils/styles.ts must be deleted; found at ${STYLES_TS}`,
    ).toBe(false)
  })
})

describe('TestFromAC_BoardGridTokens_1550', () => {
  it('AC-3: KanbanBoard.tsx board grid container uses var(--pds-spacing-md) for gap', () => {
    const source = readFileSync(KANBAN_BOARD_TSX, 'utf-8')
    expect(
      source,
      "KanbanBoard.tsx board grid gap must be var(--pds-spacing-md), not hardcoded '16px'",
    ).toMatch(/gap:\s*['"]var\(--pds-spacing-md\)['"]/)
  })

  it('AC-3: KanbanBoard.tsx board grid container uses overflowX: auto', () => {
    const source = readFileSync(KANBAN_BOARD_TSX, 'utf-8')
    expect(
      source,
      "KanbanBoard.tsx board grid overflowX must be 'auto', not 'hidden'",
    ).toMatch(/overflowX:\s*['"]auto['"]/)
  })
})
