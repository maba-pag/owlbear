import { useCallback, useMemo, useState } from 'react'
import {
  IDEAS_HEALTH_URL,
  MEMORY_HEALTH_URL,
  type IdeasHealthResponse,
  type MemoryHealthResponse,
} from '../api/health'
import { usePollingFetch } from './usePollingFetch'

export type WorkspaceHealthStatus = 'healthy' | 'attention' | 'unhealthy' | 'unavailable' | 'checking'

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
}

const HEALTH_INTERVAL_MS = 60_000
const SEVERITY: Record<WorkspaceHealthStatus, number> = {
  unhealthy: 4,
  attention: 3,
  unavailable: 2,
  checking: 1,
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
 * Poll the two health projections the backend still serves and rank them into one operator signal.
 * A failed request means the check could not run, which is reported rather than hidden.
 */
export function useWorkspaceHealth(): UseWorkspaceHealthResult {
  const [memory, setMemory] = useState<{ status: WorkspaceHealthStatus; findings: string[] }>({
    status: 'checking',
    findings: [],
  })
  const [ideas, setIdeas] = useState<{ status: WorkspaceHealthStatus; summary: string }>({
    status: 'checking',
    summary: '',
  })
  const [lastCheckedAt, setLastCheckedAt] = useState<number | null>(null)

  const { isFetching: memoryChecking, refetch: refetchMemory } = usePollingFetch<MemoryHealthResponse>(MEMORY_HEALTH_URL, {
    intervalMs: HEALTH_INTERVAL_MS,
    onSuccess: async (payload) => {
      setMemory({
        status: toStatus(payload.status),
        findings: (payload.findings ?? []).map(findingLine).filter(Boolean),
      })
      setLastCheckedAt(Date.now())
    },
    onError: async (caught) => {
      setMemory({ status: 'unavailable', findings: [caught.message] })
      setLastCheckedAt(Date.now())
    },
  })

  const { isFetching: ideasChecking, refetch: refetchIdeas } = usePollingFetch<IdeasHealthResponse>(IDEAS_HEALTH_URL, {
    intervalMs: HEALTH_INTERVAL_MS,
    onSuccess: async (payload) => {
      const status = toStatus(payload.status)
      setIdeas({
        status,
        summary: status === 'healthy' ? '' : payload.detail ?? `${payload.path} cannot be read`,
      })
      setLastCheckedAt(Date.now())
    },
    onError: async (caught) => {
      setIdeas({ status: 'unavailable', summary: caught.message })
      setLastCheckedAt(Date.now())
    },
  })

  const modules = useMemo<WorkspaceHealthModule[]>(() => [
    memoryModule(memory),
    { id: 'ideas', label: 'Ideas file', status: ideas.status, summary: ideas.summary, findings: [] },
  ], [ideas.status, ideas.summary, memory])

  const refresh = useCallback(() => {
    refetchMemory()
    refetchIdeas()
  }, [refetchIdeas, refetchMemory])

  const status = modules.reduce<WorkspaceHealthStatus>(
    (worst, module) => (SEVERITY[module.status] > SEVERITY[worst] ? module.status : worst),
    'healthy',
  )

  return { status, modules, isChecking: memoryChecking || ideasChecking, lastCheckedAt, refresh }
}
