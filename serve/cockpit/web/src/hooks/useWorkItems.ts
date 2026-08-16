import { useEffect, useRef, useState } from 'react'
import {
  answerWorkItemRequest,
  abortWorkItemTargetSync,
  abandonWorkItemChange,
  cleanupAbandonedWorkItemChange,
  cleanupCompletedWorkItemChange,
  clearWorkItemBlock,
  deferWorkItemChange,
  listCompletedChanges,
  markWorkItemPublicationReady,
  moveWorkItemBackward,
  observeWorkItemAcceptance,
  observeWorkItemPublicationChecks,
  previewWorkItemBackward,
  reconcileWorkItemPublication,
  recoverWorkItemClaim,
  recoverWorkItemChange,
  reconcileWorkItemAcceptance,
  resolveWorkItemTargetSync,
  resolveWorkItemAttention,
  resumeWorkItemChange,
  searchCompletedChanges,
  supersedeWorkItemPublication,
  syncWorkItemTarget,
  showDesignWork,
  showCompletedChange,
  workItemDetailUrl,
  type CompletedChangePage,
  type CompletedChangeRecord,
  type DeliveryRequestResolution,
  type DesignWorkDetailResponse,
  type WorkItemDetailResponse,
  type WorkItemPortfolioResponse,
  type WorkItemCardView,
  type PublicationChecksObservationResponse,
  type WorkItemStage,
  WorkItemApiError,
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
    needs: { you: 0, dependency: 0, none: 0 },
    activity: { idle: 0, ready: 0, working: 0 },
  },
  operating: {
    unfinished_change_count: 0,
    completed_change_count: 0,
    draft_design_change_ids: [],
    design_required_change_ids: [],
    claimed: [],
    queued_for_orchestration: [],
    interventions: [],
    dependency_waits: [],
    guidance: [{ kind: 'create-change', change_ids: [], work_count: 0 }],
  },
}

const EMPTY_HISTORY: CompletedChangePage = { records: [], next_cursor: null }

const ACCEPTANCE_RECONCILIATION_INTERVAL_MS = 30_000
const ACCEPTANCE_RECONCILIATION_MAX_BACKOFF_MS = 5 * 60_000

function acceptanceChangeIds(portfolio: WorkItemPortfolioResponse): string[] {
  return portfolio.groups
    .filter((group) => group.lifecycle === 'awaiting-merge' && group.items.some(
      (item) => item.scope === 'change-publication' && item.action.kind === 'observe-acceptance',
    ))
    .map((group) => group.change_id)
    .sort()
}

export function useWorkPortfolio(paused = false) {
  const [portfolio, setPortfolio] = useState<WorkItemPortfolioResponse | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const polling = usePollingFetch<WorkItemPortfolioResponse>('/api/work-items', {
    intervalMs: 3_000,
    paused,
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

export function useAcceptanceReconciliation(
  portfolio: WorkItemPortfolioResponse,
  onChanged: () => void,
  paused = false,
): void {
  const changeIds = acceptanceChangeIds(portfolio)
  const changeIdsKey = changeIds.join('\u0000')
  const changeIdsRef = useRef(changeIds)
  const onChangedRef = useRef(onChanged)
  changeIdsRef.current = changeIds
  onChangedRef.current = onChanged

  useEffect(() => {
    if (paused || !changeIdsKey) return

    let active = true
    let inFlight = false
    let timer: ReturnType<typeof setTimeout> | null = null
    let controller: AbortController | null = null
    let providerFailureCount = 0

    const clearTimer = () => {
      if (timer !== null) {
        clearTimeout(timer)
        timer = null
      }
    }

    const isVisible = () => document.visibilityState === 'visible'

    const scheduleNext = () => {
      if (!active || !isVisible() || changeIdsRef.current.length === 0) return
      const delay = Math.min(
        ACCEPTANCE_RECONCILIATION_INTERVAL_MS * (2 ** providerFailureCount),
        ACCEPTANCE_RECONCILIATION_MAX_BACKOFF_MS,
      )
      timer = setTimeout(() => {
        timer = null
        void poll()
      }, delay)
    }

    const poll = async () => {
      if (!active || !isVisible() || inFlight || changeIdsRef.current.length === 0) return
      inFlight = true
      controller = new AbortController()
      const requestedIds = [...changeIdsRef.current]
      let providerUnavailable = false
      try {
        const result = await reconcileWorkItemAcceptance(requestedIds, controller.signal)
        providerUnavailable = result.outcomes.some((outcome) => outcome.status === 'provider-unavailable')
        if (result.outcomes.some((outcome) => outcome.status !== 'waiting')) {
          onChangedRef.current()
        }
      } catch (caught: unknown) {
        if (!(caught instanceof DOMException && caught.name === 'AbortError')) {
          providerUnavailable = true
        }
      } finally {
        inFlight = false
        controller = null
        if (active) {
          providerFailureCount = providerUnavailable ? Math.min(providerFailureCount + 1, 4) : 0
          scheduleNext()
        }
      }
    }

    const onVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        clearTimer()
        controller?.abort()
        return
      }
      void poll()
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
    if (isVisible()) void poll()

    return () => {
      active = false
      clearTimer()
      controller?.abort()
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [changeIdsKey, paused])
}

export function useDesignWorkDetail(changeId: string) {
  const [retryNonce, setRetryNonce] = useState(0)
  const [resource, setResource] = useState<AsyncResource<DesignWorkDetailResponse>>({
    data: null,
    error: null,
    isLoading: true,
  })

  useEffect(() => {
    let active = true
    setResource({ data: null, error: null, isLoading: true })
    void showDesignWork(changeId)
      .then((data) => active && setResource({ data, error: null, isLoading: false }))
      .catch((caught: unknown) => {
        if (!active) return
        setResource({
          data: null,
          error: caught instanceof Error ? caught : new Error('Design work is unavailable'),
          isLoading: false,
        })
      })
    return () => {
      active = false
    }
  }, [changeId, retryNonce])

  return { ...resource, retry: () => setRetryNonce((value) => value + 1) }
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
  const [publicationChecks, setPublicationChecks] = useState<PublicationChecksObservationResponse | null>(null)
  const [publicationChecksError, setPublicationChecksError] = useState<Error | null>(null)
  const [publicationChecksStale, setPublicationChecksStale] = useState(false)
  const [isObservingPublicationChecks, setIsObservingPublicationChecks] = useState(false)
  const targetSyncOperation = useRef<{ changeId: string; operationId: string } | null>(null)
  const supersedePublicationOperation = useRef<{ changeId: string; operationId: string } | null>(null)
  const identityKey = `${identity.changeId}:${identity.itemKey}`
  const publicationIdentityRef = useRef(identityKey)
  const publicationDetailRef = useRef<WorkItemDetailResponse | null>(null)
  const publicationHeadRef = useRef<string | null>(null)
  const publicationChecksRef = useRef<PublicationChecksObservationResponse | null>(null)
  const publicationObservationGenerationRef = useRef(0)
  const publicationObservationRequestRef = useRef(0)
  const observingPublicationChecksRef = useRef(false)
  publicationIdentityRef.current = identityKey

  useEffect(() => {
    publicationDetailRef.current = null
    publicationHeadRef.current = null
    publicationChecksRef.current = null
    publicationObservationGenerationRef.current += 1
    publicationObservationRequestRef.current += 1
    observingPublicationChecksRef.current = false
    setPublicationChecks(null)
    setPublicationChecksError(null)
    setPublicationChecksStale(false)
    setIsObservingPublicationChecks(false)
  }, [identityKey])

  const polling = usePollingFetch<WorkItemDetailResponse>(
    workItemDetailUrl(identity.changeId, identity.itemKey),
    {
      intervalMs: 3_000,
      onSuccess: (next) => {
        if (next.item.card.change_id !== identity.changeId || next.item.card.item_key !== identity.itemKey) return
        const nextPublishedHead = next.item.publication?.published_head ?? null
        const previousPublishedHead = publicationHeadRef.current
        if (previousPublishedHead !== nextPublishedHead) {
          const hadObservation = publicationChecksRef.current !== null
          publicationObservationGenerationRef.current += 1
          publicationObservationRequestRef.current += 1
          observingPublicationChecksRef.current = false
          publicationChecksRef.current = null
          setPublicationChecks(null)
          setPublicationChecksError(null)
          setPublicationChecksStale(hadObservation)
          setIsObservingPublicationChecks(false)
        }
        publicationHeadRef.current = nextPublishedHead
        publicationDetailRef.current = next
        setData(next)
        setDetailError(null)
      },
      onError: setDetailError,
    },
  )

  const observePublicationChecks = async (): Promise<Error | null> => {
    const requestedIdentity = identityKey
    const requestedHead = publicationDetailRef.current?.item.publication?.published_head ?? null
    if (!requestedHead) {
      const error = new Error('Publication checks require a published head.')
      setPublicationChecksError(error)
      return error
    }
    if (observingPublicationChecksRef.current) return null
    const generation = publicationObservationGenerationRef.current
    const requestId = ++publicationObservationRequestRef.current
    observingPublicationChecksRef.current = true
    setIsObservingPublicationChecks(true)
    setPublicationChecksError(null)
    const isCurrent = () => requestId === publicationObservationRequestRef.current
      && generation === publicationObservationGenerationRef.current
      && publicationIdentityRef.current === requestedIdentity
      && publicationHeadRef.current === requestedHead
    try {
      const observed = await observeWorkItemPublicationChecks(identity.changeId)
      if (!isCurrent() || observed.change_id !== identity.changeId || observed.exact_commit !== requestedHead) {
        if (isCurrent()) {
          publicationChecksRef.current = null
          setPublicationChecks(null)
          setPublicationChecksStale(true)
          const error = new Error('Observed checks do not match the current Change published head. Refresh the Work Item and try again.')
          setPublicationChecksError(error)
          return error
        }
        return null
      }
      publicationChecksRef.current = observed
      setPublicationChecks(observed)
      setPublicationChecksStale(false)
      setPublicationChecksError(null)
      return null
    } catch (caught: unknown) {
      if (!isCurrent()) return null
      const error = caught instanceof Error ? caught : new Error('Publication checks could not be observed')
      setPublicationChecksError(error)
      return error
    } finally {
      if (requestId === publicationObservationRequestRef.current) {
        observingPublicationChecksRef.current = false
        setIsObservingPublicationChecks(false)
      }
    }
  }

  const mutate = async (
    action: string,
    operation: () => Promise<unknown>,
    result: string,
  ): Promise<Error | null> => {
    setPendingAction(action)
    setActionError(null)
    setActionResult(null)
    try {
      await operation()
      setActionResult(result)
      polling.refetch()
      onChanged()
      return null
    } catch (caught: unknown) {
      const error = caught instanceof Error ? caught : new Error('Delivery control failed')
      setActionError(error)
      return error
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
    reconcilePublication: () => mutate(
      'publication-reconcile',
      () => reconcileWorkItemPublication(identity.changeId),
      'Publication checkpoint reconciled.',
    ),
    markPublicationReady: () => mutate(
      'publication-ready',
      () => markWorkItemPublicationReady(identity.changeId),
      'Pull request marked ready.',
    ),
    publicationChecks,
    publicationChecksError,
    publicationChecksStale,
    isObservingPublicationChecks,
    observePublicationChecks,
    observeAcceptance: () => mutate(
      'acceptance-observe',
      () => observeWorkItemAcceptance(identity.changeId),
      'GitHub acceptance observed.',
    ),
    resolveAttention: (expectedDispositionId: string) => mutate(
      'attention-resolve',
      () => resolveWorkItemAttention(identity.changeId, expectedDispositionId),
      'Change attention resolved.',
    ),
    supersedePublication: () => mutate(
      'publication-supersede',
      () => {
        const existing = supersedePublicationOperation.current
        const operationId = existing?.changeId === identity.changeId
          ? existing.operationId
          : `cockpit-publication-supersede-${crypto.randomUUID()}`
        supersedePublicationOperation.current = { changeId: identity.changeId, operationId }
        return supersedeWorkItemPublication(identity.changeId, operationId)
      },
      'Publication superseded.',
    ).then((error) => {
      const operationId = supersedePublicationOperation.current?.operationId
      if (
        operationId
        && (error === null || (error instanceof WorkItemApiError && !error.retrySafe))
      ) {
        supersedePublicationOperation.current = null
      }
      return error
    }),
    syncTarget: () => mutate(
      'target-sync',
      () => {
        const existing = targetSyncOperation.current
        const operationId = existing?.changeId === identity.changeId
          ? existing.operationId
          : `cockpit-target-sync-${crypto.randomUUID()}`
        targetSyncOperation.current = { changeId: identity.changeId, operationId }
        return syncWorkItemTarget(identity.changeId, operationId)
      },
      'Target synchronized with the integration target.',
    ).then((error) => {
      const operationId = targetSyncOperation.current?.operationId
      if (
        operationId
        && (error === null || (error instanceof WorkItemApiError && !error.retrySafe))
      ) {
        targetSyncOperation.current = null
      }
      return error
    }),
    abortTargetSync: (expectedDispositionId: string, targetHead: string, operationId: string) => mutate(
      'target-sync-abort',
      () => abortWorkItemTargetSync(identity.changeId, expectedDispositionId, targetHead, operationId),
      'Target sync conflict aborted.',
    ).then((error) => {
      if (error === null) targetSyncOperation.current = null
      return error
    }),
    resolveTargetSync: (expectedDispositionId: string, targetHead: string, operationId: string) => mutate(
      'target-sync-resolve',
      () => resolveWorkItemTargetSync(identity.changeId, expectedDispositionId, targetHead, operationId),
      'Resolved target sync is ready for review.',
    ),
    deferChange: (reason: string) => mutate(
      'change-defer',
      () => deferWorkItemChange(identity.changeId, reason),
      'Change deferred.',
    ),
    resumeChange: () => mutate(
      'change-resume',
      () => resumeWorkItemChange(identity.changeId),
      'Change resumed.',
    ),
    abandonChange: (reason: string) => mutate(
      'change-abandon',
      () => abandonWorkItemChange(identity.changeId, reason),
      'Change abandoned.',
    ),
    cleanupAbandonedChange: () => mutate(
      'change-cleanup-abandoned',
      () => cleanupAbandonedWorkItemChange(identity.changeId),
      'Abandoned Change worktree cleaned up.',
    ),
    cleanupCompletedChange: (completionId: string) => mutate(
      'change-cleanup-completed',
      () => cleanupCompletedWorkItemChange(identity.changeId, completionId),
      'Completed Change worktree cleaned up.',
    ),
    recoverChangeWorktree: (recoveryReviewedHead: string) => mutate(
      'change-worktree-recover',
      () => recoverWorkItemChange(identity.changeId, recoveryReviewedHead),
      'Missing Change worktree recovered.',
    ),
    retry: polling.refetch,
  }
}

export function workItemIdentity(item: WorkItemCardView): string {
  return `${item.change_id}:${item.item_key}`
}
