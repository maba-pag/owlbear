import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import Shell from '../Shell'
import { CockpitProvider } from '../hooks/CockpitProvider'

vi.mock('../hooks/EventSourceProvider', () => ({
  useSSEEvent: vi.fn(() => ({ status: 'closed', mtime: null })),
}))

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

function renderShell() {
  return render(
    <PorscheDesignSystemProvider>
      <MemoryRouter initialEntries={['/']}>
        <CockpitProvider>
          <Shell />
        </CockpitProvider>
      </MemoryRouter>
    </PorscheDesignSystemProvider>,
  )
}

function getCollapseToggle(container: HTMLElement): HTMLElement {
  const toggle = container.querySelector('[data-testid="sidecar-collapse"]')
  if (!toggle) {
    throw new Error('sidecar-collapse toggle not found')
  }
  return toggle as HTMLElement
}

describe('TestFromAC_SidecarCollapse_1541', () => {
  it('AC-1: sidecar collapse toggle exposes disclosure ARIA and flips aria-expanded to false on click', () => {
    const { container } = renderShell()
    const toggle = getCollapseToggle(container)

    expect(toggle.getAttribute('aria-expanded')).toBe('true')

    const ariaControlsId = toggle.getAttribute('aria-controls')
    expect(ariaControlsId).toBeTruthy()
    const sidecarRegion = container.querySelector('[data-region="sidecar"]')
    expect(sidecarRegion).not.toBeNull()
    expect(sidecarRegion!.getAttribute('id')).toBe(ariaControlsId)

    fireEvent.click(toggle)

    expect(toggle.getAttribute('aria-expanded')).toBe('false')
  })

  it('AC-2: collapsed state persists after rerender', () => {
    const { container, rerender } = renderShell()
    const toggle = getCollapseToggle(container)

    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('false')

    rerender(
      <PorscheDesignSystemProvider>
        <MemoryRouter initialEntries={['/']}>
          <CockpitProvider>
            <Shell />
          </CockpitProvider>
        </MemoryRouter>
      </PorscheDesignSystemProvider>,
    )

    const persistedToggle = getCollapseToggle(container)
    expect(persistedToggle.getAttribute('aria-expanded')).toBe('false')
  })
})
