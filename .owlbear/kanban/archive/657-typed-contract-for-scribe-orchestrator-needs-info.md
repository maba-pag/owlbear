---
id: 657
title: Typed contract for scribe↔orchestrator NEEDS-INFO boundary
status: archived
priority: medium
created: 2026-04-06T07:22:30.99221+02:00
updated: 2026-04-06T13:38:15.5290908+02:00
started: 2026-04-06T13:38:15.5290908+02:00
completed: 2026-04-06T13:38:15.5290908+02:00
tags:
    - scope:pipeline
    - ' type:refactor'
    - research
class: standard
---

## Summary

Replace the text-based NEEDS-INFO signal between scribe and orchestrator with a typed return contract. The current fix (Option A carve-out) works but introduces an exception to the "never interpret subagent output" critical rule. A typed contract makes the scribe↔orchestrator boundary explicit and unambiguous — the scribe returns structured data, not a signal to be parsed.

## Context

The scribe's resolve-mode output is currently a text string:
```
RESOLVED N requests | ...
NEEDS-INFO M requests | #616 agent=researcher, ...
PENDING P awaiting user | ...
```

The orchestrator must regex-parse this to extract task IDs and agents for NEEDS-INFO dispatch injection. This is fragile and required a carve-out exception to the "never interpret subagent output" rule.

A better design: the scribe returns a structured object (via a shared file or structured output format) that the orchestrator reads as data, not interprets as text. This removes the carve-out and makes the boundary a typed contract.

## Design Direction

Options to explore:
- Scribe writes a structured summary file (e.g., `.owlbear/decisions/last-resolve.json`) with resolved/needs-info/pending arrays
- Scribe returns a structured Channel B artifact that the orchestrator reads
- Scribe uses a dedicated MCP tool to register NEEDS-INFO dispatches that pick_tasks can include

## Acceptance Criteria

- [ ] Scribe↔orchestrator boundary uses a typed contract (not text parsing)
- [ ] The "never interpret subagent output" critical rule has no exceptions
- [ ] NEEDS-INFO dispatch injection still works correctly
- [ ] No regression in DR processing (approved, rejected, completed, needs-info, auto-approved all work)
- [ ] Scribe remains a lightweight clerk (no dispatch responsibility)

[[2026-04-06]] Mon 08:01
## Research
- Research doc: .owlbear/research/scribe-orchestrator-typed-contract.md
- Sources: 7 studied (all internal codebase), 4 high-relevance
- Recommendation: Option A — resolve-summary.json file contract (confidence: .80)
- Challenge: reconsider (challenger ranked D > C > A; revised confidence from .85 → .80 after re-evaluation; A still wins on KISS — fewest tool calls, zero Python changes)
- Follow-up tasks created: #660 (implement the typed contract)
- Decision requests: none (T1 — refactor within approved scope)

[[2026-04-06]] Mon 08:10
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research deliverable only; implementation tracked by #660 |
| Interface clarity | PASS | JSON schema `{resolved, needs_info, pending}` is well-defined; file location, lifecycle (write→read→delete) specified |
| Dependency correctness | PASS | #660 depends on #657; no other deps needed |
| Module layering | PASS | File-based contract respects agent boundary; orchestrator reads infrastructure state, not subagent output |
| TDD compliance | PASS | No testable Python code (Option A = zero Python changes); `research` pass-through tag added |
| KISS/YAGNI | PASS | Option A is simplest: fewest tool calls, lowest prompt complexity, zero Python changes |
| Premise challenge | PASS | Carve-out exception is a real code smell; refactoring to typed contract is justified |
| Pattern consistency | PASS | curation-report.json precedent exists (weaker: tool→code); JSON file contract is human-inspectable |
| Security surface | PASS | No new system boundaries; internal file between agents |
| Single domain | PASS | Pipeline domain only |

### Challenge Results
- Challenger: reconsider (confidence: 0.35)
- Concerns raised: (1) semantic violation unchanged by transport change, (2) file-system failure modes unquantified, (3) Option D dismissed too quickly, (4) narrow research scope, (5) #660 AC missing failure-mode tests
- Architect response: REBUTTED on 1-4, ACCEPTED point 5 as guidance for #660
  - Point 1: Rule intent is "avoid fragile text parsing," not "prevent all coordination." Reading deposited state is architecturally distinct from parsing Channel A text.
  - Point 2: Single-orchestrator execution model makes concurrent/race concerns moot. Delete failures → idempotent re-dispatch (safe).
  - Point 3: Research trade-off matrix explicitly evaluated D; A wins on KISS with defensible rationale.
  - Point 4: 7 internal sources adequate for T1 internal refactor.
  - Point 5 (accepted): When #660 reaches backlog, its AC should include stale-file edge cases and graceful degradation tests.

### Guidance for #660 Architecture Review
When #660 reaches backlog, ensure AC includes:
- Explicit handling of stale resolve-summary.json (delete failure → next cycle behavior)
- Idempotency verification (re-dispatch of already-addressed NEEDS-INFO is safe)
- Graceful degradation test (missing file = empty dispatches, not crash)

### Verdict: APPROVE
### Action Taken: Added `research` pass-through tag. Advanced to todo. Implementation tracked by #660 (depends_on: [657]).

[[2026-04-06]] Mon 08:39
## Test-Writer Notes
- Non-implementation task (tagged `research`) — no tests applicable.
- AC describes a research deliverable and design recommendation only; zero Python source changes (Option A = file-based JSON contract, no new modules or functions).
- Architecture Review confirms: "TDD compliance PASS — no testable Python code."
- Passing through to builder.

[[2026-04-06]] Mon 12:45
## Builder Notes
- Non-implementation task — no code changes needed.
- Tagged `research` with pass-through confirmed by Test-Writer Notes and Architecture Review.
- Option A (resolve-summary.json file contract) is a zero-Python-changes design decision; implementation tracked by #660.
- Passing through to review.

[[2026-04-06]] Mon 13:08
## Review Evidence

**Task type:** Research pass-through (`research` tag) — no Python changes, no tests applicable.

**Changed files scoped to #657:**
- `.owlbear/research/scribe-orchestrator-typed-contract.md` — research document
- `.owlbear/kanban/tasks/657-...md` — task body
- `.owlbear/kanban/tasks/660-...md` — implementation follow-up task

**Quality-runner:** Not dispatched — no Python source changes; no `TestFromAC_*` classes exist (conditionally skipped per Steps 5.0/5.2). No lint scope.

**Security scan:** Proposed JSON contract (`{resolved, needs_info, pending}`) contains only internal data (task IDs, agent names) written by one agent and read by another. No user input at system boundary, no untrusted deserialization, no secrets. Clean.

**Research Gate Checklist (w-research §1–8):**
All 6 mandatory items verified. Items 7–8 (recommended): 7 is N/A per Architecture Review ("TDD PASS — no testable Python code"); 8 is satisfied by the research doc.

**Research document completeness:** All 5 required sections present. 7 internal sources (appropriate for T1 refactor). Trade-off matrix covers 4 options (A–D). Challenge step done: `reconsider` verdict received, full rebuttal recorded, point 5 accepted as guidance for #660 AC. Recommendation confidence .80 defensible.

**Follow-up task #660:** Valid YAML frontmatter confirmed by direct file read. 10 AC items with stale-file, graceful-degradation, and regression coverage. `depends_on: [657]` set correctly.

**AC disposition:** All 5 AC items deferred to #660 per Architecture Review "Single responsibility PASS — Research deliverable only." Correct use of `research` pass-through. Architecture Review APPROVED with explicit rationale.

**Deductions:** 0
**Confidence:** .93 → PASS

[[2026-04-06]] Mon 13:11
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Research pass-through; zero Python changes; implementation deferred to #660 |
| 2 | Module docstrings | No | N/A | No Python source files created or modified |
| 3 | External attribution | No | N/A | All 7 sources are internal codebase files (no external repos or articles) |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/scribe-orchestrator-typed-contract.md` exists, all 5 required sections present, linked from task body, #660 follow-up created with correct `depends_on: [657]` |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/657-*` files found)

[[2026-04-06]] Mon 13:38
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Scribe/orchestrator boundary uses typed contract | Research doc S3-4: Option A (resolve-summary.json) specified; implementation deferred to #660 | PASS (deferred) |
| "Never interpret subagent output" rule has no exceptions | Research doc S4: carve-out removal is explicit part of implementation sketch; #660 AC5 tracks it | PASS (deferred) |
| NEEDS-INFO dispatch injection still works | Research doc S4 implementation sketch; #660 AC9 tracks end-to-end verification | PASS (deferred) |
| No regression in DR processing | #660 AC10 tracks all DR states (approved, rejected, completed, needs-info, auto-approved) | PASS (deferred) |
| Scribe remains lightweight clerk | Research doc S4: scribe only writes file, no dispatch responsibility; design constraint preserved | PASS (deferred) |

### Research Gate Checklist
- Research doc exists: .owlbear/research/scribe-orchestrator-typed-contract.md (5 sections, 7 sources)
- Follow-up task #660 created at research status with depends_on: [657], 10 AC items
- #660 references research doc; includes stale-file, graceful-degradation, and regression AC per architect guidance
- Challenge step completed: reconsider verdict, full rebuttal recorded, confidence revised .85 to .80

### Test Results
- pytest: 3572 passed, 458 failed, 19 skipped (all failures pre-existing; zero Python changes in #657 scope)
- ruff: 5 errors (all in mcp-kanban, pre-existing; no files in #657 scope)

### Architect Quality: 4/5
AC was written as implementation criteria rather than research criteria. Builder/reviewer correctly interpreted as "deferred to #660" per arch review, but explicit research-scoped AC (e.g., "research doc produced with recommendation") would have prevented the pass-through interpretation step.

### Deduction Breakdown
- Start: 1.00
- Uncommitted deliverables (3 files untracked by upstream agents): -.02
- AC quality 4/5 (above 3): no deduction
- Reviewer evidence section: present, detailed, .93 PASS: no deduction
- No test failures in task scope: no deduction
- No lint violations in task scope: no deduction

### Confidence: .98
### Action: archive
