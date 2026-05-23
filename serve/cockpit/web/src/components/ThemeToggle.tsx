import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type MouseEvent as ReactMouseEvent } from 'react'
import { createPortal } from 'react-dom'
import { PButton, PButtonPure, PIcon } from '@porsche-design-system/components-react'
import { useTheme } from '../hooks/useTheme'
import type { Theme } from '../hooks/useTheme'

const THEME_LABELS = {
  light: {
    ariaLabel: 'Theme mode: light',
    shortText: 'L',
    text: 'Light',
  },
  dark: {
    ariaLabel: 'Theme mode: dark',
    shortText: 'D',
    text: 'Dark',
  },
  auto: {
    ariaLabel: 'Theme mode: auto (OS)',
    shortText: 'A',
    text: 'Auto',
  },
} as const

const THEME_OPTIONS: Theme[] = ['light', 'dark', 'auto']

function getMenuPosition(trigger: HTMLElement): { top: string; left: string } {
  const rect = trigger.getBoundingClientRect()
  const menuWidth = 196
  const viewportPadding = 12
  const maxLeft = Math.max(viewportPadding, window.innerWidth - menuWidth - viewportPadding)
  const left = Math.round(Math.min(Math.max(viewportPadding, rect.right - menuWidth), maxLeft))
  const top = Math.round(rect.bottom + 8)

  return { top: `${top}px`, left: `${left}px` }
}

interface ThemeToggleProps {
  compact?: boolean
}

export default function ThemeToggle({ compact = false }: ThemeToggleProps) {
  const { theme, toggle, selectTheme } = useTheme()
  const label = THEME_LABELS[theme]
  const triggerRef = useRef<HTMLElement | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [menuPosition, setMenuPosition] = useState({ top: '0px', left: '0px' })

  useEffect(() => {
    if (!isMenuOpen) {
      return
    }

    menuRef.current?.focus()

    const closeOnPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null
      if (!target) {
        return
      }

      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) {
        return
      }

      setIsMenuOpen(false)
    }

    const updatePosition = () => {
      if (triggerRef.current) {
        setMenuPosition(getMenuPosition(triggerRef.current))
      }
    }

    document.addEventListener('pointerdown', closeOnPointerDown)
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)

    return () => {
      document.removeEventListener('pointerdown', closeOnPointerDown)
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [isMenuOpen])

  function openMenu() {
    if (triggerRef.current) {
      setMenuPosition(getMenuPosition(triggerRef.current))
    }
    setIsMenuOpen(true)
  }

  function handleTriggerClick() {
    if (!compact) {
      toggle()
      return
    }

    if (isMenuOpen) {
      setIsMenuOpen(false)
      return
    }

    openMenu()
  }

  function handleMenuKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.preventDefault()
      setIsMenuOpen(false)
      triggerRef.current?.focus()
    }
  }

  function chooseTheme(nextTheme: Theme, shouldRestoreTriggerFocus: boolean) {
    selectTheme(nextTheme)
    setIsMenuOpen(false)
    if (shouldRestoreTriggerFocus) {
      triggerRef.current?.focus()
    }
  }

  const menu = isMenuOpen ? createPortal(
    <div
      ref={menuRef}
      data-testid="theme-mode-menu"
      role="menu"
      aria-label="Theme mode"
      tabIndex={-1}
      className="fixed z-[80] flex w-[196px] flex-col gap-static-xs rounded-sm border border-contrast-low bg-canvas p-static-xs shadow-[0_16px_48px_rgb(0_0_0_/_0.16)]"
      style={menuPosition}
      onKeyDown={handleMenuKeyDown}
    >
      {THEME_OPTIONS.map((option) => {
        const optionLabel = THEME_LABELS[option]
        const isSelected = option === theme

        return (
          <button
            key={option}
            type="button"
            role="menuitemradio"
            aria-checked={isSelected}
            data-testid={`theme-mode-option-${option}`}
            className="flex w-full items-center gap-static-xs rounded-sm px-static-xs py-static-xs text-left text-primary hover:bg-frosted-soft focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--p-color-state-focus)]"
            onClick={(event: ReactMouseEvent<HTMLButtonElement>) => chooseTheme(option, event.detail === 0)}
          >
            <span className="inline-flex size-4 shrink-0 items-center justify-center" aria-hidden="true">
              {isSelected ? <PIcon name="check" size="x-small" /> : null}
            </span>
            <span>{optionLabel.text}</span>
          </button>
        )
      })}
    </div>,
    document.body,
  ) : null

  return (
    <>
      {compact ? (
        <PButton
          ref={triggerRef}
          type="button"
          data-testid="theme-toggle"
          variant="secondary"
          compact
          hideLabel
          icon="theme"
          className="inline-flex size-11 items-center justify-center"
          aria-label={`${label.ariaLabel}; open theme menu`}
          aria-haspopup="menu"
          aria-expanded={isMenuOpen ? 'true' : 'false'}
          title={`${label.ariaLabel}; open theme menu`}
          onClick={handleTriggerClick}
        >
          Theme
        </PButton>
      ) : (
        <PButtonPure
          ref={triggerRef}
          type="button"
          icon="theme"
          className="rounded-full bg-canvas px-static-xs py-1"
          data-testid="theme-toggle"
          aria-label={label.ariaLabel}
          title={label.ariaLabel}
          onClick={handleTriggerClick}
        >
          {label.text}
        </PButtonPure>
      )}
      {compact ? menu : null}
    </>
  )
}
