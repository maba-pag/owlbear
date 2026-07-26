import { useMemo, useState } from 'react'
import { PButton } from '@porsche-design-system/components-react'
import type { NativeReceipt, NativeReceiptValidity } from '../api/native'
import { useNativeChangeSelection } from '../hooks/NativeChangeProvider'
import {
  useNativeInvalidationDetail,
  useNativeJobs,
  useNativeReceipts,
} from '../hooks/useNativeResources'

interface ReceiptView {
  receipt: NativeReceipt
  validity: NativeReceiptValidity | null
}

function codeRevision(receipt: NativeReceipt): string {
  const revision = receipt.payload.code_revision
  return typeof revision === 'string' ? revision : 'Not recorded'
}

export default function EvidencePage() {
  const { selectedSummary } = useNativeChangeSelection()
  const changeId = selectedSummary?.state === 'loaded' ? selectedSummary.change_id : null
  const jobs = useNativeJobs(changeId)
  const receipts = useNativeReceipts(changeId)
  const [mode, setMode] = useState<'current' | 'full'>('current')
  const [selectedSupersessionId, setSelectedSupersessionId] = useState<string | null>(null)
  const invalidation = useNativeInvalidationDetail(changeId, selectedSupersessionId)

  const current = useMemo<ReceiptView[]>(() => {
    const byReceipt = new Map<string, ReceiptView>()
    for (const job of jobs.items) {
      if (job.receipt) byReceipt.set(job.receipt.receipt_id, { receipt: job.receipt, validity: job.validity })
    }
    return [...byReceipt.values()]
  }, [jobs.items])
  const validityByReceipt = useMemo(
    () => new Map(current.map((item) => [item.receipt.receipt_id, item.validity])),
    [current],
  )
  const visible: ReceiptView[] = mode === 'current'
    ? current
    : receipts.items.map((receipt) => ({ receipt, validity: validityByReceipt.get(receipt.receipt_id) ?? null }))

  return (
    <main className="min-w-0 flex-1 overflow-x-hidden" data-testid="evidence-page">
      <div className="mx-auto w-full max-w-[1440px] px-static-md py-static-lg md:px-static-xl">
        <header className="flex flex-wrap items-end justify-between gap-static-md border-b border-contrast-low pb-static-md">
          <div>
            <p className="text-xs font-semibold uppercase text-contrast-medium">Immutable proof records</p>
            <h1 className="mt-static-xs text-3xl font-semibold">Evidence</h1>
          </div>
          <div aria-label="Evidence history mode" className="flex gap-static-xs">
            <PButton type="button" compact variant={mode === 'current' ? 'primary' : 'secondary'} onClick={() => setMode('current')}>Current receipts</PButton>
            <PButton type="button" compact variant={mode === 'full' ? 'primary' : 'secondary'} onClick={() => setMode('full')}>Full history</PButton>
          </div>
        </header>

        {!changeId ? <p className="mt-static-lg text-sm">Select a valid change to inspect evidence.</p> : null}
        {(jobs.error || receipts.error) ? (
          <div className="mt-static-lg flex items-center gap-static-sm" role="alert">
            <span>Evidence is unavailable. {(jobs.error ?? receipts.error)?.message}</span>
            <PButton type="button" compact variant="secondary" onClick={() => { jobs.retry(); receipts.retry() }}>Retry</PButton>
          </div>
        ) : null}
        <div className="mt-static-lg grid gap-static-md md:grid-cols-2" aria-label="Native receipts">
          {visible.map(({ receipt, validity }) => {
            const validityCode = validity?.code ?? (receipt.kind === 'supersession' ? 'SUPERSESSION' : 'HISTORICAL')
            return (
              <article key={receipt.receipt_id} className="min-w-0 border-l-4 border-info pl-static-md" data-receipt-id={receipt.receipt_id}>
                <div className="flex flex-wrap items-center justify-between gap-static-xs">
                  <h2 className="break-all text-sm font-semibold">{receipt.receipt_id}</h2>
                  <span className="text-xs font-semibold">{validityCode}</span>
                </div>
                <p className="mt-static-xs text-xs">{receipt.kind} · {receipt.issued_at}</p>
                <p className="mt-static-xs break-all text-xs"><strong>Code revision:</strong> {codeRevision(receipt)}</p>
                <p className="mt-static-xs break-all text-xs"><strong>Delivery digest:</strong> {receipt.delivery_digest}</p>
                {validity ? <p className="mt-static-xs text-xs">{validity.detail}</p> : null}
                {receipt.impact_closure ? (
                  <p className="mt-static-xs break-words text-xs">
                    <strong>Impact:</strong> {[...receipt.impact_closure.paths, ...receipt.impact_closure.authority_targets].join(', ') || 'None'}
                  </p>
                ) : null}
                {receipt.kind === 'supersession' ? (
                  <PButton type="button" compact variant="secondary" onClick={() => setSelectedSupersessionId(receipt.receipt_id)}>Inspect supersession chain</PButton>
                ) : null}
              </article>
            )
          })}
        </div>
        {!jobs.isLoading && !receipts.isLoading && visible.length === 0 && changeId ? <p className="mt-static-lg text-sm">No native receipts.</p> : null}
        {mode === 'full' && receipts.nextCursor ? (
          <PButton type="button" variant="secondary" loading={receipts.isLoadingMore} onClick={receipts.loadMore}>Load more receipts</PButton>
        ) : null}

        {selectedSupersessionId ? (
          <section className="mt-static-xl border-t border-contrast-low pt-static-md" aria-label="Supersession chain" data-testid="supersession-chain">
            <div className="flex items-center justify-between gap-static-sm">
              <h2 className="text-xl font-semibold">Supersession chain</h2>
              <PButton type="button" compact variant="secondary" onClick={() => setSelectedSupersessionId(null)}>Close</PButton>
            </div>
            {invalidation.error ? <p role="alert">Chain unavailable. {invalidation.error.message}</p> : null}
            {invalidation.data ? (
              <dl className="mt-static-md grid gap-static-sm text-sm sm:grid-cols-2">
                <div><dt className="font-semibold">Invalidation</dt><dd className="break-all">{invalidation.data.invalidation_id}</dd></div>
                <div><dt className="font-semibold">Supersession receipt</dt><dd className="break-all">{invalidation.data.supersession_receipt_id}</dd></div>
                <div><dt className="font-semibold">Superseded receipts</dt><dd className="break-words">{invalidation.data.affected_receipt_ids.join(', ') || 'None'}</dd></div>
                <div><dt className="font-semibold">Corrective findings</dt><dd className="break-words">{invalidation.data.corrective_finding_ids.join(', ') || 'None'}</dd></div>
                <div><dt className="font-semibold">Corrective jobs</dt><dd>{invalidation.data.corrective_job_ids.map((id) => `#${id}`).join(', ') || 'None'}</dd></div>
              </dl>
            ) : null}
          </section>
        ) : null}
      </div>
    </main>
  )
}
