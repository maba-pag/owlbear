import { PButton, PHeading, PIcon, PSelect, PSelectOption, PTag } from '@porsche-design-system/components-react'
import { useNativeChangeSelection } from '../hooks/NativeChangeProvider'

type SelectValueEvent = {
  target?: { value?: unknown }
  detail?: { value?: unknown }
}

function selectedValue(event: SelectValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function decisionsFrom(value: Record<string, unknown> | undefined): Array<Record<string, unknown>> {
  if (!value || !Array.isArray(value.decisions)) {
    return []
  }
  return value.decisions.filter(
    (item): item is Record<string, unknown> =>
      typeof item === 'object' && item !== null && (item as Record<string, unknown>).status === 'accepted',
  )
}

function record(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {}
}

export default function SpecificationPage() {
  const {
    changes,
    selectedChangeId,
    selectedSummary,
    missingChangeId,
    detail,
    isLoading,
    error,
    selectChange,
    retry,
  } = useNativeChangeSelection()
  const decisions = decisionsFrom(detail?.decisions)
  const graph = record(detail?.graph)
  const authority = record(graph.authority)
  const admission = record(graph.admission)
  const research = Array.isArray(authority.research) ? authority.research.map(String) : []
  const limits = Array.isArray(admission.limits) ? admission.limits.map(String) : []

  return (
    <main className="h-full min-h-0 overflow-y-auto bg-canvas" data-testid="specification-page">
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-static-lg px-static-md py-static-lg md:px-static-xl">
        <header className="flex min-w-0 flex-col gap-static-md border-b border-contrast-low pb-static-lg md:flex-row md:items-end md:justify-between">
          <div className="min-w-0">
            <p className="mb-static-xs text-sm font-semibold text-contrast-medium">Current change authority</p>
            <PHeading tag="h1" size="xl">Specification</PHeading>
          </div>
          <label className="flex w-full max-w-[30rem] flex-col gap-static-xs text-sm font-semibold" htmlFor="change-selector">
            Change
            <PSelect
              id="change-selector"
              name="change-selector"
              value={selectedChangeId ?? ''}
              onChange={(event) => selectChange(selectedValue(event as SelectValueEvent))}
            >
              {changes.map((change) => (
                <PSelectOption key={change.change_id} value={change.change_id}>
                  {change.state === 'invalid' ? `Invalid: ${change.change_id}` : change.change_id}
                </PSelectOption>
              ))}
            </PSelect>
          </label>
        </header>

        {isLoading && detail === null ? <p role="status">Loading specification...</p> : null}
        {missingChangeId ? (
          <section className="flex flex-wrap items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
            <PIcon name="error" aria-hidden="true" />
            <span className="min-w-0 flex-1">Change “{missingChangeId}” was not found.</span>
            <PButton type="button" variant="secondary" onClick={retry}>Retry</PButton>
          </section>
        ) : null}
        {error ? (
          <section className="flex flex-wrap items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
            <PIcon name="error" aria-hidden="true" />
            <span className="min-w-0 flex-1">Specification is unavailable. {error.message}</span>
            <PButton type="button" variant="secondary" onClick={retry}>Retry</PButton>
          </section>
        ) : null}
        {selectedSummary?.state === 'invalid' ? (
          <section className="border-l-4 border-warning bg-surface p-static-md" role="status" data-testid="invalid-change">
            <div className="flex items-center gap-static-sm font-semibold">
              <PIcon name="warning" aria-hidden="true" />
              Invalid authority
            </div>
            <ul className="mt-static-sm space-y-static-xs text-sm">
              {selectedSummary.diagnostics.map((diagnostic) => (
                <li key={`${diagnostic.code}-${diagnostic.target ?? ''}`}>
                  <strong>{diagnostic.code}</strong>: {diagnostic.detail}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {detail ? (
          <>
            <section aria-labelledby="authority-heading" tabIndex={0} className="grid gap-static-md border-b border-contrast-low pb-static-lg md:grid-cols-[minmax(0,1fr)_auto]">
              <div>
                <PHeading id="authority-heading" tag="h2" size="lg">Authority</PHeading>
                <p className="mt-static-sm break-words text-sm text-contrast-medium">{detail.change_id}</p>
              </div>
              <div className="min-w-0 md:text-right">
                <span className="text-xs font-semibold uppercase text-contrast-medium">Delivery digest</span>
                <code className="mt-static-xs block max-w-full break-all text-xs">{detail.delivery_digest}</code>
              </div>
            </section>

            <section aria-labelledby="metadata-heading" tabIndex={0} className="border-b border-contrast-low pb-static-lg">
              <PHeading id="metadata-heading" tag="h2" size="lg">Authority metadata</PHeading>
              <dl className="mt-static-md grid gap-static-sm text-sm sm:grid-cols-2">
                <div><dt className="font-semibold">State</dt><dd>{String(graph.state ?? 'unknown')}</dd></div>
                <div><dt className="font-semibold">Intent source</dt><dd>{String(authority.intent ?? 'intent.md')}</dd></div>
                <div><dt className="font-semibold">Design source</dt><dd>{String(authority.design ?? 'design.md')}</dd></div>
                <div><dt className="font-semibold">Decisions source</dt><dd>{String(authority.decisions ?? 'decisions.yaml')}</dd></div>
                <div><dt className="font-semibold">Admission receipt</dt><dd className="break-all">{String(admission.receipt ?? 'Not admitted')}</dd></div>
                <div><dt className="font-semibold">Research references</dt><dd>{research.join(', ') || 'None'}</dd></div>
              </dl>
              {limits.length > 0 ? (
                <div className="mt-static-md"><strong className="text-sm">Limits</strong><ul className="mt-static-xs list-disc pl-static-lg text-sm">{limits.map((limit) => <li key={limit}>{limit}</li>)}</ul></div>
              ) : null}
            </section>

            <section aria-labelledby="intent-heading" tabIndex={0} className="border-b border-contrast-low pb-static-lg">
              <PHeading id="intent-heading" tag="h2" size="lg">Product Intent</PHeading>
              <div className="mt-static-md whitespace-pre-wrap text-sm leading-relaxed text-contrast-high">{detail.intent}</div>
            </section>

            <section aria-labelledby="design-heading" tabIndex={0} className="border-b border-contrast-low pb-static-lg">
              <PHeading id="design-heading" tag="h2" size="lg">Implementation design</PHeading>
              <div className="mt-static-md whitespace-pre-wrap text-sm leading-relaxed text-contrast-high">{detail.design}</div>
            </section>

            <section aria-labelledby="decisions-heading" tabIndex={0}>
              <div className="flex flex-wrap items-center justify-between gap-static-sm">
                <PHeading id="decisions-heading" tag="h2" size="lg">Accepted decisions</PHeading>
                <PTag compact>{decisions.length} accepted</PTag>
              </div>
              <div className="mt-static-md divide-y divide-contrast-low border-y border-contrast-low">
                {decisions.map((decision) => (
                  <article key={String(decision.id)} className="grid gap-static-xs py-static-md md:grid-cols-[8rem_minmax(0,1fr)]">
                    <strong className="text-sm">{String(decision.id)}</strong>
                    <div className="min-w-0">
                      <h3 className="font-semibold">{String(decision.title ?? decision.id)}</h3>
                      <p className="mt-static-xs text-sm leading-relaxed text-contrast-medium">{String(decision.rationale ?? '')}</p>
                    </div>
                  </article>
                ))}
                {decisions.length === 0 ? <p className="py-static-md text-sm text-contrast-medium">No accepted decisions.</p> : null}
              </div>
            </section>
          </>
        ) : null}
      </div>
    </main>
  )
}
