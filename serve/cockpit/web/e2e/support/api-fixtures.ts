import type { WorkItemPortfolioResponse } from '../../src/api/workItems'

export const EMPTY_WORK_ITEM_PORTFOLIO = {
  groups: [],
  totals: {
    total: 0,
    complete: 0,
    needs: { you: 0, dependency: 0, none: 0 },
    activity: { idle: 0, ready: 0, working: 0 },
  },
  operating: {
    unfinished_change_count: 0,
    completed_change_count: 0,
    statuses: [],
    draft_design_change_ids: [],
    design_required_change_ids: [],
    claimed: [],
    queued_for_orchestration: [],
    interventions: [],
    dependency_waits: [],
    guidance: [{ kind: 'create-change', change_ids: [], work_count: 0 }],
  },
  health: {
    status: 'healthy',
    diagnostics: [],
  },
} satisfies WorkItemPortfolioResponse
