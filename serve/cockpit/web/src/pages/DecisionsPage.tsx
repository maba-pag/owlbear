import { PIcon, PText } from '@porsche-design-system/components-react'

import { WorkspaceHeader, WorkspaceHeaderMetric } from '../components/WorkspaceHeader'
import { useDRState } from '../hooks/CockpitProvider'

type DecisionBrief = {
  context: string
  options: string[]
  recommendation: string | null
  consequence: string | null
}

function formatAge(created: string): string {
  const ageMs = Math.max(0, Date.now() - Date.parse(created))
  const ageMinutes = Math.max(1, Math.floor(ageMs / 60_000))
  const unitIndex = Number(ageMinutes >= 60) + Number(ageMinutes >= 24 * 60)
  const divisors = [1, 60, 24 * 60]
  const units = ['m', 'h', 'd']
  const value = Math.floor(ageMinutes / divisors[unitIndex])
  return `${value}${units[unitIndex]} ago`
}

function truncatePreview(value: string): string {
  return value.slice(0, 200)
}

function normalizeWhitespace(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

function stripMarkdown(value: string): string {
  return normalizeWhitespace(
    value
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/^[-*+]\s+/gm, '')
      .replace(/^\d+\.\s+/gm, '')
      .replace(/[*_`>]/g, ''),
  )
}

function extractRawSection(body: string, sectionNames: string[]): string | null {
  const lines = body.split('\n')
  const sectionMatcher = new RegExp(`^#{1,6}\\s+(${sectionNames.join('|')})\\s*$`, 'i')
  let startIndex = -1

  for (const [index, line] of lines.entries()) {
    if (sectionMatcher.test(line.trim())) {
      startIndex = index + 1
      break
    }
  }

  if (startIndex === -1) {
    return null
  }

  const sectionLines: string[] = []
  for (let index = startIndex; index < lines.length; index += 1) {
    if (/^#{1,6}\s+/.test(lines[index].trim())) {
      break
    }
    sectionLines.push(lines[index])
  }

  const rawText = sectionLines.join('\n').trim()
  return rawText.length > 0 ? rawText : null
}

function extractSection(body: string, sectionNames: string[]): string | null {
  const rawText = extractRawSection(body, sectionNames)
  if (!rawText) {
    return null
  }
  const text = stripMarkdown(rawText)
  return text.length > 0 ? text : null
}

function extractOptions(body: string): string[] {
  const optionSection = extractRawSection(body, ['Options', 'Choices', 'Alternatives'])
  if (!optionSection) {
    return []
  }
  const optionLines = optionSection
    .split('\n')
    .map((line) => line.match(/^\s*(?:[-*+]|\d+\.)\s+(.+)$/)?.[1] ?? '')
    .map((option) => stripMarkdown(option))
    .filter(Boolean)
  if (optionLines.length > 0) {
    return optionLines.slice(0, 3)
  }
  return [truncatePreview(stripMarkdown(optionSection))]
}

function getDecisionBrief(item: { body: string; body_preview: string }): DecisionBrief {
  const context = extractSection(item.body, ['Context', 'Question', 'Decision'])
    ?? stripMarkdown(item.body_preview || item.body)
  const recommendation = extractSection(item.body, ['Recommendation', 'Recommended response', 'Proposal'])
  const consequence = extractSection(item.body, ['Consequence', 'Consequences', 'Impact'])
  return {
    context: truncatePreview(context),
    options: extractOptions(item.body),
    recommendation: recommendation ? truncatePreview(recommendation) : null,
    consequence: consequence ? truncatePreview(consequence) : null,
  }
}

function formatRequestType(value: string): string {
  return value
    .replace(/[-_]/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatDecisionTitle(item: { title: string; task_id: number }): string {
  const title = item.title.trim()
  return title || `Decision needed for task #${item.task_id}`
}

function DecisionsPage() {
  const drState = useDRState()
  let content

  if (drState.isLoading) {
    content = (
      <div className="rounded-lg border border-contrast-low bg-canvas p-static-md" role="status">
        <PText>Collecting decision requests...</PText>
      </div>
    )
  } else if (drState.error) {
    content = (
      <div className="rounded-lg border border-error bg-error-low p-static-md">
        <PText role="alert">Decision requests are unavailable. {drState.error.message}</PText>
      </div>
    )
  } else if (drState.items.length === 0) {
    content = (
      <div className="rounded-lg border border-contrast-low bg-canvas p-static-lg text-center">
        <PText data-testid="decisions-empty-state">No decisions are waiting.</PText>
      </div>
    )
  } else {
    content = (
      <div className="flex min-h-0 flex-col gap-static-md overflow-y-auto pr-static-xs" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {drState.items.map((item) => {
          const brief = getDecisionBrief(item)
          return (
          <div
            key={item.id}
            data-testid={`dr-item-${item.id}`}
            role="button"
            tabIndex={0}
            aria-label={`Open decision request ${item.id} for task ${item.task_id}`}
            className="group overflow-hidden rounded-lg border border-contrast-low bg-canvas text-primary shadow-sm transition-[border-color,box-shadow] duration-sm hover:border-primary hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]"
            onClick={() => {
              drState.setSelectedDRId(item.id)
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                drState.setSelectedDRId(item.id)
              }
            }}
          >
            <article data-testid={item.id} className="grid min-h-[148px] grid-cols-[4px_minmax(0,1fr)] lg:grid-cols-[4px_minmax(0,1fr)_minmax(220px,auto)]">
              <span className="bg-warning" aria-hidden="true" />
              <div className="min-w-0 p-static-md">
                <div className="mb-static-xs flex min-w-0 flex-wrap items-center gap-static-xs">
                  <span className="rounded-full border border-contrast-low bg-surface px-static-xs py-1 text-xs font-semibold text-primary">
                    {formatRequestType(item.request_type)}
                  </span>
                  <span className="rounded-full border border-contrast-low bg-surface px-static-xs py-1 text-xs font-semibold text-primary">
                    Task #{item.task_id}
                  </span>
                  <span className="text-xs font-semibold text-primary">{formatAge(item.created)}</span>
                  <span className="text-xs font-semibold text-primary">{item.agent}</span>
                </div>
                <h2 className="m-0 text-lg font-semibold leading-tight text-primary">{formatDecisionTitle(item)}</h2>
                <div className="mt-static-sm grid gap-static-sm xl:grid-cols-[minmax(0,1fr)_minmax(240px,0.55fr)]">
                  <section data-testid={`dr-context-${item.id}`} className="grid gap-1 rounded-md border border-contrast-low bg-surface p-static-xs">
                    <span className="text-xs font-semibold uppercase text-primary">Context</span>
                    <p className="m-0 text-sm leading-normal text-primary line-clamp-3">{brief.context}</p>
                  </section>
                  <section data-testid={`dr-options-${item.id}`} className="grid gap-1 rounded-md border border-contrast-low bg-surface p-static-xs">
                    <span className="text-xs font-semibold uppercase text-primary">{brief.options.length > 0 ? 'Options' : 'Request'}</span>
                    {brief.options.length > 0 ? (
                      <ul className="m-0 grid list-none gap-1 p-0 text-sm leading-normal text-primary">
                        {brief.options.map((option) => (
                          <li key={option} className="line-clamp-1">{option}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="m-0 text-sm leading-normal text-primary line-clamp-2">{truncatePreview(item.body_preview)}</p>
                    )}
                  </section>
                </div>
                {brief.recommendation || brief.consequence ? (
                  <div className="mt-static-sm grid gap-static-sm lg:grid-cols-2">
                    {brief.recommendation ? (
                      <section data-testid={`dr-recommendation-${item.id}`} className="grid gap-1 rounded-md border border-info bg-info-low p-static-xs">
                        <span className="text-xs font-semibold uppercase text-primary">Recommendation</span>
                        <p className="m-0 text-sm leading-normal text-primary line-clamp-2">{brief.recommendation}</p>
                      </section>
                    ) : null}
                    {brief.consequence ? (
                      <section data-testid={`dr-consequence-${item.id}`} className="grid gap-1 rounded-md border border-contrast-low bg-surface p-static-xs">
                        <span className="text-xs font-semibold uppercase text-primary">Consequence</span>
                        <p className="m-0 text-sm leading-normal text-primary line-clamp-2">{brief.consequence}</p>
                      </section>
                    ) : null}
                  </div>
                ) : null}
              </div>
              <div className="col-span-full grid min-w-0 gap-static-xs border-t border-contrast-low bg-surface px-static-md py-static-sm text-sm font-semibold text-primary sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center lg:col-auto lg:flex lg:flex-col lg:items-start lg:justify-center lg:border-l lg:border-t-0">
                <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Resolution</span>
                <div className="flex min-w-0 flex-wrap gap-static-xs text-xs font-semibold text-primary">
                  <span className="whitespace-nowrap rounded-full border border-contrast-low bg-canvas px-static-xs py-1 leading-none">Approve</span>
                  <span className="whitespace-nowrap rounded-full border border-contrast-low bg-canvas px-static-xs py-1 leading-none">Needs info</span>
                  <span className="whitespace-nowrap rounded-full border border-contrast-low bg-canvas px-static-xs py-1 leading-none">Reject</span>
                </div>
                <span className="flex items-center gap-static-xs whitespace-nowrap text-primary">
                  <span>Resolve decision</span>
                  <PIcon name="arrow-right" size="small" color="inherit" aria-hidden="true" />
                </span>
              </div>
            </article>
          </div>
          )
        })}
      </div>
    )
  }

  return (
    <section data-testid="decisions-page" className="relative flex h-full min-h-0 w-full flex-col overflow-hidden rounded-lg bg-canvas shadow-sm" style={{ width: '100%' }} aria-labelledby="decisions-title">
      <WorkspaceHeader
        title="Decisions"
        titleId="decisions-title"
        summaryLabel="Decision summary"
        summary={<WorkspaceHeaderMetric value={drState.items.length} label="waiting" />}
      />
      <div className="flex min-h-0 flex-1 flex-col gap-static-md overflow-hidden p-static-md">
        {content}
      </div>
    </section>
  )
}

export default DecisionsPage
