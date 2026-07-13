---
id: 498
title: Add test-writer fallback for unrecognized non-impl tasks
status: archived
priority: medium
created: 2026-03-31 09:01:15.812724+02:00
updated: 2026-04-01 12:25:53.742129+02:00
started: 2026-04-01 12:25:53.244791+02:00
completed: 2026-04-01 12:25:53.244791+02:00
tags:
- scope:agents
- ' quality'
- ' type:config'
- ' agent'
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

When the test-writer encounters a task with no testable Python in the AC and the task doesn't match non-impl pass-through tags, it has no documented recovery path. Add a content-based heuristic fallback (Step 2a) so the test-writer either auto-detects "nothing to test" and passes through with a warning, or escalates with a clear next actor.

## Acceptance Criteria

- [ ] `skills/tdd-red/SKILL.md`: Add **Step 2a — Non-impl fallback check** between Step 2 and Step 3 with this logic:
  1. If Step 2 found testable interfaces: proceed to Step 3 (no change)
  2. Scan AC for Python implementation intent — keywords: `implement`, `function`, `method`, `class`, `module`, `src/`, `packages/`, `.py`, `import`, `endpoint`, `API`
  3. If implementation intent found: proceed to Step 3 (new module RED phase, ImportError tests expected)
  4. If NO intent AND AC references only non-Python files (`.agent.md`, `SKILL.md`, `.instructions.md`, `.yml`, `.yaml`, `.json`, `.md`, `.prompt.md`): heuristic pass-through with warning note (see exact format in AC4)
  5. If ambiguous (neither clear impl nor clear non-impl): default to pass-through with strong warning; escalate to a decision request targeting the architect only when AC content is too ambiguous to determine whether the builder needs to produce code or config
- [ ] `agents/test-writer.agent.md`: Add boundary rule in `<boundaries>` section: "If the AC describes non-code deliverables only (agent files, skill files, config YAML, instruction files) and Step 2 found no testable Python interfaces, treat as heuristic non-impl pass-through per Step 2a. Do NOT trigger for AC that mentions Python implementation — even if the module doesn't exist yet, that's normal RED phase."
- [ ] `agents/test-writer.agent.md`: Add a `good_example` for heuristic pass-through in the `<examples>` section (parallel to the existing tag-based pass-through example for task #73)
- [ ] Warning note MUST use this exact format (includes "non-impl pass-through" substring for builder detection in `tdd-workflow/SKILL.md` Step 1a):
  `## Test-Writer Notes`
  `- Non-impl pass-through (heuristic) — task may be missing a pass-through tag.`
  `- AC deliverables: {list of non-Python files referenced}`
  `- No Python implementation intent found in AC.`
  `- Passing through to builder with warning.`
- [ ] The heuristic MUST NOT trigger for tasks where the AC mentions Python implementation intent (keywords in AC1.2 above), even if the module doesn't exist yet — that's normal RED phase where tests fail with ImportError
- [ ] Ambiguous cases MUST NOT use bare BLOCK. Default: pass through with strong warning (builder is next actor). Escalate to DR targeting the architect for re-tagging only when AC is genuinely too ambiguous to determine intent. Escalation must always designate a clear next actor.

## Implementation guidance

Reference: `docs/research/test-writer-non-impl-fallback-heuristic.md` for full analysis.
Decision: `docs/decisions/resolved/498-test-writer-fallback-heuristic.md` (Option A approved).
User amendment: no bare BLOCK; ambiguous cases must designate a clear next actor.

Files to modify (2 total, no Python code):
- `skills/tdd-red/SKILL.md` — insert Step 2a between existing Step 2 and Step 3
- `agents/test-writer.agent.md` — add boundary rule in `<boundaries>` + good_example in `<examples>`

Downstream compatibility: the warning note format must include "non-impl pass-through" as a substring because the builder's `tdd-workflow/SKILL.md` Step 1a matches on "Non-implementation task" or "non-impl pass-through".

## Context

Root cause analysis from tasks #467, #470, #34 stuck at in-progress without Test-Writer Notes. #467 was a pure .agent.md task tagged `scope:agents` but not `agent`, so test-writer didn't recognize it as non-impl and failed silently. Gate 4 exemption (R1) and architect tagging guidance (R2) were implemented as immediate fixes. This task is the deeper fix: test-writer resilience when tags are wrong.

## Architecture Review
**Verdict:** APPROVED
**DR Verification:** docs/decisions/resolved/498-test-writer-fallback-heuristic.md approved: true

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Step 2a in tdd-red SKILL.md | Original was vague ("if no Python source/module"). Refined with explicit 5-step logic, keyword list, and decision tree. | Rewritten |
| Boundary rule in test-writer.agent.md | Clear, but was missing scope detail. Refined to reference Step 2a and specify non-trigger condition for new-module tasks. | Rewritten |
| Warning note distinguishable | Original proposed "Non-impl detected by heuristic" which FAILS builder detection in tdd-workflow Step 1a. Prescribed exact format with "non-impl pass-through" substring. | Rewritten (critical fix) |
| Must NOT trigger for new-module Python tasks | Clear and testable as-is. | Kept |
| Ambiguous cases no bare BLOCK | Clear per DR resolution. Added selection criterion: default pass-through, DR only when genuinely ambiguous. | Refined |
| (NEW) good_example in test-writer.agent.md | Added. Challenger identified missing few-shot example for new path. | Added |

### Architecture Notes
- Single domain: agent/skill configuration (pipeline behavior). Two files in the same domain.
- No Python code changes. Only markdown edits to SKILL.md and .agent.md.
- Downstream compatibility: Critical finding. The research doc's proposed warning note format would NOT be detected by the builder's tdd-workflow/SKILL.md Step 1a, which checks for "Non-implementation task" or "non-impl pass-through" substrings. AC now prescribes exact format with the required substring.
- Pattern consistency: Step 2a follows existing Step 1a (tag-based pass-through) pattern. Keyword-based content routing mirrors CI/CD patterns (GitHub Actions paths-ignore, GitLab rules:changes).
- TDD: Not applicable. No testable Python code. Tags include agent, quality, type:config for test-writer pass-through.
- Security: No new system boundaries.
- Premise check: This capability does not exist elsewhere. The gap (L2.5 between tag-based pass-through and Gate 4 exemption) is documented and confirmed by root cause analysis of #467.

### Changes Made
- Refined AC body with 6 explicit, verifiable AC lines (was 5 vague lines)
- Added Implementation guidance section with file list and downstream compatibility note
- Preserved Context section, removed stale duplicated Decision Resolved sections

### Dependencies
- Verified: docs/decisions/resolved/498-test-writer-fallback-heuristic.md (approved: true)
- Verified: docs/research/test-writer-non-impl-fallback-heuristic.md (complete)
- No task dependencies (standalone)

### Challenge Results
- Challenger: reconsider (confidence .72)
- Key challenges: (C1) note format incompatible with builder detection, (C2) ambiguous-case disjunction unranked, (C3) keyword false positives, (C5) missing good_example
- Architect response: accepted C1 (prescribed exact format), accepted C2 (added default rule), accepted C5 (added AC line). Rebutted C3 (conservative direction is correct, keyword list refinable over time). C4 (audit prompt drift) noted as potential follow-up but out of scope.
- Confidence post-challenge: .90

[[2026-04-01]] Wed 04:15
## Test-Writer Notes
- Non-implementation task (tagged agent, quality, type:config) — no tests applicable.
- AC deliverables: skills/tdd-red/SKILL.md, agents/test-writer.agent.md (markdown edits only, no Python code)
- Passing through to builder.

[[2026-04-01]] Wed 06:51
## Builder Notes
- Files changed: skills/tdd-red/SKILL.md, agents/test-writer.agent.md
- Non-implementation task, markdown edits only, no Python code
- Step 2a added to tdd-red/SKILL.md between Step 2 and Step 3 (5-step decision tree with exact warning note format)
- Boundary rule added to test-writer.agent.md boundaries section
- Heuristic pass-through good_example added to test-writer.agent.md examples section
- Lint: N/A (markdown only)
- Committed: f5a0357

[[2026-04-01]] Wed 08:45
## Review Evidence

### Changed Files (commit f5a0357)
- skills/tdd-red/SKILL.md (+23 lines)
- agents/test-writer.agent.md (+21 lines)

### Lint / Tests
- No Python code changed. ruff N/A. pytest N/A.
- Markdown-only edits.

### Process Quality
- Builder Notes: 1 section, no retries. CLEAN.

### Test-Writer Audit
- Non-implementation task (tagged agent, quality, type:config). No TestFromAC_* classes. Step 6.0 skipped per conditional.

### Security
- No Python changes. No new dependencies. No system boundaries. PASS.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| tdd-red SKILL.md: Step 2a added between Step 2 and Step 3 | SKILL.md diff: Step 2a block inserted after Step 2 body, before Step 3 header | PASS |
| Step 2a sub-step 1: testable interfaces found => proceed to Step 3 | SKILL.md: "If Step 2 found testable interfaces: proceed to Step 3 (no change)." | PASS |
| Step 2a sub-step 2: keyword scan matches AC list | SKILL.md: exact keyword list (implement, function, method, class, module, src/, packages/, .py, import, endpoint, API) matches AC | PASS |
| Step 2a sub-step 3: intent found => Step 3, new-module RED | SKILL.md: "If implementation intent found: proceed to Step 3 (new-module RED phase, ImportError tests expected)." | PASS |
| Step 2a sub-step 4: no intent + non-Python files only => heuristic pass-through | SKILL.md: non-Python file list matches AC exactly; pass-through instructions present with exact warning format | PASS |
| Step 2a sub-step 5: ambiguous => default pass-through, DR targeting architect, clear next actor | SKILL.md: "default to pass-through with strong warning... escalate to DR targeting architect... escalation must designate a clear next actor." No bare BLOCK. | PASS |
| test-writer.agent.md: boundary rule in boundaries section | agents/test-writer.agent.md line 98: "**Heuristic non-impl pass-through (Step 2a).**" added between BLOCK rule and diff rule | PASS |
| Boundary rule: Do NOT trigger for Python implementation intent even for new modules | Exact text: "Do NOT trigger for AC that mentions Python implementation — even if the module doesnt exist yet, thats normal RED phase." | PASS |
| test-writer.agent.md: good_example for heuristic pass-through | New good_example added: why="Heuristic non-impl pass-through when pass-through tag is missing", uses task #467 scenario, parallel to existing #73 tag-based example | PASS |
| Warning note exact format with "non-impl pass-through" substring | SKILL.md Step 2a powershell block shows exact format; note begins "- Non-impl pass-through (heuristic)"; tdd-workflow Step 1a detects via case-insensitive LLM match | PASS |
| Heuristic MUST NOT trigger when Python implementation intent in AC | SKILL.md sub-steps 2-3 route to Step 3; boundary rule repeats non-trigger condition | PASS |
| Ambiguous: MUST NOT use bare BLOCK; default pass-through; clear next actor | SKILL.md Step 5: default pass-through with appended warning; DR only for genuinely ambiguous; architect named as target | PASS |
| Downstream compatibility: warning detectable by tdd-workflow Step 1a | tdd-workflow Step 1a checks "non-impl pass-through"; note contains "Non-impl pass-through (heuristic)"; architect verified in Architecture Review | PASS |

### Implementation Notes
- Step 2a placement correct: inserted after Step 2 body, before Step 3 header.
- good_example uses real root-cause task (#467) — instructive and concrete.
- Ambiguous-case Step 5 avoids bare BLOCK, designates architect as DR target per user amendment.

### Verdict: PASS (confidence .95)

[[2026-04-01]] Wed 12:25
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 2a added between Step 2 and Step 3 | tdd-red/SKILL.md: Step 2a block present after Step 2, before Step 3 | PASS |
| Sub-steps 1-5 match AC keyword list and decision tree | SKILL.md: 5-step logic with exact keyword list, file types, escalation | PASS |
| Boundary rule in test-writer.agent.md | Line 98: Heuristic non-impl pass-through (Step 2a) rule present | PASS |
| good_example for heuristic pass-through | Lines 177-194: uses #467 scenario, parallel to #73 tag-based example | PASS |
| Warning note exact format with non-impl pass-through substring | SKILL.md Step 2a powershell block matches AC4 exactly | PASS |
| Heuristic must NOT trigger for Python intent | Sub-steps 2-3 route to Step 3; boundary rule repeats condition | PASS |
| Ambiguous: no bare BLOCK, default pass-through, DR to architect | Step 5: pass-through default, DR only when genuinely ambiguous | PASS |
| Downstream compat: tdd-workflow Step 1a detects substring | tdd-workflow SKILL.md L33 matches on non-impl pass-through | PASS |

### Test Results
- pytest: 2075 passed, 235 failed (all pre-existing, none in task scope)
- ruff: 2 pre-existing PT018 in test_necessity_check_196.py, unrelated

### AC Quality Score: 5
AC was specific, complete, and led to a clean implementation. Architect caught critical downstream compatibility issue and ran challenger.

### Deduction breakdown: none (all AC lines verified, reviewer evidence thorough, commit clean)
### Confidence: 1.0
### Action: archive
