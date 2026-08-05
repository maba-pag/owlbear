const GAP = 8
const VIEWPORT_PADDING = 12

/**
 * Position a panel launched from the narrow navigation rail. Rail triggers sit against the left
 * viewport edge, so the panel opens beside the rail when it fits and flips inward when it does not.
 */
export function getRailPanelPosition(
  trigger: HTMLElement,
  width: number,
  height: number,
): { top: string; left: string } {
  const rect = trigger.getBoundingClientRect()
  const maxLeft = Math.max(VIEWPORT_PADDING, window.innerWidth - width - VIEWPORT_PADDING)
  const preferredLeft = rect.right + GAP + width <= window.innerWidth - VIEWPORT_PADDING
    ? rect.right + GAP
    : rect.right - width
  const left = Math.round(Math.min(Math.max(VIEWPORT_PADDING, preferredLeft), maxLeft))

  const fitsBelow = rect.bottom + GAP + height <= window.innerHeight - VIEWPORT_PADDING
  const maxTop = Math.max(VIEWPORT_PADDING, window.innerHeight - height - VIEWPORT_PADDING)
  const preferredTop = fitsBelow ? rect.bottom + GAP : rect.top - GAP - height
  const top = Math.round(Math.min(Math.max(VIEWPORT_PADDING, preferredTop), maxTop))

  return { top: `${top}px`, left: `${left}px` }
}
