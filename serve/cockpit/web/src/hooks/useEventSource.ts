import { useEffect, useRef, useState } from 'react'

export type UseEventSourceResult = {
  status: 'connecting' | 'open' | 'closed'
  lastEventMtime: number | null
}

export interface UseEventSourceOptions {
  enabled?: boolean
}

const STALL_TIMEOUT_MS = 15_000
const RETRY_TIMEOUT_MS = 30_000

export function useEventSource(
  url: string,
  options?: UseEventSourceOptions,
): UseEventSourceResult {
  const enabled = options?.enabled ?? true
  const [status, setStatus] = useState<'connecting' | 'open' | 'closed'>(
    enabled ? 'connecting' : 'closed',
  )
  const [lastEventMtime, setLastEventMtime] = useState<number | null>(null)

  const isMountedRef = useRef(true)
  const eventSourceRef = useRef<EventSource | null>(null)
  const stallTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    isMountedRef.current = true

    const clearStallTimer = () => {
      if (stallTimerRef.current !== null) {
        clearTimeout(stallTimerRef.current)
        stallTimerRef.current = null
      }
    }

    const clearRetryTimer = () => {
      if (retryTimerRef.current !== null) {
        clearTimeout(retryTimerRef.current)
        retryTimerRef.current = null
      }
    }

    const closeActiveSource = () => {
      eventSourceRef.current?.close()
      eventSourceRef.current = null
    }

    const openConnection = () => {
      if (!isMountedRef.current || !enabled) {
        return
      }

      closeActiveSource()
      clearStallTimer()

      const eventSource = new EventSource(url)
      eventSourceRef.current = eventSource

      if (isMountedRef.current) {
        setStatus('connecting')
      }

      eventSource.onopen = () => {
        if (!isMountedRef.current) {
          return
        }
        clearStallTimer()
        clearRetryTimer()
        setStatus('open')
      }

      eventSource.onerror = () => {
        if (!isMountedRef.current) {
          return
        }

        if (eventSource.readyState === EventSource.CLOSED) {
          clearStallTimer()
          setStatus('closed')
          closeActiveSource()
          clearRetryTimer()
          retryTimerRef.current = setTimeout(() => {
            openConnection()
          }, RETRY_TIMEOUT_MS)
          return
        }

        if (eventSource.readyState === EventSource.CONNECTING) {
          clearStallTimer()
          stallTimerRef.current = setTimeout(() => {
            if (!isMountedRef.current) {
              return
            }

            eventSource.close()
            if (eventSourceRef.current === eventSource) {
              eventSourceRef.current = null
            }

            setStatus('closed')
            clearRetryTimer()
            retryTimerRef.current = setTimeout(() => {
              openConnection()
            }, RETRY_TIMEOUT_MS)
          }, STALL_TIMEOUT_MS)
        }
      }

      eventSource.addEventListener('tasks-changed', (event: Event) => {
        if (!isMountedRef.current) {
          return
        }

        const messageEvent = event as MessageEvent<string>
        try {
          const payload = JSON.parse(messageEvent.data) as { mtime?: unknown }
          if (typeof payload.mtime === 'number') {
            setLastEventMtime(payload.mtime)
          }
        } catch {
          // Ignore malformed events to keep the stream alive.
        }
      })
    }

    if (!enabled) {
      closeActiveSource()
      clearStallTimer()
      clearRetryTimer()
      setStatus('closed')
      setLastEventMtime(null)
      return () => {
        isMountedRef.current = false
        closeActiveSource()
        clearStallTimer()
        clearRetryTimer()
      }
    }

    setStatus('connecting')
    openConnection()

    return () => {
      isMountedRef.current = false
      closeActiveSource()
      clearStallTimer()
      clearRetryTimer()
    }
  }, [enabled, url])

  return { status, lastEventMtime }
}