import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getLegacyInventory,
  getNativeChange,
  getNativeChangeHealth,
  getNativeGraph,
  getNativeInvalidation,
  getNativeJob,
  getNativeWorkHealth,
  listNativeActivity,
  listNativeAttempts,
  listNativeChanges,
  listNativeFindings,
  listNativeJobs,
  listNativeReceipts,
  listNativeRequests,
  type LegacyInventory,
  type NativeActivityEntry,
  type NativeAttempt,
  type NativeChangeDetail,
  type NativeChangeList,
  type NativeFinding,
  type NativeGraphDetail,
  type NativeHealthPage,
  type NativeInvalidationDetail,
  type NativeJobProjection,
  type NativeJobDetail,
  type NativeReceipt,
  type NativeResource,
  type NativeStoredRequest,
} from '../api/native'
import { useNativeInvalidation } from './NativeInvalidationProvider'
import { useNativePage, type UseNativePageResult } from './useNativePage'

export function useNativeJobs(changeId: string): UseNativePageResult<NativeJobProjection> {
  const load = useCallback((cursor?: string) => listNativeJobs(changeId, cursor), [changeId])
  return useNativePage({ resource: 'jobs', load, identity: (item) => item.job_id })
}

export function useNativeRequests(changeId: string): UseNativePageResult<NativeStoredRequest> {
  const load = useCallback((cursor?: string) => listNativeRequests(changeId, cursor), [changeId])
  return useNativePage({ resource: 'requests', load, identity: (item) => item.request.request_id })
}

export function useNativeAttempts(changeId: string): UseNativePageResult<NativeAttempt> {
  const load = useCallback((cursor?: string) => listNativeAttempts(changeId, cursor), [changeId])
  return useNativePage({ resource: 'attempts', load, identity: (item) => item.attempt_id })
}

export function useNativeFindings(changeId: string): UseNativePageResult<NativeFinding> {
  const load = useCallback((cursor?: string) => listNativeFindings(changeId, cursor), [changeId])
  return useNativePage({ resource: 'findings', load, identity: (item) => item.finding_id })
}

export function useNativeReceipts(changeId: string): UseNativePageResult<NativeReceipt> {
  const load = useCallback((cursor?: string) => listNativeReceipts(changeId, cursor), [changeId])
  return useNativePage({ resource: 'receipts', load, identity: (item) => item.receipt_id })
}

export function useNativeActivity(changeId: string): UseNativePageResult<NativeActivityEntry> {
  const load = useCallback((cursor?: string) => listNativeActivity(changeId, cursor), [changeId])
  return useNativePage({
    resource: 'attempts',
    additionalResources: ['findings', 'receipts', 'requests'],
    alwaysPoll: true,
    load,
    identity: (item) => item.identity,
  })
}

interface NativeValueOptions<T> {
  resources: NativeResource[]
  load: () => Promise<T>
  pollIntervalMs?: number
}

function useNativeValue<T>({ resources, load, pollIntervalMs = 10_000 }: NativeValueOptions<T>): {
  data: T | null
  error: Error | null
  isLoading: boolean
  retry: () => void
} {
  const primary = useNativeInvalidation(resources[0])
  const secondary = useNativeInvalidation(resources[1] ?? resources[0])
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const generationRef = useRef(0)
  const primaryTokenRef = useRef(primary.token)
  const secondaryTokenRef = useRef(secondary.token)
  const loadRef = useRef(load)
  loadRef.current = load

  const refresh = useCallback(async () => {
    const generation = ++generationRef.current
    setIsLoading(true)
    try {
      const payload = await loadRef.current()
      if (generation === generationRef.current) {
        setData(payload)
        setError(null)
      }
    } catch (caught) {
      if (generation === generationRef.current) {
        setError(caught instanceof Error ? caught : new Error('Native resource request failed'))
      }
    } finally {
      if (generation === generationRef.current) {
        setIsLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    generationRef.current += 1
    void refresh()
  }, [load, refresh])

  useEffect(() => {
    const changed =
      (primary.token !== null && primary.token !== primaryTokenRef.current) ||
      (secondary.token !== null && secondary.token !== secondaryTokenRef.current)
    primaryTokenRef.current = primary.token
    secondaryTokenRef.current = secondary.token
    if (changed) {
      void refresh()
    }
  }, [primary.token, refresh, secondary.token])

  useEffect(() => {
    if (primary.status === 'open') {
      return
    }
    const interval = setInterval(() => void refresh(), pollIntervalMs)
    return () => clearInterval(interval)
  }, [pollIntervalMs, primary.status, refresh])

  return { data, error, isLoading, retry: () => void refresh() }
}

export function useNativeChanges(): ReturnType<typeof useNativeValue<NativeChangeList>> {
  return useNativeValue({ resources: ['changes'], load: listNativeChanges })
}

export function useNativeChange(changeId: string): ReturnType<typeof useNativeValue<NativeChangeDetail>> {
  const load = useCallback(() => getNativeChange(changeId), [changeId])
  return useNativeValue({ resources: ['changes'], load })
}

export function useNativeGraph(changeId: string): ReturnType<typeof useNativeValue<NativeGraphDetail>> {
  const load = useCallback(() => getNativeGraph(changeId), [changeId])
  return useNativeValue({ resources: ['graphs'], load })
}

export function useNativeInvalidationDetail(
  changeId: string,
  receiptId: string,
): ReturnType<typeof useNativeValue<NativeInvalidationDetail>> {
  const load = useCallback(() => getNativeInvalidation(changeId, receiptId), [changeId, receiptId])
  return useNativeValue({ resources: ['receipts'], load })
}

export function useNativeWorkHealth(changeId: string): ReturnType<typeof useNativeValue<NativeHealthPage>> {
  const load = useCallback(() => getNativeWorkHealth(changeId), [changeId])
  return useNativeValue({ resources: ['jobs'], load })
}

export function useNativeChangeHealth(changeId: string): ReturnType<typeof useNativeValue<NativeHealthPage>> {
  const load = useCallback(() => getNativeChangeHealth(changeId), [changeId])
  return useNativeValue({ resources: ['changes'], load })
}

export function useLegacyInventory(): ReturnType<typeof useNativeValue<LegacyInventory>> {
  return useNativeValue({ resources: ['changes'], load: getLegacyInventory, pollIntervalMs: 30_000 })
}

export function useNativeJob(
  changeId: string,
  jobId: number,
): ReturnType<typeof useNativeValue<NativeJobDetail>> {
  const load = useCallback(() => getNativeJob(changeId, jobId), [changeId, jobId])
  return useNativeValue({ resources: ['jobs'], load })
}
