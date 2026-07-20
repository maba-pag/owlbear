import { useCallback, useEffect, useRef, useState } from 'react'
import { getResponseErrorMessage } from '../api/errorMessage'
import type { RepairOutcome } from '../api/repair'

export type WorkspaceModuleName = 'tasks' | 'requests' | 'memory' | 'ideas'
export type WorkspaceModuleStatus = 'checking' | 'unknown' | 'healthy' | 'attention' | 'unhealthy' | 'check-failed'

export interface WorkspaceModuleHealth {
  status: WorkspaceModuleStatus
  findings?: Array<Record<string, unknown>>
  checked_at?: string
  [key: string]: unknown
}

export interface WorkspaceHealthResponse {
  status: WorkspaceModuleStatus
  modules: Partial<Record<WorkspaceModuleName, WorkspaceModuleHealth>>
}

export interface RepairReceipt {
  outcomes: RepairOutcome[]
  task_health_result: WorkspaceModuleHealth | null
}

export interface UseWorkspaceHealthResult {
  health: WorkspaceHealthResponse
  connectionError: string | null
  isFetching: boolean
  receipt: RepairReceipt | null
  refresh: () => void
  refreshAfterMutation: () => void
  mergeRepair: (repair: RepairReceipt) => void
  dismissReceipt: () => void
}

const MODULES: WorkspaceModuleName[] = ['tasks', 'requests', 'memory', 'ideas']
const STATUS_RANK: Record<WorkspaceModuleStatus, number> = {
  unhealthy: 5,
  'check-failed': 5,
  attention: 4,
  checking: 3,
  unknown: 3,
  healthy: 1,
}

function initialHealth(): WorkspaceHealthResponse {
  return { status: 'checking', modules: Object.fromEntries(MODULES.map((name) => [name, { status: 'unknown' }])) }
}

function aggregate(
  modules: WorkspaceHealthResponse['modules'],
  connectionError: string | null,
  received: boolean,
): WorkspaceModuleStatus {
  if (connectionError) return 'check-failed'
  if (!received) return 'checking'
  return MODULES.reduce<WorkspaceModuleStatus>(
    (current, name) => STATUS_RANK[modules[name]?.status ?? 'unknown'] > STATUS_RANK[current]
      ? (modules[name]?.status ?? 'unknown')
      : current,
    'healthy',
  )
}

function isNewer(next: WorkspaceModuleHealth, current: WorkspaceModuleHealth | undefined, generation: number, appliedGeneration: number): boolean {
  if (generation < appliedGeneration) return false
  if (current?.checked_at && next.checked_at) return next.checked_at > current.checked_at
  return generation > appliedGeneration || !current?.checked_at
}

export function useWorkspaceHealth(intervalMs = 3000): UseWorkspaceHealthResult {
  const [health, setHealth] = useState(initialHealth)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [received, setReceived] = useState(false)
  const [isFetching, setIsFetching] = useState(false)
  const [receipt, setReceipt] = useState<RepairReceipt | null>(null)
  const generationRef = useRef(0)
  const appliedGenerationRef = useRef<Record<WorkspaceModuleName, number>>(
    Object.fromEntries(MODULES.map((name) => [name, 0])) as Record<WorkspaceModuleName, number>,
  )

  const refresh = useCallback(async () => {
    const generation = ++generationRef.current
    setIsFetching(true)
    try {
      const response = await fetch('/health')
      if (!response.ok) throw new Error(await getResponseErrorMessage(response, `Health request failed with status ${response.status}`))
      const next = (await response.json()) as WorkspaceHealthResponse
      setHealth((current) => {
        const modules = { ...current.modules }
        for (const name of MODULES) {
          const result = next.modules[name]
          if (result && isNewer(result, modules[name], generation, appliedGenerationRef.current[name])) {
            modules[name] = result
            appliedGenerationRef.current[name] = generation
          }
        }
        return { status: aggregate(modules, null, true), modules }
      })
      setReceived(true)
      setConnectionError(null)
    } catch (error) {
      setConnectionError(error instanceof Error ? error.message : 'Health request failed')
    } finally {
      setIsFetching(false)
    }
  }, [])

  const refreshAfterMutation = useCallback(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    void refresh()
    const timer = setInterval(() => void refresh(), intervalMs)
    return () => clearInterval(timer)
  }, [intervalMs, refresh])

  const mergeRepair = useCallback((repair: RepairReceipt) => {
    setReceipt(repair)
    if (!repair.task_health_result) return
    const generation = ++generationRef.current
    setHealth((current) => {
      const modules = { ...current.modules, tasks: repair.task_health_result as WorkspaceModuleHealth }
      appliedGenerationRef.current.tasks = generation
      return { status: aggregate(modules, connectionError, true), modules }
    })
  }, [connectionError])

  return {
    health: { ...health, status: aggregate(health.modules, connectionError, received) },
    connectionError,
    isFetching,
    receipt,
    refresh: () => void refresh(),
    refreshAfterMutation,
    mergeRepair,
    dismissReceipt: () => setReceipt(null),
  }
}
