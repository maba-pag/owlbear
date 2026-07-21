import { useRef, useState } from 'react'
import * as repairApi from '../api/repair'
import type { WorkspaceRepairResponse } from '../api/repair'

export type RepairPhase = 'idle' | 'confirming' | 'repairing' | 'error'

export interface UseRepairFlowOptions {
  onSuccess?: (repair: WorkspaceRepairResponse) => void
}

export interface UseRepairFlowResult {
  phase: RepairPhase
  repairableCount: number | null
  error: string | null
  requestRepair: (count: number) => void
  confirmRepair: () => Promise<void>
  cancelRepair: () => void
  dismissError: () => void
}

export function useRepairFlow(options?: UseRepairFlowOptions): UseRepairFlowResult {
  const [phase, setPhase] = useState<RepairPhase>('idle')
  const [repairableCount, setRepairableCount] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const repairInFlight = useRef(false)

  const requestRepair = (count: number): void => {
    setRepairableCount(count)
    setError(null)
    setPhase('confirming')
  }

  const cancelRepair = (): void => {
    setRepairableCount(null)
    setError(null)
    setPhase('idle')
  }

  const dismissError = (): void => {
    setRepairableCount(null)
    setError(null)
    setPhase('idle')
  }

  const confirmRepair = async (): Promise<void> => {
    if (repairInFlight.current) return
    repairInFlight.current = true
    setError(null)
    setPhase('repairing')
    try {
      const repair = await repairApi.repairWorkspace()
      options?.onSuccess?.(repair)
      setRepairableCount(null)
      setPhase('idle')
    } catch (caught: unknown) {
      const message = caught instanceof Error ? caught.message : String(caught)
      setError(message)
      setPhase('error')
    } finally {
      repairInFlight.current = false
    }
  }

  return {
    phase,
    repairableCount,
    error,
    requestRepair,
    confirmRepair,
    cancelRepair,
    dismissError,
  }
}
