import { useEffect, useState } from 'react'
import {
  answerWorkItemRequest,
  clearWorkItemBlock,
  listWorkItems,
  moveWorkItemBackward,
  recoverWorkItemClaim,
  retryWorkItemIntegration,
  showWorkItem,
  type DeliveryRequestResolution,
  type WorkItemDetailResponse,
  type WorkItemPortfolioResponse,
  type WorkItemProjection,
  type WorkItemStage,
} from '../api/workItems'

export interface WorkItemIdentity {
  changeId: string
  workItemId: string
}

interface AsyncResource<T> {
  data: T | null
  error: Error | null
  isLoading: boolean
}

const EMPTY_PORTFOLIO: WorkItemPortfolioResponse = {
  items: [],
  attention_counts: { user: 0, agent: 0, waiting: 0, none: 0 },
}

export function useWorkPortfolio() {
  const [resource, setResource] = useState<AsyncResource<WorkItemPortfolioResponse>>({
    data: null,
    error: null,
    isLoading: true,
  })
  const [retryNonce, setRetryNonce] = useState(0)

  useEffect(() => {
    let active = true
    setResource((current) => ({ ...current, isLoading: true, error: null }))
    void listWorkItems()
      .then((data) => active && setResource({ data, error: null, isLoading: false }))
      .catch((caught: unknown) => {
        if (!active) return
        setResource({
          data: null,
          error: caught instanceof Error ? caught : new Error('Work portfolio is unavailable'),
          isLoading: false,
        })
      })
    return () => {
      active = false
    }
  }, [retryNonce])

  return {
    portfolio: resource.data ?? EMPTY_PORTFOLIO,
    error: resource.error,
    isLoading: resource.isLoading,
    retry: () => setRetryNonce((value) => value + 1),
  }
}

export function useWorkItemDetail(identity: WorkItemIdentity | null, onChanged: () => void) {
  const [detail, setDetail] = useState<AsyncResource<WorkItemDetailResponse>>({
    data: null,
    error: null,
    isLoading: false,
  })
  const [retryNonce, setRetryNonce] = useState(0)
  const [pendingAction, setPendingAction] = useState<string | null>(null)
  const [actionError, setActionError] = useState<Error | null>(null)
  const [actionResult, setActionResult] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setActionError(null)
    setActionResult(null)
    if (!identity) {
      setDetail({ data: null, error: null, isLoading: false })
      return () => {
        active = false
      }
    }
    setDetail((current) => ({ ...current, isLoading: true, error: null }))
    void showWorkItem(identity.changeId, identity.workItemId)
      .then((data) => active && setDetail({ data, error: null, isLoading: false }))
      .catch((caught: unknown) => {
        if (!active) return
        setDetail({
          data: null,
          error: caught instanceof Error ? caught : new Error('Work item detail is unavailable'),
          isLoading: false,
        })
      })
    return () => {
      active = false
    }
  }, [identity?.changeId, identity?.workItemId, retryNonce])

  const mutate = async (action: string, operation: () => Promise<unknown>, result: string) => {
    if (!identity) return
    setPendingAction(action)
    setActionError(null)
    setActionResult(null)
    try {
      await operation()
      const nextDetail = await showWorkItem(identity.changeId, identity.workItemId)
      setDetail({ data: nextDetail, error: null, isLoading: false })
      setActionResult(result)
      onChanged()
    } catch (caught: unknown) {
      setActionError(caught instanceof Error ? caught : new Error('Delivery control failed'))
    } finally {
      setPendingAction(null)
    }
  }

  return {
    detail,
    pendingAction,
    actionError,
    actionResult,
    answerRequest: (requestId: string, resolution: DeliveryRequestResolution) => mutate(
      'answer',
      () => answerWorkItemRequest(identity!.changeId, requestId, resolution),
      'Request answered.',
    ),
    clearBlock: (blockId: string, note: string, locators: string[]) => mutate(
      'clear',
      () => clearWorkItemBlock(identity!.changeId, identity!.workItemId, blockId, note, locators),
      'Block cleared.',
    ),
    recoverClaim: (attemptId: string, claimId: string) => mutate(
      'recover',
      () => recoverWorkItemClaim(identity!.changeId, identity!.workItemId, attemptId, claimId),
      'Claim recovered.',
    ),
    moveBackward: async (target: WorkItemStage, reason: string) => {
      if (!identity) return
      setPendingAction('move')
      setActionError(null)
      setActionResult(null)
      try {
        const moved = await moveWorkItemBackward(identity.changeId, identity.workItemId, target, reason)
        const nextDetail = await showWorkItem(identity.changeId, identity.workItemId)
        setDetail({ data: nextDetail, error: null, isLoading: false })
        const invalidated = moved.invalidated_outcome_ids.join(', ')
        setActionResult(invalidated ? `Moved backward. Reset: ${invalidated}.` : 'Moved backward.')
        onChanged()
      } catch (caught: unknown) {
        setActionError(caught instanceof Error ? caught : new Error('Backward move failed'))
      } finally {
        setPendingAction(null)
      }
    },
    retryIntegration: () => mutate(
      'integration',
      () => retryWorkItemIntegration(identity!.changeId),
      'Integration retried.',
    ),
    retry: () => setRetryNonce((value) => value + 1),
  }
}

export function workItemIdentity(item: WorkItemProjection): string {
  return `${item.change_id}:${item.work_item_id}`
}
