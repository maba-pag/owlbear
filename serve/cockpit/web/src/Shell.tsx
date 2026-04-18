import { Routes, Route } from 'react-router'

function Shell() {
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
        <p-tabs>
          <p-tabs-item ref={(el: HTMLElement | null) => el?.setAttribute('label', 'Detail')}>
            <div data-tab-content="detail" />
          </p-tabs-item>
          <p-tabs-item ref={(el: HTMLElement | null) => el?.setAttribute('label', 'Activity')}>
            <div data-tab-content="activity" />
          </p-tabs-item>
        </p-tabs>
      </aside>
      <div data-region="contextual" />
    </div>
  )
}

export default Shell
