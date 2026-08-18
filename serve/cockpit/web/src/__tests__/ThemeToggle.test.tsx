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

function renderThemeToggle(theme: ThemeMode = 'light', toggle = vi.fn(), selectTheme = vi.fn()) {
  mockedUseTheme.mockReturnValue({
    theme,
    toggle,
    selectTheme,
    isDark: theme === 'dark',
  })

  const view = render(
    <PorscheDesignSystemProvider>
      <ThemeToggle />
    </PorscheDesignSystemProvider>,
  )

  return { ...view, toggle, selectTheme }
}

function renderCompactThemeToggle(theme: ThemeMode = 'light', toggle = vi.fn(), selectTheme = vi.fn()) {
  mockedUseTheme.mockReturnValue({
    theme,
    toggle,
    selectTheme,
    isDark: theme === 'dark',
  })

  const view = render(
    <PorscheDesignSystemProvider>
      <ThemeToggle compact />
    </PorscheDesignSystemProvider>,
  )

  return { ...view, toggle, selectTheme }
}

function getButtonDescriptor(theme: ThemeMode): string {
  const { container, unmount } = renderThemeToggle(theme)
  const button = container.querySelector('[data-testid="theme-toggle"]')
  const descriptor = `${button?.getAttribute('aria-label') ?? ''}|${button?.textContent ?? ''}`
  unmount()
  return descriptor
}

describe('TestFromAC_ThemeToggle_1540', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AC-1: renders an accessible PDS button-pure element', () => {
    const { container } = renderThemeToggle('light')

    const button = container.querySelector('[data-testid="theme-toggle"]')
    expect(button).toBeInTheDocument()
    expect(button!.tagName.toLowerCase()).toBe('p-button-pure')
    expect(button).toHaveAttribute('aria-label', 'Theme mode: light')
  })

  it('AC-2: clicking toggle button invokes useTheme().toggle exactly once', () => {
    const { container, toggle } = renderThemeToggle('light')

    fireEvent.click(container.querySelector('[data-testid="theme-toggle"]')!)

    expect(toggle).toHaveBeenCalledTimes(1)
  })

  it('AC-3: button accessible name or content differs across light, dark, and auto theme states', () => {
    const descriptors = [getButtonDescriptor('light'), getButtonDescriptor('dark'), getButtonDescriptor('auto')]

    expect(new Set(descriptors).size).toBe(3)
  })

  it('compact mode renders a centered icon trigger', () => {
    const { container } = renderCompactThemeToggle('auto')
    const button = container.querySelector<HTMLElement>('[data-testid="theme-toggle"]')

    expect(button!.tagName.toLowerCase()).toBe('button')
    expect(button).toHaveAttribute('aria-label', 'Theme mode: auto (OS); open theme menu')
    expect(button).toHaveAttribute('title', 'Theme mode: auto (OS); open theme menu')
    expect(button).toHaveAttribute('aria-haspopup', 'menu')
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(button?.className).toContain('size-8')
    expect(button?.querySelector('p-icon')).not.toBeNull()
    expect(container.querySelector('[data-testid="theme-mode-indicator"]')).toBeNull()
  })

  it('compact mode opens a mode menu and selects an explicit theme', () => {
    const { container, toggle, selectTheme } = renderCompactThemeToggle('auto')
    const button = container.querySelector('[data-testid="theme-toggle"]')!

    fireEvent.click(button)

    expect(toggle).not.toHaveBeenCalled()
    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByTestId('theme-mode-menu')).toHaveAttribute('role', 'menu')
    expect(screen.getByTestId('theme-mode-option-auto')).toHaveAttribute('aria-checked', 'true')

    fireEvent.click(screen.getByTestId('theme-mode-option-dark'))

    expect(selectTheme).toHaveBeenCalledWith('dark')
    expect(screen.queryByTestId('theme-mode-menu')).toBeNull()
  })

  it('compact mode does not restore trigger focus after pointer option selection', () => {
    const { container, selectTheme } = renderCompactThemeToggle('auto')
    const button = container.querySelector('[data-testid="theme-toggle"]') as HTMLElement
    const focusSpy = vi.spyOn(button, 'focus')

    fireEvent.click(button)
    fireEvent.click(screen.getByTestId('theme-mode-option-dark'), { detail: 1 })

    expect(selectTheme).toHaveBeenCalledWith('dark')
    expect(focusSpy).not.toHaveBeenCalled()
    focusSpy.mockRestore()
  })

  it('compact mode restores trigger focus after keyboard option activation', () => {
    const { container, selectTheme } = renderCompactThemeToggle('auto')
    const button = container.querySelector('[data-testid="theme-toggle"]') as HTMLElement
    const focusSpy = vi.spyOn(button, 'focus')

    fireEvent.click(button)
    fireEvent.click(screen.getByTestId('theme-mode-option-dark'), { detail: 0 })

    expect(selectTheme).toHaveBeenCalledWith('dark')
    expect(focusSpy).toHaveBeenCalledTimes(1)
    focusSpy.mockRestore()
  })

  it('compact mode closes the menu on Escape and restores trigger focus', () => {
    const { container } = renderCompactThemeToggle('auto')
    const button = container.querySelector('[data-testid="theme-toggle"]') as HTMLElement
    const focusSpy = vi.spyOn(button, 'focus')

    fireEvent.click(button)
    fireEvent.keyDown(screen.getByTestId('theme-mode-menu'), { key: 'Escape' })

    expect(screen.queryByTestId('theme-mode-menu')).toBeNull()
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(focusSpy).toHaveBeenCalledTimes(1)
    focusSpy.mockRestore()
  })

  it('compact mode closes the menu when a pointer starts outside it', () => {
    const { container } = renderCompactThemeToggle('auto')
    const button = container.querySelector('[data-testid="theme-toggle"]')!

    fireEvent.click(button)
    fireEvent.pointerDown(document.body)

    expect(screen.queryByTestId('theme-mode-menu')).toBeNull()
  })

  it('compact mode keeps the menu open when a pointer starts inside it', () => {
    const { container } = renderCompactThemeToggle('auto')
    const button = container.querySelector('[data-testid="theme-toggle"]')!

    fireEvent.click(button)
    fireEvent.pointerDown(screen.getByTestId('theme-mode-menu'))

    expect(screen.getByTestId('theme-mode-menu')).toBeInTheDocument()
  })

  it('compact mode closes an open menu when the trigger is clicked again', () => {
    const { container } = renderCompactThemeToggle('auto')
    const button = container.querySelector('[data-testid="theme-toggle"]')!

    fireEvent.click(button)
    fireEvent.click(button)

    expect(screen.queryByTestId('theme-mode-menu')).toBeNull()
    expect(button).toHaveAttribute('aria-expanded', 'false')
  })
})
