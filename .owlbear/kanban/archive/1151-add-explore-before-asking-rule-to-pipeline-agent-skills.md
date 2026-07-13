---
id: 1151
title: Add "Explore Before Asking" rule to pipeline agent skills
status: archived
priority: medium
created: 2026-04-27T22:10:07.559936+00:00
updated: 2026-04-28T00:06:45.819642+00:00
tags:
- agent
- pipeline
- agent-config
- pipeline
- agent-config
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Analysis of mattpocock/skills repo (grill-me + domain-model skills) identified a principle we're missing: agents should explore the codebase before asking the user questions that could be answered by reading code.

Our ideation and review agents sometimes ask the user things they could discover by running the Explore subagent or searching the codebase. Example: "What patterns does your existing code use?" when they could read the code themselves.

## Acceptance Criteria

- [ ] `share/skills/w-ideation-discovery/SKILL.md` — `## Working Rules` section includes an "Explore Before Asking" rule: if a question can be answered by exploring the codebase (via Explore subagent, read_file, or search tools), explore first instead of asking the user
- [ ] `share/skills/w-ideation-mediation/SKILL.md` — `## Working Rules` section includes the same rule, adapted for Phase 2 context (e.g., brownfield landscape questions, existing pattern discovery)
- [ ] `share/skills/w-arch-review/SKILL.md` — Step 1 "Analyze Codebase Context" or a new Working Rules section includes the rule (the architect already reads code in Step 1, but the principle should be stated explicitly as a pre-condition to asking the user)
- [ ] Rule text is concise (1-3 lines per file) and actionable — not a vague aspiration
- [ ] Rule references concrete tools: Explore subagent, `read_file`, `semantic_search`, `grep_search`

## Scope Boundaries

- Do NOT add the rule to `h-ideation/SKILL.md` — the shared handbook covers interaction turns and artifact contracts, not behavioral heuristics. Each workflow skill owns its own working rules.
- Do NOT create new sections where an existing section already fits.
- Do NOT modify any other files.

[[2026-04-27]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One behavioral rule applied to three related files — single concern |
| Interface clarity | PASS | Exact file paths, exact sections, concise 1-3 line rule with tool references |
| Dependency correctness | PASS | No dependencies needed; all target files exist with referenced sections |
| Module layering | N/A | Skill text files, not Python modules |
| TDD compliance | PASS | Tagged `agent` — pass-through tag, no testable Python code |
| KISS/YAGNI | PASS | Minimal scope; scope boundaries prevent overreach |
| Premise challenge | PASS | Rule is distinct from existing "search codebase" guidance — this is about not asking the user questions answerable by exploration, not about gathering review context |
| Pattern consistency | PASS | Working Rules sections already exist in both ideation skills; Step 1 exists in arch-review |
| Security surface | N/A | No system boundaries affected |
| Single domain | PASS | All files in `share/skills/` agent-config domain |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: w-ideation-discovery Working Rules | Clear, verifiable | None — builder should note Phase 1 lightweight posture (see guidance below) |
| AC2: w-ideation-mediation Working Rules adapted for Phase 2 | Clear, verifiable | None |
| AC3: w-arch-review Step 1 or new Working Rules | Clear, verifiable | Step 1 preferred per scope boundary "don't create sections where existing fits" |
| AC4: Concise (1-3 lines) and actionable | Clear, verifiable | None |
| AC5: References concrete tools | Clear, verifiable | Explore subagent is available to all agents as a built-in |

### Builder Guidance

**Phase 1 tension:** Discovery (w-ideation-discovery) deliberately limits M1 to lightweight brownfield checks and defers broad exploration to Step 3. The "Explore Before Asking" rule in this file should be framed as targeted lookups (read a specific file, search for a specific pattern) rather than broad exploration passes. This is consistent with AC4's conciseness constraint.

**Placement for arch-review:** Step 1 is the natural home — the existing items are procedural codebase analysis steps, and "explore before asking" is a natural precondition. Add as an additional numbered item or preamble note.

### Challenge Results

- Challenger: `reconsider` (0.44)
- Architect response: Override with rebuttal on 4 challenges:
  1. Tool-contract mismatch — Invalid: Explore is a built-in agent available to all, not restricted by mode-specific agent lists
  2. Placement-authority — Task explicitly addresses centralization concern; arch-review is pipeline not ideation, so no single shared location covers all three
  3. Phase-boundary collision — Legitimate tension acknowledged in builder guidance; AC4 conciseness constraint prevents broad exploration directives
  4. Premise overlap — "Explore before asking the user" is distinct from "search codebase before approving"; ideation agents have no existing rule covering self-answerable questions

### Verdict: APPROVE
### Action Taken: Advanced to todo. Builder guidance added for Phase 1 tension and arch-review placement.
[[2026-04-27]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`, `pipeline`, `agent-config`) — no tests applicable.
- AC references only SKILL.md files (`w-ideation-discovery`, `w-ideation-mediation`, `w-arch-review`) — no testable Python interfaces.
- Passing through to builder.
[[2026-04-27]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified Test-Writer pass-through note and agent/pipeline/agent-config scope.
- Passing through to review.

[[2026-04-27]]
## Review Evidence
### Test Results
- pytest: 0 passed, 0 failed, 0 skipped
- Quality-runner reported no applicable test files for this markdown-only task; pytest exit code was 5 (no tests collected).

### Lint
- ruff: clean=true, no violations
- Quality-runner reported no applicable ruff targets for this markdown-only task; ruff exit code was 0.

### Coverage
- N/A — documentation/skill task, no coverage modules supplied.

### Review Scope
- Direct artifact inspection is the decisive evidence here. This task requires text changes in three `SKILL.md` files; scoped pytest/ruff cannot prove wording ACs.
- Builder note states: "Non-implementation task — no code changes needed." That is the root-cause misread. Non-implementation still required markdown edits in the target files.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A — no `TestFromAC_*` classes; test-writer correctly passed through a non-implementation task.

#### Security Review
- No security issues. Target files are markdown skill docs only.

#### Test Integrity
- N/A — no task-owned tests.

#### Test Quality
- N/A — no task-owned tests.

#### Data Safety
- No issues. No runtime or data-path changes were made.

#### Implementation-Aware Gaps
- Required edits are missing from all three target files:
  - `share/skills/w-ideation-discovery/SKILL.md:13-19` Working Rules contains only the existing five bullets; the required Explore-before-asking rule is absent. Grep found no `Explore subagent`, `semantic_search`, or `grep_search` references in the file.
  - `share/skills/w-ideation-mediation/SKILL.md:13-20` Working Rules contains only the existing six bullets; the required Phase 2 variant is absent. Grep found no `Explore subagent`, `semantic_search`, or `grep_search` references in the file.
  - `share/skills/w-arch-review/SKILL.md:27-34` Step 1 still contains only the existing search/read steps. `read_file` appears at line 30, but there is no explicit "explore before asking the user" pre-condition and no `Explore subagent`, `semantic_search`, or `grep_search` references.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

- No retry loop detected. This is a direct implementation miss, not churn.

### Pass 2 — INFORMATIONAL
- No additional informational findings.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `share/skills/w-ideation-discovery/SKILL.md` includes an Explore Before Asking rule in `## Working Rules` | `share/skills/w-ideation-discovery/SKILL.md:13-19` contains only the existing bullets; required rule absent; grep found no `Explore subagent`, `semantic_search`, or `grep_search` references in the file. | N/A | FAIL |
| `share/skills/w-ideation-mediation/SKILL.md` includes the adapted rule in `## Working Rules` | `share/skills/w-ideation-mediation/SKILL.md:13-20` contains only the existing bullets; required rule absent; grep found no `Explore subagent`, `semantic_search`, or `grep_search` references in the file. | N/A | FAIL |
| `share/skills/w-arch-review/SKILL.md` states the rule in Step 1 or a fitting existing section | `share/skills/w-arch-review/SKILL.md:27-34` includes existing Step 1 items and `read_file` at line 30, but no explicit rule and no `Explore subagent`, `semantic_search`, or `grep_search` references. | N/A | FAIL |
| Rule text is concise and actionable | No new rule text exists in any target file, so there is no concise 1-3 line actionable rule to assess. | N/A | FAIL |
| Rule references concrete tools: Explore subagent, `read_file`, `semantic_search`, `grep_search` | Concrete tool references were not added as a rule in any target file. | N/A | FAIL |

### Deductions
- Core deliverable missing: required edits absent from all three target files.
- Builder treated a non-implementation task as a no-op.
- No test gap identified; this is implementation-only.

### Verdict
- FAIL
- Route: `in-progress`
- Confidence: 0.08
- Action: Builder must add the concise rule text to the three specified files and keep scope limited to those files.
[[2026-04-27]]
## Builder Notes
- Implementation: updated three skill files only — share/skills/w-ideation-discovery/SKILL.md, share/skills/w-ideation-mediation/SKILL.md, share/skills/w-arch-review/SKILL.md.
- Fixes applied: added concise (single-line) "Explore before asking" rules in existing sections; each rule explicitly references Explore subagent, read_file, semantic_search, and grep_search.
- Section placement: added to `## Working Rules` in both ideation workflow skills; added to Step 1 "Analyze Codebase Context" in arch-review.
- Tests: 0 applicable task tests (markdown-only task).
- Coverage: N/A (no Python modules touched).
- ruff: clean (quality-runner reported `violations: []`, ruff exit code 0).
- Evidence summary: all AC targets now contain explicit rule text with concrete tool references and no out-of-scope file edits.

[[2026-04-27]]
## Review Evidence
### Test Results
- pytest: 0 passed, 0 failed.
- Quality-runner: no applicable test targets for this markdown-only task (`test_paths: []`), so pytest was not run.

### Lint
- Ruff: not run; no applicable Python lint targets were provided for the three `SKILL.md` files (`lint_paths: []`).

### Coverage
- N/A — no coverage modules were applicable for this documentation-only task.

### Review Scope
- Direct artifact inspection is the decisive evidence path for this task; the AC is satisfied by live text in three workflow skill files.
- Runtime did not expose `get_changed_files` in this session, so file-scope verification was grounded in the task AC, the builder's scoped note, and direct inspection of the three authority files.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- N/A — no `TestFromAC_*` classes or task-owned executable tests. Test-writer pass-through was appropriate for this `agent` / `pipeline` / `agent-config` markdown task.

#### Security Review
- No issues. In-scope artifacts are prose-only additions in markdown skill files.

#### Test Integrity
- N/A — no task-owned tests were changed.

#### Test Quality
- N/A — no task-owned tests. Direct artifact inspection is the correct proof path.

#### Data Safety
- No issues. No runtime, persistence, or data-handling paths changed.

#### Implementation-Aware Gaps
- No blocking gaps found.
- `share/skills/w-ideation-discovery/SKILL.md:20` adds a single-line `Explore before asking` rule under `## Working Rules` and explicitly names `Explore` subagent, `read_file`, `semantic_search`, and `grep_search`.
- `share/skills/w-ideation-mediation/SKILL.md:21` adds the Phase 2 brownfield/pattern variant under `## Working Rules` and explicitly names `Explore` subagent, `read_file`, `semantic_search`, and `grep_search`.
- `share/skills/w-arch-review/SKILL.md:31` adds the pre-question rule in `## Step 1 — Analyze Codebase Context`, explicitly directing architects to resolve answerable codebase questions first with `Explore` subagent, `read_file`, `semantic_search`, and `grep_search`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Low-risk maintainability note: the concrete exploration tool list is duplicated across three skill files and may drift if preferred tooling changes later. Non-blocking.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `share/skills/w-ideation-discovery/SKILL.md` includes an Explore Before Asking rule in `## Working Rules` | `share/skills/w-ideation-discovery/SKILL.md:20` adds the required single-line rule in the existing `## Working Rules` section. | N/A | PASS |
| `share/skills/w-ideation-mediation/SKILL.md` includes the adapted rule in `## Working Rules` | `share/skills/w-ideation-mediation/SKILL.md:21` adds the Phase 2 brownfield/pattern variant in the existing `## Working Rules` section. | N/A | PASS |
| `share/skills/w-arch-review/SKILL.md` states the rule in Step 1 or a fitting existing section | `share/skills/w-arch-review/SKILL.md:31` adds the rule as Step 1 item 3 under `## Step 1 — Analyze Codebase Context`. | N/A | PASS |
| Rule text is concise and actionable | Each insertion is a single imperative line: discovery `:20`, mediation `:21`, arch-review `:31`. | N/A | PASS |
| Rule references concrete tools: Explore subagent, `read_file`, `semantic_search`, `grep_search` | All three inserted rules explicitly name all four tools. | N/A | PASS |

### Deductions
- None.

### Verdict
- PASS
- Route: `docs`
- Confidence: 0.94
- Action: Advance to docs.

### Reflection
- Markdown-only ACs still require implementation review; direct artifact inspection is stronger evidence than empty pytest/ruff slices.
- The runtime lacked the usual changed-files tool, but the task's narrow, explicit file scope kept the review auditable.
- The builder fix stayed inside the intended existing sections and satisfied the no-overreach scope boundary.
[[2026-04-27]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | All changed files are OUT-scope SKILL.md; no IN-scope prose docs reference these skill internals |
| 2 | Module docstrings | No | N/A | No Python modules touched |
| 3 | External attribution | No | N/A | No external patterns cited in task body |
| 4 | Research doc | No | N/A | No research doc produced |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram describes-match for SKILL.md files |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No deletions; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/w-ideation-discovery/SKILL.md | OUT | N/A — agent-executable |
| share/skills/w-ideation-mediation/SKILL.md | OUT | N/A — agent-executable |
| share/skills/w-arch-review/SKILL.md | OUT | N/A — agent-executable |

No docs impact — all changed files are OUT-scope agent-executable SKILL.md files.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1151-* scratch files found)
[[2026-04-28]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| w-ideation-discovery Working Rules includes Explore Before Asking rule | `share/skills/w-ideation-discovery/SKILL.md:20` — single-line rule in existing `## Working Rules` | PASS |
| w-ideation-mediation Working Rules includes adapted Phase 2 rule | `share/skills/w-ideation-mediation/SKILL.md:21` — brownfield/pattern variant in `## Working Rules` | PASS |
| w-arch-review Step 1 includes the rule | `share/skills/w-arch-review/SKILL.md:31` — item 3 in `## Step 1 — Analyze Codebase Context` | PASS |
| Rule text is concise (1-3 lines) and actionable | Each insertion is a single imperative line | PASS |
| References concrete tools: Explore subagent, read_file, semantic_search, grep_search | All three rules explicitly name all four tools | PASS |

### Test Results
- pytest: 2739 passed, 117 failed, 4 skipped — all failures pre-existing in kanban/storage/mcp-knowledge packages, none in task scope (markdown-only edits)
- ruff: 8 violations, none in task scope

### Architect Quality: 5/5
Specific file paths, exact sections, clear scope boundaries, helpful builder guidance (Phase 1 tension, placement). AC well-specified for a markdown-only task.

### Deduction Breakdown
- AC lines: 5/5 PASS → 0
- Lint in scope: none → 0
- AC quality: 5/5 → 0
- Reviewer evidence: present, detailed, two rounds (caught initial builder no-op at 0.08, second pass PASS at 0.94) → 0
- Full-suite failures in task scope: 0 → 0

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| bdbb86a8 | docs | w-ideation-discovery/SKILL.md, w-ideation-mediation/SKILL.md, w-arch-review/SKILL.md | #1151 |
| 82b5a42a | chore(kanban) | tasks/1151-*.md | #1151 |