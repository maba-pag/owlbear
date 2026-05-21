import { useCallback, useEffect, useRef, useState } from 'react'
import { getResponseErrorMessage } from '../api/errorMessage'

const DEFAULT_INTERVAL_MS = 3000

type PollReason = 'initial' | 'interval' | 'manual'

export interface UsePollingFetchOptions<TPayload> {
  intervalMs?: number
  paused?: boolean
  method?: string
  requestInit?: Omit<RequestInit, 'method' | 'signal'>
  parse?: (response: Response) => Promise<TPayload>
  onSuccess?: (payload: TPayload) => void | Promise<void>
  onError?: (error: Error) => void | Promise<void>
}

export interface UsePollingFetchResult {
  isFetching: boolean
  hasFetched: boolean
  refetch: () => void
}

export function usePollingFetch<TPayload = unknown>(
  url: string,
  options?: UsePollingFetchOptions<TPayload>,
): UsePollingFetchResult {
  const intervalMs = options?.intervalMs ?? DEFAULT_INTERVAL_MS
  const [isFetching, setIsFetching] = useState(false)
  const [hasFetched, setHasFetched] = useState(false)
  const isMountedRef = useRef(true)
  const inFlightRef = useRef(false)
  const pendingPollReasonRef = useRef<PollReason | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const pausedRef = useRef(options?.paused ?? false)

  const methodRef = useRef(options?.method)
  const requestInitRef = useRef(options?.requestInit)
  const parseRef = useRef(options?.parse)
  const onSuccessRef = useRef(options?.onSuccess)
  const onErrorRef = useRef(options?.onError)
  methodRef.current = options?.method
  requestInitRef.current = options?.requestInit
  parseRef.current = options?.parse
  onSuccessRef.current = options?.onSuccess
  onErrorRef.current = options?.onError
  pausedRef.current = options?.paused ?? false

  const poll = useCallback(async (reason: PollReason): Promise<void> => {
    if (inFlightRef.current) {
      pendingPollReasonRef.current = reason
      return
    }

    inFlightRef.current = true
    pendingPollReasonRef.current = null
    if (isMountedRef.current) {
      setIsFetching(true)
    }

    const controller = new AbortController()
    controllerRef.current = controller

    try {
      const response = await fetch(url, {
        ...(requestInitRef.current ?? {}),
        method: methodRef.current ?? 'GET',
        signal: controller.signal,
      })
      if (!response.ok) {
        const errorMessage = await getResponseErrorMessage(
          response,
          `Polling request failed with status ${response.status}`,
        )
        throw new Error(errorMessage)
      }

      const parse = parseRef.current ?? (async (res: Response) => (await res.json()) as TPayload)
      const payload = await parse(response)
      await onSuccessRef.current?.(payload)
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === 'AbortError') {
        return
      }
      const error = caught instanceof Error ? caught : new Error('Polling request failed')
      await onErrorRef.current?.(error)
    } finally {
      inFlightRef.current = false
      if (controllerRef.current === controller) {
        controllerRef.current = null
      }
      if (isMountedRef.current) {
        setIsFetching(false)
        setHasFetched(true)
      }
      const pendingReason = pendingPollReasonRef.current
      if (pendingReason !== null && isMountedRef.current && (pendingReason === 'initial' || !pausedRef.current)) {
        pendingPollReasonRef.current = null
        void poll(pendingReason)
      }
    }
  }, [url])

  useEffect(() => {
    isMountedRef.current = true
    void poll('initial')

    const intervalId = setInterval(() => {
      if (!pausedRef.current) {
        void poll('interval')
      }
    }, intervalMs)

    return () => {
      isMountedRef.current = false
      clearInterval(intervalId)
      controllerRef.current?.abort()
      controllerRef.current = null
    }
  }, [intervalMs, poll])

  const stableRefetch = useCallback(() => {
    void poll('manual')
  }, [poll])

  return {
    isFetching,
    hasFetched,
    refetch: stableRefetch,
  }
}
