import { useRef, useEffect, useState } from 'react'
import { Routes, Route } from 'react-router'
import KanbanBoard from './KanbanBoard'
import DRStatusIndicator from './components/DRStatusIndicator'
import HealthBadge, { type ScanItem as HealthBadgeItem } from './components/HealthBadge'
import ResolveModal from './components/ResolveModal'
import { usePendingDRs } from './hooks/usePendingDRs'
import { usePolling } from './hooks/usePolling'
import { type ScanItem as ScanPollingItem, useScanPolling } from './hooks/useScanPolling'
import './Shell.css'

function isHealthBadgeItem(item: ScanPollingItem): item is HealthBadgeItem {
  return item.code !== null && item.detail !== null && item.file_path !== null
}

function Shell() {
  const { health } = usePolling('/health')
  const { count: pendingDRCount, items: pendingDRItems, refetch: refetchPendingDRs } = usePendingDRs()
  const { items: scanItems, isLoading, refetch } = useScanPolling()
  const normalizedItems = scanItems.filter(isHealthBadgeItem)
  const [hasLoadedScan, setHasLoadedScan] = useState(false)
  const [selectedDRId, setSelectedDRId] = useState<string | null>(null)
  const selectedDR = pendingDRItems.find((item) => item.id === selectedDRId) ?? null
  const tabsRef = useRef<HTMLElement>(null)
  const detailRef = useRef<HTMLDivElement>(null)
  const activityRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isLoading) {
      setHasLoadedScan(true)
    }
  }, [isLoading])

  useEffect(() => {
    const tabs = tabsRef.current
    if (!tabs) return
    const onTabChange = (e: Event) => {
      const index = (e as CustomEvent<{ activeTabIndex: number }>).detail.activeTabIndex
      detailRef.current?.setAttribute('aria-hidden', String(index !== 0))
      activityRef.current?.setAttribute('aria-hidden', String(index !== 1))
    }
    tabs.addEventListener('tabChange', onTabChange)
    return () => tabs.removeEventListener('tabChange', onTabChange)
  }, [])

  return (
    <div className="shell">
      <header className="shell__status-bar" data-region="status-bar">
        <span data-testid="traffic-light" data-health={health} />
        <span data-testid="task-count" />
        {hasLoadedScan ? (
          <HealthBadge
            items={normalizedItems}
            corruptionCount={normalizedItems.length}
            onRepairSuccess={refetch}
          />
        ) : null}
        <DRStatusIndicator
          count={pendingDRCount}
          items={pendingDRItems}
          onItemClick={setSelectedDRId}
        />
      </header>
      <nav className="shell__nav-rail" data-region="nav-rail">
        <button data-surface="kanban" aria-current="page">
          <p-icon name="list" aria-hidden="true" />
          Kanban
        </button>
      </nav>
      <main className="shell__workspace" data-region="workspace">
        <Routes>
          <Route path="/" element={<KanbanBoard />} />
          <Route path="/hello" element={<div>hello</div>} />
        </Routes>
      </main>
      <aside className="shell__sidecar" data-region="sidecar">
        <p-tabs ref={tabsRef}>
          <p-tabs-item ref={(el: HTMLElement | null) => el?.setAttribute('label', 'Detail')}>
            <div ref={detailRef} data-tab-content="detail" aria-hidden="false" />
          </p-tabs-item>
          <p-tabs-item ref={(el: HTMLElement | null) => el?.setAttribute('label', 'Activity')}>
            <div ref={activityRef} data-tab-content="activity" aria-hidden="true" />
          </p-tabs-item>
        </p-tabs>
      </aside>
      {selectedDR ? (
        <ResolveModal
          dr={selectedDR}
          onClose={() => setSelectedDRId(null)}
          onResolved={() => {
            void refetchPendingDRs()
            setSelectedDRId(null)
          }}
        />
      ) : null}
      <div className="shell__contextual" data-region="contextual" />
    </div>
  )
}

export default Shell
