import { useEffect, useRef, useState } from 'react'
import { PButton, PSelect, PSelectOption, PTextarea } from '@porsche-design-system/components-react'
import {
  getNativeRequest,
  NativeApiError,
  resolveNativeRequest,
  type NativeStoredRequest,
  type ResolveNativeRequestResult,
} from '../api/native'

type TextValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function textValue(event: TextValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

export default function NativeRequestResolver({
  stored,
  onResolved,
  onReturn,
}: {
  stored: NativeStoredRequest
  onResolved: () => void
  onReturn?: () => void
}) {
  const request = stored.request
  const isResolved = stored.resolution !== null
  const [response, setResponse] = useState(stored.resolution?.response ?? '')
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(stored.resolution?.selected_option_id ?? null)
  const [disposition, setDisposition] = useState<'local' | 'material'>('local')
  const [resolutionDigest, setResolutionDigest] = useState(request.delivery_digest)
  const [conflict, setConflict] = useState<NativeApiError | null>(null)
  const [conflictCurrent, setConflictCurrent] = useState<unknown>(null)
  const [result, setResult] = useState<ResolveNativeRequestResult | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const statusRef = useRef<HTMLDivElement | null>(null)
  const returnRef = useRef<HTMLElement | null>(null)
  const onResolvedRef = useRef(onResolved)
  onResolvedRef.current = onResolved

  useEffect(() => {
    if (result || conflict) {
      statusRef.current?.focus()
    }
  }, [conflict, result])

  useEffect(() => {
    if (!result) return
    let refreshFrame = 0
    const paintFrame = requestAnimationFrame(() => {
      refreshFrame = requestAnimationFrame(() => onResolvedRef.current())
    })
    return () => {
      cancelAnimationFrame(paintFrame)
      cancelAnimationFrame(refreshFrame)
    }
  }, [result])

  const resolve = async () => {
    setSubmitting(true)
    setConflict(null)
    setConflictCurrent(null)
    try {
      const nextResult = await resolveNativeRequest(request.change_id, request.request_id, {
        delivery_digest: resolutionDigest,
        disposition,
        resolved_at: new Date().toISOString(),
        resolved_by: 'cockpit-user',
        selected_option_id: selectedOptionId,
        response: response.trim() || null,
        rationale: 'Resolved from Cockpit Requests.',
      })
      setResult(nextResult)
    } catch (caught) {
      const nextConflict = caught instanceof NativeApiError
        ? caught
        : new NativeApiError(0, { code: 'ERR_NATIVE_REQUEST', detail: 'Resolution failed' })
      setConflict(nextConflict)
      setConflictCurrent(nextConflict.current ?? null)
      if (nextConflict.currentDeliveryDigest) {
        setResolutionDigest(nextConflict.currentDeliveryDigest)
      }
      if (nextConflict.status === 409 && !nextConflict.current) {
        try {
          setConflictCurrent(await getNativeRequest(request.change_id, request.request_id))
        } catch {
          setConflictCurrent(null)
        }
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mt-static-md border-t border-contrast-low pt-static-md" data-testid="native-request-resolver">
      {request.kind === 'decision' ? (
        <div className="grid gap-static-sm md:grid-cols-2">
          {(request.options ?? []).map((option) => (
            <button
              key={option.option_id}
              type="button"
              className={[
                'min-w-0 border p-static-md text-left',
                selectedOptionId === option.option_id ? 'border-primary bg-surface' : 'border-contrast-low bg-canvas',
              ].join(' ')}
              disabled={isResolved}
              aria-pressed={selectedOptionId === option.option_id}
              onClick={() => setSelectedOptionId(option.option_id)}
            >
              <span className="flex items-center justify-between gap-static-sm font-semibold">
                {option.label}
                {option.recommended ? <span aria-label="Recommended">Recommended</span> : null}
              </span>
              <span className="mt-static-xs block text-xs">Confidence {Math.round(option.confidence * 100)}%</span>
              <span className="mt-static-sm block text-xs"><strong>Pros:</strong> {option.pros.join(', ') || 'None'}</span>
              <span className="mt-1 block text-xs"><strong>Cons:</strong> {option.cons.join(', ') || 'None'}</span>
              <span className="mt-1 block text-xs"><strong>Risks:</strong> {option.risks.join(', ') || 'None'}</span>
              <span className="mt-1 block text-xs">{option.rationale}</span>
            </button>
          ))}
        </div>
      ) : (
        <div>
          <p className="text-sm"><strong>Evidence:</strong> {(request.evidence ?? []).join(', ')}</p>
          <p className="mt-static-xs text-sm"><strong>Resume when:</strong> {request.resume_condition}</p>
          {isResolved ? (
            <>
              <p className="mt-static-xs text-sm"><strong>Response:</strong> {stored.resolution?.response ?? 'None'}</p>
            </>
          ) : (
            <PTextarea
              name={`request-response-${request.request_id}`}
              label="Response"
              value={response}
              onChange={(event) => setResponse(textValue(event as TextValueEvent))}
            />
          )}
        </div>
      )}
      {isResolved ? (
        <div className="mt-static-sm flex flex-wrap items-center gap-static-sm text-xs" data-testid="persisted-resolution">
          <p>Resolved by {stored.resolution?.resolved_by ?? 'user'}.</p>
          <p>Disposition: {stored.resolution?.disposition}.</p>
          <p>Rationale: {stored.resolution?.rationale || 'None'}.</p>
          {onReturn ? <PButton ref={returnRef} type="button" variant="secondary" onClick={onReturn}>Return</PButton> : null}
        </div>
      ) : (
        <div className="mt-static-sm flex flex-wrap items-end gap-static-sm">
          <PSelect
            name={`request-disposition-${request.request_id}`}
            label="Resolution effect"
            value={disposition}
            onChange={(event) => {
              const value = textValue(event as TextValueEvent)
              if (value === 'local' || value === 'material') setDisposition(value)
            }}
          >
            <PSelectOption value="local">Resume linked jobs</PSelectOption>
            <PSelectOption value="material">Return to design</PSelectOption>
          </PSelect>
          <PButton
            type="button"
            disabled={submitting || (request.kind === 'decision' ? selectedOptionId === null : response.trim() === '')}
            onClick={() => void resolve()}
          >Complete request</PButton>
          {onReturn ? <PButton ref={returnRef} type="button" variant="secondary" onClick={onReturn}>Return</PButton> : null}
        </div>
      )}

      {result ? (
        <div ref={statusRef} tabIndex={-1} className="mt-static-md border-l-4 border-success pl-static-sm text-sm" role="status">
          {result.resume ? (
            <p>Resumed linked jobs: {result.resumed_jobs.map((item) => `#${item.job.job_id}`).join(', ') || result.resume.job_ids.map((id) => `#${id}`).join(', ')}</p>
          ) : (
            <p>Design re-entry: {result.design_reentry?.target_node_id ?? result.design_reentry?.change_id}</p>
          )}
        </div>
      ) : null}
      {conflict ? (
        <div ref={statusRef} tabIndex={-1} className="mt-static-md border-l-4 border-warning pl-static-sm text-xs" role="alert">
          <strong>{conflict.code}</strong> {conflict.detail}
          <p className="break-all">Current digest: {conflict.currentDeliveryDigest ?? 'unavailable'}</p>
          <p>Submitted: {selectedOptionId ?? response}</p>
          {conflictCurrent ? <pre className="max-h-32 overflow-auto whitespace-pre-wrap">{JSON.stringify(conflictCurrent, null, 2)}</pre> : null}
          <PButton type="button" compact variant="secondary" onClick={() => void resolve()}>Retry resolution</PButton>
          {onReturn ? <PButton type="button" compact variant="secondary" onClick={() => { onReturn(); requestAnimationFrame(() => returnRef.current?.focus()) }}>Return</PButton> : null}
        </div>
      ) : null}
    </div>
  )
}
