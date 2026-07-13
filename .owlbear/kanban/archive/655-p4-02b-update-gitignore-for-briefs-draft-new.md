---
id: 655
title: 'P4-02b: Update .gitignore for briefs draft-new/ pattern'
status: archived
priority: medium
created: 2026-04-06T07:17:22.9176335+02:00
updated: 2026-04-06T19:52:08.899772+02:00
started: 2026-04-06T19:52:08.899772+02:00
completed: 2026-04-06T19:52:08.899772+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:config'
depends_on:
    - 642
class: standard
---

## Acceptance Criteria

- [ ] `.gitignore` includes pattern to ignore `.owlbear/briefs/draft-new/` (transient template directory)
- [ ] `.gitignore` preserves `.owlbear/briefs/.gitkeep` and `.owlbear/briefs/README.md`
- [ ] Completed `draft-{name}/` directories are NOT ignored (tracked for audit trail)

## Context

Research: `.owlbear/research/briefs-directory-structure.md` §3B — versioning strategy C.
The `draft-new/` template is created by the Mediator on invocation and renamed to `draft-{project-name}/` after Moment 1. Only the transient template should be ignored.

[[2026-04-06]] Mon 15:01
## Research
- Research doc: .owlbear/research/briefs-directory-structure.md (parent #642, validated)
- Sources: 2 verified — briefs-directory-structure.md S3B/S3C (design decision), .gitignore L55-58 (existing scratch pattern)
- Recommendation: Use specific path pattern `.owlbear/briefs/draft-new/` — no wildcard, no exemptions needed (confidence: .92)
- Follow-up tasks created: none (this IS the implementation follow-up)
- Decision requests: none — T1 autonomous (config tweak)

## Challenge Results
- Challenger: FALLBACK — T1 trivial config with pre-existing research validation from parent #642
- Confidence in original: .92
- Key challenges: wildcard vs specific-path approach — specific path wins on KISS (no exemptions, no risk of matching draft-{name}/)
- Researcher response: accepted — approach A is minimal-risk

## Implementation Guidance
Add to .gitignore (after the scratch section, ~line 58):

```
# Briefs — transient template directory (renamed to draft-{name}/ at M1)
.owlbear/briefs/draft-new/
```

No `!` exemptions needed — pattern is specific to draft-new/ only. .gitkeep, README.md, and completed draft-{name}/ directories are all inherently preserved.

[[2026-04-06]] Mon 16:15
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: add one gitignore pattern for `.owlbear/briefs/draft-new/` |
| Interface clarity | PASS | AC specifies exact pattern, what to preserve, and what NOT to ignore. Implementation guidance gives exact line placement and content. |
| Dependency correctness | PASS | Depends on #642 (archived). No dependency on sibling #654 — correct; gitignore patterns work regardless of directory existence. |
| Module layering | N/A | Config file edit, no modules involved. |
| TDD compliance | N/A | Non-code deliverable. `type:config` pass-through tag present. |
| KISS/YAGNI | PASS | Specific path pattern `.owlbear/briefs/draft-new/` — no wildcards, no `!` exemptions needed. Minimal approach per research challenge (wildcard vs specific-path: specific-path wins on KISS). |
| Premise challenge | PASS | Gitignore update is required to prevent tracking transient template directories created at Mediator invocation. No existing pattern covers this path. |
| Pattern consistency | PASS | Follows `.owlbear/scratch/*` gitignore pattern (lines 55-58). Same structure: comment line + specific path. Key difference: scratch uses wildcard + exemptions; briefs uses specific subdirectory path — correct because only draft-new/ is transient while scratch/* is entirely transient. |
| Security surface | PASS | No new system boundaries. Static config file edit. |
| Single domain | PASS | Config domain only. |

### Failure Mode Map
N/A — no codepaths with failure modes; static config file edit.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `.gitignore` includes pattern to ignore `.owlbear/briefs/draft-new/` | CLEAR — verifiable by grep; implementation guidance gives exact content | No change needed |
| `.gitignore` preserves `.owlbear/briefs/.gitkeep` and `.owlbear/briefs/README.md` | CLEAR — trivially satisfied because only `draft-new/` is ignored (no wildcard on parent dir). AC serves as constraint against overly broad patterns | No change needed |
| Completed `draft-{name}/` dirs are NOT ignored | CLEAR — `draft-new/` pattern does not match `draft-{name}/`. Verifiable by `git check-ignore` test | No change needed |

### Architecture Notes
- Research doc (`.owlbear/research/briefs-directory-structure.md` §3B) thoroughly evaluates 3 versioning strategies. Strategy C (track completed, ignore draft-new/) is sound.
- Existing `.gitignore` scratch pattern (L55-58) provides direct precedent. Briefs pattern is simpler — no exemptions needed because only one specific subdirectory is ignored.
- Implementation guidance specifies exact placement (after scratch section, ~line 58) and exact content. Builder has clear instructions.
- No `!` exemptions needed — `.owlbear/briefs/.gitkeep`, `README.md`, and `draft-{name}/` directories are all outside the ignore pattern by construction.

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in session. T1 trivial config task with pre-validated research from parent #642 and embedded challenge results from researcher.
- Architect response: accepted — researcher's challenge (wildcard vs specific-path) is well-reasoned, KISS principle correctly applied.

### Verdict: APPROVE
### Action Taken: Advanced to todo. All 3 AC lines are precise and verifiable. Pattern follows existing .gitignore conventions. `type:config` pass-through tag present for downstream pipeline.

[[2026-04-06]] Mon 17:01
## Test-Writer Notes
- Non-implementation task (tagged `type:config`) — no tests applicable.
- Passing through to builder.

[[2026-04-06]] Mon 18:48
## Builder Notes
- Non-implementation task (`type:config`) — no code changes needed, one config change only.
- **File changed:** `.gitignore` — added 2 lines after the scratch section (line ~59):
  ```
  # Briefs — transient template directory (renamed to draft-{name}/ at M1)
  .owlbear/briefs/draft-new/
  ```
- Pattern is specific to `draft-new/` only — no wildcards, no `!` exemptions needed.
- `.owlbear/briefs/.gitkeep`, `README.md`, and completed `draft-{name}/` directories are preserved by construction.
- AC verified: pattern matches only the transient template; completed dirs remain trackable.
- Lint/tests: N/A — config-only change.

[[2026-04-06]] Mon 19:16
## Review Evidence

### Changed Files
- `.gitignore` — only changed file attributed to this task (23 total unstaged, rest belong to sibling tasks)

### Tests
- N/A — `type:config` pass-through. Test-writer correctly passed through with no `TestFromAC_*` classes.

### Lint
- N/A — static config file, no Python changed.

### Coverage  
- N/A

### Security (5.1)
- No concerns. Static config file edit with no new system boundaries.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| `.gitignore` includes `.owlbear/briefs/draft-new/` | `.gitignore` L60-61 — comment + exact pattern present | PASS |
| `.gitignore` preserves `.owlbear/briefs/.gitkeep` and `.owlbear/briefs/README.md` | No pattern in full `.gitignore` (L1-70) matches those paths. Scratch wildcard (L56) is scoped to `.owlbear/scratch/*` — does not bleed into `.owlbear/briefs/` | PASS |
| Completed `draft-{name}/` dirs NOT ignored | Pattern `.owlbear/briefs/draft-new/` is an exact match only — `draft-abc/`, `draft-myproject/` etc. are unaffected | PASS |

### Pass 1 Critical Checks
- 5.0 TestFromAC audit: N/A — no `TestFromAC_*` classes (type:config task)
- 5.1 Security: PASS — static config, no new surface
- 5.2 TestFromAC integrity: N/A
- 5.3 Test quality: N/A
- 5.4 Data safety: N/A
- 5.5 Implementation-aware gap analysis: N/A — single-line config
- 5.6 Necessity: PASS — pattern did not previously exist; `git check-ignore -v .owlbear/briefs/draft-new/somefile` would return this rule
- 5.7 Builder process: CLEAN — single cycle, no retries

### Deductions
0

### Verdict
Confidence: .98 → PASS

Pattern placement follows existing `.owlbear/scratch/*` precedent. Specific path (not wildcard) correctly prevents over-matching. All 3 AC lines satisfied by construction.

[[2026-04-06]] Mon 19:21
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `.github/copilot-instructions.md` is a 5-line identity stub; no briefs directory or gitignore conventions documented there. Pure config change — no behavior or API changed. |
| 2 | Module docstrings | No | N/A | No Python files changed — `type:config` task. |
| 3 | External attribution | No | N/A | Only internal sources used: `.owlbear/research/briefs-directory-structure.md` (parent #642, pre-validated). No external repos/articles/docs cited. |
| 4 | CLI changes | No | N/A | No CLI changes. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/briefs-directory-structure.md` exists. Linked in task body. Follow-up tasks: none needed — this task IS the implementation follow-up per researcher notes. |

### Implementation Verified
- `.gitignore` L60-61: comment + `.owlbear/briefs/draft-new/` pattern present exactly as specified in AC and implementation guidance.
- AC1 PASS: pattern exists. AC2 PASS: no wildcard on parent dir; `.gitkeep` and `README.md` unaffected. AC3 PASS: `draft-new/` is exact-match only; `draft-{name}/` dirs are unaffected.

### Files Updated
- None — no documentation updates required.

### Scratch Files Cleaned
- None — no `655-*` scratch files found.

[[2026-04-06]] Mon 19:52
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| .gitignore includes pattern to ignore .owlbear/briefs/draft-new/ | .gitignore L60-61: comment + exact pattern present (verified via git diff and file read) | PASS |
| .gitignore preserves .owlbear/briefs/.gitkeep and README.md | Full .gitignore L50-70 reviewed: no pattern matches those paths. Scratch wildcard (L56) scoped to .owlbear/scratch/* only | PASS |
| Completed draft-{name}/ dirs NOT ignored | Pattern .owlbear/briefs/draft-new/ is exact-match only; draft-abc/, draft-myproject/ etc. unaffected by construction | PASS |

### Test Results
- pytest: N/A (type:config task, no Python changed). Full suite has pre-existing failures from other tasks (test_agent_port_v2.py, test_planner_gates.py) — none related to .gitignore.
- ruff: N/A (no Python changed)

### Architect Quality: 5/5
All 3 AC lines specific, verifiable, and correctly scoped. Implementation guidance gave exact placement and content. No builder improvisation needed.

### Deduction Breakdown
- Start: 1.00
- AC lines with no evidence: 0 (all 3 verified with file evidence)
- Lint violations: 0
- AC quality deduction: 0 (score 5/5)
- Missing reviewer evidence: 0 (present, detailed, .98 PASS)
- Full-suite failures in task scope: 0

### Confidence: .98
### Action: archive

### Notes
- Builder did not commit the .gitignore change (unstaged). Auditor committed as 4c13d32. Quality gap noted but not a rubric deduction item.
- Reviewer evidence thorough: all 3 AC lines mapped with specific line references.

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4c13d32 | fix(config) | .gitignore | #655 |
