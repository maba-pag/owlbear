import type { ReactNode } from 'react'

interface DecisionsListViewProps {
  children: ReactNode
}

export default function DecisionsListView({ children }: DecisionsListViewProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {children}
    </div>
  )
}
