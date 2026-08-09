import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import CockpitShell from './CockpitShell'

vi.mock('./components/ThemeToggle', () => ({
  default: () => <button type="button">Theme</button>,
}))

vi.mock('./routes', () => {
  const routeConfig = [
    { path: '/delivery', label: 'Delivery', icon: 'work', component: () => <main>Work portfolio</main> },
    { path: '/memory', label: 'Memory', icon: 'memory', component: () => <main>Memory workspace</main> },
    { path: '/ideas', label: 'Ideas', icon: 'ideas', component: () => <main>Ideas workspace</main> },
  ]
  return {
    routeConfig,
    routeForPath: (pathname: string) => routeConfig.find((route) => {
      if (route.path !== '/delivery') return pathname === route.path
      const segments = pathname.split('/').filter(Boolean)
      return segments[0] === 'delivery' && (segments.length === 1 || segments.length === 3)
    }),
  }
})

it('navigates between the target product areas', async () => {
  render(
    <MemoryRouter initialEntries={['/delivery']}>
      <CockpitShell />
    </MemoryRouter>,
  )

  expect(screen.getByText('Work portfolio')).toBeInTheDocument()
  const desktopNavigation = screen.getByTestId('desktop-product-navigation')
  expect(desktopNavigation.querySelector('a[title="Delivery"]')).toHaveAttribute('aria-current', 'page')

  fireEvent.click(desktopNavigation.querySelector('a[title="Memory"]')!)

  expect(await screen.findByText('Memory workspace')).toBeInTheDocument()
  expect(desktopNavigation.querySelector('a[title="Memory"]')).toHaveAttribute('aria-current', 'page')
})

it('opens labeled product navigation from the compact mobile header', () => {
  render(
    <MemoryRouter initialEntries={['/delivery']}>
      <CockpitShell />
    </MemoryRouter>,
  )

  fireEvent.click(screen.getByText('Open navigation'))

  const flyout = document.querySelector('p-flyout') as HTMLElement & { open: boolean }
  expect(flyout.open).toBe(true)
  expect(flyout.querySelector('p-link-pure')).toHaveTextContent('Delivery')
})

it('renders Not Found for an unmatched path', () => {
  render(
    <MemoryRouter initialEntries={['/unknown']}>
      <CockpitShell />
    </MemoryRouter>,
  )

  expect(screen.getByTestId('not-found-view')).toBeInTheDocument()
  expect(screen.getByText('Go to Delivery portfolio')).toBeInTheDocument()
})
