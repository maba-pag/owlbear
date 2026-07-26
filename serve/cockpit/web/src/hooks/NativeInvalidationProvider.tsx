import {
  createContext,
  type PropsWithChildren,
  type ReactElement,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import type { NativeChangedEvent, NativeResource } from '../api/native'

export type NativeConnectionStatus = 'connecting' | 'open' | 'closed'

interface NativeInvalidationContextValue {
  status: NativeConnectionStatus
  tokens: Partial<Record<NativeResource, number>>
}

interface NativeInvalidationProviderProps extends PropsWithChildren {
  url?: string
  reconnectMs?: number
}

const NativeInvalidationContext = createContext<NativeInvalidationContextValue | null>(null)

function isNativeChangedEvent(value: unknown): value is NativeChangedEvent {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const record = value as Record<string, unknown>
  return (
    Array.isArray(record.resources) &&
    record.resources.every((item) => typeof item === 'string') &&
    typeof record.token === 'number' &&
    Number.isSafeInteger(record.token)
  )
}

export function NativeInvalidationProvider({
  children,
  url = '/api/events',
  reconnectMs = 30_000,
}: NativeInvalidationProviderProps): ReactElement {
  const [status, setStatus] = useState<NativeConnectionStatus>('connecting')
  const [tokens, setTokens] = useState<Partial<Record<NativeResource, number>>>({})
  const sourceRef = useRef<EventSource | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let active = true

    const clearReconnect = () => {
      if (reconnectRef.current !== null) {
        clearTimeout(reconnectRef.current)
        reconnectRef.current = null
      }
    }

    const connect = () => {
      if (!active) {
        return
      }
      sourceRef.current?.close()
      const source = new EventSource(url)
      sourceRef.current = source
      setStatus('connecting')

      source.onopen = () => {
        if (active && sourceRef.current === source) {
          clearReconnect()
          setStatus('open')
        }
      }
      source.addEventListener('native-changed', (event) => {
        if (!active || sourceRef.current !== source) {
          return
        }
        try {
          const payload = JSON.parse((event as MessageEvent<string>).data) as unknown
          if (!isNativeChangedEvent(payload)) {
            return
          }
          setTokens((previous) => {
            if (payload.resources.every((resource) => payload.token <= (previous[resource] ?? 0))) {
              return previous
            }
            const next = { ...previous }
            for (const resource of payload.resources) {
              if (payload.token > (next[resource] ?? 0)) {
                next[resource] = payload.token
              }
            }
            return next
          })
        } catch {
          // Malformed invalidations do not tear down the live connection.
        }
      })
      source.onerror = () => {
        if (!active || sourceRef.current !== source) {
          return
        }
        source.close()
        sourceRef.current = null
        setStatus('closed')
        clearReconnect()
        reconnectRef.current = setTimeout(connect, reconnectMs)
      }
    }

    connect()
    return () => {
      active = false
      sourceRef.current?.close()
      sourceRef.current = null
      clearReconnect()
    }
  }, [reconnectMs, url])

  return (
    <NativeInvalidationContext.Provider value={{ status, tokens }}>
      {children}
    </NativeInvalidationContext.Provider>
  )
}

export function useNativeInvalidation(resource: NativeResource): {
  status: NativeConnectionStatus
  token: number | null
} {
  const context = useContext(NativeInvalidationContext)
  if (!context) {
    throw new Error('useNativeInvalidation must be used within NativeInvalidationProvider')
  }
  return { status: context.status, token: context.tokens[resource] ?? null }
}
