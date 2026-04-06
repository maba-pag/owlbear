# Blocked-Task Scan for Decision-Request Notifications

> **Owning task:** #348 — Add blocked-task scan for decision-request notifications
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #348 asks the orchestrator to scan for blocked tasks with pending decision
requests during the dispatch loop and notify the user. It was created as the final
task in the notification feature chain: #344 (Notifier protocol) → #347 (loop
integration) → #348 (blocked-task scan).

Decision #514 (2026-04-01) deferred the entire notification feature. User chose
"D: Defer / do nothing" — no Slack available, Teams integration not possible due
to corporate policy. Tasks #344 and #347 were archived without implementation.

**Question:** Should #348 proceed independently, or does it fall within #514's
deferral scope? If independent, what mechanism surfaces blocked-task DR data
without a notification channel?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|:---------:|------|
| S1 | Decision #514 (resolved) | 1.0 | Deferred notification feature; chose "D: Defer" [.owlbear/decisions/resolved/514-slack-notification-approach.md] |
| S2 | slack-notification-v2.md (research) | .90 | Designed `Notifier.on_decision_request(task_id, reason)` as blocked-scan consumer [.owlbear/research/slack-notification-v2.md] |
| S3 | w-orchestration SKILL.md | 1.0 | Step 0 resolves DRs via scribe; `gate_warned` tracks gate-blocked tasks; cycle output format defined [share/skills/w-orchestration/SKILL.md] |
| S4 | w-dispatch-planning SKILL.md | .95 | Planner already emits `pending` field: `{decisions_t2, decisions_t3, actions}` counts in JSON output |
| S5 | bearclaw CLI status command | .85 | Already shows blocked tasks: `BLOCKED #N title: reason` [serve/orchestrator/src/owlbear/cli.py] |
| S6 | Azure DevOps approval checks | .80 | Approvals pause pipeline stages; user notified via UI + email; timeout marks stage as skipped [learn.microsoft.com] |
| S7 | GitHub Actions environment protection | .75 | Required reviewers gate deployments; notification via GitHub UI; configurable wait timer [docs.github.com] |
| S8 | gate-blocked-task-remediation.md | .85 | Established pattern: visibility before action, no auto-remediation; `gate_warned` cycle tracking [.owlbear/research/gate-blocked-task-remediation.md] |

## 3. Analysis

### 3.1 #514 Deferral Scope

| Signal | Includes #348? | Reasoning |
|--------|:--------------:|-----------|
| Task title contains "notifications" | Yes | Explicitly part of notification feature |
| Created as part of #344→#347→#348 chain | Yes | Same `create` batch in slack-notification-v2.md |
| #514 deferred "Slack notification integration" | Yes | All four downstream tasks blocked |
| Scan is useful without notification channel | Partially | Data source exists (`pending` field, `bearclaw status`) but has no active consumer |

**Assessment:** #348 falls within #514's deferral scope. The scan was designed to
feed into `Notifier.on_decision_request()` (S2). Without the Notifier protocol,
the scan's output has no consumer beyond what already exists.

### 3.2 Existing Coverage

| Mechanism | What it covers | Gap |
|-----------|---------------|-----|
| Scribe Step 0 (S3) | Resolves approved DRs before each cycle | Does not report remaining pending DRs |
| `bearclaw status` (S5) | Lists all blocked tasks with reasons | Requires manual invocation; not during orchestration |
| Planner `pending` field (S4) | Counts pending DRs per type | Not consumed by orchestrator; exists in plan JSON |
| `gate_warned` tracking (S3) | Surfaces gate-blocked tasks in cycle output | Only covers Gate 3/4 failures, not DR-blocked tasks |

**Gap:** No in-flight DR-pending reporting during orchestration runs. However,
the scribe's 5-day auto-resolution and the `bearclaw status` command mitigate this.

### 3.3 Option Comparison

| Criterion | A: Defer (align #514) | B: Scan in loop.py | C: Skill-only enhancement | D: Notifier-ready scan |
|-----------|:---------------------:|:-------------------:|:-------------------------:|:----------------------:|
| Honors #514 decision | **Yes** | No | Ambiguous | No |
| Code changes needed | 0 | ~30 LOC | 0 (but creates spec-reality gap) | ~50 LOC |
| User-visible value added | 0 | Low (terminal output) | Low (cycle output) | Low (no-op notifier) |
| KISS/YAGNI alignment | **High** | Medium | Medium | Low |
| Spec-reality gap risk | None | None | **High** (gate_warned precedent) | None |
| Future notification hook | Deferred naturally | Partial | No | Ready |
| Confidence | **.80** | .60 | .55 | .50 |

### 3.4 Established System Patterns (S6, S7)

Azure DevOps and GitHub Actions both surface blocked stages in the UI. The
notification is tied to the UI layer, not the orchestration engine. The scan
(detecting blocked stages) is implicit — every pipeline run knows which stages
are waiting. The notification is a separate concern wired to the user's
preferred channel (email, Teams, Slack, in-app).

OwlBear mirrors this: the board already tracks blocked tasks; the question is
purely about the notification channel, which was deferred.

## 4. Recommendation (.80 confidence)

**Option A: Defer to align with Decision #514.**

Rationale:
1. #348 was created as part of the notification feature chain (S2); the feature
   was explicitly deferred by user decision (S1).
2. Blocked-task visibility is already provided by `bearclaw status` (S5) and
   the planner's `pending` field (S4) — no action gap exists.
3. The scribe resolves approved DRs before each cycle (S3); unresolved T3 DRs
   cause the board to stagnate (empty dispatch plan), which the orchestrator
   already handles by stopping the loop.
4. Building scan infrastructure without a notification consumer is YAGNI.
5. The skill-only approach (Option C) creates a spec-reality gap based on
   `gate_warned` precedent (specified in skill but not in loop.py code).

**When to revisit:** When a notification channel becomes available (Slack,
Teams, or alternative), reactivate #348 and implement the blocked-task scan
as the data source for `Notifier.on_decision_request()`.

Challenge: RECONSIDER — confidence in original: .85 → revised to .80 after
challenger identified #514 scope ambiguity and spec-reality gap risk. Accepted
challenger's points on scope inclusion and downgraded from Option C to Option A.

## 5. Follow-up Tasks

1. Create tracking task for future reactivation when notification channel is enabled.
