import type { CSSProperties } from 'react'

export function rowStyleForState(state: string): CSSProperties {
  if (state === 'blocked' || state === 'rejected') {
    return {
      cursor: 'pointer',
      borderLeft: '4px solid var(--pds-theme-light-notification-error)',
      backgroundColor: 'var(--pds-theme-light-notification-error-soft)',
    }
  }

  if (state === 'stuck') {
    return {
      cursor: 'pointer',
      borderLeft: '4px solid var(--pds-theme-light-notification-warning)',
      backgroundColor: 'var(--pds-theme-light-notification-warning-soft)',
    }
  }

  return {
    cursor: 'pointer',
    borderLeft: '4px solid var(--pds-theme-light-contrast-low)',
  }
}

