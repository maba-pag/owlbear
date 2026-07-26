import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import NativeShell from '../NativeShell'

vi.mock('../hooks/NativeChangeProvider', () => ({
  useNativeChangeSelection: vi.fn(() => ({ selectedChangeId: 'change-a' })),
}))

vi.mock('../routes', () => ({
  routeConfig: [
    { path: '/', label: 'Specification', icon: 'specification', component: () => <div>Specification content</div> },
    { path: '/delivery', label: 'Delivery', icon: 'delivery', component: () => <div>Delivery content</div> },
    { path: '/memories', label: 'Memory', icon: 'memory', component: () => <div>Memory content</div> },
    { path: '/ideas', label: 'Ideas', icon: 'ideas', component: () => <div>Ideas content</div> },
  ],
}))

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>
}

describe('NativeShell', () => {
  afterEach(() => vi.clearAllMocks())

  it('presents Specification and Delivery as peer product phases', () => {
    render(
      <MemoryRouter initialEntries={['/?change=change-a']}>
        <NativeShell />
      </MemoryRouter>,
    )

    const nav = screen.getByRole('navigation', { name: 'Product phases' })
    expect(nav).toHaveTextContent('Specification')
    expect(nav).toHaveTextContent('Delivery')
    expect(screen.getByText('Specification content')).toBeInTheDocument()
  })

  it('preserves selected change identity when navigating phases', () => {
    render(
      <MemoryRouter initialEntries={['/?change=change-a']}>
        <NativeShell />
        <LocationProbe />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByText('Delivery'))

    expect(screen.getByTestId('location')).toHaveTextContent('/delivery?change=change-a')
    expect(screen.getByText('Delivery content')).toBeInTheDocument()
  })

  it('translates retained Memory task-link events into native Delivery job URLs', () => {
    render(
      <MemoryRouter initialEntries={['/memories?change=change-a']}>
        <NativeShell />
        <LocationProbe />
      </MemoryRouter>,
    )

    act(() => window.dispatchEvent(new CustomEvent('cockpit:open-task-detail', { detail: { taskId: 42 } })))

    expect(screen.getByTestId('location')).toHaveTextContent('/delivery?change=change-a&job=42')
  })
})
