import { useState } from 'react'
import type { PendingDR } from '../hooks/usePendingDRs'

export interface DRStatusIndicatorProps {
  count: number
  items: PendingDR[]
  onItemClick: (id: string) => void
}

function formatAge(created: string): string {
  const parsedCreatedAt = Date.parse(created)
  const createdAt = Number.isFinite(parsedCreatedAt) ? parsedCreatedAt : Date.now()
  const ageMs = Math.max(0, Date.now() - createdAt)
  const ageHours = Math.max(1, Math.floor(ageMs / 3_600_000))
  return `${ageHours}h ago`
}

export default function DRStatusIndicator({ count, items, onItemClick }: DRStatusIndicatorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const status = count > 0 ? 'attention' : 'dormant'

  return (
    <div>
      <button
        type="button"
        data-testid="dr-indicator"
        data-status={status}
        aria-label={`Pending decision requests: ${count}`}
        onClick={() => setIsOpen((current) => !current)}
      >
        DR {count}
      </button>

      {isOpen ? (
        <div data-testid="dr-popover" role="dialog" aria-label="Pending decision requests">
          {items.length === 0 ? (
            <p>No pending decision requests</p>
          ) : (
            <ul>
              {items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    data-testid={`dr-item-${item.id}`}
                    onClick={() => onItemClick(item.id)}
                  >
                    <span>{item.title}</span>
                    <span>{item.agent}</span>
                    <span>{item.task_id}</span>
                    <span>{formatAge(item.created)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}