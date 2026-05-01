/**
 * Failing tests for #1226: Frontend — dedup rowStyleForState + delete scratch files
 *
 * AC1 (td:1): rowStyleForState extracted to a shared module under src/utils/
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
})
