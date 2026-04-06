---
id: 655
title: 'P4-02b: Update .gitignore for briefs draft-new/ pattern'
status: review
priority: needed
created: 2026-04-06T07:17:22.9176335+02:00
updated: 2026-04-06T18:48:09.8729502+02:00
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
