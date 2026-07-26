import { PHeading, PIcon } from '@porsche-design-system/components-react'
import { useSearchParams } from 'react-router'
import { useNativeChangeSelection } from '../hooks/NativeChangeProvider'

export default function DeliveryPage() {
  const { selectedChangeId, selectedSummary } = useNativeChangeSelection()
  const [searchParams] = useSearchParams()
  const selectedJobId = searchParams.get('job')

  return (
    <main className="h-full min-h-0 overflow-y-auto bg-canvas" data-testid="delivery-page">
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-static-lg px-static-md py-static-lg md:px-static-xl">
        <header className="border-b border-contrast-low pb-static-lg">
          <p className="mb-static-xs text-sm font-semibold text-contrast-medium">Current change execution</p>
          <PHeading tag="h1" size="xl">Delivery</PHeading>
        </header>
        <section tabIndex={0} aria-labelledby="delivery-change-heading">
          <PHeading id="delivery-change-heading" tag="h2" size="lg">{selectedChangeId ?? 'No change selected'}</PHeading>
          <p className="mt-static-sm max-w-[60rem] text-sm leading-relaxed text-contrast-medium">
            {selectedSummary?.state === 'invalid'
              ? 'Delivery is unavailable until the selected specification is valid.'
              : 'Plans, jobs, requests, and evidence for this change appear here.'}
          </p>
          {selectedSummary?.state === 'invalid' ? (
            <div className="mt-static-md flex items-center gap-static-sm border-l-4 border-warning bg-surface p-static-md" role="status">
              <PIcon name="warning" aria-hidden="true" />
              <span>Invalid authority prevents delivery.</span>
            </div>
          ) : null}
          {selectedJobId ? <p className="mt-static-md text-sm">Selected job #{selectedJobId}</p> : null}
        </section>
      </div>
    </main>
  )
}
