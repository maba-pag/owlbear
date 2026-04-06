# Revisit Blocked-Task DR Scan — Notification Channel Prerequisite

> **Owning task:** #631 — Revisit blocked-task DR scan when notification channel is enabled
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #631 was created as a follow-up from #348's research, which recommended
deferring the blocked-task scan to align with Decision #514 (defer notifications).
#631 is the canonical "revisit when ready" tracking task.

**Question:** Has anything changed since #348's deferral recommendation? Is the
prerequisite (notification channel availability) now met or closer to being met?

## 2. Sources Studied

| # | Source | Rel. | What |
|---|--------|:----:|------|
| S1 | Decision #514 (resolved) | 1.0 | "D: Defer / do nothing" — no Slack, Teams blocked by corp policy [.owlbear/decisions/resolved/514-slack-notification-approach.md] |
| S2 | Research #348 | 1.0 | Full blocked-task scan analysis; recommended deferral (.80 confidence) [.owlbear/research/blocked-task-scan-decision-notifications.md] |
| S3 | Research #592 | .95 | Power Automate Workflows technically feasible but corp availability unknown [.owlbear/research/power-automate-workflows-teams-notifications.md] |
| S4 | Task #597 (todo) | 1.0 | Manual user verification of Teams Workflows — critical path, not yet executed |
| S5 | Codebase: serve/orchestrator/ | 1.0 | Zero notification code: no Notifier protocol, no SlackNotifier, no on_decision_request, no read_blocked_tasks() |
| S6 | Task #344 (archived) | .90 | Notifier protocol — archived, never implemented |
| S7 | Task #347 (archived) | .90 | Loop integration — archived, never implemented |
| S8 | bearclaw CLI status command | .85 | Existing blocked-task visibility via `bearclaw status` [serve/orchestrator/src/owlbear/cli.py] |

## 3. Analysis

### 3.1 What Changed Since #348 Research

| Signal | Status | Impact on #631 |
|--------|--------|----------------|
| Decision #514 | Still approved, unchanged | Deferral still in effect |
| Notification code in codebase | Zero — confirmed via search [S5] | No infrastructure to build on |
| Power Automate Workflows research (#592) | Complete [S3] | New alternative identified but unverified |
| Corp Teams Workflows availability (#597) | `todo` — manual user test pending [S4] | **Critical path blocker — unchanged** |
| O365 Connectors deprecation | April 30, 2026 (25 days) [S3] | Increases urgency of #597 verification |
| Existing coverage: bearclaw status | Still available [S8] | Gap remains acceptable |
| Predecessor chain (#344→#347→#348) | All archived or rejected [S6, S7] | Dependency chain broken |

**Assessment:** Nothing material has changed. The blocked-task scan cannot
proceed because:
1. AC1 ("Notification channel is available and configured") is unmet [S1, S4]
2. Prerequisites #344 (Notifier protocol) and #347 (loop integration) are
   archived and unbuilt [S5, S6, S7]
3. The only active path to unblocking is #597 (manual Teams verification)

### 3.2 Dependency Graph

```
#597 (manual Teams test, todo)
  → if pass: reopen #514 (T3 DR)
    → unarchive #344 (Notifier protocol)
      → unarchive #347 (loop integration)
        → #631 (blocked-task scan) becomes actionable
  → if fail: #631 remains indefinitely deferred
```

### 3.3 Option Comparison

| Criterion | A: Keep deferred (.85) | B: Add depends_on #597 (.75) | C: Archive #631 (.60) |
|-----------|:----------------------:|:----------------------------:|:---------------------:|
| Honors #514 | Yes | Yes | Yes |
| Tracks reactivation | Yes | Yes with explicit dep | Lost |
| Actionable signal | Manual (check board) | Automatic (dep resolution) | None |
| Supersession risk | None | None | Must recreate later |
| KISS alignment | High | Medium (adds dep chain) | High but lossy |

## 4. Recommendation (.85 confidence)

**Option A: Keep #631 at ideation/someday. No code changes. No new tasks.**

Rationale:
1. Decision #514 is unchanged — deferral still applies [S1]
2. The only active unblocking path is #597 (Teams Workflows verification),
   which is at `todo` and time-sensitive (O365 Connectors retire Apr 30) [S3, S4]
3. Zero notification infrastructure exists; even if #597 succeeds, #344 and
   #347 must be rebuilt before #631 becomes actionable [S5, S6, S7]
4. Existing blocked-task visibility (`bearclaw status`, planner `pending`
   field) provides adequate coverage for manual workflows [S8]
5. #348 should be archived — it was rejected by architect and superseded
   by #631

Challenge: SKIPPED — validation pass on existing research; no new
recommendation produced. Prior research challenged at .80 confidence [S2].

## 5. Follow-up Tasks

1. Archive #348 (superseded by #631, per architect recommendation)
2. No new tasks — #597 is already the correct next step

