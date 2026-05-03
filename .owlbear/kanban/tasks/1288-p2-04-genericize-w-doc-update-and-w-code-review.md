---
id: 1288
title: 'P2-04: Genericize w-doc-update and w-code-review'
status: in-progress
priority: important
created: 2026-05-02T16:01:17.090078+00:00
updated: 2026-05-03T19:10:05.364798+00:00
tags:
- phase-2
- scope:docs
- shared-layer
- type:docs
parent: 1280
depends_on:
- 1285
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] All serve/ path references genericized: w-doc-update (1 entry), w-code-review (2 entries) — total 3 (td:0)
- [ ] w-code-review: both lint_paths template occurrences use workspace/ prefix (td:0)
- [ ] No `serve/` paths remain in either skill (MCP tool names excluded) (td:0)
- [ ] Notation uses `workspace/` prefix as project-neutral path placeholder in template syntax (per parent #1280 brief convention) (td:0)
- [ ] Existing test gate `test_no_serve_path_refs_in_skill_files` passes for these two skills (td:0)

## Scope

- IN: w-doc-update/SKILL.md, w-code-review/SKILL.md
- OUT: Path-heavy skills (#1287), architecture extraction (#1289)
[[2026-05-03]]
## Architecture Review (re-review after reviewer FAIL)

### Root Cause
AC4 claimed `workspace/` was "consistent with sibling skills (h-pytest, h-vitest, h-quality-runner)" — those siblings still use `serve/` in project-specific example blocks and have no `workspace/` occurrences. The consistency claim was false (sibling genericization is #1287, currently in review).

### AC4 Refinement
Replaced: "Notation uses `workspace/` prefix consistent with sibling skills (h-pytest, h-vitest, h-quality-runner)"
With: "Notation uses `workspace/` prefix as project-neutral path placeholder in template syntax (per parent #1280 brief convention)"

This is verifiable by inspecting the two target files:
- `share/skills/w-doc-update/SKILL.md:50` → `workspace/*/README.md`
- `share/skills/w-code-review/SKILL.md:52` → `workspace/{package}/src/`
- `share/skills/w-code-review/SKILL.md:104` → `workspace/{package}/src/`

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: verify 2 genericized skill files |
| Interface clarity | PASS | AC4 now factually verifiable without cross-file dependency |
| Dependency correctness | PASS | #1285 archived (work done); #1287 is independent |
| Module layering | PASS | Skill .md files only |
| TDD compliance | PASS | Existing test gate covers AC3/AC5 |
| KISS/YAGNI | PASS | 3 path substitutions, verification-only |
| Premise challenge | PASS | Work done in #1285; task confirms state |
| Pattern consistency | PASS | workspace/ is the brief convention for neutralized paths |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | docs/shared-layer only |

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0 (verification-only task)

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Refined AC4 to remove false sibling-consistency claim. Replaced with verifiable brief-convention reference. All other AC lines unchanged — still satisfied by parent #1285 commit 8e442bdc. Tagged type:docs retained for pass-through.
[[2026-05-03]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.