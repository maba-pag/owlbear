import type { ReactNode } from 'react'

interface WorkspaceViewHeaderProps {
  headingId: string
  title: string
  /** Inline fact the heading and the page header do not already state; omitted when there is none. */
  meta?: ReactNode
  metaTestId?: string
  tools?: ReactNode
}

/**
 * Content header for one workspace view. Both Delivery views use it, and its single row keeps a
 * constant height so switching views or revealing a count never shifts the content below.
 */
export default function WorkspaceViewHeader({
  headingId,
  title,
  meta,
  metaTestId,
  tools,
}: WorkspaceViewHeaderProps) {
  return (
    <div className="flex min-h-11 min-w-0 flex-wrap items-center justify-between gap-x-static-md gap-y-static-xs border-b border-contrast-low pb-static-sm">
      <div className="flex min-w-0 items-center gap-static-xs">
        <h2 id={headingId} className="m-0 min-w-0 truncate text-md font-semibold leading-tight text-primary">{title}</h2>
        <span className="inline-flex min-w-0 items-center" aria-live="polite" data-testid={metaTestId}>{meta}</span>
      </div>
      {tools ? (
        <div className="flex min-w-0 flex-wrap items-center justify-end gap-x-static-sm gap-y-static-xs">{tools}</div>
      ) : null}
    </div>
  )
}

export function WorkspaceViewCount({ value, unit }: { value: ReactNode; unit: string }) {
  const filteredCount = typeof value === 'string' ? value.match(/^(\d+) of (\d+)$/) : null
  return (
    <span className="inline-flex items-baseline gap-1 whitespace-nowrap text-xs">
      <strong className="font-semibold text-primary">{filteredCount?.[1] ?? value}</strong>
      {filteredCount ? <> <span className="text-contrast-medium">of {filteredCount[2]} shown</span></> : null}
      <span className="sr-only"> {filteredCount ? unit.replace(/ shown$/, '') : unit}</span>
    </span>
  )
}
