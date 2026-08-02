---
id: 195
title: Add premise challenge step to arch-review skill
status: archived
priority: medium
created: 2026-03-29 23:08:21.445756+02:00
updated: 2026-03-30 04:28:53.252160+02:00
started: 2026-03-30 04:28:48.269760+02:00
completed: 2026-03-30 04:28:48.269760+02:00
tags:
- agent
- quality
- scope:agents
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add a premise validation step to the arch-review skill so the architect questions whether tasks should exist, not just whether AC is well-formed.

## Acceptance Criteria

- [ ] `skills/arch-review/SKILL.md` Step 3: new item 7 inserted after KISS/YAGNI (current item 6), before Pattern consistency (current item 7). Current items 7-10 renumbered to 8-11. Item 7 text: **Premise challenge** -- Should this task exist? Does the capability already exist in: (a) IDE features (built-in MCP, IntelliSense, Git integration, terminal), (b) runtime (Python stdlib, installed packages, OS utilities), (c) existing tooling (scripts/, MCP servers, kanban-md features), or (d) extensions (Copilot built-in server, VS Code extensions)? If the capability exists, block to ideation with evidence. Applies to ALL tasks including ones labeled trivial.
- [ ] `skills/arch-review/SKILL.md` self-critique checklist: new item added: Premise challenge applied -- verified capability is not already provided by environment (IDE/runtime/tooling/extensions)
- [ ] `agents/architect.agent.md` Red flags section: new bullet added: You are approving a feature addition without checking if the environment already provides it
- [ ] No functional behavior changes -- markdown/skill files only

## Architecture Notes
- Placement rationale: item 7 (after KISS/YAGNI) per research recommendation. Premise challenge is a form of YAGNI validation and groups naturally with it.
- Environment categories (IDE, runtime, tooling, extensions) must appear in the step text so architects know what to check.
- Trivial-task format: for tasks the architect considers trivial, the premise check is a one-liner: Premise validated -- no duplicate capability. But the check must still happen.

## Context
See docs/research/pipeline-quality-audit.md recommendation R2.
See docs/research/arch-review-premise-challenge.md for full research.
Sibling tasks: #194 (R1), #196 (R3), #197 (R4) -- independent, no cross-deps.

[[2026-03-30]] Mon 00:06
## Architecture Review
**Verdict:** Approve

### AC Assessment

AC1 (Step 3 item 7): Precise -- specifies exact placement, renumbering, full text, environment categories. Verifiable.
AC2 (self-critique checklist): Precise -- specifies file, section, exact text. Verifiable.
AC3 (Red flags): Precise -- specifies file, section, exact text. Verifiable.
AC4 (no functional changes): Correct scope guard. Verifiable.

### Architecture Notes
- Research is thorough (.90 confidence), grounded in Klein 2007 pre-mortem, Chesterton's fence, Du et al. 2023 anchoring cascade. No concerns.
- Placement as item 7 (after KISS/YAGNI) is the right call: premise challenge extends YAGNI validation naturally.
- Two files touched: skills/arch-review/SKILL.md and agents/architect.agent.md. Both are markdown-only edits.
- TDD not applicable: no .py files modified. Documentation-only change.
- No dependencies. Siblings #194, #196, #197 are independent.

### Changes Made
- Refined AC: replaced vague 3.10 placement with precise item 7 insertion spec
- Added explicit file targets for each AC line
- Added environment categories and trivial-task format to Architecture Notes
- Approved to todo

[[2026-03-30]] Mon 01:34
## Test-Writer Notes

[[2026-03-30]] Mon 01:34
- Non-implementation task (markdown/skill files only, no .py) - no tests applicable.
- Architecture Review confirms: TDD not applicable.
- Passing through to builder.

[[2026-03-30]] Mon 03:05
## Builder Notes
- Files changed: skills/arch-review/SKILL.md, agents/architect.agent.md
- AC1: Step 3 item 7 inserted (Premise challenge) after KISS/YAGNI; old items 7-10 renumbered to 8-11
- AC2: Self-critique checklist item added: Premise challenge applied
- AC3: Red flags bullet added to architect.agent.md
- AC4: No .py, .toml, or test files touched
- Tests: N/A (markdown-only task)
- Lint: N/A
- Commit: dcdf72a

[[2026-03-30]] Mon 03:41
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal skill/agent workflow change; no system-level API or convention change |
| 2 | Docstrings | No | N/A | No .py files modified (markdown-only task) |
| 3 | docs/sources/overview.md | Yes | Pass | Task #195 section already present with Klein 2007 and Chesterton entries |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/arch-review-premise-challenge.md exists, linked in task body Context section |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/195-* files found)

[[2026-03-30]] Mon 04:28
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Step 3 item 7 inserted | SKILL.md L87-93: Premise challenge with env categories (a-d), after KISS/YAGNI, items 8-11 renumbered | PASS |
| AC2: Self-critique checklist item | SKILL.md L248: Premise challenge applied line present | PASS |
| AC3: Red flags bullet in architect.agent.md | architect.agent.md L133: environment check bullet present | PASS |
| AC4: No functional changes | Only .md files in commit dcdf72a | PASS |

### Test Results
- pytest: 3 collection errors (pre-existing: owlbear.planner, owlbear.voice.process). No task-scoped failures.
- ruff: E902 on src (path issue), PT018 in test_necessity_check_196.py. No task-scoped violations.

### Architect Quality
- AC quality score: 5 -- precise placement spec, exact text, renumbering instructions, file targets for each AC line
- Research grounded in Klein 2007, Chesterton's fence, Du et al. 2023

### Commit Verification
- dcdf72a: docs: add premise challenge step to arch-review skill (#195, builder)

### Deduction breakdown
- -.02 missing reviewer evidence section (no ## Review Evidence in task body)
### Confidence: .98
### Action: archive
