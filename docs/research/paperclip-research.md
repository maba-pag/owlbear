# Paperclip AI — Feature Evaluation for OwlBear

> **Owning task:** #746 — Research paperclipai/paperclip for OwlBear
> **Date:** 2026-03-12 **Status:** Complete

## 1. Context and Question

Paperclip ([paperclipai/paperclip](https://github.com/paperclipai/paperclip)) is an open-source orchestration platform for "zero-human companies" — it manages teams of AI agents with org charts, budgets, governance, and a heartbeat protocol. Which Paperclip patterns are worth adopting in OwlBear?

**Key architectural difference:** Paperclip is a *control plane* orchestrating external agent processes (Claude Code, Codex, Gemini CLI) via adapters and a PostgreSQL database. OwlBear is an *agent framework* with in-process PydanticAI agents on a single laptop. Many Paperclip patterns solve multi-tenant/multi-process problems OwlBear doesn't have.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Paperclip README + architecture docs | [github.com/paperclipai/paperclip](https://github.com/paperclipai/paperclip) | .90 |
| Paperclip heartbeat SKILL.md | `skills/paperclip/SKILL.md` in repo | .85 |
| Paperclip PARA memory skill | `skills/para-memory-files/SKILL.md` in repo | .70 |
| Paperclip cost/approval API docs | `docs/api/costs.md`, `docs/api/approvals.md` in repo | .80 |
| Paperclip adapter overview | `docs/adapters/overview.md` in repo | .65 |
| OwlBear `UsageTracker` | `src/owlbear/memory/usage.py` | .90 |
| OwlBear `HeartbeatRunner` | `src/owlbear/core/heartbeat.py` | .85 |
| OwlBear daemon orchestration | `src/owlbear/daemon.py` | .90 |
| OwlBear approval/policy system | `src/owlbear/safety/gate.py`, `safety/policy.py` | .80 |

## 3. Analysis

### Feature Comparison Matrix

| Pattern | Paperclip Approach | OwlBear Equivalent | Gap? | KISS/YAGNI |
|---------|-------------------|-------------------|------|------------|
| Budget enforcement | Per-agent monthly limits, auto-pause at 100% | `UsageTracker` records costs but no thresholds | **YES** | KISS ✓ — small extension |
| Blocked-task dedup | Skip tasks with no new context since last comment | Not implemented | **YES** | KISS ✓ — prevents wasted LLM calls |
| Wake-reason context | `PAPERCLIP_WAKE_REASON` + `PAPERCLIP_TASK_ID` env vars | `HeartbeatRunner` reads `HEARTBEAT.md` file | Partial | KISS ✓ — enrich existing |
| Goal ancestry | Tasks carry full goal chain for context | `depends_on` in kanban but no goal hierarchy | Minor | YAGNI — kanban body suffices |
| Heartbeat protocol | 9-step procedure with event-triggered wakes | `HeartbeatRunner` + `poll_loop`/`poll_tick` | None | Already simpler ✓ |
| Adapter model | 7 adapters for external CLI agents | PydanticAI in-process agents | N/A | Different paradigm |
| Org chart hierarchy | Tree with reporting lines, escalation | Flat `AgentRegistry` + role policies | N/A | YAGNI — single user |
| PARA memory | File-based 3-layer (graph, daily, tacit) | SQLite + Qdrant + `SessionStore` | N/A | OwlBear's is richer |
| Multi-tenancy | Company-scoped data isolation | Single workspace | N/A | YAGNI — laptop daemon |
| Atomic checkout | 409 Conflict on concurrent task claim | kanban-md `--claim` system | None | Already have |
| Audit trail | `X-Paperclip-Run-Id` on all mutations | `ObservabilityHook` JSONL events | None | Already have |
| Config governance | Approval gates + revision rollback | `ApprovalGateToolset` (tool-level) | Partial | YAGNI — no config rollback needed |

### Adoptable Patterns (detailed)

**1. Budget thresholds with auto-pause (.80 confidence)**

Paperclip enforces per-agent monthly cost limits via `POST /api/costs/events` and auto-pauses agents at 100% budget. OwlBear's `UsageTracker` already records per-request costs and has `total_cost` aggregation, but lacks configurable thresholds or enforcement. Adding a `budget_limit` config field and a check in `_record_usage()` that raises/warns at threshold is ~30 LOC. Sources: Paperclip `docs/api/costs.md` (budget enforcement model), OwlBear `src/owlbear/memory/usage.py` (existing cost tracking).

**2. Blocked-task dedup (.75 confidence)**

Paperclip's heartbeat skips blocked tasks that have no new context since the agent's last comment — preventing the agent from repeatedly failing on the same stuck task. OwlBear's `poll_tick` currently processes all eligible tasks without checking "has anything changed since last attempt?" Adding a `last_attempted` timestamp per task and skipping tasks with no new activity since that timestamp prevents wasted LLM calls in autonomous mode. Sources: Paperclip `skills/paperclip/SKILL.md` (step 4: pick work, skip blocked), OwlBear `src/owlbear/daemon.py` (`poll_tick` task selection).

**3. Wake-reason context (.65 confidence)**

Paperclip passes `PAPERCLIP_WAKE_REASON` (timer/event/manual) and task ID as env vars so agents know *why* they woke. OwlBear's `HeartbeatRunner` could pass a `wake_reason` field to `poll_tick` to enable smarter prioritization (e.g., event-triggered tasks get higher priority than timer ticks). However, OwlBear's current channel-based architecture already provides context via message content. Lower confidence because the benefit is marginal. Sources: Paperclip `skills/paperclip/SKILL.md` (wake-reason env vars), OwlBear `src/owlbear/core/heartbeat.py`.

### Patterns NOT Recommended

| Pattern | Reason for rejection |
|---------|---------------------|
| Adapter model | Solves external-process orchestration; OwlBear uses in-process PydanticAI agents |
| Org chart hierarchy | YAGNI — OwlBear is single-user, flat `AgentRegistry` with role policies is sufficient |
| PARA memory system | OwlBear's SQLite+Qdrant hybrid search is more sophisticated than file-based PARA |
| Multi-tenancy | YAGNI — laptop-resident daemon serves one user |
| Goal ancestry | Kanban task body + `depends_on` already provides sufficient context; adding a formal goal chain adds complexity without clear payoff |
| Config governance with rollback | YAGNI — no evidence of config drift problems |

## 4. Recommendation (.75 confidence)

Adopt two patterns, defer one:

1. **Adopt: Budget thresholds** — Extend `UsageTracker` with configurable per-session and monthly cost limits. Auto-warn at 80%, auto-pause at 100%. Small change (~30 LOC), high value for autonomous mode safety.
2. **Adopt: Blocked-task dedup** — Track `last_attempted` per task in `poll_tick`. Skip tasks with no new activity since last attempt. Prevents wasted LLM calls in autonomous mode.
3. **Defer: Wake-reason context** — Marginal value given OwlBear's channel architecture already conveys context. Revisit if `HeartbeatRunner` grows more complex.

**Risk:** Budget enforcement needs careful design — hard-pause vs. warn-and-continue, per-session vs. per-day limits, grace periods. Keep the first implementation simple (single global threshold, log warning, skip task) and iterate.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add budget threshold to UsageTracker" --priority needed --status backlog --tags "phase-4,config,agent,scope:core" --body "## Acceptance Criteria`n- [ ] Add 'budget_limit_usd' field to OwlBearSettings (default: None = unlimited)`n- [ ] UsageTracker checks cumulative cost against threshold after each _record_usage()`n- [ ] At 80%: log warning via ObservabilityHook`n- [ ] At 100%: raise BudgetExceededError (caught by poll_tick to skip further work)`n- [ ] Unit tests for threshold logic (0%, 80%, 100%, None/unlimited)`n`n## References`n- Paperclip budget model: docs/api/costs.md`n- Research: docs/research/paperclip-research.md"

kanban\kanban-md.exe create "Add blocked-task dedup to poll_tick" --priority important --status backlog --tags "phase-4,agent,scope:core" --body "## Acceptance Criteria`n- [ ] Track 'last_attempted_at' timestamp per task in OrchestratorState`n- [ ] poll_tick skips tasks where last_attempted_at > last_activity_at (no new kanban comments/edits since last attempt)`n- [ ] Log skipped tasks at DEBUG level`n- [ ] Unit tests: task with no new activity skipped, task with new activity processed`n`n## References`n- Paperclip skip-blocked pattern: skills/paperclip/SKILL.md step 4`n- Research: docs/research/paperclip-research.md"
```
