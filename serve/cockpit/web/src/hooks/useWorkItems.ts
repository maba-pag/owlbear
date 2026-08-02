import { useEffect, useState } from 'react'
import {
  createWorkItemRequest,
  listWorkItemRequests,
  listWorkItems,
  showWorkItem,
  showWorkItemTrace,
  type WorkItemDetailResponse,
  type WorkItemPortfolioResponse,
  type WorkItemProjection,
  type WorkItemRequestsResponse,
  type WorkItemTraceResponse,
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

function useSelectedWorkItem(identity: WorkItemIdentity | null, retryNonce: number) {
  const [detail, setDetail] = useState<AsyncResource<WorkItemDetailResponse>>({
    data: null,
    error: null,
    isLoading: false,
  })
  const [requests, setRequests] = useState<AsyncResource<WorkItemRequestsResponse>>({
    data: null,
    error: null,
    isLoading: false,
  })
  useEffect(() => {
    let active = true
    if (!identity) {
      setDetail({ data: null, error: null, isLoading: false })
      setRequests({ data: null, error: null, isLoading: false })
      return () => {
        active = false
      }
    }
    setDetail((current) => ({ ...current, isLoading: true, error: null }))
    setRequests((current) => ({ ...current, isLoading: true, error: null }))
    void Promise.all([
      showWorkItem(identity.workItemId, identity.changeId),
      listWorkItemRequests(identity.workItemId, identity.changeId),
    ]).then(([nextDetail, nextRequests]) => {
      if (!active) return
      setDetail({ data: nextDetail, error: null, isLoading: false })
      setRequests({ data: nextRequests, error: null, isLoading: false })
    }).catch((caught: unknown) => {
      if (!active) return
      const error = caught instanceof Error ? caught : new Error('Work item detail is unavailable')
      setDetail({ data: null, error, isLoading: false })
      setRequests({ data: null, error, isLoading: false })
    })
    return () => {
      active = false
    }
  }, [identity?.changeId, identity?.workItemId, retryNonce])

  return { detail, requests, setRequests }
}

function useWorkItemTrace(identity: WorkItemIdentity | null, traceOpen: boolean) {
  const [trace, setTrace] = useState<AsyncResource<WorkItemTraceResponse>>({
    data: null,
    error: null,
    isLoading: false,
  })

  useEffect(() => {
    let active = true
    if (!identity || !traceOpen) return () => {
      active = false
    }
    setTrace({ data: null, error: null, isLoading: true })
    void showWorkItemTrace(identity.workItemId, identity.changeId)
      .then((data) => active && setTrace({ data, error: null, isLoading: false }))
      .catch((caught: unknown) => {
        if (!active) return
        setTrace({
          data: null,
          error: caught instanceof Error ? caught : new Error('Technical trace is unavailable'),
          isLoading: false,
        })
      })
    return () => {
      active = false
    }
  }, [identity?.changeId, identity?.workItemId, traceOpen])

  return trace
}

export function useWorkItemDetail(identity: WorkItemIdentity | null) {
  const [traceOpen, setTraceOpen] = useState(false)
  const [retryNonce, setRetryNonce] = useState(0)
  const { detail, requests, setRequests } = useSelectedWorkItem(identity, retryNonce)
  const trace = useWorkItemTrace(identity, traceOpen)

  useEffect(() => setTraceOpen(false), [identity?.changeId, identity?.workItemId])

  const createRequest = async (summary: string) => {
    if (!identity || !detail.data || detail.data.commitments.length === 0) return
    await createWorkItemRequest(identity.workItemId, identity.changeId, {
      request_id: `request-${Date.now()}`,
      authority_digest: detail.data.authority_identity,
      commitment_id: detail.data.commitments[0].commitment_id,
      task_id: null,
      created_at: new Date().toISOString(),
      summary,
    })
    const nextRequests = await listWorkItemRequests(identity.workItemId, identity.changeId)
    setRequests({ data: nextRequests, error: null, isLoading: false })
  }

  return {
    detail,
    requests,
    trace,
    traceOpen,
    openTrace: () => setTraceOpen(true),
    closeTrace: () => setTraceOpen(false),
    createRequest,
    retry: () => setRetryNonce((value) => value + 1),
  }
}

export function workItemIdentity(item: WorkItemProjection): string {
  return `${item.change_id}:${item.work_item_id}`
}
