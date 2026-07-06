export type CardSignal = 'dr-pending' | 'blocked' | 'claimed' | 'deps-unmet' | 'ready' | 'unknown'

interface SignalInput {
  id: number
  blocked: boolean
  claimed: boolean
  dep_status: string | null
}

function isSignalInput(task: unknown): task is SignalInput {
  return typeof task === 'object' && task !== null && typeof (task as { id?: unknown }).id === 'number'
}

export function computeSignal(task: unknown, pendingDRIds: Set<number>): CardSignal {
  if (!isSignalInput(task)) {
    return 'unknown'
  }

  if (pendingDRIds.has(task.id)) {
    return 'dr-pending'
  }

  if (task.blocked) {
    return 'blocked'
  }

  if (task.claimed) {
    return 'claimed'
  }

  if (task.dep_status === 'blocked') {
    return 'deps-unmet'
  }

  return 'ready'
}
