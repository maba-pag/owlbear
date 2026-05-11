/**
 * Workflow behavior tests1226: Frontend — dedup rowStyleForState + delete scratch files
 *
 * AC1 (td:2): rowStyleForState extracted to a shared module under src/utils/;
 * all branches (blocked/rejected, stuck, default) return correct style objects.
 *
 * All tests are RED (failing) until the builder implements src/utils/styles.ts.
 */
import { describe, it, expect } from 'vitest'
import { rowStyleForState } from '../utils/styles'

describe('TestFromAC_RowStyleExtraction', () => {
  // AC1: rowStyleForState exported from shared utils/styles module

  it('returns error-styled object for blocked state', () => {
    const style = rowStyleForState('blocked')
    expect(style).toMatchObject({
      cursor: 'pointer',
      borderLeft: '4px solid var(--pds-theme-light-notification-error)',
      backgroundColor: 'var(--pds-theme-light-notification-error-soft)',
    })
  })

  it('returns error-styled object for rejected state', () => {
    const style = rowStyleForState('rejected')
    expect(style).toMatchObject({
      cursor: 'pointer',
      borderLeft: '4px solid var(--pds-theme-light-notification-error)',
      backgroundColor: 'var(--pds-theme-light-notification-error-soft)',
    })
  })

  it('returns warning-styled object for stuck state', () => {
    const style = rowStyleForState('stuck')
    expect(style).toMatchObject({
      cursor: 'pointer',
      borderLeft: '4px solid var(--pds-theme-light-notification-warning)',
      backgroundColor: 'var(--pds-theme-light-notification-warning-soft)',
    })
  })

  it('returns default low-contrast style for any other state', () => {
    const style = rowStyleForState('in-progress')
    expect(style).toMatchObject({
      cursor: 'pointer',
      borderLeft: '4px solid var(--pds-theme-light-contrast-low)',
    })
    expect(style).not.toHaveProperty('backgroundColor')
  })
})
