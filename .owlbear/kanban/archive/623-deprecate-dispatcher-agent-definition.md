---
id: 623
title: Deprecate dispatcher agent definition
status: archived
priority: medium
created: 2026-04-05T01:31:22.2282042+02:00
updated: 2026-04-05T23:02:21.1228177+02:00
started: 2026-04-05T23:02:21.1228177+02:00
completed: 2026-04-05T23:02:21.1228177+02:00
tags:
    - scope:agents
    - phase-2
    - type:build
    - agent
parent: 619
depends_on:
    - 622
class: standard
---

## Acceptance Criteria

- Dispatcher agent file (share/agents/dispatcher.agent.md) is marked deprecated:
  - YAML frontmatter: `deprecated: true` (or equivalent marker)
  - Description prefixed with "(DEPRECATED)"
  - Body explains replacement by pick_tasks MCP tool
- Dispatcher removed from orchestrator agent's `agents:` list (if it was listed there)
- copilot-instructions.md pipeline description updated if it references dispatcher
- No remaining references to dispatcher as a live subagent in any active agent/skill file
- Dispatcher agent file NOT deleted (kept for reference), just deprecated

[[2026-04-05]] Sun 14:18
## Research
- Research doc: .owlbear/research/deprecate-dispatcher-agent.md
- Sources: 8 studied, 7 high-relevance (all codebase-internal, no external)
- Recommendation: Follow h-kanban-md deprecation pattern (description prefix + body callout); narrow scope to dispatcher.agent.md + orchestrator agents: list; copilot-instructions.md has no refs (N/A) (confidence: .88)
- Follow-up tasks created: none (gap noted in #629 body for w-task-decomposition L19)
- Decision requests: none — T1 autonomous, executing pre-approved migration plan

## Challenge Results
- Challenger: SKIP — T1 execution of pre-approved plan (#619 arch review approved all subtasks including deprecation)
- Tier: T1 (autonomous), no new capability or architecture change
- Key findings: (1) 38 dispatcher refs across 8 files; only 4 refs in #623 scope (agent file + orchestrator agents: list); (2) AC item 4 overlaps #629 — narrow to orchestrator agents: list verification; (3) w-task-decomposition L19 gap added to #629
- Researcher response: documented scope boundary; no new tasks needed (existing subtasks cover all work)

[[2026-04-05]] Sun 15:55
## Architecture Review

### AC Refinements (binding for downstream agents)

| Original AC | Issue | Revised AC |
|-------------|-------|------------|
| YAML frontmatter: `deprecated: true` (or equivalent marker) | No precedent in workspace; unknown if VS Code recognizes key | REMOVED. Rely on description prefix (h-kanban-md pattern) only |
| No remaining references to dispatcher as a live subagent | Unachievable by #623 alone; 27+ refs owned by #622/#629 | Replaced with explicit scope boundary deferring to #629 |
| copilot-instructions.md updated if it references dispatcher | Verified: zero refs in copilot-instructions.md | Marked N/A, no changes needed |

**Binding AC for builder (supersedes original where they differ):**
1. `share/agents/dispatcher.agent.md` description field prefixed with "(DEPRECATED)" per h-kanban-md pattern
2. `share/agents/dispatcher.agent.md` body contains deprecation callout: `> **Deprecated.** Replaced by pick_tasks MCP tool (#621). See #619 migration plan.`
3. `share/agents/orchestrator.agent.md` L10: remove `dispatcher` from agents list
4. File NOT deleted (kept for reference)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: deprecate dispatcher agent definition |
| Interface clarity | PASS (refined) | Original AC mixed proven/speculative patterns; narrowed to h-kanban-md. Scope overlap with #629 resolved. |
| Dependency correctness | PASS | Depends on #622 (todo). Correct: wire replacement before deprecating. Chain: #620, #621, #628, #622, #623 |
| Module layering | PASS | Agent file edits only; no code changes |
| TDD compliance | PASS | Non-impl task; tagged `agent` (pass-through) |
| KISS/YAGNI | PASS | Minimal scope: 2 files, description prefix + body callout |
| Premise challenge | PASS | Dispatcher is disable-model-invocation=true, being replaced by MCP tool; deprecation is correct step |
| Pattern consistency | PASS (refined) | Removed speculative `deprecated: true` YAML key. Aligned to h-kanban-md (only proven deprecation convention). |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Agents domain only (scope:agents) |

### Challenge Results
- Challenger: FALLBACK (not in available agents list)
- Mitigant: T1 task executing pre-approved migration plan (#619 arch review APPROVED; challenger ran on parent)
- Research challenge data: thorough (38-ref inventory, scope boundary analysis, gap tracking to #629)
- Architect confidence: .92

### Conflict Note
#629 AC includes "dispatcher.agent.md: add deprecated header OR delete file" which overlaps #623 scope. #623 runs first per dependency chain, so #629 architect should narrow that AC item to verification only.

### Verdict: APPROVE (via REFINE)
### Action: AC tightened (3 items refined per table above); backlog to todo

[[2026-04-05]] Sun 15:56
Architecture review complete. AC refined: removed speculative YAML key, narrowed scope boundary with #629, confirmed copilot-instructions.md N/A. All 10 criteria PASS. Confidence .92.

[[2026-04-05]] Sun 17:45
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- AC scope: edits to `share/agents/dispatcher.agent.md` and `share/agents/orchestrator.agent.md` only.
- No Python interfaces created or modified; no testable contract exists.
- Passing through to builder.

[[2026-04-05]] Sun 20:48
## Builder Notes
- Files changed: `share/agents/dispatcher.agent.md` (2 edits)
- Changes: description prefixed with "(DEPRECATED)"; deprecation callout added to body
- Orchestrator `agents:` list: no `dispatcher` entry found — AC item 3 pre-satisfied (no change needed)
- copilot-instructions.md: zero refs confirmed by architecture review — N/A
- No tests applicable (non-impl task, tagged `agent`)
- No Python code modified; ruff N/A
- Confidence: 1.0 — all binding AC items satisfied

[[2026-04-05]] Sun 21:37
## Review Evidence\n- Tests: N/A (non-impl task, tagged `agent`; test-writer correctly passed through)\n- Lint: N/A (no Python code modified)\n- Coverage: N/A\n- Changed files in scope: `share/agents/dispatcher.agent.md` only\n\n### AC Compliance\n| Binding AC | Evidence | Status |\n|---|---|---|\n| 1. description prefixed \"(DEPRECATED)\" | git diff confirmed exact change | PASS |\n| 2. body deprecation callout (exact text) | git diff confirmed exact text added | PASS |\n| 3. dispatcher removed from orchestrator agents: list | Not present in orchestrator.agent.md; file not in changed set (pre-satisfied) | PASS |\n| 4. File NOT deleted | File exists; 2-line edit only | PASS |\n\n- TestFromAC modifications: None (no test files for this task)\n- Security: No new system boundaries or code paths\n- Deductions: 0\n- Confidence: .97 → PASS

[[2026-04-05]] Sun 22:02
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Agent file edit only; `disable-model-invocation: true` (already inert); zero refs in `copilot-instructions.md` confirmed by S4 + grep |
| 2 | Module docstrings | No | N/A | No Python files created or modified |
| 3 | External attribution | No | N/A | All 7 high-relevance sources codebase-internal (research doc S1–S7) |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/deprecate-dispatcher-agent.md` exists, linked in task body Research section |

### Files Updated
- None

### Scratch Files Cleaned
- None found (`623-*` glob: no results)

[[2026-04-05]] Sun 23:02
## Audit\n\n### AC Verification\n| Binding AC | Evidence | Status |\n|---|---|---|\n| 1. description prefixed "(DEPRECATED)" | dispatcher.agent.md L2: exact prefix present | PASS |\n| 2. body deprecation callout | dispatcher.agent.md L13: exact blockquote present | PASS |\n| 3. dispatcher removed from orchestrator agents: list | orchestrator.agent.md agents: list confirmed no dispatcher entry (pre-satisfied) | PASS |\n| 4. File NOT deleted | File exists, 2-line edit only | PASS |\n\n### Test Results\n- Full suite: 2914 passed, 420 failed, 18 skipped (405s)\n- Failures in task scope: 0 (zero Python files changed; all 420 are pre-existing RED-phase tests)\n- Lint (ruff): All checks passed\n\n### Scoring\n- AC quality: 4/5 (original AC needed significant architect refinement; binding AC was clean)\n- Reviewer section: present, detailed, PASS at .97\n- Deductions: 0\n- Confidence: 1.00\n\n### Action: ARCHIVE
