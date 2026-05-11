import { useCallback, useEffect, useRef, useState } from 'react'
import { getResponseErrorMessage } from '../api/errorMessage'

const DEFAULT_INTERVAL_MS = 3000

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
  const pendingPollRef = useRef(false)
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

  const poll = useCallback(async (): Promise<void> => {
    if (inFlightRef.current) {
      pendingPollRef.current = true
      return
    }

    inFlightRef.current = true
    pendingPollRef.current = false
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
      if (pendingPollRef.current && isMountedRef.current && !pausedRef.current) {
        pendingPollRef.current = false
        void poll()
      }
    }
  }, [url])

  useEffect(() => {
    isMountedRef.current = true
    void poll()

    const intervalId = setInterval(() => {
      if (!pausedRef.current) {
        void poll()
      }
    }, intervalMs)

    return () => {
      isMountedRef.current = false
      clearInterval(intervalId)
      controllerRef.current?.abort()
      controllerRef.current = null
    }
  }, [intervalMs, poll])

  return {
    isFetching,
    hasFetched,
    refetch: () => {
      void poll()
    },
  }
}

