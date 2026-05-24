import { type Page } from '@playwright/test'

const DEFAULT_TIMEOUT_MS = 8_000
const TRANSFORM_EPSILON = 0.01

type WorkspaceReadinessOptions = {
  routeContentSelector?: string
  timeout?: number
}

type RawWorkspaceSnapshot = {
  panelCount: number
  panelOpacity: number | null
  panelTransform: string | null
  panelTranslateX: number | null
  panelTranslateY: number | null
  panelTop: number | null
  panelLeft: number | null
  routeContentVisible: boolean
  routeLoadingVisible: boolean
  transformSettled: boolean
  ready: boolean
}

export type WorkspaceReadinessSnapshot = RawWorkspaceSnapshot & {
  stableAcrossFrames: boolean
}

const workspaceSelector = '[data-region="workspace"]'
const routeLoadingSelector = '[data-testid="route-loading"]'

export async function waitForWorkspaceReady(
  page: Page,
  options: WorkspaceReadinessOptions = {},
): Promise<void> {
  const timeout = options.timeout ?? DEFAULT_TIMEOUT_MS
  const deadline = Date.now() + timeout

  await page.locator(workspaceSelector).waitFor({ state: 'visible', timeout })
  if (options.routeContentSelector) {
    await page.locator(options.routeContentSelector).first().waitFor({ state: 'visible', timeout })
  }

  let latestSnapshot: WorkspaceReadinessSnapshot | null = null
  while (Date.now() <= deadline) {
    latestSnapshot = await getWorkspaceReadinessSnapshot(page, options)
    if (latestSnapshot.ready && latestSnapshot.stableAcrossFrames) {
      return
    }
  }

  throw new Error(`Workspace route did not settle before screenshot readiness timeout: ${JSON.stringify(latestSnapshot)}`)
}

export async function getWorkspaceReadinessSnapshot(
  page: Page,
  options: WorkspaceReadinessOptions = {},
): Promise<WorkspaceReadinessSnapshot> {
  const firstSnapshot = await readWorkspaceSnapshot(page, options)
  await waitForNextAnimationFrame(page)
  const secondSnapshot = await readWorkspaceSnapshot(page, options)

  return {
    ...secondSnapshot,
    stableAcrossFrames: snapshotsAreStable(firstSnapshot, secondSnapshot),
  }
}

async function waitForNextAnimationFrame(page: Page): Promise<void> {
  await page.evaluate(
    () =>
      new Promise<void>((resolve) => {
        window.requestAnimationFrame(() => resolve())
      }),
  )
}

async function readWorkspaceSnapshot(
  page: Page,
  options: WorkspaceReadinessOptions,
): Promise<RawWorkspaceSnapshot> {
  return page.evaluate(
    ({ routeContentSelector, routeLoadingSelector: loadingSelector, transformEpsilon, workspaceSelector: rootSelector }) => {
      const isVisible = (element: Element | null): boolean => {
        if (!(element instanceof HTMLElement)) return false

        const styles = window.getComputedStyle(element)
        const rect = element.getBoundingClientRect()
        const opacity = Number.parseFloat(styles.opacity)

        return (
          styles.display !== 'none' &&
          styles.visibility !== 'hidden' &&
          opacity > 0 &&
          rect.width > 0 &&
          rect.height > 0
        )
      }

      const parseTransform = (transform: string): { translateX: number | null; translateY: number | null } => {
        try {
          const matrix = new DOMMatrixReadOnly(transform === 'none' ? undefined : transform)
          return { translateX: matrix.m41, translateY: matrix.m42 }
        } catch {
          return { translateX: null, translateY: null }
        }
      }

      const workspace = document.querySelector(rootSelector)
      const panels = workspace instanceof HTMLElement
        ? Array.from(workspace.children).filter((child): child is HTMLElement => child instanceof HTMLElement)
        : []
      const panel = panels.length === 1 ? panels[0] : null
      const panelStyles = panel ? window.getComputedStyle(panel) : null
      const panelRect = panel ? panel.getBoundingClientRect() : null
      const panelOpacity = panelStyles ? Number.parseFloat(panelStyles.opacity) : null
      const panelTransform = panelStyles?.transform ?? null
      const transformParts = panelTransform ? parseTransform(panelTransform) : { translateX: null, translateY: null }
      const transformSettled =
        transformParts.translateX !== null &&
        transformParts.translateY !== null &&
        Math.abs(transformParts.translateX) <= transformEpsilon &&
        Math.abs(transformParts.translateY) <= transformEpsilon
      const routeContent = routeContentSelector && panel
        ? panel.matches(routeContentSelector)
          ? panel
          : panel.querySelector(routeContentSelector)
        : null
      const routeContentVisible = routeContentSelector ? isVisible(routeContent) : true
      const routeLoadingVisible = isVisible(workspace?.querySelector(loadingSelector) ?? null)
      const opacitySettled = panelOpacity !== null && Math.abs(panelOpacity - 1) <= 0.001

      return {
        panelCount: panels.length,
        panelOpacity,
        panelTransform,
        panelTranslateX: transformParts.translateX,
        panelTranslateY: transformParts.translateY,
        panelTop: panelRect?.top ?? null,
        panelLeft: panelRect?.left ?? null,
        routeContentVisible,
        routeLoadingVisible,
        transformSettled,
        ready: panels.length === 1 && opacitySettled && transformSettled && routeContentVisible && !routeLoadingVisible,
      }
    },
    {
      routeContentSelector: options.routeContentSelector,
      routeLoadingSelector,
      transformEpsilon: TRANSFORM_EPSILON,
      workspaceSelector,
    },
  )
}

function snapshotsAreStable(firstSnapshot: RawWorkspaceSnapshot, secondSnapshot: RawWorkspaceSnapshot): boolean {
  return (
    firstSnapshot.ready &&
    secondSnapshot.ready &&
    firstSnapshot.panelTransform === secondSnapshot.panelTransform &&
    nearlyEqual(firstSnapshot.panelOpacity, secondSnapshot.panelOpacity) &&
    nearlyEqual(firstSnapshot.panelTranslateX, secondSnapshot.panelTranslateX) &&
    nearlyEqual(firstSnapshot.panelTranslateY, secondSnapshot.panelTranslateY) &&
    nearlyEqual(firstSnapshot.panelTop, secondSnapshot.panelTop) &&
    nearlyEqual(firstSnapshot.panelLeft, secondSnapshot.panelLeft)
  )
}

function nearlyEqual(firstValue: number | null, secondValue: number | null): boolean {
  if (firstValue === null || secondValue === null) return firstValue === secondValue
  return Math.abs(firstValue - secondValue) <= TRANSFORM_EPSILON
}
