const EMPTY_FALLBACK = '—'
const UNKNOWN_SIGNAL = 'Unknown'

const PRIORITY_LABELS: Record<string, string> = {
  low: 'Low',
  normal: 'Normal',
  needed: 'Needed',
  important: 'Important',
  critical: 'Critical',
}

const SIGNAL_LABELS: Record<string, string> = {
  ready: 'Ready',
  blocked: 'Blocked',
  claimed: 'Claimed',
  'deps-unmet': 'Dependencies blocked',
  'dr-pending': 'Decision pending',
}

function toTitleCaseWords(raw: string): string {
  return raw
    .replace(/-/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function formatRelativeTime(updated: string | null | undefined): string {
  if (!updated) {
    return EMPTY_FALLBACK
  }

  const updatedAt = Date.parse(updated)
  if (!Number.isFinite(updatedAt)) {
    return 'Updated recently'
  }

  const ageMs = Math.max(0, Date.now() - updatedAt)
  const ageMinutes = Math.max(1, Math.floor(ageMs / 60_000))
  return `${ageMinutes}m ago`
}

export function formatPriority(priority: string | null | undefined): string {
  if (!priority) {
    return EMPTY_FALLBACK
  }

  return PRIORITY_LABELS[priority] ?? (toTitleCaseWords(priority) || EMPTY_FALLBACK)
}

export function formatStatus(status: string | null | undefined): string {
  if (!status) {
    return EMPTY_FALLBACK
  }

  return toTitleCaseWords(status) || EMPTY_FALLBACK
}

export function formatSignalDescription(signal: string | null | undefined): string {
  if (!signal) {
    return UNKNOWN_SIGNAL
  }

  return SIGNAL_LABELS[signal] ?? (toTitleCaseWords(signal) || UNKNOWN_SIGNAL)
}
