# Notifier Protocol and SlackNotifier — Duplicate & Deferral Assessment

> **Owning task:** #344 — Implement Notifier protocol and SlackNotifier (webhook + urllib)
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Task #344 asks for a `Notifier` protocol and `SlackNotifier` implementation using
Incoming Webhooks + stdlib urllib in `packages/orchestrator/`. This task was created
as a follow-up from #26's research (`slack-notification-v2.md`) on 2026-03-30.

Two days later (2026-04-01), the planner decomposed #26's follow-ups into a proper
TDD task chain: #514 (tests) → #515 (impl) → #516 (tests) → #517 (loop integration)
→ #518 (tests) → #519 (decision-request scan). Task #515 has the identical title
and scope as #344. All six tasks were deferred and archived after decision #514
chose "Defer / do nothing."

**Key questions:**
1. Is #344 a true duplicate of #515?
2. Does the blocking decision (#514) still apply?
3. Are there alternatives (e.g., Teams) that could unblock the feature?

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `docs/research/slack-notification-v2.md` | 1.0 | Complete design for Notifier protocol + SlackNotifier (Option A: webhook + urllib) |
| S2 | `docs/decisions/resolved/514-slack-notification-approach.md` | 1.0 | Approved deferral: "No Slack available. Teams integration not possible due to corp policy" |
| S3 | Task #515 (archived) | 1.0 | Identical title, scope, and AC to #344; part of #514-#519 TDD chain |
| S4 | `packages/orchestrator/src/owlbear/orchestrator/loop.py` | 1.0 | Current dispatch loop — no notifier integration exists |
| S5 | `packages/orchestrator/pyproject.toml` | 1.0 | 3 deps (ACP, pydantic, typer) — unchanged since prior research |
| S6 | MS Teams Incoming Webhooks docs (learn.microsoft.com) | .85 | Teams webhooks use HTTP POST + JSON (MessageCard or Adaptive Card); same urllib pattern |
| S7 | MS Teams connector deprecation notice (learn.microsoft.com) | .90 | M365 Connectors nearing deprecation; migration path: Power Automate Workflows |
| S8 | `docs/research/notification-hook.md` | .80 | v1 NotificationBackend protocol and priority-chain design |

## 3. Analysis

### 3.1 Duplicate Assessment

| Dimension | #344 | #515 | Verdict |
|-----------|------|------|---------|
| Title | Implement Notifier protocol and SlackNotifier (webhook + urllib) | Identical | Duplicate |
| Scope | Notifier protocol + SlackNotifier in orchestrator package | Identical | Duplicate |
| Depends on | #26 (archived) | #514 (archived) | Different parent chain but same feature |
| AC | (empty body) | Full AC with 10 checkable items | #515 is more complete |
| Status | ideation | archived (someday) | #515 already processed |

**Conclusion:** #344 is a duplicate of #515 with a weaker specification. [S1, S3]

### 3.2 Decision Status

Decision #514 (approved 2026-04-01) chose "D: Defer / do nothing" with notes: "No
Slack available. Teams integration due to corp policy currently not possible." This
is a **T3 blocking decision** — no auto-resolve. The decision applies to the entire
notification subsystem (#514-#519), and by extension to #344. [S2]

### 3.3 Teams Webhook as Alternative

| Criterion | Slack Incoming Webhook (.85) | Teams Workflows Webhook (.65) | Generic Webhook (.55) |
|-----------|:----------------------------:|:-----------------------------:|:---------------------:|
| New deps | 0 (stdlib urllib) | 0 (stdlib urllib) | 0 (stdlib urllib) |
| Config vars | 1 (webhook URL) | 1 (webhook URL) | 2+ (URL + payload template) |
| Payload format | `{"text": "msg"}` | Adaptive Card JSON (~15 lines) | User-defined template |
| Setup complexity | Create webhook in Slack app | Power Automate workflow + trigger | Depends on target |
| Corp availability | **Not available** [S2] | **Unknown** — needs evaluation | N/A |
| M365 deprecation risk | None | Connector API deprecated; Workflows API is the replacement [S7] | None |
| LOC estimate | ~35 | ~45 (heavier JSON payload) | ~60 (template engine) |
| KISS | Highest | High | Medium |

**Risk:** Microsoft 365 Connectors (the old Teams webhook approach) are nearing
deprecation. The new approach uses Power Automate Workflows with a webhook trigger —
technically similar (HTTP POST) but requires Power Automate licensing and org-level
enablement. Whether this is available in the corp environment is unknown. [S6, S7]

### 3.4 Notifier Protocol Viability

The protocol design from `slack-notification-v2.md` remains valid regardless of
backend choice. The three-method protocol (`on_dispatch`, `on_completion`,
`on_decision_request`) is transport-agnostic — `SlackNotifier`, `TeamsNotifier`, or
`GenericWebhookNotifier` all implement the same interface. [S1, S4]

The orchestrator package still has exactly 3 dependencies. No code has been written
for notifications. The dispatch loop integration points identified in the research
(`dispatch_entry`, `_apply_wave_result`, blocked-task scan) are unchanged. [S4, S5]

## 4. Recommendation (.85 confidence)

**Archive #344 as duplicate of #515. The deferral decision (#514) still applies.**

If notifications become desirable again, the path forward is:
1. Confirm whether Power Automate Workflows are available in the corp environment
2. If yes: reopen decision #514 with Teams Workflows as Option D
3. If no: feature remains deferred until Slack or an alternative becomes available

The Notifier protocol design is sound and ready for implementation when unblocked.

Challenge: FALLBACK — `challenger` agent not available in agent list.

## 5. Follow-up Tasks

1. **Evaluate Power Automate Workflows for Teams notifications** — check corp
   availability of Workflows webhook trigger as alternative to Slack. (Created at
   ideation, nice-to-have.)
