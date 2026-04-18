import { useRef, useEffect } from 'react'
import { Routes, Route } from 'react-router'

function Shell() {
  const tabsRef = useRef<HTMLElement>(null)
  const detailRef = useRef<HTMLDivElement>(null)
  const activityRef = useRef<HTMLDivElement>(null)

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
    <div>
      <header data-region="status-bar">
        <span data-testid="traffic-light" />
        <span data-testid="task-count" />
      </header>
      <nav data-region="nav-rail">
        <button data-surface="kanban" aria-current="page">
          Kanban
        </button>
      </nav>
      <main data-region="workspace">
        <Routes>
          <Route path="/" element={<div>kanban</div>} />
          <Route path="/hello" element={<div>hello</div>} />
        </Routes>
      </main>
      <aside data-region="sidecar">
        <p-tabs ref={tabsRef}>
          <p-tabs-item ref={(el: HTMLElement | null) => el?.setAttribute('label', 'Detail')}>
            <div ref={detailRef} data-tab-content="detail" aria-hidden="false" />
          </p-tabs-item>
          <p-tabs-item ref={(el: HTMLElement | null) => el?.setAttribute('label', 'Activity')}>
            <div ref={activityRef} data-tab-content="activity" aria-hidden="true" />
          </p-tabs-item>
        </p-tabs>
      </aside>
      <div data-region="contextual" />
    </div>
  )
}

export default Shell
