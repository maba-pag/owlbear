import { useState } from 'react'
import * as repairApi from '../api/repair'
import type { RepairOutcome, WorkspaceRepairResponse } from '../api/repair'

export type RepairPhase = 'idle' | 'confirming' | 'repairing' | 'done' | 'error'

export interface GroupedRepairOutcomes {
  fixed: RepairOutcome[]
  quarantined: RepairOutcome[]
  failed: RepairOutcome[]
}

export interface UseRepairFlowOptions {
  onSuccess?: (repair: WorkspaceRepairResponse) => void
}

export interface UseRepairFlowResult {
  phase: RepairPhase
  corruptionCount: number | null
  results: GroupedRepairOutcomes | null
  error: string | null
  requestRepair: (count: number) => void
  confirmRepair: () => Promise<void>
  cancelRepair: () => void
  dismissResults: () => void
}

function groupOutcomes(outcomes: RepairOutcome[]): GroupedRepairOutcomes {
  return outcomes.reduce<GroupedRepairOutcomes>(
    (acc, outcome) => {
      acc[outcome.action].push(outcome)
      return acc
    },
    { fixed: [], quarantined: [], failed: [] },
  )
}

export function useRepairFlow(options?: UseRepairFlowOptions): UseRepairFlowResult {
  const [phase, setPhase] = useState<RepairPhase>('idle')
  const [corruptionCount, setCorruptionCount] = useState<number | null>(null)
  const [results, setResults] = useState<GroupedRepairOutcomes | null>(null)
  const [error, setError] = useState<string | null>(null)

  const requestRepair = (count: number): void => {
    setCorruptionCount(count)
    setResults(null)
    setError(null)
    setPhase('confirming')
  }

  const cancelRepair = (): void => {
    setCorruptionCount(null)
    setResults(null)
    setError(null)
    setPhase('idle')
  }

  const dismissResults = (): void => {
    setCorruptionCount(null)
    setResults(null)
    setError(null)
    setPhase('idle')
  }

  const confirmRepair = async (): Promise<void> => {
    setError(null)
    setPhase('repairing')
    try {
      const repair = await repairApi.repairWorkspace()
      const { outcomes, task_health_result: taskHealthResult } = repair
      setResults(groupOutcomes(outcomes))
      setPhase('done')
      options?.onSuccess?.({ outcomes, task_health_result: taskHealthResult })
    } catch (caught: unknown) {
      const message = caught instanceof Error ? caught.message : String(caught)
      setResults(null)
      setError(message)
      setPhase('error')
    }
  }

  return {
    phase,
    corruptionCount,
    results,
    error,
    requestRepair,
    confirmRepair,
    cancelRepair,
    dismissResults,
  }
}
