export type CardSignal = 'dr-pending' | 'blocked' | 'claimed' | 'deps-unmet' | 'ready'

interface SignalInput {
  id: number
  blocked: boolean
  claimed: boolean
  dep_status: string | null
}

export function computeSignal(task: SignalInput, pendingDRIds: Set<number>): CardSignal {
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
