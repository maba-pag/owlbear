import { PButtonPure } from '@porsche-design-system/components-react'
import { useTheme } from '../hooks/useTheme'

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

interface ThemeToggleProps {
  compact?: boolean
}

export default function ThemeToggle({ compact = false }: ThemeToggleProps) {
  const { theme, toggle } = useTheme()
  const label = THEME_LABELS[theme]

  return (
    <PButtonPure
      type="button"
      icon="theme"
      hideLabel={false}
      className={[
        'rounded-full bg-canvas py-1',
        compact ? 'px-1 text-xs' : 'px-static-xs',
      ].join(' ')}
      data-testid="theme-toggle"
      aria-label={label.ariaLabel}
      title={label.ariaLabel}
      onClick={toggle}
    >
      {compact ? (
        <>
          <span
            data-testid="theme-mode-indicator"
            className="inline-flex size-5 items-center justify-center rounded-full border border-contrast-low bg-frosted-soft text-[0.68rem] font-semibold leading-none text-primary"
            aria-hidden="true"
          >
            {label.shortText}
          </span>
          <span className="sr-only">{label.text}</span>
        </>
      ) : label.text}
    </PButtonPure>
  )
}
