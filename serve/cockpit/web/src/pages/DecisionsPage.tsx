import { PText } from '@porsche-design-system/components-react'

import type { KanbanBoardProps } from '../KanbanBoard'
import { useDRState } from '../hooks/CockpitProvider'

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

function DecisionsPage(_props: KanbanBoardProps) {
  let content = null

  try {
    const drState = useDRState()
    if (drState.isLoading) {
      content = <PText>Loading pending decisions...</PText>
    } else if (drState.error) {
      content = <PText role="alert">{drState.error.message}</PText>
    } else if (drState.items.length === 0) {
      content = <PText data-testid="decisions-empty-state">There is nothing to decide right now.</PText>
    } else {
      content = (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {drState.items.map((item) => (
            <div
              key={item.id}
              data-testid={`dr-item-${item.id}`}
              onClick={() => {
                drState.setSelectedDRId(item.id)
              }}
            >
              <article data-testid={item.id}>
                <PText>
                  <strong>Agent:</strong> {item.agent}
                </PText>
                <PText>
                  <strong>Request type:</strong> {item.request_type}
                </PText>
                <PText>
                  <strong>Age:</strong> {formatAge(item.created)}
                </PText>
                <PText>
                  <strong>Task:</strong> {item.task_id}
                </PText>
                <PText>{truncatePreview(item.body_preview)}</PText>
              </article>
            </div>
          ))}
        </div>
      )
    }
  } catch (error) {
    void error
  }

  return (
    <section data-testid="decisions-page" style={{ width: '100%' }}>
      {content}
    </section>
  )
}

export default DecisionsPage
