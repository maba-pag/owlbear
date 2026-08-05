import type { WorkItemAttention } from './api/workItems'

/** Single user-facing vocabulary for backend attention states, shared by every Delivery surface. */
export const ATTENTION_LABELS: Record<WorkItemAttention, string> = {
  user: 'Needs you',
  agent: 'Agent working',
  waiting: 'Waiting on dependencies',
  none: 'No action needed',
}

/**
 * Status-strip wording for the four attention states the portfolio API counts.
 * `short` keeps the strip scannable; `full` carries the same meaning to assistive technology.
 * `none` covers unbriefed and completed items alike, so it must not imply either.
 */
export const ATTENTION_SUMMARY_LABELS: Record<WorkItemAttention, { short: string; full: string }> = {
  user: { short: 'need you', full: 'work items need you' },
  agent: { short: 'with agents', full: 'work items are with agents' },
  waiting: { short: 'waiting', full: 'work items are waiting on dependencies' },
  none: { short: 'no action needed', full: 'work items have no action needed' },
}

/**
 * Names the counted noun explicitly: the portfolio projects change design, outcome, and
 * change-assembly cards, so "work item" — not "outcome" — is the noun that covers every card.
 */
export function workItemCountLabel(count: number): string {
  return count === 1 ? 'work item' : 'work items'
}
