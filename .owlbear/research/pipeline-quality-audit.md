# Pipeline Quality Audit: Why 6 Agents Missed an Obvious Redundancy

> **Owning task:** #192 — Research: pipeline quality audit
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

A GitHub MCP server entry was added to `setup.py` and `.vscode/mcp.json` (#18, #121)
despite the Copilot extension already providing it. Six pipeline agents plus the auditor
all approved this redundancy. Why did the pipeline fail as a quality gate, and what
structural changes would prevent similar blind spots?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | Task #18 trail (kanban/tasks/018-*.md) | Internal | 1.0 |
| S2 | Task #121 trail (kanban/tasks/121-*.md) | Internal | 1.0 |
| S3 | 88 archived tasks (verdict distributions) | Internal | 0.9 |
| S4 | Agent definitions (agents/*.agent.md) | Internal | 0.9 |
| S5 | Skill files (code-review, arch-review, task-verification, research-workflow) | Internal | 0.9 |
| S6 | VS Code MCP Server Guide | External | 0.8 |
| S7 | Du et al. 2023 — Multi-agent Debate (arXiv:2305.14325) | External | 0.7 |

## 3. Analysis

### 3.1 Decision Trail Reconstruction (#18 → #121)

| Agent | What it did | What it missed |
|-------|-------------|----------------|
| **Researcher** (#18) | Recommended GitHub MCP at .85 confidence. Cited S3/S6 for config format. | Never asked "does the Copilot extension already provide this?" Neither research doc mentions built-in provision. |
| **Architect** (#18) | Kept AC line: "Template includes community GitHub MCP server (if applicable)" | Accepted researcher's .85 recommendation without verifying the premise. Approved as trivially correct. |
| **Researcher** (#121) | Validated exact config, .90 confidence. Produced 95-line doc. | Entire doc validates HOW to add the server. Never asks IF it should be added. |
| **Architect** (#121) | Approved as "trivial: 3-line dict entry" | "Trivial" label suppressed scrutiny. No environment audit. |
| **Test-writer** (#121) | Wrote 6 tests — all testing the config exists | Tests verified implementation correctness, not premise validity. Working as designed. |
| **Builder** (#121) | Added 3 lines, all tests pass | Working as designed — implements AC. |
| **Reviewer** (#121) | Caught ruff E501. FAIL then PASS after fix. | Entire review focused on mechanical checks (tests pass, lint clean, assertions intact). Never questioned premise. |
| **Writer** (#121) | Updated docstrings, copilot-instructions.md | Working as designed — documents what was built. |
| **Auditor** (#121) | .90 confidence, rejected for ruff. Later would archive. | Scored AC quality 4/5. Never questioned if the feature was needed. |

**Root cause chain:** Researcher introduced unvalidated assumption → architect rubber-stamped it
→ every downstream agent verified the *implementation* of that assumption, not the assumption itself.

### 3.2 Broader Pipeline Patterns (88 archived tasks)

**Architect verdict distribution:**
- APPROVE: 52 (79%) | REFINE: 6 (9%) | BLOCK: 4 (6%) | MERGE: 4 (6%)
- 79% first-pass approval is high. The architect pushes back only on vague AC and
  duplicates — not on premise validity.

**Auditor confidence clustering:**
- .97 = 34 tasks (59%) | .95 = 12 (21%) | Other = 12 (20%)
- 80% of scores cluster in .95–.97. This is not meaningful differentiation — it's a
  default score with minor perturbation. Contrast: only 1 task scored below .90.

**Reviewer pattern:** Reviewer FAIL count (33) is healthy — it catches mechanical issues
well (lint, test integrity, assertion specificity). But 0 reviewer rejections cite
"unnecessary feature" or "premise invalid" — the reviewer only checks *how*, never *why*.

### 3.3 Structural Gaps Identified

| Gap | Affects | Evidence |
|-----|---------|----------|
| **No environment audit** | Researcher, Architect | Neither the research checklist (7 items) nor the arch-review skill (9 checks) asks "does the runtime/IDE already provide this?" |
| **Anchoring cascade** | All agents | Each agent inherits upstream assumptions. Du et al. (S7) show multi-agent debate reduces hallucination only when agents reason independently — OwlBear's pipeline is sequential, not adversarial. |
| **"Trivial" label suppresses scrutiny** | Architect, Reviewer, Auditor | Architect labeled #121 "trivial" → test-writer/builder/reviewer all treated it with minimal scrutiny. The pipeline has no floor on review depth. |
| **No "should this exist?" checkpoint** | Reviewer | code-review skill checks security, test quality, assertion integrity, AC compliance — but never "should this AC have been written?" |
| **Confidence scoring is performative** | Auditor | 59% of scores = .97. No calibration. No recalibration mechanism. No historical comparison. |
| **Commission bias** | All agents | Every check is "did you do the right thing?" (errors of commission). No check asks "should you have done nothing?" (errors of omission-in-reverse). |

### 3.4 Error Type Blindness

| Error Type | Pipeline Coverage | Evidence |
|------------|------------------|----------|
| Wrong implementation | Strong | Reviewer catches lint, test integrity, assertion specificity |
| Missing implementation | Moderate | Auditor runs full suite, catches regressions |
| Unnecessary addition | None | No agent is instructed to question whether work should exist |
| Wrong premise | None | Researcher validates feasibility, not necessity against environment |

## 4. Recommendations (.80 confidence)

Four structural changes, ordered by expected impact:

**R1. Add "Environment Audit" to Research Checklist** — New mandatory item in
research-workflow skill: "Is this capability already provided by the IDE, runtime,
or existing tooling? Check VS Code extensions, built-in features, and installed
packages before recommending additions." This directly prevents the #121 class of error.

**R2. Add "Premise Challenge" to Architect Review** — New step in arch-review skill
Step 3: "Question the premise: should this task exist? Check if the proposed change
duplicates existing environment capabilities, IDE features, or installed tools."
The architect is the last gate before development begins — it must validate *why*, not
just *how*.

**R3. Add "Necessity Check" to Reviewer Critical Checks** — New item in code-review
skill Pass 1 (§6.0 currently): "For feature additions, verify the feature doesn't
duplicate IDE-provided or environment-provided capabilities." The reviewer already
has an adversarial mandate — extend it to premise validity.

**R4. Calibrate Auditor Confidence Scoring** — Current scoring is meaningless (59% = .97).
Add scoring rubric to task-verification skill with explicit deduction criteria:
- -.02 for each AC line with no specific evidence
- -.05 for ruff/lint issues found
- -.03 for AC quality score <= 3
- Start from 1.0 and deduct, rather than picking from a narrow range.

**Not recommended:** Adding more agents or review stages. The pipeline has enough
checkpoints — the problem is that all checkpoints verify the same dimension
(implementation quality) and none verify necessity.

## 5. Follow-up Tasks

See task body for executed `kanban-md create` commands.
