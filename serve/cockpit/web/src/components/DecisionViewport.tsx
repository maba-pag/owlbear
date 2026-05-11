import { PText } from '@porsche-design-system/components-react'

import type { PendingDR } from '../hooks/usePendingDRs'

export interface DecisionViewportProps {
  items: PendingDR[]
  isLoading: boolean
  error: Error | null
  onItemClick: (id: string) => void
}

function formatAge(created: string): string {
  const parsedCreatedAt = Date.parse(created)
  const createdAt = Number.isFinite(parsedCreatedAt) ? parsedCreatedAt : Date.now()
  const ageMs = Math.max(0, Date.now() - createdAt)
  const ageMinutes = Math.max(1, Math.floor(ageMs / 60_000))

  if (ageMinutes >= 24 * 60) {
    const ageDays = Math.floor(ageMinutes / (24 * 60))
    return `${ageDays}d ago`
  }

  if (ageMinutes >= 60) {
    const ageHours = Math.floor(ageMinutes / 60)
    return `${ageHours}h ago`
  }

  return `${ageMinutes}m ago`
}

export default function DecisionViewport({ items, isLoading, error, onItemClick }: DecisionViewportProps) {
  if (isLoading) {
    return <PText data-testid="decision-loading">Loading pending decisions...</PText>
  }

  if (error) {
    return (
      <PText data-testid="decision-error" role="alert">
        {error.message}
      </PText>
    )
  }

  if (items.length === 0) {
    return <PText data-testid="decision-empty">No pending decision requests.</PText>
  }

  return (
    <ul>
      {items.map((item) => (
        <li key={item.id}>
          <button
            type="button"
            data-testid={`decision-item-${item.id}`}
            onClick={() => onItemClick(item.id)}
          >
            <span data-testid={`decision-task-ref-${item.id}`}>{item.task_id}</span>
            <PText>{item.agent}</PText>
            <PText>{item.request_type}</PText>
            <PText data-testid={`decision-age-${item.id}`}>{formatAge(item.created)}</PText>
            <PText>{item.body_preview}</PText>
          </button>
        </li>
      ))}
    </ul>
  )
}