import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders PHeading component in DOM', () => {
    const { container } = render(<App />)
    expect(container.querySelector('p-heading')).not.toBeNull()
  })

  it('PHeading contains visible heading text', () => {
    const { container } = render(<App />)
    expect(container.textContent).toContain('OwlBear Cockpit')
  })
})
