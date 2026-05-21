import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import App from './App'

describe('TestFromAC_AppShellIntegration', () => {
  it('App renders status-bar region (Shell integrated into App)', () => {
    const { container } = render(<App />)
    expect(container.querySelector('[data-region="status-bar"]')).not.toBeNull()
  })

  it('App renders nav-rail region (Shell integrated into App)', () => {
    const { container } = render(<App />)
    expect(container.querySelector('[data-region="nav-rail"]')).not.toBeNull()
  })

  it('App renders workspace region (Shell integrated into App)', () => {
    const { container } = render(<App />)
    expect(container.querySelector('[data-region="workspace"]')).not.toBeNull()
  })

  it('App does not render the retired task sidecar region', () => {
    const { container } = render(<App />)
    expect(container.querySelector('[data-region="sidecar"]')).toBeNull()
    expect(container.querySelector('.shell')?.hasAttribute('data-no-sidecar')).toBe(true)
  })

  it('App renders contextual region (Shell integrated into App)', () => {
    const { container } = render(<App />)
    expect(container.querySelector('[data-region="contextual"]')).not.toBeNull()
  })
})
