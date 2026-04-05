# Update .github/skills/ References to skills/

> **Owning task:** #116 — Update .github/skills/ references to skills/ after copy
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #115 (copy 21 skills) is done. The `skills/` directory now has all 22 skills (21 ported + mcp-kanban). This research verifies that #116's acceptance criteria are correct and complete — i.e., do the listed files capture every live `.github/skills/` reference that should update?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `docs/research/port-skills-to-v2.md` §3b — original reference map | 1.0 |
| 2 | Workspace-wide grep for `.github/skills/` — 2026-03-29 | 1.0 |
| 3 | kanban-md show #115, #116 — task state | .90 |

## 3. Analysis

### Verified reference map (live files only)

| File | Line(s) | Ref count | In AC? |
|------|---------|-----------|--------|
| `.github/copilot-instructions.md` | 129 | 1 | Yes |
| `instructions/agent-common.instructions.md` | 49 | 1 | Yes |
| `instructions/research-docs.instructions.md` | 20 | 1 | Yes |
| `agents/researcher.agent.md` | 48 | 1 | Yes |
| `.github/prompts/design-context.prompt.md` | 61 | 1 | Yes |
| `.github/prompts/agent-audit.prompt.md` | 17 | 1 | Yes |
| `kanban/README.md` | 32 | 1 (text + href) | Yes |
| `skills/README.md` | 4 | 1 (outdated text) | Yes |
| `skills/research-workflow/SKILL.md` | 99 | 1 | Yes |
| `tests/test_validate_skills_ci.py` | 28 | 1 (`_SKILLS_DIR`) | Yes |
| `tests/test_argument_hint_skills.py` | 8–9 | 2 | Yes |

### References intentionally excluded (scoped to #117 — delete .github/skills/)

| File | Lines | Reason to skip |
|------|-------|----------------|
| `tests/test_copy_skills_to_root.py` | many | Tests #115 copy; reads from `.github/skills/` as source |
| `tests/test_monorepo_skeleton.py` | 274–278 | Asserts `.github/skills` in agentSkillsLocations |
| `tests/test_setup_script.py` | 117–126 | Asserts `.github/skills` in setup output |
| `.github/skills/research-workflow/SKILL.md` | 99 | Will be deleted with `.github/skills/` |
| Historical docs, archived tasks | ~30 refs | AC explicitly excludes them |

### Replacement strategy

Each reference is a simple string replacement: `.github/skills/` → `skills/`. No content restructuring needed.

Special cases:
- **`kanban/README.md`**: Both link text and href need updating (`[.github/skills/kanban-md/SKILL.md](../.github/skills/kanban-md/SKILL.md)` → `[skills/kanban-md/SKILL.md](../skills/kanban-md/SKILL.md)`)
- **`skills/README.md`**: Rewrite to reflect that `skills/` is now the primary location (remove "transition placeholder" language)
- **`test_validate_skills_ci.py`**: Change `_SKILLS_DIR` from `_REPO_ROOT / ".github" / "skills"` to `_REPO_ROOT / "skills"` and update expected count from 21 to 22

## 4. Recommendation (.95 confidence)

AC is **correct and complete**. No missing references for the #116 scope. No additional files need updating. The task is a mechanical find-and-replace with 11 file edits and a test verification pass.

N/A — trivial change (path updates after file copy). No architectural decisions, no alternative approaches. KISS applies: just replace the paths.

## 5. Follow-up Tasks

No new tasks needed — #116 covers all live reference updates, and #117 already covers the deletion + settings cleanup.
