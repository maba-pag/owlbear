import { expect, type Page } from '@playwright/test'

const WORKSPACE_SELECTOR = '[data-region="workspace"]'

export interface PageErrorTracker {
  messages: string[]
  firstError: Promise<Error>
}

export function trackPageErrors(page: Page): PageErrorTracker {
  const messages: string[] = []
  let resolveFirstError: (error: Error) => void = () => {}
  const firstError = new Promise<Error>((resolve) => {
    resolveFirstError = resolve
  })

  const recordError = (message: string): void => {
    messages.push(message)
    resolveFirstError(new Error(message))
  }

  page.on('pageerror', (error) => recordError(error.stack ?? error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') recordError(`Browser console error: ${message.text()}`)
  })

  return { messages, firstError }
}

export async function waitForWorkspaceWithoutPageErrors(
  page: Page,
  tracker: PageErrorTracker,
): Promise<void> {
  const pageError = tracker.firstError.then((error) => {
    throw new Error(`Browser page error before workspace was ready: ${error.stack ?? error.message}`)
  })

  await Promise.race([
    page.locator(WORKSPACE_SELECTOR).waitFor({ state: 'visible' }),
    pageError,
  ])

  expect(
    tracker.messages,
    'Browser page must not emit errors during workspace startup',
  ).toHaveLength(0)
}
