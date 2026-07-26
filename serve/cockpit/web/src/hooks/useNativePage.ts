import { useCallback, useEffect, useRef, useState } from 'react'
import { NativeApiError, type NativePage, type NativeResource } from '../api/native'
import { useNativeInvalidation } from './NativeInvalidationProvider'

const DEFAULT_POLL_INTERVAL_MS = 10_000

export interface UseNativePageOptions<T> {
  resource: NativeResource
  additionalResources?: NativeResource[]
  alwaysPoll?: boolean
  enabled?: boolean
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
  enabled = true,
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
  const inFlightGenerationRef = useRef<number | null>(null)
  const pendingRefreshGenerationRef = useRef<number | null>(null)
  const generationRef = useRef(0)
  const loadRef = useRef(load)
  const identityRef = useRef(identity)
  const lastTokenRef = useRef<string>(
    [token, secondary.token, tertiary.token, quaternary.token]
      .filter((value): value is string => value !== null)
      .reduce((latest, value) => (BigInt(value) > BigInt(latest) ? value : latest), '0'),
  )
  loadRef.current = load
  identityRef.current = identity

  const refresh = useCallback(async (cursor?: string) => {
    const generation = generationRef.current
    if (inFlightGenerationRef.current === generation) {
      if (!cursor) {
        pendingRefreshGenerationRef.current = generation
      }
      return
    }
    inFlightGenerationRef.current = generation
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
      if (inFlightGenerationRef.current === generation) {
        inFlightGenerationRef.current = null
      }
      if (mountedRef.current && generation === generationRef.current) {
        setIsLoading(false)
        setIsLoadingMore(false)
      }
      if (pendingRefreshGenerationRef.current === generation && mountedRef.current) {
        pendingRefreshGenerationRef.current = null
        void refresh()
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    generationRef.current += 1
    pendingRefreshGenerationRef.current = null
    setNextCursor(null)
    if (!enabled) {
      setItems([])
      setError(null)
      setIsLoading(false)
      return
    }
    void refresh()
    return () => {
      mountedRef.current = false
    }
  }, [enabled, load, refresh])

  useEffect(() => {
    const newestToken = [token, secondary.token, tertiary.token, quaternary.token]
      .filter((value): value is string => value !== null)
      .reduce((latest, value) => (BigInt(value) > BigInt(latest) ? value : latest), '0')
    if (!enabled || BigInt(newestToken) <= BigInt(lastTokenRef.current ?? '0')) {
      return
    }
    lastTokenRef.current = newestToken
    void refresh()
  }, [enabled, quaternary.token, refresh, secondary.token, tertiary.token, token])

  useEffect(() => {
    if (!enabled || (!alwaysPoll && status === 'open')) {
      return
    }
    const interval = setInterval(() => void refresh(), pollIntervalMs)
    return () => clearInterval(interval)
  }, [alwaysPoll, enabled, pollIntervalMs, refresh, status])

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
