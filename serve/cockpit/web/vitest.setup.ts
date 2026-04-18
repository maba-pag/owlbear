import '@porsche-design-system/components-react/jsdom-polyfill'
import { skipPorscheDesignSystemCDNRequestsDuringTests } from '@porsche-design-system/components-react'
import { vi } from 'vitest'

skipPorscheDesignSystemCDNRequestsDuringTests()

// jsdom does not implement showModal/close on HTMLDialogElement
if (typeof HTMLDialogElement !== 'undefined') {
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = vi.fn()
  }
  if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = vi.fn()
  }
}

// jsdom does not implement attachInternals (needed by some PDS form components)
// attachInternals lives on HTMLElement, not Element
if (typeof HTMLElement !== 'undefined' && !HTMLElement.prototype.attachInternals) {
  ;(HTMLElement.prototype as unknown as Record<string, unknown>)['attachInternals'] = vi.fn(
    () => ({
      setFormValue: vi.fn(),
      setValidity: vi.fn(),
      checkValidity: vi.fn(() => true),
      reportValidity: vi.fn(() => true),
    }),
  )
}
