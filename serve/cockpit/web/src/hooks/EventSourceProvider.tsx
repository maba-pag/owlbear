import {
  createContext,
  type ReactElement,
  type PropsWithChildren,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'

type EventSourceStatus = 'connecting' | 'open' | 'closed'

const EVENT_TYPES = ['tasks-changed', 'decisions-changed', 'activity-changed'] as const
const STALL_TIMEOUT_MS = 15_000
const RETRY_TIMEOUT_MS = 30_000

type EventType = (typeof EVENT_TYPES)[number]
type EventTypeMtimes = Record<EventType, number | null>

interface EventSourceContextValue {
  status: EventSourceStatus
  mtimes: EventTypeMtimes
}

interface EventSourceProviderProps extends PropsWithChildren {
  url: string
}

const EventSourceContext = createContext<EventSourceContextValue | null>(null)

function createInitialMtimes(): EventTypeMtimes {
  return {
    'tasks-changed': null,
    'decisions-changed': null,
    'activity-changed': null,
  }
}

export function EventSourceProvider({
  url,
  children,
}: EventSourceProviderProps): ReactElement {
  const [status, setStatus] = useState<EventSourceStatus>('connecting')
  const [mtimes, setMtimes] = useState<EventTypeMtimes>(createInitialMtimes)

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

    const isCurrentSource = (source: EventSource) => eventSourceRef.current === source

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

      for (const eventType of EVENT_TYPES) {
        eventSource.addEventListener(eventType, (event: Event) => {
          if (!isMountedRef.current || !isCurrentSource(eventSource)) {
            return
          }

          const messageEvent = event as MessageEvent<string>
          try {
            const payload = JSON.parse(messageEvent.data) as { mtime?: unknown }
            if (typeof payload.mtime === 'number') {
              setMtimes((previous): EventTypeMtimes => ({
                ...previous,
                [eventType]: payload.mtime,
              }))
            }
          } catch {
            // Ignore malformed events to keep the stream alive.
          }
        })
      }
    }

    setStatus('connecting')
    setMtimes(createInitialMtimes())
    openConnection()

    return () => {
      isMountedRef.current = false
      closeActiveSource()
      clearStallTimer()
      clearRetryTimer()
    }
  }, [url])

  return (
    <EventSourceContext.Provider value={{ status, mtimes }}>
      {children}
    </EventSourceContext.Provider>
  )
}

export function useSSEEvent(eventType: string): {
  mtime: number | null
  status: EventSourceStatus
} {
  const context = useContext(EventSourceContext)
  if (!context) {
    throw new Error('useSSEEvent must be used within an EventSourceProvider')
  }

  return {
    mtime: (context.mtimes as Record<string, number | null>)[eventType] ?? null,
    status: context.status,
  }
}
