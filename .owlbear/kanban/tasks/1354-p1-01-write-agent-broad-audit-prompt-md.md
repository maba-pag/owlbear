---
id: 1354
title: 'P1-01: Write agent-broad-audit.prompt.md'
status: in-progress
priority: needed
created: 2026-05-04T21:22:32.017764+00:00
updated: 2026-05-05T09:56:21.582507+00:00
tags:
- phase-1
- scope:prompts
- prompt
- snr
parent: 1353
depends_on: []
blocked: true
block_reason: postponed
claimed_at:
archival_reason:
archival_refs: []
---

## AC (from Brief AC1 + AC3 broad side)

**In scope:**
- Create `share/prompts/agent-broad-audit.prompt.md` that replaces `.owlbear/prompts/agent-audit.prompt.md`
- Preserve all existing audit dimensions (D1-D5, D7) with finding-loop interaction model
- Strengthen D6 (SNR): scan for 6-category noise-taxonomy patterns, emit attention flags, highlight universal files (`applyTo: **`) as highest-leverage
- Add end-of-run ranked report: dual-axis scoring (noise density relative to category peers × context-budget weight)
- Inline the shared 6-category noise taxonomy (matching definitions used in #1355)
- Delete the old `.owlbear/prompts/agent-audit.prompt.md` after new prompt is verified

**Out of scope:**
- Per-sentence compression proposals (that's the deep-dive's job)
- Automated pipeline between broad and deep-dive
- Actually running the audit on all files

**6-category noise taxonomy (inline in prompt):**
1. Verbose prose wrappers
2. Over-specification
3. Redundant conditionals
4. Prescriptive message templates
5. Cross-reference ceremony
6. Stale institutional memory

**Key input:** Read `.owlbear/prompts/agent-audit.prompt.md` (existing, being replaced) to understand current D1-D7 structure.

**Brief:** see parent #1353 → `.owlbear/briefs/draft-skill-snr/brief.md`
[[2026-05-05]]
## Test-Writer Notes
- Non-implementation task (tagged `prompt`) — no tests applicable.
- AC describes creating `share/prompts/agent-broad-audit.prompt.md` and deleting `.owlbear/prompts/agent-audit.prompt.md`. These are markdown prompt files with no testable Python interfaces.
- Passing through to builder.
[[2026-05-05]]
## Builder Notes
- Non-implementation task confirmed from `## Test-Writer Notes` in task body.
- No code changes applied.
- No tests or lint run (not applicable for prompt pass-through).
- Passing through to review.
[[2026-05-05]]
## Review Evidence
### Test Results
- pytest: skipped
- quality-runner: skipped. Prompt-only artifact task; no task test file or executable module in scope. Review based on direct artifact inspection.

### Lint: skipped
- Ruff not applicable. No Python source or task test file in scope.

### Coverage: skipped
- No executable module changed in scope.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped: no `TestFromAC_*` classes; task scope is a `.prompt.md` replacement.

#### Security Review
- No security issues found in the inspected existing artifact. Not the gating concern here.

#### Test Integrity
- N/A: no task tests exist, and builder reported no test changes.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | No task tests exist for this prompt-only task |
| Negative/error-path coverage | N/A | No task tests exist for this prompt-only task |
| Manual mutation reasoning | N/A | No task tests exist for this prompt-only task |
| Test independence | N/A | No task tests exist for this prompt-only task |
| Descriptive test names | N/A | No task tests exist for this prompt-only task |

#### Data Safety
- No data-safety issue identified from current repo state. Primary failure is missing implementation.

#### Implementation-Aware Gaps
- Task AC requires `share/prompts/agent-broad-audit.prompt.md` (`.owlbear/kanban/tasks/1354-p1-01-write-agent-broad-audit-prompt-md.md:25`), but workspace file search for that exact path returned no file.
- Task AC requires deleting `.owlbear/prompts/agent-audit.prompt.md` (`.owlbear/kanban/tasks/1354-p1-01-write-agent-broad-audit-prompt-md.md:30`), but the legacy prompt still exists (`.owlbear/prompts/agent-audit.prompt.md:5`) and remains indexed in `.owlbear/doc-index.md:58`.
- Builder notes explicitly state `No code changes applied.` and `Passing through to review.` (`.owlbear/kanban/tasks/1354-p1-01-write-agent-broad-audit-prompt-md.md:56`, `:58`), which does not satisfy a file-creation/file-replacement task.
- Live workspace references still target `agent-audit.prompt.md`, including `tests/test_path_neutrality_1285.py:48` and `tests/test_mcp_memory_1266.py:852`; replacement work is incomplete even before deletion.

#### Necessity Check
- N/A: no new dependency, integration, or external tool added.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The old prompt is still part of active repo references. When implementing the replacement, reconcile live references before deleting the legacy file.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Create `share/prompts/agent-broad-audit.prompt.md` that replaces `.owlbear/prompts/agent-audit.prompt.md` | Required target file is absent; legacy prompt still present | N/A | FAIL |
| Preserve all existing audit dimensions (D1-D5, D7) with finding-loop interaction model | No replacement file exists to inspect for retained dimensions or interaction flow | N/A | FAIL |
| Strengthen D6 (SNR): scan for 6-category noise-taxonomy patterns, emit attention flags, highlight universal files (`applyTo: **`) as highest-leverage | No replacement file exists to inspect for D6 behavior | N/A | FAIL |
| Add end-of-run ranked report: dual-axis scoring (noise density relative to category peers × context-budget weight) | No replacement file exists to inspect for ranked-report instructions | N/A | FAIL |
| Inline the shared 6-category noise taxonomy (matching definitions used in #1355) | No replacement file exists to inspect for taxonomy text | N/A | FAIL |
| Delete the old `.owlbear/prompts/agent-audit.prompt.md` after new prompt is verified | Legacy prompt still exists and remains indexed/referenced | N/A | FAIL |

### Confidence: 0.18
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Create the replacement broad-audit prompt and implement the AC-defined broad-audit behavior | share/prompts/agent-broad-audit.prompt.md | Implementation-Aware Gaps bullets 1-3; AC Compliance rows 1-5 |
| 2 | builder | Reconcile active references to the legacy prompt, then remove the retired `.owlbear` prompt only after the replacement is in place | .owlbear/prompts/agent-audit.prompt.md, .owlbear/doc-index.md, tests/test_path_neutrality_1285.py, tests/test_mcp_memory_1266.py | Implementation-Aware Gaps bullets 2 and 4; AC Compliance row 6 |