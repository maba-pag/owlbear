---
id: 1930
title: Document auto-staged collector archive recovery
status: build
priority: medium
created: 2026-07-14T01:12:22.720349+02:00
updated: 2026-07-14T01:32:56.509387+02:00
tags:
  - agent
  - kanban
  - type:docs
parent:
depends_on: []
ac:
  - Safe exact-path auto-stage recovery is documented
  - Ambiguous staged ownership is never silently unstaged
  - Collector lifecycle links the recovery procedure
  - Focused regression guard covers the contract
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Define the safe recovery procedure when collector archival is auto-staged before `commit-owned` runs.

## Acceptance Criteria
- Governance requires inspection of both owned task/archive paths before unstaging.
- Recovery unstages only the verified task-owned paths and retries `commit-owned`.
- Ambiguous or mixed owned-path content routes to `COMMIT_FAILED` rather than being unstaged.
- Collector-facing lifecycle guidance points to the procedure.
- A focused regression assertion prevents removal of the recovery contract.

[[2026-07-14T01:14:20+02:00]]
## Builder Notes

- Change envelope: document safe recovery when collector archive paths are auto-staged before `commit-owned`.
- Added `Owned Auto-Staging Recovery` to workspace governance: exact two-path cached diff inspection, strict ownership/rename check, `COMMIT_FAILED` on ambiguity, exact-path reset, and scoped retry.
- Clarified that `git reset` may list unrelated unstaged paths without modifying their index state.
- Added collector-facing lifecycle pointer and focused static assertions.
- Proof: `uv run pytest tests/test_skill_authority_wiring.py -q` -> 4 passed; Ruff clean; all 23 agent files validate; diff check clean.
- Builder challenger: pass; no concrete blocker.

[[2026-07-14T01:19:22+02:00]]
## Verify Notes

- Verified commit `ddd1ef8292334fb51795833fef76646056df3a7f`; focused tests, Ruff, and agent validation pass.
- Verifier challenger found the ownership gate insufficient: cached `--name-status` proves the expected rename path but cannot prove the staged archive blob contains no pre-existing user edits.
- No verifier patches applied.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Require content-level proof before unstaging: verify the staged archive blob matches the committed pre-archive task blob; route any mismatch or unavailable comparison to `COMMIT_FAILED`. Update the focused assertion. | `share/skills/r-workspace-governance/SKILL.md`, `tests/test_skill_authority_wiring.py` | Verifier challenger: name-status alone cannot establish staged content ownership. |

[[2026-07-14T01:27:12+02:00]]
## Builder Notes

- Adopted verifier follow-up: name-status alone is insufficient to prove staged content ownership.
- Recovery now requires content-level proof: compare the committed pre-archive task blob with the staged archive blob using `git rev-parse`; proceed only when both resolve, IDs match, and the staged shape is exactly the expected rename.
- Any mismatch, missing object, or unexpected staged shape routes to `COMMIT_FAILED` without unstaging.
- Scope boundary: recovery remains an agent procedure because generic `commit-owned` intentionally lacks Kanban/task semantics and continues to reject all pre-staged owned paths.
- Proof: focused tests 4 passed; Ruff and diff check clean.
- Builder challenger: pass after reassessment against the documentation task and helper safety boundary.

[[2026-07-14T01:32:56+02:00]]
## Verify Notes

- Verified repair commit `03ebc5fedf1923f547b9bc4086f7d3059b7e5224`; tests, lint, and agent validation pass.
- Initial challenge identified that post-`end_work` content normally differs from HEAD.
- Reassessment confirmed a safe narrow recovery: require cached `R100` plus staged archive blob equality with the pre-archive HEAD task blob. This proves only the stale pure-rename state observed, where collector-authored final content remains unstaged; reset then lets `commit-owned` stage the complete working-tree archive.
- No verifier patches applied.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | State the recovery as narrow to cached `R100` stale pure renames; explain that collector-authored final content remains in the working tree and is staged by the retry. Fail closed for every other staged shape/blob. | `share/skills/r-workspace-governance/SKILL.md`, `tests/test_skill_authority_wiring.py` | Verifier challenger reassessment: proposed precision resolves blocker. |
