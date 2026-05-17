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

/** Resolve the element controlled by the toggle via its aria-controls id. */
function getControlledElement(container: HTMLElement, toggle: HTMLElement): HTMLElement {
  const id = toggle.getAttribute('aria-controls')
  if (!id) throw new Error('toggle missing aria-controls attribute')
  const el = container.querySelector(`#${id}`)
  if (!el) throw new Error(`controlled element #${id} not found in DOM`)
  return el as HTMLElement
}

describe('TestFromAC_SidecarCollapse_1541', () => {
  it('AC-1: toggle is a native <button> with aria-expanded="true" and aria-controls within sidecar', () => {
    const { container } = renderShell()
    const toggle = getCollapseToggle(container)

    expect(toggle.tagName).toBe('BUTTON')
    expect(toggle.getAttribute('aria-expanded')).toBe('true')

    const ariaControlsId = toggle.getAttribute('aria-controls')
    expect(ariaControlsId).toBeTruthy()

    const controlled = container.querySelector(`#${ariaControlsId}`)
    expect(controlled).not.toBeNull()

    const sidecarRegion = container.querySelector('[data-region="sidecar"]')
    expect(sidecarRegion).not.toBeNull()
    expect(sidecarRegion!.contains(controlled) || sidecarRegion === controlled).toBe(true)
  })

  it('AC-1: controlled element does not have aria-hidden="true" in default state (panel starts open)', () => {
    const { container } = renderShell()
    const toggle = getCollapseToggle(container)
    const controlled = getControlledElement(container, toggle)

    expect(controlled.getAttribute('aria-hidden')).not.toBe('true')
  })

  it('AC-1: controlled element does not contain the toggle (containment proof)', () => {
    const { container } = renderShell()
    const toggle = getCollapseToggle(container)
    const controlled = getControlledElement(container, toggle)

    expect(controlled.contains(toggle)).toBe(false)
  })

  it('AC-1: clicking toggle sets aria-expanded="false" and controlled element aria-hidden="true"', () => {
    const { container } = renderShell()
    const toggle = getCollapseToggle(container)
    const controlled = getControlledElement(container, toggle)

    fireEvent.click(toggle)

    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(controlled.getAttribute('aria-hidden')).toBe('true')
  })

  it('AC-1: after collapse, re-queried toggle is in DOM and not a descendant of any aria-hidden="true" element (reopenability proof)', () => {
    const { container } = renderShell()
    const toggle = getCollapseToggle(container)
    fireEvent.click(toggle)

    const freshToggle = getCollapseToggle(container)
    let ancestor = freshToggle.parentElement
    while (ancestor) {
      expect(ancestor.getAttribute('aria-hidden')).not.toBe('true')
      ancestor = ancestor.parentElement
    }
  })

  it('AC-1 round-trip: second click restores aria-expanded="true" and controlled element is no longer aria-hidden', () => {
    const { container } = renderShell()
    const toggle = getCollapseToggle(container)
    const controlled = getControlledElement(container, toggle)

    // collapse
    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(controlled.getAttribute('aria-hidden')).toBe('true')

    // expand
    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(controlled.getAttribute('aria-hidden')).not.toBe('true')
  })

  it('AC-2: collapsed state persists after rerender — aria-expanded="false" and controlled element aria-hidden="true"', () => {
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
    const persistedControlled = getControlledElement(container, persistedToggle)
    expect(persistedToggle.getAttribute('aria-expanded')).toBe('false')
    expect(persistedControlled.getAttribute('aria-hidden')).toBe('true')
  })

  it('AC-2: after rerender, re-queried toggle is not a descendant of any aria-hidden="true" element (reopenability persists)', () => {
    const { container, rerender } = renderShell()
    const toggle = getCollapseToggle(container)

    fireEvent.click(toggle)

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
    let ancestor = persistedToggle.parentElement
    while (ancestor) {
      expect(ancestor.getAttribute('aria-hidden')).not.toBe('true')
      ancestor = ancestor.parentElement
    }
  })
})
