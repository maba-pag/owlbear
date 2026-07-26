import { useLegacyInventory } from '../hooks/useNativeResources'

function recordIdentity(value: Record<string, unknown>, fallback: string): string {
  for (const key of ['id', 'request_id', 'task_id', 'event_id', 'title', 'kind']) {
    const candidate = value[key]
    if (typeof candidate === 'string' || typeof candidate === 'number') return String(candidate)
  }
  return fallback
}

export default function LegacyPage() {
  const inventory = useLegacyInventory()

  return (
    <main className="min-w-0 flex-1 overflow-x-hidden" data-testid="legacy-page">
      <div className="mx-auto w-full max-w-[1440px] px-static-md py-static-lg md:px-static-xl">
        <header className="border-b border-contrast-low pb-static-md">
          <p className="text-xs font-semibold uppercase text-contrast-medium">Read-only compatibility inventory</p>
          <h1 className="mt-static-xs text-3xl font-semibold">Legacy</h1>
        </header>
        {inventory.error ? <p className="mt-static-lg" role="alert">Legacy inventory is unavailable. {inventory.error.message}</p> : null}
        {inventory.data ? (
          <div className="mt-static-lg grid gap-static-xl lg:grid-cols-3">
            <section aria-labelledby="legacy-tasks-heading">
              <h2 id="legacy-tasks-heading" className="text-xl font-semibold">Tasks</h2>
              {inventory.data.truncated.tasks ? <p className="text-xs font-semibold">Truncated to the first 100 records</p> : null}
              <ol className="mt-static-sm divide-y divide-contrast-low">
                {inventory.data.tasks.map((entry, index) => (
                  <li key={`${entry.provenance}-${index}`} className="min-w-0 py-static-sm text-sm">
                    <span className="block text-xs font-semibold">{entry.provenance}</span>
                    <span className="block break-words">{recordIdentity(entry.task, `Task ${index + 1}`)}</span>
                  </li>
                ))}
              </ol>
            </section>
            <section aria-labelledby="legacy-requests-heading">
              <h2 id="legacy-requests-heading" className="text-xl font-semibold">Requests</h2>
              {inventory.data.truncated.requests ? <p className="text-xs font-semibold">Truncated to the first 100 records</p> : null}
              <ol className="mt-static-sm divide-y divide-contrast-low">
                {inventory.data.requests.map((entry, index) => (
                  <li key={`${entry.provenance}-${index}`} className="min-w-0 py-static-sm text-sm">
                    <span className="block text-xs font-semibold">{entry.provenance}</span>
                    <span className="block break-words">{recordIdentity(entry.request, `Request ${index + 1}`)}</span>
                  </li>
                ))}
              </ol>
            </section>
            <section aria-labelledby="legacy-activity-heading">
              <h2 id="legacy-activity-heading" className="text-xl font-semibold">Activity</h2>
              {inventory.data.truncated.activity ? <p className="text-xs font-semibold">Truncated to the latest 100 records</p> : null}
              <ol className="mt-static-sm divide-y divide-contrast-low">
                {inventory.data.activity.map((entry, index) => (
                  <li key={`${entry.provenance}-${index}`} className="min-w-0 py-static-sm text-sm">
                    <span className="block text-xs font-semibold">{entry.provenance}</span>
                    <span className="block break-words">{recordIdentity(entry.event, `Event ${index + 1}`)}</span>
                  </li>
                ))}
              </ol>
            </section>
          </div>
        ) : null}
      </div>
    </main>
  )
}
