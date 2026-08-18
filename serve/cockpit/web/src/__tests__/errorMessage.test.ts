import { describe, expect, it } from 'vitest'
import { getResponseErrorMessage } from '../api/errorMessage'

function jsonResponse(body: unknown): Response {
  return { json: async () => body } as Response
}

describe('getResponseErrorMessage', () => {
  it('normalizes message, detail, and validation error payloads', async () => {
    await expect(getResponseErrorMessage(jsonResponse({ message: '  invalid request  ' }), 'fallback'))
      .resolves.toBe('invalid request')
    await expect(getResponseErrorMessage(jsonResponse({ detail: '  unavailable  ' }), 'fallback'))
      .resolves.toBe('unavailable')
    await expect(getResponseErrorMessage(jsonResponse({
      detail: [
        ' first error ',
        { loc: ['body', 'items', 0], msg: ' invalid item ' },
        { loc: ['query', 'page'], msg: ' is required ' },
        { msg: 'general error' },
        { msg: ' ' },
        null,
      ],
    }), 'fallback')).resolves.toBe('first error; items: invalid item; page: is required; general error')
  })

  it('uses the fallback when the response has no readable error', async () => {
    await expect(getResponseErrorMessage(jsonResponse({ detail: [] }), 'fallback'))
      .resolves.toBe('fallback')
    await expect(getResponseErrorMessage(jsonResponse(null), 'fallback'))
      .resolves.toBe('fallback')
    await expect(getResponseErrorMessage(
      { json: async () => { throw new Error('invalid json') } } as Response,
      'fallback',
    )).resolves.toBe('fallback')
  })
})
