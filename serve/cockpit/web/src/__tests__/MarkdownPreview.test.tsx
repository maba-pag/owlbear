import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import MarkdownPreview from '../components/MarkdownPreview'

describe('MarkdownPreview', () => {
  it('renders numbered lists, bullet lists, and separated paragraphs with preview styling', () => {
    const markdown = [
      'First paragraph.',
      '',
      '1. First numbered item',
      '2. Second numbered item',
      '',
      '- First bullet',
      '- Second bullet',
      '',
      'Second paragraph.',
    ].join('\n')

    const { getByTestId } = render(<MarkdownPreview data-testid="markdown-preview">{markdown}</MarkdownPreview>)
    const preview = getByTestId('markdown-preview')

    expect(preview.querySelector('ol')?.textContent).toContain('First numbered item')
    expect(preview.querySelector('ul')?.textContent).toContain('First bullet')
    expect(preview.querySelectorAll('p').length).toBeGreaterThanOrEqual(2)
    expect(preview.className).toContain('[&_ol]:list-decimal')
    expect(preview.className).toContain('[&_ul]:list-disc')
    expect(preview.className).toContain('[&_p]:my-static-xs')
  })
})
