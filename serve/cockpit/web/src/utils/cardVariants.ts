import type { TagVariant } from '@porsche-design-system/components-react'

const STATUS_VARIANTS: Record<string, TagVariant> = {
  research: 'secondary',
  backlog: 'info',
  todo: 'secondary',
  'in-progress': 'info',
  review: 'info',
  docs: 'secondary',
  done: 'success',
}

const PRIORITY_VARIANTS: Record<string, TagVariant> = {
  someday: 'secondary',
  'nice-to-have': 'secondary',
  important: 'info',
  needed: 'info',
  critical: 'error',
}

function normalize(value: string): string {
  return value.trim().toLowerCase()
}

export function statusToVariant(status: string): TagVariant {
  const normalized = normalize(status)
  return STATUS_VARIANTS[normalized] ?? 'secondary'
}

export function priorityToVariant(priority: string): TagVariant {
  const normalized = normalize(priority)
  return PRIORITY_VARIANTS[normalized] ?? 'secondary'
}
