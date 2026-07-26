import {
  createContext,
  type PropsWithChildren,
  type ReactElement,
  useContext,
  useEffect,
  useMemo,
} from 'react'
import { useSearchParams } from 'react-router'
import type { NativeChangeDetail } from '../api/native'
import { useNativeChange, useNativeChanges } from './useNativeResources'

export interface NativeChangeSummary {
  change_id: string
  state: 'loaded' | 'invalid'
  delivery_digest: string | null
  diagnostics: Array<{ code: string; detail: string; target: string | null }>
}

interface NativeChangeContextValue {
  changes: NativeChangeSummary[]
  selectedChangeId: string | null
  selectedSummary: NativeChangeSummary | null
  missingChangeId: string | null
  detail: NativeChangeDetail | null
  isLoading: boolean
  error: Error | null
  selectChange: (changeId: string) => void
  retry: () => void
}

const NativeChangeContext = createContext<NativeChangeContextValue | null>(null)

export function NativeChangeProvider({ children }: PropsWithChildren): ReactElement {
  const [searchParams, setSearchParams] = useSearchParams()
  const summaries = useNativeChanges()
  const requestedChangeId = searchParams.get('change')
  const changes = summaries.data?.changes ?? []
  const requestedSummary = changes.find((change) => change.change_id === requestedChangeId) ?? null
  const missingChangeId = requestedChangeId !== null && requestedSummary === null ? requestedChangeId : null
  const selectedChangeId = requestedChangeId !== null ? requestedChangeId : (changes[0]?.change_id ?? null)
  const selectedSummary = changes.find((change) => change.change_id === selectedChangeId) ?? null
  const selectedDetail = useNativeChange(
    selectedSummary?.state === 'loaded' ? selectedSummary.change_id : null,
  )

  useEffect(() => {
    if (requestedChangeId !== null || selectedChangeId === null) {
      return
    }
    const next = new URLSearchParams(searchParams)
    next.set('change', selectedChangeId)
    setSearchParams(next, { replace: true })
  }, [requestedChangeId, searchParams, selectedChangeId, setSearchParams])

  const value = useMemo<NativeChangeContextValue>(
    () => ({
      changes,
      selectedChangeId,
      selectedSummary,
      missingChangeId,
      detail:
        selectedSummary?.state === 'loaded' && selectedDetail.data?.change_id === selectedSummary.change_id
          ? selectedDetail.data
          : null,
      isLoading: summaries.isLoading || (selectedSummary?.state === 'loaded' && selectedDetail.isLoading),
      error: summaries.error ?? (selectedSummary?.state === 'loaded' ? selectedDetail.error : null),
      selectChange: (changeId: string) => {
        const next = new URLSearchParams(searchParams)
        next.set('change', changeId)
        setSearchParams(next)
      },
      retry: () => {
        summaries.retry()
        if (selectedSummary?.state === 'loaded') {
          selectedDetail.retry()
        }
      },
    }),
    [changes, missingChangeId, searchParams, selectedChangeId, selectedDetail, selectedSummary, setSearchParams, summaries],
  )

  return <NativeChangeContext.Provider value={value}>{children}</NativeChangeContext.Provider>
}

export function useNativeChangeSelection(): NativeChangeContextValue {
  const context = useContext(NativeChangeContext)
  if (!context) {
    throw new Error('useNativeChangeSelection must be used within NativeChangeProvider')
  }
  return context
}
