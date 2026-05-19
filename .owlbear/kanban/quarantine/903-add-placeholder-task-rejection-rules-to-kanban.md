---
id: 903
title: Add placeholder-task rejection rules to kanban-planner.agent.md
status: archived
priority: important
created: 2026-03-21T14:47:33.3987665+01:00
updated: 2026-03-22T00:19:00.5793792+01:00
started: 2026-03-22T00:18:55.5821163+01:00
completed: 2026-03-22T00:18:55.5821163+01:00
tags:
    - agent
    - docs
    - scope:copilot
    - type:docs
class: standard
---

Source: docs/research/planner-placeholder-guardrails.md

## Context

Add canonical placeholder-task rejection rules to .github/agents/kanban-planner.agent.md.
See docs/research/planner-placeholder-guardrails.md and docs/research/planner-agent-placeholder-rejection-rules.md.

## Acceptance Criteria

- [ ] .github/agents/kanban-planner.agent.md critical_rules explicitly reject planned task titles matching TEMP-*.
- [ ] .github/agents/kanban-planner.agent.md critical_rules explicitly reject planned task bodies that are empty after frontmatter or contain only placeholder text with no concrete scope or acceptance criteria.
- [ ] The same critical_rules text states that when either placeholder condition is hit, the planner must refine the task or stop instead of emitting kanban-md create output or leaving a placeholder board artifact.
- [ ] .github/agents/kanban-planner.agent.md red flags explicitly call out TEMP-* titles and empty or unscoped bodies as stop-and-reassess conditions before output.
- [ ] At least one red flag or example uses TEMP-planner-test as the explicit rejected pattern.
- [ ] File scope stays limited to .github/agents/kanban-planner.agent.md.

[[2026-03-21]] Sat 15:23

## Research

- Doc: docs/research/planner-agent-placeholder-rejection-rules.md
- Verified scope stays limited to .github/agents/kanban-planner.agent.md; task #904 already covers the task-decomposition skill mirror.
- Recommendation (.94): keep #903 agent-only, put the hard prohibition in critical_rules, and repeat the failure mode in red flags.
- Required rejection contract:
  - reject titles starting with TEMP-
  - reject bodies empty after frontmatter or containing only placeholder text with no concrete scope or acceptance criteria
  - refine the task or stop instead of emitting placeholder board artifacts or kanban-md create output
  - use TEMP-planner-test as the explicit rejected example
- Attribution logged in docs/sources/overview.md.
- Follow-up task commands executed: none. The action items already exist as #903 and #904, so creating duplicates would violate the existing split from docs/research/planner-placeholder-guardrails.md.

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| .github/agents/kanban-planner.agent.md critical_rules explicitly reject planned task titles matching TEMP-*. | Verifiable and matches the agent-specific research recommendation to put the hard ban in critical_rules rather than only in boundaries. The current file has no TEMP-* rule today. | Keep. |
| .github/agents/kanban-planner.agent.md critical_rules explicitly reject planned task bodies that are empty after frontmatter or contain only placeholder text with no concrete scope or acceptance criteria. | Verifiable and aligned with the existing adjacent red flag for bodies that are empty or only say implement this; the refined AC makes the placeholder-body class explicit. | Keep. |
| The same critical_rules text states that when either placeholder condition is hit, the planner must refine the task or stop instead of emitting kanban-md create output or leaving a placeholder board artifact. | Verifiable control-flow requirement; without this, the builder could add passive prose instead of a binding rejection contract. | Keep. |
| .github/agents/kanban-planner.agent.md red flags explicitly call out TEMP-* titles and empty or unscoped bodies as stop-and-reassess conditions before output. | Verifiable and matches the current file structure where critical_rules hold hard constraints and red flags hold self-check triggers. | Keep. |
| At least one red flag or example uses TEMP-planner-test as the explicit rejected pattern. | Verifiable example anchored to the real placeholder artifact already documented in #855 and docs/research/planner-temp-task-hygiene.md. | Keep. |
| File scope stays limited to .github/agents/kanban-planner.agent.md. | Correct scope guard and consistent with the existing split between canonical agent rule (#903) and mirrored skill rule (#904). | Keep. |

### Architecture Notes

- Single domain verified: this is one agent-config file in .github/agents/, not shared instructions, skill work, or runtime application code.
- Existing kanban-planner guidance already separates hard constraints in critical_rules from self-check triggers in red flags; the placeholder rule should follow that structure instead of living only in boundaries.
- Current kanban-planner red flags already treat a body that is empty or only says implement this as invalid. The new task should strengthen that adjacent pattern with explicit TEMP-* and refine-or-stop wording, not invent a new section or second canonical source.
- Verified split: docs/research/planner-placeholder-guardrails.md and docs/research/planner-agent-placeholder-rejection-rules.md keep #903 agent-only, while #904 remains the task-decomposition skill mirror and already depends on #903.
- TDD pairing: not required. This is a markdown-only agent-config task and board precedent treats type:docs / scope:copilot file edits as non-implementation work with no RED predecessor.
- Security surface and failure mode map: not applicable; no new runtime codepaths or external boundaries are introduced.

### Changes Made

- Claimed #903 as architect-903.
- Rewrote the task body with explicit critical_rules placement, explicit red flags reinforcement, and explicit refine-or-stop behavior.
- Verified docs/research/planner-placeholder-guardrails.md, docs/research/planner-agent-placeholder-rejection-rules.md, and the current kanban-planner agent file before approval.
- Approved #903 for todo.

### Dependencies

- Verified: #904 exists as the mirrored task-decomposition skill follow-up and already depends on #903.
- Verified: no RED-test predecessor is required for this docs-only agent-config task.
- Added/Removed: none.

[[2026-03-21]] Sat 17:13

## Test-Writer Notes

Non-implementation task (tagged docs, type:docs, scope:copilot) - markdown-only change to .github/agents/kanban-planner.agent.md. Architecture Review explicitly states TDD pairing not required. AC forbids .py, src/, and tests/ modifications. Passing through to builder.

[[2026-03-21]] Sat 17:52

## Builder Notes

- Files changed: .github/agents/kanban-planner.agent.md
- Changes: Added Never emit placeholder tasks critical_rule (TEMP-* title + empty/placeholder body refine or stop); added two new red flag bullets with TEMP-planner-test example
- Tests: N/A (docs-only task, no tests required per Architecture Review)
- Lint: N/A (markdown file)
- Evidence: All 6 AC lines verified by direct file inspection

[[2026-03-21]] Sat 23:16

## Review Evidence

## Review: #903 - Add placeholder-task rejection rules to kanban-planner.agent.md

### Test Results

- `uv run pytest tests/test_agent_definitions.py tests/test_agent_def.py -q --tb=short` -> 96 passed, 0 failed.
- AC text checker (inline Python over `.github/agents/kanban-planner.agent.md`) -> `ac_text_checks=PASS`, `missing=none`.
- Broader sanity run including `tests/test_agent_registry.py` had 5 unrelated failures tied to separate role-policy work; not in #903 scope.

### Lint Results

- `uv run ruff check tests/test_agent_definitions.py tests/test_agent_def.py` -> All checks passed.

### Coverage

- N/A (docs-only task, single markdown agent file).

### Pass 1 - CRITICAL

#### Security Review

- No security issues found (policy-text change only, no runtime code path changes).

#### Test Integrity

- No `TestFromAC_*` classes were created for #903 (docs-only task; TDD not required in prior notes).

#### Test Quality

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | AC checker verifies exact required phrases for placeholder-title/body rejection and refine/stop behavior. |
| Negative/error paths | ADEQUATE | Verifies both critical_rules contract and red-flag stop conditions. |
| Mutation reasoning | STRONG | Removing/weakening required phrases fails checker immediately. |
| Test independence | STRONG | Pure file-text assertions plus deterministic pytest slice. |
| Descriptive names | ADEQUATE | Checker keys map directly to AC clauses. |

#### Data Safety

- No data-safety issues found.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Reject TEMP-* titles in critical_rules | `.github/agents/kanban-planner.agent.md:59` includes `title starts with \`TEMP-\`` | AC checker `critical_temp_title` | PASS |
| Reject empty/placeholder bodies in critical_rules | `.github/agents/kanban-planner.agent.md:59` includes body-placeholder rejection clause | AC checker `critical_placeholder_body` | PASS |
| Require refine/stop and forbid placeholder artifacts/create output | `.github/agents/kanban-planner.agent.md:59` includes `refine the task or stop`, no-create, no-artifact text | AC checker `critical_refine_or_stop`, `critical_no_create`, `critical_no_placeholder_artifact` | PASS |
| Red flags call out TEMP-* and unscoped placeholder bodies | `.github/agents/kanban-planner.agent.md:132` and `.github/agents/kanban-planner.agent.md:133` | AC checker `redflag_temp`, `redflag_placeholder_body` | PASS |
| Uses explicit TEMP-planner-test rejected pattern | Appears in critical_rules example and red-flag bullet (`.github/agents/kanban-planner.agent.md:59`, `.github/agents/kanban-planner.agent.md:132`) | AC checker + grep evidence | PASS |
| Scope limited to this file | `git show --name-only --pretty=oneline 547d3cc` lists only `.github/agents/kanban-planner.agent.md` | Commit-scope verification | PASS |

### Verdict: PASS

- Confidence: .94

### Action Taken

- Moving #903 from `review` -> `docs`.

[[2026-03-21]] Sat 23:48

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Agent-internal guardrail only; no project-level behavior, API, or convention change |
| 2 | Docstrings complete | No | N/A | No Python files changed; markdown-only task |
| 3 | sources/overview.md | Yes | Updated | Task body claimed attribution was logged but entries were absent; added Task #903 section with GitHub Docs (issue forms + issue templates) and GitLab Docs (description templates) as architecture-idea priors |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/planner-agent-placeholder-rejection-rules.md exists and is referenced in task body; #904 (skill mirror) exists as follow-up |

### Files Updated

- docs/sources/overview.md (added Task #903 attribution section)

### Scratch Files Cleaned

- docs/scratch/903-architect-append.err
- docs/scratch/903-architect-append.out
- docs/scratch/903-tw-notes.tmp

[[2026-03-22]] Sun 00:18

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| critical_rules reject TEMP-* titles | L59: `title starts with TEMP-` (e.g., TEMP-planner-test) | PASS |
| critical_rules reject empty/placeholder bodies | L59: `body is empty after frontmatter or contains only placeholder text` | PASS |
| critical_rules: refine or stop, no create, no artifact | L59: `refine the task or stop -- do not emit a kanban-md create command and do not leave a placeholder board artifact` | PASS |
| red flags call out TEMP-* and unscoped bodies | L132-133: two new red flag bullets with stop-and-refine wording | PASS |
| TEMP-planner-test as explicit rejected pattern | L59 and L132 both use `TEMP-planner-test` example | PASS |
| File scope limited to kanban-planner.agent.md | Commit 547d3cc touches only .github/agents/kanban-planner.agent.md | PASS |

### Test Results

- pytest: 3746 passed, 102 failed (all pre-existing: numpy compat, bootstrap unpacking, integration regressions -- none related to #903)
- ruff: N/A (markdown-only task)

### Upstream Commit Verification

- Builder commit 547d3cc: .github/agents/kanban-planner.agent.md only -- correct scope
- Writer docs/sources/overview.md update: uncommitted (upstream gap, not blocking)

### Confidence: .97

### Action: archive
