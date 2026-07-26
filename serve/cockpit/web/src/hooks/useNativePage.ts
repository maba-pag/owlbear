import { useCallback, useEffect, useRef, useState } from 'react'
import { NativeApiError, type NativePage, type NativeResource } from '../api/native'
import { useNativeInvalidation } from './NativeInvalidationProvider'

const DEFAULT_POLL_INTERVAL_MS = 10_000

export interface UseNativePageOptions<T> {
  resource: NativeResource
  additionalResources?: NativeResource[]
  alwaysPoll?: boolean
  load: (cursor?: string) => Promise<NativePage<T>>
  identity: (item: T) => string | number
  pollIntervalMs?: number
}

export interface UseNativePageResult<T> {
  items: T[]
  nextCursor: string | null
  isLoading: boolean
  isLoadingMore: boolean
  error: NativeApiError | Error | null
  retryFromStart: boolean
  loadMore: () => void
  retry: () => void
}

function appendUnseen<T>(current: T[], incoming: T[], identity: (item: T) => string | number): T[] {
  const seen = new Set(current.map(identity))
  return [...current, ...incoming.filter((item) => !seen.has(identity(item)))]
}

export function useNativePage<T>({
  resource,
  additionalResources = [],
  alwaysPoll = false,
  load,
  identity,
  pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
}: UseNativePageOptions<T>): UseNativePageResult<T> {
  const { status, token } = useNativeInvalidation(resource)
  const secondary = useNativeInvalidation(additionalResources[0] ?? resource)
  const tertiary = useNativeInvalidation(additionalResources[1] ?? resource)
  const quaternary = useNativeInvalidation(additionalResources[2] ?? resource)
  const [items, setItems] = useState<T[]>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<NativeApiError | Error | null>(null)
  const [retryFromStart, setRetryFromStart] = useState(false)
  const mountedRef = useRef(true)
  const inFlightRef = useRef(false)
  const pendingRefreshRef = useRef(false)
  const generationRef = useRef(0)
  const loadRef = useRef(load)
  const identityRef = useRef(identity)
  const lastTokenRef = useRef<number | null>(null)
  loadRef.current = load
  identityRef.current = identity

  const refresh = useCallback(async (cursor?: string) => {
    if (inFlightRef.current) {
      if (!cursor) {
        pendingRefreshRef.current = true
      }
      return
    }
    const generation = generationRef.current
    inFlightRef.current = true
    if (cursor) {
      setIsLoadingMore(true)
    } else {
      setIsLoading(true)
    }
    try {
      const page = await loadRef.current(cursor)
      if (!mountedRef.current || generation !== generationRef.current) {
        return
      }
      setItems((current) => (cursor ? appendUnseen(current, page.items, identityRef.current) : page.items))
      setNextCursor(page.next_cursor)
      setRetryFromStart(false)
      setError(null)
    } catch (caught) {
      if (!mountedRef.current || generation !== generationRef.current) {
        return
      }
      const nextError = caught instanceof Error ? caught : new Error('Native resource request failed')
      setError(nextError)
      if (cursor && caught instanceof NativeApiError && caught.code === 'ERR_CURSOR_STALE') {
        setNextCursor(null)
        setRetryFromStart(true)
      }
    } finally {
      inFlightRef.current = false
      if (mountedRef.current) {
        setIsLoading(false)
        setIsLoadingMore(false)
      }
      if (pendingRefreshRef.current && mountedRef.current) {
        pendingRefreshRef.current = false
        void refresh()
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    generationRef.current += 1
    setNextCursor(null)
    void refresh()
    return () => {
      mountedRef.current = false
    }
  }, [load, refresh])

  useEffect(() => {
    const newestToken = Math.max(token ?? 0, secondary.token ?? 0, tertiary.token ?? 0, quaternary.token ?? 0)
    if (newestToken <= (lastTokenRef.current ?? 0)) {
      return
    }
    lastTokenRef.current = newestToken
    void refresh()
  }, [quaternary.token, refresh, secondary.token, tertiary.token, token])

  useEffect(() => {
    if (!alwaysPoll && status === 'open') {
      return
    }
    const interval = setInterval(() => void refresh(), pollIntervalMs)
    return () => clearInterval(interval)
  }, [alwaysPoll, pollIntervalMs, refresh, status])

  return {
    items,
    nextCursor,
    isLoading,
    isLoadingMore,
    error,
    retryFromStart,
    loadMore: () => {
      if (nextCursor !== null) {
        void refresh(nextCursor)
      }
    },
    retry: () => void refresh(),
  }
}
