type CardVariant = 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'notification'

const STATUS_VARIANTS: Record<string, CardVariant> = {
  research: 'primary',
  backlog: 'notification',
  todo: 'success',
  'in-progress': 'warning',
  review: 'notification',
  docs: 'secondary',
  done: 'success',
}

const PRIORITY_VARIANTS: Record<string, CardVariant> = {
  someday: 'primary',
  'nice-to-have': 'secondary',
  important: 'warning',
  needed: 'notification',
  critical: 'error',
}

function normalize(value: string): string {
  return value.trim().toLowerCase()
}

export function statusToVariant(status: string): CardVariant {
  const normalized = normalize(status)
  return STATUS_VARIANTS[normalized] ?? 'secondary'
}

export function priorityToVariant(priority: string): CardVariant {
  const normalized = normalize(priority)
  return PRIORITY_VARIANTS[normalized] ?? 'secondary'
}
