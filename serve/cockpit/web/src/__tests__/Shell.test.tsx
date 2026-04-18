import { describe, it, expect } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'

function renderShell(route = '/') {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={[route]}>
        <Shell />
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

    it('renders sidecar region', () => {
      const { container } = renderShell()
      expect(container.querySelector('[data-region="sidecar"]')).not.toBeNull()
    })

    it('renders contextual region (reserved/empty)', () => {
      const { container } = renderShell()
      expect(container.querySelector('[data-region="contextual"]')).not.toBeNull()
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

    it('renders task count placeholder', () => {
      const { container } = renderShell()
      const statusBar = container.querySelector('[data-region="status-bar"]')
      expect(statusBar?.querySelector('[data-testid="task-count"]')).not.toBeNull()
    })
  })

  describe('Routing', () => {
    it('route "/" renders kanban surface placeholder in workspace region', () => {
      const { container } = renderShell('/')
      const workspace = container.querySelector('[data-region="workspace"]')
      expect(workspace?.textContent?.toLowerCase()).toContain('kanban')
    })

    it('route "/hello" renders hello content in workspace region', () => {
      const { container } = renderShell('/hello')
      const workspace = container.querySelector('[data-region="workspace"]')
      expect(workspace?.textContent?.toLowerCase()).toContain('hello')
    })

    it('route "/hello" keeps all 5 grid regions present (shell layout unchanged)', () => {
      const { container } = renderShell('/hello')
      expect(container.querySelector('[data-region="status-bar"]')).not.toBeNull()
      expect(container.querySelector('[data-region="nav-rail"]')).not.toBeNull()
      expect(container.querySelector('[data-region="workspace"]')).not.toBeNull()
      expect(container.querySelector('[data-region="sidecar"]')).not.toBeNull()
      expect(container.querySelector('[data-region="contextual"]')).not.toBeNull()
    })
  })

  describe('Sidecar tabs', () => {
    it('sidecar region contains a p-tabs element', () => {
      const { container } = renderShell()
      const sidecar = container.querySelector('[data-region="sidecar"]')
      expect(sidecar?.querySelector('p-tabs')).not.toBeNull()
    })

    it('sidecar has a Detail tab', () => {
      const { container } = renderShell()
      const sidecar = container.querySelector('[data-region="sidecar"]')
      const tabItems = Array.from(sidecar?.querySelectorAll('p-tabs-item') ?? [])
      const labels = tabItems.map(el => el.getAttribute('label'))
      expect(labels).toContain('Detail')
    })

    it('sidecar has an Activity tab', () => {
      const { container } = renderShell()
      const sidecar = container.querySelector('[data-region="sidecar"]')
      const tabItems = Array.from(sidecar?.querySelectorAll('p-tabs-item') ?? [])
      const labels = tabItems.map(el => el.getAttribute('label'))
      expect(labels).toContain('Activity')
    })

    it('switching to Activity tab shows Activity content area', () => {
      const { container } = renderShell()
      const sidecar = container.querySelector('[data-region="sidecar"]') as HTMLElement
      const tabs = sidecar.querySelector('p-tabs') as HTMLElement
      fireEvent(tabs, new CustomEvent('tabChange', { detail: { activeTabIndex: 1 }, bubbles: true }))
      expect(sidecar.querySelector('[data-tab-content="activity"]')).not.toBeNull()
    })

    it('Detail tab content area is present on initial render', () => {
      const { container } = renderShell()
      const sidecar = container.querySelector('[data-region="sidecar"]')
      expect(sidecar?.querySelector('[data-tab-content="detail"]')).not.toBeNull()
    })
  })
})
