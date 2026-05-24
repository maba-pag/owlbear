import type { Board } from '../hooks/useBoard'

export function formatStatusLabel(status: string): string {
  return status
    .replace(/-/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function getOrderedTransitionTargets(board: Board, status: string): string[] {
  const transitionSet = new Set(board.valid_transitions[status] ?? [])
  return board.statuses
    .map(({ name }) => name)
    .filter((name) => name !== 'archived' && transitionSet.has(name))
}

export function shouldShowArchiveAction(status: string): boolean {
  return status !== 'archived'
}
