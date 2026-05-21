import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

// ─── Fetch stub (file-level) ──────────────────────────────────────────────────
// Route "/" mounts KanbanBoard which fires fetch on mount.
// Never-resolving promise keeps KanbanBoard in loading state, preventing state
// updates after assertions and eliminating React act() warnings.
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn((_url: string, init?: RequestInit) =>
    new Promise<never>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    }),
  ))
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function renderShell(route = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

describe('TestFromAC_AppShell', () => {
  describe('CSS Grid regions', () => {
    it('renders status-bar region', () => {
      const { container } = renderShell()
      expect(container.querySelector('[data-region="status-bar"]')).not.toBeNull()
    })

    it('renders nav-rail region', () => {
      const { container } = renderShell()
      expect(container.querySelector('[data-region="nav-rail"]')).not.toBeNull()
    })

    it('renders workspace region', () => {
      const { container } = renderShell()
      expect(container.querySelector('[data-region="workspace"]')).not.toBeNull()
    })

    it('does not render the retired task sidecar region', () => {
      const { container } = renderShell()
      expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
      expect(container.querySelector('.shell')?.hasAttribute('data-no-sidecar')).toBe(true)
    })

    it('renders contextual region (reserved/empty)', () => {
      const { container } = renderShell()
      expect(container.querySelector('[data-region="contextual"]')).not.toBeNull()
    })
  })

  describe('Product identity', () => {
    it('renders OwlBear identity in the canvas header start slot', () => {
      const { container } = renderShell()
      const identity = container.querySelector('[data-testid="app-identity"]')
      expect(identity).toHaveAttribute('slot', 'header-start')
      expect(identity).toHaveAttribute('aria-label', 'OwlBear Dashboard')
      expect(identity?.textContent).toContain('OwlBear')
      expect(identity?.textContent).toContain('Dashboard')
    })

    it('pins the hidden PDS brand and utility slots to explicit header columns', () => {
      const { container } = renderShell()
      const canvas = container.querySelector('p-canvas.shell')
      const override = canvas?.shadowRoot?.querySelector('[data-cockpit-canvas-override]')

      expect(override?.textContent).toContain('.header__area--start{grid-column:1')
      expect(override?.textContent).toContain('.header__area--end{grid-column:3')
    })

    it('does not place product identity in the global status bar', () => {
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      expect(statusBar?.textContent).not.toContain('OwlBear')
    })
  })

  describe('Nav rail', () => {
    it('renders at least one surface selector item inside nav-rail', () => {
      const { container } = renderShell()
      const navRail = container.querySelector('[data-region="nav-rail"]')
      expect(navRail?.querySelector('[data-surface]')).not.toBeNull()
    })

    it('kanban surface selector is active by default (aria-current="page")', () => {
      const { container } = renderShell()
      const navRail = container.querySelector('[data-region="nav-rail"]')
      const activeItem = navRail?.querySelector('[data-surface="kanban"][aria-current="page"]')
      expect(activeItem).not.toBeNull()
    })
  })

  describe('Status bar', () => {
    it('renders traffic-light placeholder', () => {
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      expect(statusBar?.querySelector('[data-testid="traffic-light"]')).not.toBeNull()
    })

    it('does not duplicate board task count in the global status bar', () => {
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      expect(statusBar?.querySelector('[data-testid="task-count"]')).toBeNull()
    })

    it('keeps healthy workspace status compact in the global status bar', () => {
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      const badge = statusBar?.querySelector('[data-testid="health-badge"]')
      expect(badge?.textContent?.trim()).toBe('')
      expect(badge).toHaveAttribute('title', 'Workspace status: OK')
    })

    it('renders compact theme mode indicator in the global status bar', () => {
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      const toggle = statusBar?.querySelector('[data-testid="theme-toggle"]')
      expect(toggle?.querySelector('[data-testid="theme-mode-indicator"]')).not.toBeNull()
      expect(toggle).toHaveAttribute('aria-label', expect.stringMatching(/Theme mode/))
    })
  })

  describe('Routing', () => {
    it('route "/" renders KanbanBoard (loading indicator visible) in workspace region', () => {
      const { container } = renderShell('/')
      const workspace = container.querySelector('[data-region="workspace"]')
      expect(workspace?.querySelector('[data-testid="loading-indicator"]')).not.toBeNull()
    })

    it('route "/hello" does not render hello content in workspace region', () => {
      const { container } = renderShell('/hello')
      const workspace = container.querySelector('[data-region="workspace"]')
      expect(workspace?.textContent?.toLowerCase()).not.toContain('hello')
    })

    it('route "/hello" keeps shell regions present without restoring the task sidecar', () => {
      const { container } = renderShell('/hello')
      expect(container.querySelector('[data-region="status-bar"]')).not.toBeNull()
      expect(container.querySelector('[data-region="nav-rail"]')).not.toBeNull()
      expect(container.querySelector('[data-region="workspace"]')).not.toBeNull()
      expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
      expect(container.querySelector('[data-region="contextual"]')).not.toBeNull()
    })
  })

  describe('Task detail surface', () => {
    it('task detail modal is absent until a task is selected', () => {
      const { container } = renderShell()
      expect(container.querySelector('[data-testid="task-detail-modal"]')).toBeNull()
    })

    it('PCanvas end sidebar slots are not used for task detail', () => {
      const { container } = renderShell()
      expect(container.querySelector('[slot="sidebar-end"]')).toBeNull()
      expect(container.querySelector('[slot="sidebar-end-header"]')).toBeNull()
    })
  })
})

describe('TestBuilderDiscovered', () => {
  it('kanban nav-rail button contains an icon element (p-icon or svg)', () => {
    const { container } = renderShell()
    const kanbanBtn = container.querySelector('[data-region="nav-rail"] [data-surface="kanban"]')
    const icon = kanbanBtn?.querySelector('p-icon, svg')
    expect(icon).not.toBeNull()
  })

  it('nav-rail button keeps its text as tooltip and aria-label instead of visible label text', () => {
    const { container } = renderShell()
    const kanbanBtn = container.querySelector('[data-region="nav-rail"] [data-surface="kanban"]')
    expect(kanbanBtn?.getAttribute('aria-label')).toBe('Kanban')
    expect(kanbanBtn?.getAttribute('title')).toBe('Kanban')
    expect(kanbanBtn?.textContent).not.toContain('Kanban')
  })
})
