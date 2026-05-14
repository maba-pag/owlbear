/**
 * Task #1548 — P3-06: impl — theme toggle UI: status bar button
 * Covers: AC-1 (renders button), AC-2 (click → toggle), AC-3 (distinct descriptors)
 *
 * RED phase: ThemeToggle component does not exist yet.
 * Import fails → entire file fails at collection (ImportError).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { PorscheDesignSystemProvider } from '@porsche-design-system/components-react'
import ThemeToggle from '../components/ThemeToggle'
import { useTheme } from '../hooks/useTheme'

vi.mock('../hooks/useTheme', () => ({
  useTheme: vi.fn(),
}))

type ThemeMode = 'light' | 'dark' | 'auto'

const mockedUseTheme = vi.mocked(useTheme)

function renderThemeToggle(theme: ThemeMode = 'light', toggle = vi.fn()) {
  mockedUseTheme.mockReturnValue({ theme, toggle, isDark: theme === 'dark' })
  const view = render(
    <PorscheDesignSystemProvider>
      <ThemeToggle />
    </PorscheDesignSystemProvider>,
  )
  return { ...view, toggle }
}

function getButtonDescriptor(theme: ThemeMode): string {
  const { unmount } = renderThemeToggle(theme)
  const button = screen.getByRole('button')
  const descriptor = `${button.getAttribute('aria-label') ?? ''}|${button.textContent ?? ''}`
  unmount()
  return descriptor
}

describe('TestFromAC_ThemeToggleComponent_1548', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // AC-1: ThemeToggle default export renders a button-role element
  it('AC-1 happy: ThemeToggle renders an element with role="button"', () => {
    renderThemeToggle('light')

    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('AC-1 edge: ThemeToggle renders exactly one button element (no duplicate controls)', () => {
    renderThemeToggle('dark')

    expect(screen.getAllByRole('button')).toHaveLength(1)
  })

  // AC-2: clicking the button calls useTheme().toggle once per click
  it('AC-2 happy: single click invokes useTheme().toggle once', () => {
    const { toggle } = renderThemeToggle('light')

    fireEvent.click(screen.getByRole('button'))

    expect(toggle).toHaveBeenCalledTimes(1)
  })

  it('AC-2 edge: toggle is not called before any click', () => {
    const { toggle } = renderThemeToggle('light')

    expect(toggle).not.toHaveBeenCalled()
  })

  it('AC-2 boundary: two clicks invoke toggle exactly twice', () => {
    const { toggle } = renderThemeToggle('dark')

    fireEvent.click(screen.getByRole('button'))
    fireEvent.click(screen.getByRole('button'))

    expect(toggle).toHaveBeenCalledTimes(2)
  })

  // AC-3: combined aria-label + textContent descriptor is unique for each of 3 states
  it('AC-3 happy: descriptors are distinct across light, dark, and auto states (3 unique values)', () => {
    const descriptors = [
      getButtonDescriptor('light'),
      getButtonDescriptor('dark'),
      getButtonDescriptor('auto'),
    ]

    expect(new Set(descriptors).size).toBe(3)
  })

  it('AC-3 boundary: light-state descriptor differs from dark-state descriptor', () => {
    expect(getButtonDescriptor('light')).not.toBe(getButtonDescriptor('dark'))
  })

  it('AC-3 boundary: dark-state descriptor differs from auto-state descriptor', () => {
    expect(getButtonDescriptor('dark')).not.toBe(getButtonDescriptor('auto'))
  })

  it('AC-3 boundary: auto-state descriptor differs from light-state descriptor', () => {
    expect(getButtonDescriptor('auto')).not.toBe(getButtonDescriptor('light'))
  })
})
