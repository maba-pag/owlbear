import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { fireEvent, render, waitFor } from '@testing-library/react'
import KanbanBoard from '../KanbanBoard'
import type { Board, Task } from '../hooks/useBoard'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const SRC_DIR = resolve(__dirname, '..')
const COMPONENTS_DIR = resolve(SRC_DIR, 'components')
const SHELL_CSS = resolve(SRC_DIR, 'Shell.css')
const KANBAN_BOARD_TSX = resolve(SRC_DIR, 'KanbanBoard.tsx')
const KANBAN_BOARD_CSS = resolve(SRC_DIR, 'KanbanBoard.css')
const STYLES_TS = resolve(SRC_DIR, 'utils', 'styles.ts')
const HISTORY_SUBTAB_TSX = resolve(COMPONENTS_DIR, 'HistorySubtab.tsx')
const ACTIVITY_TAB_TSX = resolve(COMPONENTS_DIR, 'ActivityTab.tsx')

function extractCssImports(source: string): string[] {
  return Array.from(source.matchAll(/import\s+['"]([^'"]+\.css)['"]/g), (match) => match[1])
}

function hasSelectorWithDeclaration(css: string, selector: string): boolean {
  for (const match of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const selectorList = match[1]
      .split(',')
      .map((entry) => entry.trim())
      .filter((entry) => entry.length > 0)
    const declarations = match[2]
    if (!selectorList.includes(selector)) {
      continue
    }
    if (/:\s*[^;]+;/.test(declarations)) {
      return true
    }
  }

  return false
}

function findClassSelectorsWithRequiredTokens(css: string): string[] {
  const classBlockPattern = /\.([a-zA-Z0-9_-]+)\s*\{([\s\S]*?)\}/g
  const classNames: string[] = []

  for (const match of css.matchAll(classBlockPattern)) {
    const className = match[1]
    const block = match[2]
    const hasSurface = block.includes('var(--pds-background-surface)')
    const hasShadow = block.includes('var(--pds-shadow-md)')
    const hasRadius = block.includes('var(--pds-radius-md)')
    if (hasSurface && hasShadow && hasRadius) {
      classNames.push(className)
    }
  }

  return classNames
}

function makeBoard(): Board {
  return {
    statuses: [{ name: 'backlog' }, { name: 'todo' }, { name: 'done' }],
    priorities: ['low', 'normal', 'high'],
    valid_transitions: {
      backlog: ['todo'],
      todo: ['done'],
      done: [],
    },
  }
}

function makeTask(): Task {
  return {
    id: 1,
    title: 'Task 1',
    status: 'backlog',
    priority: 'normal',
    updated: '2026-05-13T00:00:00+00:00',
    tags: [],
    blocked: false,
    block_reason: null,
    claimed: false,
  }
}

describe('TestFromAC_ShellTokenMigration_1542', () => {
  it('AC-1: Shell.css has zero --pds-theme-light-* tokens and at least 5 --pds-* token references', () => {
    const css = readFileSync(SHELL_CSS, 'utf-8')
    const legacy = css.match(/--pds-theme-light-[a-z0-9-]+/g) ?? []
    const agnostic = css.match(/--pds-[a-z0-9-]+/g) ?? []

    expect(legacy, 'Shell.css must not contain legacy --pds-theme-light-* tokens').toHaveLength(0)
    expect(
      agnostic.length,
      'Shell.css must include at least 5 --pds-* token references to guard against empty/gutted file',
    ).toBeGreaterThanOrEqual(5)
  })
})

describe('TestFromAC_ContextMenuCssWiring_1542', () => {
  it('AC-2: KanbanBoard.tsx imports ./KanbanBoard.css', () => {
    const source = readFileSync(KANBAN_BOARD_TSX, 'utf-8')
    expect(source).toMatch(/import\s+['"]\.\/KanbanBoard\.css['"]/)
  })

  it('AC-2: KanbanBoard.css has a context-menu class rule using --pds-background-surface, --pds-shadow-md, --pds-radius-md', () => {
    expect(existsSync(KANBAN_BOARD_CSS), `KanbanBoard.css must exist at ${KANBAN_BOARD_CSS}`).toBe(true)
    const css = readFileSync(KANBAN_BOARD_CSS, 'utf-8')

    const classNames = findClassSelectorsWithRequiredTokens(css)
    expect(
      classNames.length,
      'KanbanBoard.css must define at least one class rule containing var(--pds-background-surface), var(--pds-shadow-md), and var(--pds-radius-md)',
    ).toBeGreaterThan(0)
  })

  it('AC-2: rendered context-menu element has the CSS class declared in KanbanBoard.css', async () => {
    const css = readFileSync(KANBAN_BOARD_CSS, 'utf-8')
    const classNames = findClassSelectorsWithRequiredTokens(css)
    expect(classNames.length).toBeGreaterThan(0)

    const { container } = render(
      <KanbanBoard
        board={makeBoard()}
        tasks={[makeTask()]}
        loading={false}
        error={null}
      />,
    )

    await waitFor(() => {
      expect(container.querySelector('[data-testid="task-card"][data-id="1"]')).not.toBeNull()
    })

    const card = container.querySelector('[data-testid="task-card"][data-id="1"]') as HTMLElement
    fireEvent.contextMenu(card)

    await waitFor(() => {
      const menu = container.querySelector('[data-testid="context-menu"]') as HTMLElement | null
      expect(menu).not.toBeNull()
      const menuClassList = Array.from(menu!.classList)
      expect(menuClassList.some((className) => classNames.includes(className))).toBe(true)
    })
  })
})

describe('TestFromAC_SecondaryCssMigration_1542', () => {
  it('AC-3: styles.ts is absent OR rowStyleForState named export is removed', () => {
    if (!existsSync(STYLES_TS)) {
      expect(existsSync(STYLES_TS)).toBe(false)
      return
    }

    const stylesSource = readFileSync(STYLES_TS, 'utf-8')

    expect(stylesSource).not.toMatch(/export\s+(?:const|let|var|function|class)\s+rowStyleForState\b/)
    expect(stylesSource).not.toMatch(/export\s+function\s+rowStyleForState\s*\(/)
    expect(stylesSource).not.toMatch(/export\s*\{[^}]*\browStyleForState\b[^}]*\}/)
  })

  it('AC-3: HistorySubtab.tsx and ActivityTab.tsx no longer import rowStyleForState', () => {
    const historySource = readFileSync(HISTORY_SUBTAB_TSX, 'utf-8')
    const activitySource = readFileSync(ACTIVITY_TAB_TSX, 'utf-8')

    expect(historySource).not.toMatch(/rowStyleForState/)
    expect(activitySource).not.toMatch(/rowStyleForState/)
  })

  it('AC-3: both components import the same CSS file and that file styles blocked/rejected/stuck data-state selectors', () => {
    const historySource = readFileSync(HISTORY_SUBTAB_TSX, 'utf-8')
    const activitySource = readFileSync(ACTIVITY_TAB_TSX, 'utf-8')

    const historyCssImports = extractCssImports(historySource)
    const activityCssImports = extractCssImports(activitySource)

    expect(historyCssImports.length, 'HistorySubtab.tsx must import a CSS file for data-state row styles').toBeGreaterThan(0)
    expect(activityCssImports.length, 'ActivityTab.tsx must import a CSS file for data-state row styles').toBeGreaterThan(0)

    const sharedCssImport = historyCssImports.find((path) => activityCssImports.includes(path))
    expect(sharedCssImport, 'HistorySubtab.tsx and ActivityTab.tsx must import the same CSS file').toBeTruthy()

    const cssPath = resolve(COMPONENTS_DIR, sharedCssImport!)
    expect(existsSync(cssPath), `Shared CSS file must exist: ${cssPath}`).toBe(true)

    const css = readFileSync(cssPath, 'utf-8')
    expect(
      hasSelectorWithDeclaration(css, '[data-state="blocked"]'),
      'CSS file must include [data-state="blocked"] selector with declaration(s)',
    ).toBe(true)
    expect(
      hasSelectorWithDeclaration(css, '[data-state="rejected"]'),
      'CSS file must include [data-state="rejected"] selector with declaration(s)',
    ).toBe(true)
    expect(
      hasSelectorWithDeclaration(css, '[data-state="stuck"]'),
      'CSS file must include [data-state="stuck"] selector with declaration(s)',
    ).toBe(true)
  })
})
