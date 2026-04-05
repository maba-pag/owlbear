# Delete .github/skills/ and Remove Dual-Path Settings

> **Owning task:** #117 — Delete .github/skills/ and remove dual-path settings
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

After porting all 21 skills from `.github/skills/` to `skills/` (#115), updating references (#116), and syncing drifted content (#131), the `.github/skills/` directory is now redundant. Task #117 deletes it and removes dual-path configuration. This research validates the AC completeness and identifies risks.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | VS Code Agent Skills docs | https://code.visualstudio.com/docs/copilot/customization/agent-skills | .90 — confirms `.github/skills/` is a native auto-discovery path; `chat.agentSkillsLocations` adds custom paths |
| 2 | agentskills.io specification | https://agentskills.io/specification | .85 — skill location is not mandated; any directory works |
| 3 | OwlBear port-skills research | `docs/research/port-skills-to-v2.md` | 1.0 — migration plan, sections 3c–3f cover deletion strategy |
| 4 | OwlBear codebase grep | Local `.github/skills` references | 1.0 — 20 Python hits, 30+ markdown hits audited |

## 3. Analysis

### 3a. Dependency Chain Verification

| Predecessor | Status | Blocker? |
|-------------|--------|----------|
| #115 — Copy skills | archived | No |
| #116 — Update references | done | No |
| #131 — Sync drifted content | review | **Yes — must complete before #117** |

**Critical gap:** `depends_on` only lists `[116]`. Must add `131` before the task proceeds.

### 3b. AC Gap Analysis

| Current AC item | Assessment |
|----------------|------------|
| Delete .github/skills/ directory | OK |
| Remove from .vscode/settings.json | OK |
| Update scripts/setup.py | OK — line 36 has the `.github/skills` entry |
| Update test_monorepo_skeleton.py | OK — 3 assertions on lines 274–278 |
| Update test_setup_script.py | OK — 3 assertions on lines 117–126 |
| Verify 22 skills load from skills/ | OK — `test_validate_skills_ci.py` already validates from `skills/` |
| All tests pass | OK |

**Missing AC items (4 gaps found):**

| Gap | Files affected | Impact |
|-----|---------------|--------|
| Add `depends_on: 131` | Task frontmatter | High — premature deletion loses synced content |
| Delete/archive `tests/test_copy_skills_to_root.py` | 1 file, ~160 lines | High — reads from `.github/skills/` (42 parametrized tests), all will error |
| Update/delete `tests/test_skill_sync_131.py` | 1 file, ~145 lines | High — lines 42, 78 read from `.github/skills/` via `GITHUB_SKILLS` constant |
| Update `docs/decisions/README.md` line 49 | 1 line | Low — stale `.github/skills/` reference in live doc |

### 3c. Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Skills stop loading | Low | `chat.agentSkillsLocations` already maps `skills/`; `test_validate_skills_ci.py` validates all 22 |
| Test failures from orphaned test files | High if missed | AC must include test_copy_skills_to_root.py and test_skill_sync_131.py cleanup |
| Content lost | Low | #131 syncs all drifted content before deletion |
| VS Code native path confusion | None | `.github/skills/` is auto-discovered; after deletion, discovery falls to custom `skills/` path — intended behavior (sources 1, 2) |

### 3d. Test File Disposition

Both test files validated predecessor tasks and become obsolete once `.github/skills/` is deleted:

- **test_copy_skills_to_root.py** — AC3/AC4 tests compare `skills/` to `.github/skills/`. After deletion, the source is gone. Delete the file.
- **test_skill_sync_131.py** — Two test classes read from `GITHUB_SKILLS` path. After deletion, these error. Tests for `skills/`-only content (kanban-md pitfalls, research-workflow cross-ref) could survive but are already covered by `test_validate_skills_ci.py`. Delete the file.

## 4. Recommendation (.90 confidence)

The task is well-scoped. The architect should refine the AC to add:

1. `depends_on: [116, 131]` — prevent premature deletion
2. Delete `tests/test_copy_skills_to_root.py` — obsolete after source removal
3. Delete `tests/test_skill_sync_131.py` — obsolete after source removal
4. Update `docs/decisions/README.md` line 49 — change `.github/skills/` to `skills/`

No new follow-up tasks needed — all gaps are refinements to #117 itself.

## 5. Follow-up Tasks

None — findings refine #117's AC rather than creating new work. The architect gate will incorporate the 4 AC additions identified in section 3b.
