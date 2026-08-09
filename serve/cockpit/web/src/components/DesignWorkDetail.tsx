import { PHeading, PTag } from '@porsche-design-system/components-react'
import type { DesignWorkDetailResponse } from '../api/workItems'
import CopyCommand from './CopyCommand'
import MarkdownPreview from './MarkdownPreview'
import { designCommand, designWorkTitle } from './designWorkPresentation'

export default function DesignWorkDetail({ detail }: { detail: DesignWorkDetailResponse }) {
  return (
    <article className="min-w-0" aria-labelledby="design-work-detail-heading" data-testid="design-work-detail">
      <header className="flex min-w-0 flex-wrap items-start justify-between gap-static-sm">
        <div className="min-w-0">
          <code className="text-xs text-contrast-medium">{detail.change_id}</code>
          <PHeading id="design-work-detail-heading" tag="h2" size="lg">{designWorkTitle(detail.change_id)}</PHeading>
        </div>
        <PTag compact>Design</PTag>
      </header>
      <p className="mt-static-md max-w-[72ch] text-base leading-relaxed">Authored Design work that has not been admitted to Delivery.</p>
      <div className="mt-static-md flex flex-wrap items-baseline gap-static-xs text-sm">
        <span className="text-contrast-medium">Continue with</span>
        <CopyCommand command={designCommand(detail.change_id)} />
      </div>
      <div className="mt-static-lg grid gap-static-md">
        <details open className="min-w-0 border-t border-contrast-low pt-static-sm">
          <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">Intent</summary>
          <MarkdownPreview className="mt-static-md text-sm">{detail.intent_markdown}</MarkdownPreview>
        </details>
        <details className="min-w-0 border-t border-contrast-low pt-static-sm">
          <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">Design</summary>
          <MarkdownPreview className="mt-static-md text-sm">{detail.design_markdown}</MarkdownPreview>
        </details>
        <details className="min-w-0 border-t border-contrast-low pt-static-sm">
          <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">Technical identity</summary>
          <code className="mt-static-sm block break-all text-xs text-contrast-medium">{detail.package_id}</code>
        </details>
      </div>
    </article>
  )
}
