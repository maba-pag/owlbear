import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import CockpitShell from './CockpitShell'

vi.mock('./components/ThemeToggle', () => ({
  default: () => <button type="button">Theme</button>,
}))

vi.mock('./routes', () => ({
  routeConfig: [
    { path: '/work', label: 'Work', icon: 'work', component: () => <main>Work portfolio</main> },
    { path: '/memories', label: 'Memory', icon: 'memory', component: () => <main>Memory workspace</main> },
    { path: '/ideas', label: 'Ideas', icon: 'ideas', component: () => <main>Ideas workspace</main> },
  ],
}))

it('navigates between the target product areas', async () => {
  render(
    <MemoryRouter initialEntries={['/work']}>
      <CockpitShell />
    </MemoryRouter>,
  )

  expect(screen.getByText('Work portfolio')).toBeInTheDocument()
  expect(screen.getByText('Work').closest('p-link')).toHaveAttribute('aria-current', 'page')

  fireEvent.click(screen.getByText('Memory').closest('p-link')!)

  expect(await screen.findByText('Memory workspace')).toBeInTheDocument()
  expect(screen.getByText('Memory').closest('p-link')).toHaveAttribute('aria-current', 'page')
})
