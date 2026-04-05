# Cancel Stale Subtasks #580–#584

> **Owning task:** #595 — Cancel stale subtasks #580-#584 under Phase B parent #484
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Parent #484 (Phase B: MCP-only kanban) had 5 subtasks (#580–#584) created from
pre-reorganization research (2026-04-03). Architect review (2026-04-04) rewrote
#484's AC from scratch and recommended cancellation. All 5 have circular
`depends_on: [484]` (child depending on own parent), permanently blocking dispatch.

**Question:** Is cancellation of all 5 justified, or does any retain actionable scope?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `.github/agents/*.agent.md` grep (0 kanban-md) | Codebase | .95 |
| 2 | `.github/instructions/*.instructions.md` grep (0 kanban-md) | Codebase | .90 |
| 3 | `.github/copilot-instructions.md` grep (1 ref, L27 factual) | Codebase | .90 |
| 4 | 8 cheatsheet skill files grep (0 kanban-md each) | Codebase | .90 |
| 5 | #484 body — architect review, revised AC, stale subtask section | Board | .95 |
| 6 | docs/research/remove-cli-refs-agent-files-580.md | Research | .90 |
| 7 | #580–#584 task bodies — individual research findings | Board | .85 |

## 3. Analysis

### Per-Subtask Verification

| Task | Original Scope | Verified State (2026-04-04) | Verdict |
|------|---------------|---------------------------|---------|
| #580 | 44 CLI refs in 11 agent files | 0 refs (grep-verified) | Obsolete |
| #581 | 8 skill cheatsheets need rewrite | 0 refs in all 8 files | Obsolete |
| #582 | 5 inline-ref skills need update | 2 refs in w-dispatch-planning only — captured in #484 AC 4-7 | Superseded |
| #583 | Rewrite instruction files | 0 refs; agent-common.instructions.md deleted | Obsolete |
| #584 | copilot-instructions L143/149/165/169 | File is 54 lines; target lines don't exist; L27 is factual tech-stack entry | Obsolete |

### Blocking Conditions (both independently sufficient)

1. **Scope obsolescence:** 4/5 tasks have zero actionable work. 1/5 (#582) has
   remaining scope fully captured in parent #484's revised AC.
2. **Circular dependency:** All 5 have `depends_on: [484]` while being children of
   #484. kanban-md cannot resolve this — tasks are permanently undispatchable.

### Tier Classification

**T1 — Autonomous.** Board hygiene cleanup. No new capability, no architecture
change, no security impact. Cancelling stale tasks with documented justification.

## 4. Recommendation

**Cancel all 5 subtasks** (confidence: .95)

Every subtask is either fully obsolete or superseded by #484's revised AC. The
circular dependency makes them permanently undispatchable regardless of scope.

Challenge: skipped — trivial validation finding, no trade-off between options.

## 5. Follow-up Tasks

None. Task #595 IS the follow-up task (created by #580's researcher). Execution
is moving these 5 tasks to done with cancellation notes.
