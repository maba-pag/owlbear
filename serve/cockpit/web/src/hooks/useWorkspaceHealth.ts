import { useCallback, useMemo, useRef, useState } from 'react'
import {
  IDEAS_HEALTH_URL,
  MEMORY_HEALTH_URL,
  type IdeasHealthResponse,
  type MemoryHealthResponse,
} from '../api/health'
import { getResponseErrorMessage } from '../api/errorMessage'

export type WorkspaceHealthStatus = 'healthy' | 'attention' | 'unhealthy' | 'unavailable' | 'checking' | 'unknown'

export interface WorkspaceHealthModule {
  id: 'memory' | 'ideas'
  label: string
  status: WorkspaceHealthStatus
  /** Empty while healthy: the green status already carries that answer. */
  summary: string
  findings: string[]
}

export interface UseWorkspaceHealthResult {
  status: WorkspaceHealthStatus
  modules: WorkspaceHealthModule[]
  isChecking: boolean
  /** Epoch milliseconds of the last settled check, so the panel can state its own freshness. */
  lastCheckedAt: number | null
  refresh: () => void
}

export const WORKSPACE_HEALTH_LABELS: Record<WorkspaceHealthStatus, string> = {
  healthy: 'Healthy',
  attention: 'Needs attention',
  unhealthy: 'Unhealthy',
  unavailable: 'Cannot be checked',
  checking: 'Checking',
  unknown: 'Not checked',
}

const SEVERITY: Record<WorkspaceHealthStatus, number> = {
  unhealthy: 5,
  attention: 4,
  unavailable: 3,
  checking: 2,
  unknown: 1,
  healthy: 0,
}

/** The backend reports `check-failed` when a module checker could not run at all. */
function toStatus(reported: string): WorkspaceHealthStatus {
  if (reported === 'healthy' || reported === 'attention' || reported === 'unhealthy') return reported
  return 'unavailable'
}

function findingLine(finding: { path?: string; code?: string; detail?: string }): string {
  return [finding.path, finding.code, finding.detail].filter(Boolean).join(' — ')
}

async function fetchHealth<TPayload>(url: string): Promise<TPayload> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(await getResponseErrorMessage(response, `Health check failed with status ${response.status}`))
  }
  return await response.json() as TPayload
}

/**
 * The backend reports only problem paths, never the full inspected set, so the summary states the
 * count of storage issues and never a readable-file count.
 */
function memoryModule(state: { status: WorkspaceHealthStatus; findings: string[] }): WorkspaceHealthModule {
  const count = state.findings.length
  return {
    id: 'memory',
    label: 'Memory store',
    status: state.status,
    summary: state.status === 'unavailable'
      ? 'Health check did not complete'
      : count === 0
        ? ''
        : `${count} storage ${count === 1 ? 'issue' : 'issues'} found`,
    findings: state.findings,
  }
}

/**
 * Check the two health projections on explicit operator request and rank them into one signal.
 * A failed request means the check could not run, which is reported rather than hidden.
 */
export function useWorkspaceHealth(): UseWorkspaceHealthResult {
  const [memory, setMemory] = useState<{ status: WorkspaceHealthStatus; findings: string[] }>({
    status: 'unknown',
    findings: [],
  })
  const [ideas, setIdeas] = useState<{ status: WorkspaceHealthStatus; summary: string }>({
    status: 'unknown',
    summary: '',
  })
  const [isChecking, setIsChecking] = useState(false)
  const [lastCheckedAt, setLastCheckedAt] = useState<number | null>(null)
  const checkingRef = useRef(false)

  const modules = useMemo<WorkspaceHealthModule[]>(() => [
    memoryModule(memory),
    { id: 'ideas', label: 'Ideas file', status: ideas.status, summary: ideas.summary, findings: [] },
  ], [ideas.status, ideas.summary, memory])

  const refresh = useCallback(() => {
    if (checkingRef.current) return
    checkingRef.current = true
    setIsChecking(true)
    setMemory({ status: 'checking', findings: [] })
    setIdeas({ status: 'checking', summary: '' })

    void Promise.allSettled([
      fetchHealth<MemoryHealthResponse>(MEMORY_HEALTH_URL),
      fetchHealth<IdeasHealthResponse>(IDEAS_HEALTH_URL),
    ]).then(([memoryResult, ideasResult]) => {
      if (memoryResult.status === 'fulfilled') {
        setMemory({
          status: toStatus(memoryResult.value.status),
          findings: (memoryResult.value.findings ?? []).map(findingLine).filter(Boolean),
        })
      } else {
        setMemory({ status: 'unavailable', findings: [memoryResult.reason instanceof Error ? memoryResult.reason.message : 'Health check failed'] })
      }
      if (ideasResult.status === 'fulfilled') {
        const status = toStatus(ideasResult.value.status)
        setIdeas({
          status,
          summary: status === 'healthy' ? '' : ideasResult.value.detail ?? `${ideasResult.value.path} cannot be read`,
        })
      } else {
        setIdeas({ status: 'unavailable', summary: ideasResult.reason instanceof Error ? ideasResult.reason.message : 'Health check failed' })
      }
      setLastCheckedAt(Date.now())
    }).finally(() => {
      checkingRef.current = false
      setIsChecking(false)
    })
  }, [])

  const status = modules.reduce<WorkspaceHealthStatus>(
    (worst, module) => (SEVERITY[module.status] > SEVERITY[worst] ? module.status : worst),
    'healthy',
  )

  return { status, modules, isChecking, lastCheckedAt, refresh }
}
