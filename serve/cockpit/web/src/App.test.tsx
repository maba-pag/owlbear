import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('./CockpitShell', () => ({
  default: () => <div data-testid="cockpit-shell" data-no-sidecar="" />,
}))

describe('App target shell integration', () => {
  it('renders the target product shell', () => {
    const { getByTestId } = render(<App />)
    expect(getByTestId('cockpit-shell')).toBeInTheDocument()
  })
})
