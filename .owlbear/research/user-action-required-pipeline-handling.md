# Pipeline Handling for User-Action-Required Tasks

> **Owning task:** #661 — Pipeline handling for user-action-required tasks
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Tasks requiring manual user action (GUI verification, external approvals, credential setup) loop futilely through the automated pipeline. Task #597 proved this empirically: 6 agents passed through as `type:test`, auditor rejected (.88), architect confirmed re-entry would repeat verbatim. Four pipeline cycles before the architect resorted to manual blocking.

**Question:** What convention identifies user-action tasks early and routes them outside the automated pipeline until the user completes the action?

## 2. Sources Studied

| Source | URL/Path | Relevance |
|--------|----------|-----------|
| #597 task body (4 architect cycles) | .owlbear/kanban/tasks/597-*.md | 1.0 — empirical evidence of the gap |
| #221 research: action requests | .owlbear/research/extend-decision-request-for-action-requests.md | 1.0 — existing AR infrastructure design |
| r-pipeline-protocol §5 Escalation | share/skills/r-pipeline-protocol/SKILL.md | 1.0 — existing blocking convention |
| AutoGen Human-in-the-Loop docs | microsoft.github.io/autogen/.../human-in-the-loop.html | .85 — HandoffTermination + async resume |
| GitHub Actions environment protection | docs.github.com/en/.../managing-environments | .75 — required-reviewer gate, structured file |
| 5 resolved action requests | .owlbear/decisions/resolved/167-*, 548-*, 532-* | .90 — proof AR mechanism works |
| gates.py / server.py NON_IMPL_TAGS | serve/orchestrator/src/owlbear/planner/gates.py | 1.0 — actual scope of pass-through tags |
| selector.py STATUS_AGENT_MAP | serve/orchestrator/src/owlbear/planner/selector.py | 1.0 — dispatch routing is status-based only |

## 3. Analysis

### What already works

| Mechanism | Status | Evidence |
|-----------|--------|----------|
| Scribe action requests (`request_type: action`) | Implemented | 5 resolved ARs (#167, #548, #532) |
| Blocking/unblocking via scribe | Implemented | Pipeline-protocol §5, scribe agent |
| `pick_tasks` excludes blocked tasks | Implemented | `--not-blocked` flag in board.py |
| NON_IMPL_TAGS TDD gate exemption | Implemented | gates.py, server.py |
| pipeline-protocol §5 user-action instruction | Documented | BUT #597 agents didn't follow it |

### What's missing

| Gap | Impact | #597 evidence |
|-----|--------|---------------|
| No detection convention (tag/marker) for user-action tasks | Agents can't mechanically identify them | 6 agents passed through without creating AR |
| No architect gate rule for user-action tasks | Architect approved to todo instead of blocking | Cycle 1 architect approved #597 |
| No post-AR-completion fast-path | After user completes, task re-enters at backlog → architect re-evaluates fully | Cycles 2-4: architect had to manually reason about re-entry |
| Dual-nature tasks (user action + code) unaddressed | Binary non-impl tag can't represent both | #167 had both UI verification and code changes |

### Option comparison

| Criterion | A: Tag + AR blocking + fast-path (.78) | B: New `waiting` status (.55) | C: Strengthen instructions only (.40) |
|-----------|----------------------------------------|-------------------------------|---------------------------------------|
| KISS | High — uses existing AR/blocking | Low — new status, new mapping | High but ineffective |
| Mechanical enforcement | Blocking IS mechanical (pick_tasks excludes) | Status-based exclusion | None (same #597 failure) |
| Detection reliability | Tag is data, checkable by rules | Status change is mechanical | Instruction-only, unreliable |
| Post-completion path | Architect fast-path via `## Action Completed` | Status → backlog, same issue | Undefined |
| Dual-nature support | Split into 2 tasks (atomicity rule) | Split or hybrid status | N/A |
| Code changes | Add tag to NON_IMPL_TAGS (4 locations, 2 loc) | STATUS_AGENT_MAP, board reader, MCP | None |
| Instruction changes | 3 skill files (arch-review, pipeline-protocol, agent-common) | 5+ files | 2 files |

### AutoGen / GitHub Actions patterns

AutoGen's `HandoffTermination` confirms the pattern: agent declares a typed pause, system surfaces it, user resolves, team resumes. GitHub Actions' required-reviewer gate is the closest analog: structured file, required approval, auto-timeout. Both validate the file-based async-deferral approach OwlBear already uses via action requests.

Key insight from both: the **blocking** is the mechanism, not the routing. AutoGen blocks the team until user responds. GitHub Actions blocks the deployment until reviewer approves. OwlBear's scribe+blocking already implements this — the gap is detection timing.

## 4. Recommendation (.78 confidence)

**Option A: `type:user-action` tag + AR blocking + architect fast-path.**

### Mechanism (3 parts)

**Part 1 — Detection & Tagging.** Add `type:user-action` tag convention. Detection heuristics for architect:
- AC contains physical actions (Open, Click, Navigate, Verify in browser/GUI)
- AC references systems outside the codebase (Teams, Azure portal, external tools)
- No testable Python interfaces AND AC requires human observation
- AC contains checkbox steps the user must perform manually

Researcher may tag during research; architect is the mandatory gate.

**Part 2 — Blocking via AR.** When architect sees `type:user-action`: create action request via scribe → block → `end_work(outcome="block")`. The blocking mechanism IS the mechanical enforcement — `pick_tasks` already excludes blocked tasks via `--not-blocked`. No dispatch code changes needed.

**Part 3 — Post-AR-completion fast-path.** When architect receives a task with `## Action Completed` in body + `type:user-action` tag: verify AC checkboxes are checked → approve to `todo`. The "Resolved Decision Pre-flight" in pipeline-protocol already requires agents to check for resolved DRs. This adds a specific rule: action-completed user-action tasks get fast-approval.

**Dual-nature tasks:** Split into user-action task + code task per atomicity rule. Code task `depends_on` user-action task. Standard decomposition.

**NON_IMPL_TAGS:** Add `type:user-action` for TDD gate exemption (test-writer pass-through after user completes). This does NOT prevent dispatch — it only exempts the TDD readiness gate.

### #597-style dry-run scenario

1. Task created: "Verify Teams Workflows availability" with `type:user-action` tag
2. Researcher: validates research, confirms `type:user-action`
3. Architect: detects tag → creates AR via scribe → blocks → end_work(outcome="block")
4. Orchestrator cycle: `pick_tasks` returns empty for this task (blocked) — no agents dispatched
5. User: performs action → sets `response: completed` in AR file
6. Scribe resolve: writes `## Action Completed`, unblocks task
7. Architect (re-entry): sees `## Action Completed` + `type:user-action` → verifies AC → approves
8. Pipeline: test-writer/builder pass through (NON_IMPL_TAGS), reviewer/auditor verify → archive

Result: 2 architect cycles (initial block + post-completion review) vs #597's 4+ cycles with no resolution.

Challenge: proceed/reconsider/block — challenger issued **block** (.35 confidence). Key challenges accepted: NON_IMPL_TAGS scope correction, post-unblock path, dual-nature tasks. Revised recommendation incorporates all three. Rejected: "architect gate is identical to Option C" — the tag is a data point that enables mechanical rules, not just prose instructions. Blocking IS mechanical enforcement.

## 5. Follow-up Tasks

1. **Add `type:user-action` to NON_IMPL_TAGS and document convention** — update gates.py, server.py, w-dispatch-planning, w-tdd-red (4 locations, ~2 LOC each)
2. **Add architect user-action gate rule** — update w-arch-review with detection heuristics and AR-creation rule for `type:user-action` tasks
3. **Add architect post-AR fast-path** — update w-arch-review with `## Action Completed` + `type:user-action` → fast-approve rule
4. **Document convention in r-pipeline-protocol** — add `type:user-action` section to §5.Escalation with detection heuristics, flow diagram, dry-run scenario
5. **Update agent-common.instructions.md** — add user-action detection responsibilities to per-agent guidance
