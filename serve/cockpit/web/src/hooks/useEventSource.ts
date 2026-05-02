import { useEffect, useMemo, useRef, useState } from 'react'

export type UseEventSourceResult = {
  status: 'connecting' | 'open' | 'closed'
  lastEventMtime: number | null
  lastEventByType: Record<string, number>
}

export interface UseEventSourceOptions {
  enabled?: boolean
  eventTypes?: string[]
}

const STALL_TIMEOUT_MS = 15_000
const RETRY_TIMEOUT_MS = 30_000

export function useEventSource(
  url: string,
  options?: UseEventSourceOptions,
): UseEventSourceResult {
  const enabled = options?.enabled ?? true
  const eventTypesKey = (options?.eventTypes ?? ['tasks-changed']).join('|')
  const eventTypes = useMemo(
    () => options?.eventTypes ?? ['tasks-changed'],
    [eventTypesKey],
  )
  const [status, setStatus] = useState<'connecting' | 'open' | 'closed'>(
    enabled ? 'connecting' : 'closed',
  )
  const [lastEventMtime, setLastEventMtime] = useState<number | null>(null)
  const [lastEventByType, setLastEventByType] = useState<Record<string, number>>({})

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

    const isCurrentSource = (source: EventSource) =>
      eventSourceRef.current === source

    const openConnection = () => {
      if (!isMountedRef.current) {
        return
      }

      closeActiveSource()
      clearStallTimer()

      const eventSource = new EventSource(url)
      eventSourceRef.current = eventSource

      setStatus('connecting')

      eventSource.onopen = () => {
        if (!isMountedRef.current || !isCurrentSource(eventSource)) {
          return
        }
        clearStallTimer()
        clearRetryTimer()
        setStatus('open')
      }

      eventSource.onerror = () => {
        if (!isMountedRef.current || !isCurrentSource(eventSource)) {
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
            if (!isMountedRef.current || !isCurrentSource(eventSource)) {
              return
            }

            eventSource.close()
            eventSourceRef.current = null

            setStatus('closed')
            clearRetryTimer()
            retryTimerRef.current = setTimeout(() => {
              openConnection()
            }, RETRY_TIMEOUT_MS)
          }, STALL_TIMEOUT_MS)
        }
      }

      for (const eventType of eventTypes) {
        eventSource.addEventListener(eventType, (event: Event) => {
          if (!isMountedRef.current || !isCurrentSource(eventSource)) {
            return
          }

          const messageEvent = event as MessageEvent<string>
          try {
            const payload = JSON.parse(messageEvent.data) as { mtime?: unknown }
            if (typeof payload.mtime === 'number') {
              setLastEventByType((previousByType) => {
                const nextByType = {
                  ...previousByType,
                  [eventType]: payload.mtime,
                }
                const nextMaxMtime = Math.max(...Object.values(nextByType))
                setLastEventMtime(nextMaxMtime)
                return nextByType
              })
            }
          } catch {
            // Ignore malformed events to keep the stream alive.
          }
        })
      }
    }

    if (!enabled) {
      closeActiveSource()
      clearStallTimer()
      clearRetryTimer()
      setStatus('closed')
      setLastEventMtime(null)
      setLastEventByType({})
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
  }, [enabled, eventTypes, url])

  return { status, lastEventMtime, lastEventByType }
}
