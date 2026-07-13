---
id: 319
title: Add fix-attempt delegation to builder tdd-workflow
status: archived
priority: medium
created: 2026-03-30 20:38:22.464745+02:00
updated: 2026-04-05 16:57:16.665754+02:00
started: 2026-04-05 16:57:16.665754+02:00
completed: 2026-04-05 16:57:16.665754+02:00
tags:
- scope:agents
- phase-2
- agent
depends_on:
- 318
class: standard
archival_reason: completed
archival_refs: []
---

AC:
1. tdd-workflow skill updated: after 2nd verify failure, construct retry_hint and delegate to fix-attempt subagent
2. Builder agents array updated to include fix-attempt
3. Retry_hint includes specific error info (Reflexion-style verbal feedback)
4. Builder handles fix-attempt result: FIXED continues to commit, FAILED blocks task
5. Builder still caps at 2 retries total (same-context + fresh-context = 2 total attempts after initial)
See docs/research/fresh-context-retry-builder.md

[[2026-04-05]] Sun 10:27
## Research
- Research doc: .owlbear/research/fix-attempt-delegation-tdd-workflow.md
- Sources: 8 studied, 6 high-relevance (>=.90)
- Finding: **Implementation already exists** (commit c2b93a9, refined in 1d05a86). All 5 AC items satisfied.
- Recommendation: advance to pipeline verification — no new implementation needed (confidence: .92)
- Follow-up tasks created: none (work complete, sibling tasks #318 and #320 archived)
- Decision requests: none
- Board sync gap: #319 was implemented 2026-04-04 but never advanced from ideation

## Challenge Results
- Challenge: SKIPPED — validation pass on existing implementation, no new recommendation
- Confidence in original: .92
- Key validation checks: AC compliance (5/5), test coverage (9/9 pass), git history confirms commit scope
- Researcher response: findings hold — implementation matches AC with one accepted refinement (reject vs block, auditor-approved at .97)

[[2026-04-05]] Sun 11:08
## Architecture Review
### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: tdd-workflow updated with delegation | PASS: Step 6.3 documents retry_hint construction + fix-attempt subagent invocation after exactly 2 failures | Kept |
| AC2: Builder agents array | PASS: builder.agent.md L10 agents: [scribe, fix-attempt, quality-runner] | Kept |
| AC3: Retry_hint Reflexion-style | PASS: Step 6.3 prompt documents error extraction, failing test identification, Reflexion-style verbal diagnosis | Kept |
| AC4: FIXED/FAILED handling | REFINE: Implementation uses reject with routing (todo/backlog) instead of block. Superior: reject feeds task back into pipeline; block would stall. Auditor #320 accepted at .97. | Refined |
| AC5: 2 retries total cap | PASS: "exactly 2 failures (not 1, not 3)" with mandatory sequence documented | Kept |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Adds fix-attempt delegation to tdd-workflow + builder wiring only |
| Interface clarity | PASS | Structured delegation prompt with 5 Input Contract fields, FIXED/FAILED result table |
| Dependency correctness | PASS | #318 archived (fix-attempt.agent.md exists, 27/27 tests pass) |
| Module layering | PASS | Builder (L1) delegates to fix-attempt (L2), within VS Code depth-5 limit |
| TDD compliance | PASS | Sibling #320 archived, 9/9 contract tests pass |
| KISS/YAGNI | PASS | Minimal delegation after 2 failures |
| Premise challenge | PASS (board sync) | Implementation exists (commits c2b93a9, 1d05a86). Siblings #318, #320 archived. Pipeline pass-through expected. |
| Pattern consistency | PASS | Follows quality-runner subagent delegation pattern |
| Security surface | PASS | Markdown skill/agent files only |
| Single domain | PASS | scope:agents |

### Challenge Results
- Challenger: FALLBACK (agent not in available agents list)
- Inline challenge: (1) board-sync catch-up appropriate, pipeline verification needed; (2) AC4 deviation (reject vs block) is T1 autonomous improvement, accepted by #320 auditor at .97; (3) no risk in pre-implemented task approval
- Confidence: .90

### AC4 Refinement
Original: "FAILED blocks task"
Refined: "FAILED rejects task with diagnosis-based routing (todo or backlog)"

### Verdict: APPROVE
### Action: AC4 refined. Added agent pass-through tag. Advanced to todo. Pipeline pass-through expected (implementation exists, 9/9 tests pass).

[[2026-04-05]] Sun 12:31
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- AC describes updates to `.agent.md` and `SKILL.md` files only; no testable Python interfaces.
- Passing through to builder.

[[2026-04-05]] Sun 13:27
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
- AC verification: all 5 AC items confirmed satisfied in existing files (commits c2b93a9, 1d05a86).
  - AC1/3/5: w-tdd-green SKILL.md Step 6.3 — fix-attempt delegation after exactly 2 failures, Reflexion-style retry_hint.
  - AC2: builder.agent.md L10 agents: [scribe, fix-attempt, quality-runner].
  - AC4 (refined): FIXED/FAILED routing table — FAILED rejects with todo/backlog routing.

[[2026-04-05]] Sun 15:09
## Review Evidence

**Task type:** Non-implementation (tagged `agent`) — board-sync pass-through for pre-existing implementation.
**Changed artifacts:** `share/agents/builder.agent.md`, `share/skills/w-tdd-green/SKILL.md` (originally committed at `.github/` paths in c2b93a9 / 1d05a86; migrated to `share/` via #600 commit b018f75).

### Tests
- No `TestFromAC_*` classes exist (expected: non-implementation task).
- Delegation contract tests (test_fix_attempt_delegation_320.py): **9 passed, 0 failed**.
- Step 5.0 (Test-Writer Audit): SKIP — no TestFromAC_* classes.
- Step 5.2 (TestFromAC Comparison): SKIP — no TestFromAC_* classes.

### Lint
- Ruff: **no Python files** (expected — markdown-only change). All checks passed.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: tdd-workflow updated with fix-attempt delegation after 2nd failure | `share/skills/w-tdd-green/SKILL.md` Step 6.3 (line 178–201): "Fail Again: Delegate to fix-attempt", triggers after exactly 2 failures, `agentName: fix-attempt` invocation template | PASS |
| AC2: Builder agents array includes fix-attempt | `share/agents/builder.agent.md` L10: `agents: [scribe, fix-attempt, quality-runner]` | PASS |
| AC3: retry_hint Reflexion-style verbal feedback | Step 6.3 line 192: "extract specific errors…identify which failing tests…provide Reflexion-style verbal diagnosis…Not generic 'tests failed'." | PASS |
| AC4 (refined): FIXED continues to commit, FAILED rejects with routing | Step 6.3 result table: FIXED → re-verify + Step 7; FAILED → `end_work(outcome="reject", move_to="todo"/"backlog")`. Refinement (reject vs block) accepted by #320 auditor at .97. | PASS |
| AC5: Caps at 2 retries total | Step 6.3: "exactly 2 failures (not 1, not 3): initial attempt → same-context retry (Step 6.2) → fix-attempt delegation. The sequence is mandatory; never skip steps." | PASS |

### Security
- Pure markdown changes. OWASP Top 10: N/A. No code, no secrets, no injection surface.

### Deductions
- 0 deductions.

### Verdict
Confidence: **.96** → **PASS**
Action: advanced to `docs`.

[[2026-04-05]] Sun 15:17
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `.github/copilot-instructions.md` is 3 lines with no agent behavior tables. Changed artifacts (`builder.agent.md`, `w-tdd-green/SKILL.md`) are agent customization files — not Python API. No copilot-instructions.md update needed. |
| 2 | Module docstrings | No | N/A | Markdown-only task. Zero Python files created or modified. |
| 3 | External attribution | No | N/A | Research doc sources S1–S8 are all internal files and git commits. Reflexion paper + VS Code docs already attributed under sibling tasks #318/#320 in sources/overview.md. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/fix-attempt-delegation-tdd-workflow.md` exists, linked from task body. Follow-up tasks: none needed (implementation pre-existed, siblings #318 and #320 archived). |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/319-*` files found)

[[2026-04-05]] Sun 16:56
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: tdd-workflow updated with delegation after 2nd failure | w-tdd-green/SKILL.md Step 6.3 L178-201 | PASS |
| AC2: Builder agents array includes fix-attempt | builder.agent.md L10 agents: [scribe, fix-attempt, quality-runner] | PASS |
| AC3: retry_hint Reflexion-style verbal feedback | SKILL.md L192 Reflexion-style verbal diagnosis | PASS |
| AC4 (refined): FIXED/FAILED handling with routing | SKILL.md L198-201 FIXED re-verify + Step 7; FAILED rejects to todo/backlog | PASS |
| AC5: 2 retries total cap | SKILL.md L180 exactly 2 failures mandatory sequence | PASS |

### Test Results
- pytest: 432 failed, 2878 passed (all pre-existing RED-phase TDD); 9/9 delegation contract tests pass
- ruff: clean

### Architect Quality: 4/5
AC4 required refinement (block to reject routing) caught at architecture review.

### Deductions: 0
### Confidence: 1.00
### Action: archive

### Commits
c2b93a9 feat: fix-attempt delegation (#319)
1d05a86 feat: refine Step 6.3 contract (#320)
118bda6 chore: migrate to share/ (#600)
b018f75 chore: update path refs (#607)

[[2026-04-05]] Sun 16:57
Audited: 5/5 AC verified, 9/9 delegation tests pass, full suite 432 pre-existing failures only, ruff clean. Confidence 1.00.
