import type { TagVariant } from '@porsche-design-system/components-react'

const STATUS_VARIANTS: Record<string, TagVariant> = {
  research: 'primary',
  backlog: 'info',
  todo: 'success',
  'in-progress': 'warning',
  review: 'info',
  docs: 'secondary',
  done: 'success',
}

const PRIORITY_VARIANTS: Record<string, TagVariant> = {
  someday: 'primary',
  'nice-to-have': 'secondary',
  important: 'warning',
  needed: 'warning',
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
