import { useEffect, useRef, useState } from 'react'
import {
  answerWorkItemRequest,
  clearWorkItemBlock,
  listCompletedChanges,
  moveWorkItemBackward,
  previewWorkItemBackward,
  recoverWorkItemClaim,
  retryWorkItemIntegration,
  searchCompletedChanges,
  showCompletedChange,
  workItemDetailUrl,
  type CompletedChangePage,
  type CompletedChangeRecord,
  type DeliveryRequestResolution,
  type WorkItemDetailResponse,
  type WorkItemPortfolioResponse,
  type WorkItemCardView,
  type WorkItemStage,
} from '../api/workItems'
import { usePollingFetch } from './usePollingFetch'

export interface WorkItemIdentity {
  changeId: string
  itemKey: string
}

interface AsyncResource<T> {
  data: T | null
  error: Error | null
  isLoading: boolean
}

const EMPTY_PORTFOLIO: WorkItemPortfolioResponse = {
  groups: [],
  totals: {
    total: 0,
    complete: 0,
    needs: { you: 0, dependency: 0, repair: 0, none: 0 },
    activity: { idle: 0, ready: 0, working: 0, repairing: 0 },
  },
}

const EMPTY_HISTORY: CompletedChangePage = { records: [], next_cursor: null }

export function useWorkPortfolio() {
  const [portfolio, setPortfolio] = useState<WorkItemPortfolioResponse | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const polling = usePollingFetch<WorkItemPortfolioResponse>('/api/work-items', {
    intervalMs: 3_000,
    onSuccess: (data) => {
      setPortfolio(data)
      setError(null)
    },
    onError: setError,
  })

  return {
    portfolio: portfolio ?? EMPTY_PORTFOLIO,
    hasData: portfolio !== null,
    error,
    isLoading: polling.isFetching && portfolio === null,
    retry: polling.refetch,
  }
}

export function useCompletedHistory(query: string) {
  const [resource, setResource] = useState<AsyncResource<CompletedChangePage>>({
    data: null,
    error: null,
    isLoading: true,
  })
  const [retryNonce, setRetryNonce] = useState(0)
  const requestGeneration = useRef(0)
  const latestQuery = useRef(query)
  latestQuery.current = query

  useEffect(() => {
    let active = true
    const generation = ++requestGeneration.current
    setResource((current) => ({ ...current, isLoading: true, error: null }))
    const request = query ? searchCompletedChanges(query) : listCompletedChanges()
    void request
      .then((data) => active && generation === requestGeneration.current
        && setResource({ data, error: null, isLoading: false }))
      .catch((caught: unknown) => {
        if (!active || generation !== requestGeneration.current) return
        setResource({
          data: null,
          error: caught instanceof Error ? caught : new Error('Completed history is unavailable'),
          isLoading: false,
        })
      })
    return () => {
      active = false
    }
  }, [query, retryNonce])

  const loadMore = async () => {
    const current = resource.data
    if (!current?.next_cursor || resource.isLoading) return
    const generation = requestGeneration.current
    const requestedQuery = query
    setResource({ data: current, error: null, isLoading: true })
    try {
      const next = query
        ? await searchCompletedChanges(query, current.next_cursor)
        : await listCompletedChanges(current.next_cursor)
      if (generation !== requestGeneration.current || requestedQuery !== latestQuery.current) return
      setResource({
        data: { records: [...current.records, ...next.records], next_cursor: next.next_cursor },
        error: null,
        isLoading: false,
      })
    } catch (caught: unknown) {
      if (generation !== requestGeneration.current || requestedQuery !== latestQuery.current) return
      setResource({
        data: current,
        error: caught instanceof Error ? caught : new Error('Completed history is unavailable'),
        isLoading: false,
      })
    }
  }

  return {
    page: resource.data ?? EMPTY_HISTORY,
    error: resource.error,
    isLoading: resource.isLoading,
    loadMore,
    retry: () => {
      requestGeneration.current += 1
      setRetryNonce((value) => value + 1)
    },
  }
}

export function useCompletedChange(identity: { changeId: string; completionId: string } | null) {
  const [resource, setResource] = useState<AsyncResource<CompletedChangeRecord>>({
    data: null,
    error: null,
    isLoading: false,
  })

  useEffect(() => {
    let active = true
    if (!identity) {
      setResource({ data: null, error: null, isLoading: false })
      return () => {
        active = false
      }
    }
    setResource({ data: null, error: null, isLoading: true })
    void showCompletedChange(identity.changeId, identity.completionId)
      .then((data) => active && setResource({ data, error: null, isLoading: false }))
      .catch((caught: unknown) => {
        if (!active) return
        setResource({
          data: null,
          error: caught instanceof Error ? caught : new Error('Completed change is unavailable'),
          isLoading: false,
        })
      })
    return () => {
      active = false
    }
  }, [identity?.changeId, identity?.completionId])

  return resource
}

export function useWorkItemDetail(identity: WorkItemIdentity, onChanged: () => void) {
  const [data, setData] = useState<WorkItemDetailResponse | null>(null)
  const [detailError, setDetailError] = useState<Error | null>(null)
  const [pendingAction, setPendingAction] = useState<string | null>(null)
  const [actionError, setActionError] = useState<Error | null>(null)
  const [actionResult, setActionResult] = useState<string | null>(null)
  const polling = usePollingFetch<WorkItemDetailResponse>(
    workItemDetailUrl(identity.changeId, identity.itemKey),
    {
      intervalMs: 3_000,
      onSuccess: (next) => {
        setData(next)
        setDetailError(null)
      },
      onError: setDetailError,
    },
  )

  const mutate = async (action: string, operation: () => Promise<unknown>, result: string) => {
    setPendingAction(action)
    setActionError(null)
    setActionResult(null)
    try {
      await operation()
      setActionResult(result)
      polling.refetch()
      onChanged()
    } catch (caught: unknown) {
      setActionError(caught instanceof Error ? caught : new Error('Delivery control failed'))
    } finally {
      setPendingAction(null)
    }
  }

  return {
    detail: {
      data,
      error: detailError,
      isLoading: polling.isFetching && data === null,
    },
    pendingAction,
    actionError,
    actionResult,
    answerRequest: (requestId: string, resolution: DeliveryRequestResolution) => mutate(
      'answer',
      () => answerWorkItemRequest(identity.changeId, requestId, resolution),
      'Request answered.',
    ),
    clearBlock: (blockId: string, note: string, locators: string[]) => mutate(
      'clear',
      () => clearWorkItemBlock(identity.changeId, data!.item.card.work_item_id, blockId, note, locators),
      'Block cleared.',
    ),
    recoverClaim: (attemptId: string, claimId: string) => mutate(
      'recover',
      () => recoverWorkItemClaim(identity.changeId, data!.item.card.work_item_id, attemptId, claimId),
      'Claim recovered.',
    ),
    previewBackward: async (target: WorkItemStage) => {
      setPendingAction('preview')
      setActionError(null)
      try {
        return await previewWorkItemBackward(identity.changeId, data!.item.card.work_item_id, target)
      } catch (caught: unknown) {
        setActionError(caught instanceof Error ? caught : new Error('Backward move preview failed'))
        return null
      } finally {
        setPendingAction(null)
      }
    },
    moveBackward: async (target: WorkItemStage, reason: string, snapshotVersion: string) => {
      setPendingAction('move')
      setActionError(null)
      setActionResult(null)
      try {
        const moved = await moveWorkItemBackward(
          identity.changeId,
          data!.item.card.work_item_id,
          target,
          reason,
          snapshotVersion,
        )
        const invalidated = moved.invalidated_outcome_ids.join(', ')
        setActionResult(invalidated ? `Moved backward. Reset: ${invalidated}.` : 'Moved backward.')
        polling.refetch()
        onChanged()
      } catch (caught: unknown) {
        setActionError(caught instanceof Error ? caught : new Error('Backward move failed'))
      } finally {
        setPendingAction(null)
      }
    },
    retryIntegration: () => mutate(
      'integration',
      () => retryWorkItemIntegration(identity.changeId),
      'Integration verification started.',
    ),
    retry: polling.refetch,
  }
}

export function workItemIdentity(item: WorkItemCardView): string {
  return `${item.change_id}:${item.item_key}`
}
