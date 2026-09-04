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

  page.on('pageerror', (error) => {
    messages.push(error.stack ?? error.message)
    resolveFirstError(error)
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
