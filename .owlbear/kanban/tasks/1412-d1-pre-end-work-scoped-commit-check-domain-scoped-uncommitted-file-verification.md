---
id: 1412
title: 'D1: Pre-end_work scoped commit check — domain-scoped uncommitted file verification'
status: backlog
priority: important
created: 2026-05-07T23:16:25.281801+00:00
updated: 2026-05-08T12:37:28.475777+00:00
tags:
- pipeline
- ws-protocol
- scope:agents
parent: 1403
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: `r-pipeline-protocol` updated with pre-`end_work` commit check requirement
P2: Each agent verifies uncommitted files in its own file domain before calling `end_work`: researcher (`.owlbear/research/`), test-writer (`tests/`), builder (`serve/*/src/`), doc-writer (docs), etc.
P2: Check is domain-scoped — NOT raw `git status --porcelain` (which shows other agents' dirty files in shared worktree)
P2: Protocol specifies the check happens before `end_work`, not as a PostToolUse hook
P3: Verification by diff comparison of modified protocol file

## Scope

**In scope:** Protocol update for scoped commit check in `r-pipeline-protocol`
**Out of scope:** Implementing the check as code/tooling (protocol-level only), PostToolUse hooks
[[2026-05-08]]
## Planning

Created 1 follow-up task:

| ID | Title | Status | Parent | Priority | Tags |
|----|-------|--------|--------|----------|------|
| #1435 | Add pre-advance commit verification rule to r-pipeline-protocol | backlog | #1403 | important | pipeline, ws-protocol, scope:agents |

AC carried forward from dispatch verbatim. No dependencies — standalone protocol update task.
[[2026-05-08]]
## Research
- Research doc: .owlbear/research/1412-pre-end-work-scoped-commit-check.md
- Sources: 4 studied, 3 high-relevance
- Recommendation: Add "Pre-advance verification" rule to `r-pipeline-protocol` § 4 Closing → Who Commits What → Rules. Domain-path table per agent + `git status --porcelain -- <domain-paths>` verification + self-heal commit action. Mechanism already proven in `w-code-review` Step 1.1. (confidence: .90)
- Challenge: SKIP — trivial protocol change
- Follow-up: #1435 (backlog) — implement the protocol text change
[[2026-05-08]]
## Test-Writer Notes

**Test file:** `tests/test_pipeline_commit_check_1412.py`
**Class:** `TestFromAC_PreAdvanceCommitCheck`

### Test counts by category

| Category | Tests |
|----------|-------|
| Happy path (rule exists) | 1 |
| Per-agent domain table | 4 |
| Verification command | 1 |
| Rule placement | 1 |
| Self-heal action | 1 |
| **Total** | **8** |

All 8 tests FAIL on current codebase (RED confirmed via quality-runner). Lint: clean.

### AC coverage

| AC line | Test(s) |
|---------|---------|
| P1: r-pipeline-protocol updated with pre-end_work commit check requirement | `test_pre_advance_verification_heading_exists` |
| P2: Each agent verifies uncommitted files in its domain | `test_researcher_domain_paths_present`, `test_test_writer_domain_paths_present`, `test_builder_domain_paths_present`, `test_doc_writer_domain_paths_present` |
| P2: Check is domain-scoped — NOT raw `git status --porcelain` | `test_verification_command_uses_pathspec_syntax` |
| P2: Protocol specifies before end_work, not PostToolUse hooks | `test_rule_placed_in_who_commits_what_section` |
| P3: Verification by diff comparison | this test file IS the diff verification |

### Note on P3
P3 ("Verification by diff comparison of modified protocol file") is fulfilled by the test file itself — the tests read and assert on the SKILL.md content, which constitutes the diff-based verification mechanism.
[[2026-05-08]]
## Builder Notes
- Implementation: updated share/skills/r-pipeline-protocol/SKILL.md under `### Who Commits What` rules.
- Added `Pre-advance verification` requirement before `end_work`.
- Added per-agent domain table: researcher (`.owlbear/research/`, `.owlbear/sources/`), test-writer (`tests/`), builder (`serve/`), doc-writer (README/doc paths).
- Added required domain-scoped command form: `git status --porcelain -- <domain-paths>`.
- Added self-heal action: stage + commit missed in-domain files, then continue to `end_work`.
- Tests: 8/8 passed in tests/test_pipeline_commit_check_1412.py (`TestFromAC_PreAdvanceCommitCheck`).
- Coverage: N/A for this docs/protocol text change task-scoped test.
- Lint: clean (quality-runner scoped run).
- Commit: 26caf036 (`docs: add pre-end_work domain-scoped commit check rule (#1412, builder)`).

### Post-task Reflection
- Problem faced: rule placement had to be inside `### Who Commits What` to satisfy section-scoped assertion.
- Pattern discovered: AC text checks are strict on literal command syntax (`git status --porcelain --`).
- Workaround applied: used one surgical insertion in the existing Rules list to minimize risk.
- Quality gap avoided: ensured self-heal wording states commit-and-continue, not a blocking gate.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped pytest on `tests/test_pipeline_commit_check_1412.py`: 8 passed, 0 failed

### Lint: clean
- quality-runner scoped ruff on `tests/test_pipeline_commit_check_1412.py`: clean

### Coverage: not applicable
- Implementation artifact is markdown/protocol text (`share/skills/r-pipeline-protocol/SKILL.md`), not an instrumented Python module.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| P1: `r-pipeline-protocol` updated with pre-`end_work` commit check requirement | `test_pre_advance_verification_heading_exists` | Yes — missing rule text would fail (`tests/test_pipeline_commit_check_1412.py:58`) | COVERED |
| P2: Each agent verifies uncommitted files in its own file domain before calling `end_work` (builder example: `serve/*/src/`) | `test_builder_domain_paths_present` | No — the test explicitly accepts `serve/` (`tests/test_pipeline_commit_check_1412.py:86-89`), so it stays green while the live artifact violates the builder example (`share/skills/r-pipeline-protocol/SKILL.md:248`) | LAX |
| P2: Check is domain-scoped — NOT raw `git status --porcelain` | `test_verification_command_uses_pathspec_syntax` | Yes — missing `--` pathspec would fail (`tests/test_pipeline_commit_check_1412.py:104-108`; `share/skills/r-pipeline-protocol/SKILL.md:251`) | COVERED |
| P2: Protocol specifies the check happens before `end_work`, not as a PostToolUse hook | `test_rule_placed_in_who_commits_what_section` | Yes — missing placement under `### Who Commits What` would fail (`tests/test_pipeline_commit_check_1412.py:115-119`; `share/skills/r-pipeline-protocol/SKILL.md:229,242`) | COVERED |
| P3: Verification by diff comparison of modified protocol file | Task-local file-content assertions plus direct review of the live artifact | Adequate for this text-only task: the tests assert against the modified protocol file and the review compared that file to the task/brief contract | COVERED |

#### Security Review
- No issues. This task changes protocol text only; no secrets, input handling, filesystem access, or execution surface were introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_pipeline_commit_check_1412.py::test_builder_domain_paths_present` | Commit presence was verified (`26caf036` is present in `.git/logs`), but changed-file diff access was unavailable in this tool surface, so builder-side immutability could not be proven from git evidence alone | UNVERIFIABLE (non-gating here) |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | `test_builder_domain_paths_present` accepts any builder mapping containing `serve/` (`tests/test_pipeline_commit_check_1412.py:88-89`), so it does not prove the AC-required `serve/*/src/` domain from the task (`.owlbear/kanban/tasks/1412-d1-pre-end-work-scoped-commit-check-domain-scoped-uncommitted-file-verification.md:26`) and brief (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md:50,115`). |
| Negative/error-path coverage | ADEQUATE | The raw-vs-scoped and placement clauses have direct assertions that would fail if omitted (`tests/test_pipeline_commit_check_1412.py:104-119`). |
| Manual mutation reasoning | WEAK | The exact wrong implementation currently present — builder domain broadened to `serve/` in `share/skills/r-pipeline-protocol/SKILL.md:248` — still passes the task-local suite. |
| Test independence | STRONG | Each test reads the artifact independently and does not share mutable state. |
| Descriptive test names | STRONG | Test names map cleanly to the AC clauses. |

#### Data Safety
- No issues.

#### Implementation-Aware Gaps
- The live protocol still broadens the builder verification domain to `serve/` (`share/skills/r-pipeline-protocol/SKILL.md:248`). The task AC requires the builder example to be `serve/*/src/` (`.owlbear/kanban/tasks/1412-d1-pre-end-work-scoped-commit-check-domain-scoped-uncommitted-file-verification.md:26`), and the parent brief repeats the same requirement (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md:50,115`). Because `serve/` includes non-source subtrees, the delivered rule is not scoped to the builder's own file domain.

#### Necessity Check
- N/A — no new dependency, integration, or external capability was added.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Builder commit `26caf036` was verified in `.git/logs/refs/heads/dev:2093` and `.git/logs/HEAD:2270`.
- Full changed-file diff and dirty-scope contamination checks were not reconstructable with the available tool surface. That lowers confidence slightly on TestFromAC immutability, but it does not affect the verdict because the AC miss is directly visible in the live artifact and the current green test still encodes the same wrong contract.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| P1: `r-pipeline-protocol` updated with pre-`end_work` commit check requirement | Rule exists under `### Who Commits What` (`share/skills/r-pipeline-protocol/SKILL.md:229,242`) | `test_pre_advance_verification_heading_exists` | PASS |
| P2: Each agent verifies uncommitted files in its own file domain before calling `end_work`: researcher (`.owlbear/research/`), test-writer (`tests/`), builder (`serve/*/src/`), doc-writer (docs), etc. | Task and brief both require builder `serve/*/src/` (`.owlbear/kanban/tasks/1412-d1-pre-end-work-scoped-commit-check-domain-scoped-uncommitted-file-verification.md:26`; `.owlbear/briefs/draft-pipeline-review-rethink/brief.md:50,115`), but the delivered table says `serve/` (`share/skills/r-pipeline-protocol/SKILL.md:248`) | `test_builder_domain_paths_present` | FAIL |
| P2: Check is domain-scoped — NOT raw `git status --porcelain` | The rule requires `git status --porcelain -- <domain-paths>` (`share/skills/r-pipeline-protocol/SKILL.md:251`) | `test_verification_command_uses_pathspec_syntax` | PASS |
| P2: Protocol specifies the check happens before `end_work`, not as a PostToolUse hook | The rule is placed inside `### Who Commits What` and says "Before calling `end_work`" (`share/skills/r-pipeline-protocol/SKILL.md:229,242`) | `test_rule_placed_in_who_commits_what_section` | PASS |
| P3: Verification by diff comparison of modified protocol file | The task-local tests assert directly on the modified protocol file and this review inspected that file against the task/brief contract | `tests/test_pipeline_commit_check_1412.py` | PASS |

### Confidence: .63
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Narrow the builder domain entry in the pre-advance verification table from `serve/` to the AC-required `serve/*/src/` | `share/skills/r-pipeline-protocol/SKILL.md` | AC Compliance row for P2; task line 26; brief lines 50/115; live artifact line 248 |
| 2 | builder | Strengthen `test_builder_domain_paths_present` so it rejects broader `serve/` mappings and proves the exact builder-domain contract on retry | `tests/test_pipeline_commit_check_1412.py` | Test-Writer AC Coverage + Test Quality findings; live assertion at lines 86-89 remains green on the current AC violation |
[[2026-05-08]]
## Builder Notes
- Implementation: updated share/skills/r-pipeline-protocol/SKILL.md in `### Who Commits What` -> `Pre-advance verification` table.
- Fix applied: narrowed Builder domain from `serve/` to `serve/*/src/` to match AC-scoped builder file domain.
- Tests: task-scoped suite `tests/test_pipeline_commit_check_1412.py` is green (8 passed, 0 failed).
- Lint: clean (scoped run).
- Coverage: not applicable for this markdown/protocol text change (no instrumented module imported).
- Commit gate: domain-scoped check run before release (`git status --porcelain -- share/skills/r-pipeline-protocol/`), committed, then rechecked clean.
- Commit: 3e98d0be (`docs: narrow builder commit-check domain to serve src paths (#1412, builder)`).
- Evidence summary: protocol now enforces path-scoped pre-`end_work` verification with Builder mapped to `serve/*/src/`, aligning with task AC wording.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped pytest on tests/test_pipeline_commit_check_1412.py: 8 passed, 0 failed

### Lint
- quality-runner scoped ruff on tests/test_pipeline_commit_check_1412.py: clean

### Coverage
- Not applicable. The changed artifact is share/skills/r-pipeline-protocol/SKILL.md, a markdown protocol file.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| P1: r-pipeline-protocol updated with pre-end_work commit check requirement | test_pre_advance_verification_heading_exists | Yes. Removing the rule text would fail the assertion in tests/test_pipeline_commit_check_1412.py:56-60. | COVERED |
| P2: Each agent verifies uncommitted files in its own file domain before calling end_work, including builder serve/*/src/ | test_builder_domain_paths_present | No. The live artifact is correct at share/skills/r-pipeline-protocol/SKILL.md:248, but the assertion at tests/test_pipeline_commit_check_1412.py:88 and message at :89 still accept any builder row containing serve/. A regression from serve/*/src/ back to broader serve/ would stay green. | LAX |
| P2: Check is domain-scoped, not raw porcelain status over the whole tree | test_verification_command_uses_pathspec_syntax | Yes. The live rule requires a path-scoped porcelain status check with a pathspec separator at share/skills/r-pipeline-protocol/SKILL.md:251. | COVERED |
| P2: The check happens before end_work, not as a hook | test_rule_placed_in_who_commits_what_section | Yes. The rule remains inside the Who Commits What section at share/skills/r-pipeline-protocol/SKILL.md:229-251 and the test asserts that placement at tests/test_pipeline_commit_check_1412.py:116-120. | COVERED |
| P3: Verification by diff comparison of the modified protocol file | task-local file-content assertions against the modified protocol file | Adequate for this text-only task. The task-local suite reads the modified protocol file directly and this review rechecked the live artifact. | COVERED |

#### Security Review
- No issues. This task changes protocol text only and does not introduce secrets, execution surface, or input handling.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| tests/test_pipeline_commit_check_1412.py::test_builder_domain_paths_present | No new weakening is visible in the live file, but commit-specific ownership could not be reconstructed from the available tool surface | UNVERIFIABLE (non-gating) |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | The matcher at tests/test_pipeline_commit_check_1412.py:88 and message at :89 accept broader serve/ rather than exact serve/*/src/. |
| Negative/error-path coverage | ADEQUATE | The command-scope and placement clauses still have discriminating assertions that would fail if removed. |
| Manual mutation reasoning | WEAK | Reverting the live builder row at share/skills/r-pipeline-protocol/SKILL.md:248 from serve/*/src/ to serve/ would still pass the scoped suite. |
| Test independence | STRONG | Each test reads the artifact independently and does not share mutable state. |
| Descriptive test names | STRONG | Test names map directly to the task AC clauses. |

#### Data Safety
- No issues.

#### Implementation-Aware Gaps
- The protocol artifact now satisfies the builder-domain requirement in the task and the parent brief. The remaining gap is proof quality: the task-local suite does not contain an assertion that would fail on a broader builder-domain mapping.

#### Necessity Check
- N/A. No new dependency, integration, or external capability was added.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Approach variation | Yes. The retry narrowed the builder domain after the first review finding. |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- One prior Review Evidence section already exists in the task file at .owlbear/kanban/tasks/1412-d1-pre-end-work-scoped-commit-check-domain-scoped-uncommitted-file-verification.md:101. No architecture narrowing rewrote this concern out of scope.
- Commit-diff and dirty-scope contamination checks could not be reconstructed with the available tool surface, so TestFromAC immutability carries a small confidence deduction.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| P1: r-pipeline-protocol updated with pre-end_work commit check requirement | The rule exists in share/skills/r-pipeline-protocol/SKILL.md:229-251. | test_pre_advance_verification_heading_exists | PASS |
| P2: Each agent verifies uncommitted files in its own file domain before calling end_work: researcher (.owlbear/research/), test-writer (tests/), builder (serve/*/src/), doc-writer (docs), etc. | The task AC at .owlbear/kanban/tasks/1412-d1-pre-end-work-scoped-commit-check-domain-scoped-uncommitted-file-verification.md:26 and the parent brief at .owlbear/briefs/draft-pipeline-review-rethink/brief.md:50 and :115 require builder serve/*/src/. The live protocol row at share/skills/r-pipeline-protocol/SKILL.md:248 matches that contract. | test_builder_domain_paths_present | PASS |
| P2: Check is domain-scoped, not raw porcelain status over the whole tree | The live rule at share/skills/r-pipeline-protocol/SKILL.md:251 requires a path-scoped porcelain status check with a pathspec separator. | test_verification_command_uses_pathspec_syntax | PASS |
| P2: Protocol specifies the check happens before end_work, not as a hook | The live rule remains inside the Who Commits What section in share/skills/r-pipeline-protocol/SKILL.md:229-251. | test_rule_placed_in_who_commits_what_section | PASS |
| P3: Verification by diff comparison of modified protocol file | The task-local tests read the modified protocol file directly and this review rechecked the live artifact. | tests/test_pipeline_commit_check_1412.py | PASS |

### Deductions
- -0.12: test_builder_domain_paths_present is non-discriminating and still accepts a broader serve/ match.
- -0.03: builder/test ownership and dirty-scope contamination could not be fully reconstructed from git evidence in this tool surface.
- -0.04: this is a second review cycle with the same remaining proof gap, so loop-breaker routing applies.

### Confidence: .81
### Verdict: FAIL
### Action
- Route to backlog. The implementation now satisfies the AC, but the task-owned TestFromAC still provides weak proof, and this is the second review cycle.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Re-route the retry as a proof-only correction and write the retry contract so the builder-domain assertion requires exact serve/*/src/ and rejects broader serve/ matches | tests/test_pipeline_commit_check_1412.py; .owlbear/kanban/tasks/1412-d1-pre-end-work-scoped-commit-check-domain-scoped-uncommitted-file-verification.md | tests/test_pipeline_commit_check_1412.py:88-89 stay green on a broader serve/ mapping; task line 26 and brief lines 50 and 115 require serve/*/src/ |
| 2 | architect | Preserve the current protocol text unless a new artifact defect is found; the remaining failure is proof quality, not the live protocol row | share/skills/r-pipeline-protocol/SKILL.md | The live builder row at share/skills/r-pipeline-protocol/SKILL.md:248 matches the task AC, and the latest builder retry is recorded at .owlbear/kanban/tasks/1412-d1-pre-end-work-scoped-commit-check-domain-scoped-uncommitted-file-verification.md:182 |