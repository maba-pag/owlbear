# Port Skills from .github/skills/ to skills/

> **Owning task:** #9 — Port skills to agentskills.io format
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #9 requires porting 21 skills from `.github/skills/` to `skills/` at repo root. The prior research (#3, `docs/research/agentskills-io.md`) confirmed all 21 skills are already agentskills.io compliant. This research focuses on the **migration mechanics**: what to move, what references to update, and what risks to manage during the cut-over.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | agentskills.io spec | https://agentskills.io/specification | .95 — directory structure, discovery |
| 2 | VS Code Agent Skills docs | https://code.visualstudio.com/docs/copilot/customization/agent-skills | .90 — discovery paths, `chat.agentSkillsLocations` |
| 3 | OwlBear agentskills-io research | `docs/research/agentskills-io.md` | 1.0 — prior art, compliance status |
| 4 | OwlBear .vscode/settings.json | Local file | 1.0 — current `chat.agentSkillsLocations` config |
| 5 | OwlBear validate_skills.py | `scripts/validate_skills.py` | .85 — CI validator references |

## 3. Analysis

### 3a. Inventory: What to Move

| Category | Count | Details |
|----------|-------|---------|
| Skills (SKILL.md only) | 17 | arch-review, architecture-standards, code-review, curation-workflow, decision-requests, dispatch-planning, docs-gate, knowledge-ops, orchestration, project-definition, pytest-and-linting, research-workflow, retro, task-decomposition, task-verification, tdd-red, tdd-workflow |
| Skills + `references/` | 3 | excalidraw-diagram (3 files), frontend-design (7 files), kanban-md (1 file) |
| Skills + `templates/` | 1 | visual-output (3 HTML files) |
| Already in `skills/` | 1 | mcp-kanban (v2-native, no `.github/skills/` counterpart) |
| **Total to copy** | **21** | 21 directories, 37 files total |

### 3b. Reference Update Scope

Files requiring `.github/skills/` → reference updates after migration:

| Category | Files | Edit count | Risk |
|----------|-------|------------|------|
| **Live config** (high priority) | `.github/copilot-instructions.md`, `instructions/agent-common.instructions.md`, `instructions/research-docs.instructions.md`, `agents/researcher.agent.md` | 4 edits | Medium — agents read these every session |
| **Prompts** | `.github/prompts/design-context.prompt.md`, `.github/prompts/agent-audit.prompt.md` | 2 edits | Low |
| **READMEs** | `kanban/README.md`, `skills/README.md` | 2 edits | Low |
| **Tests** | `tests/test_validate_skills_ci.py` (hard-coded `_SKILLS_DIR`), `tests/test_argument_hint_skills.py`, `tests/test_monorepo_skeleton.py`, `tests/test_setup_script.py` | 4 files | Medium — must pass after change |
| **Within skills** | `.github/skills/research-workflow/SKILL.md` → 1 cross-ref | 1 edit (in new location) | Low |
| **Historical docs** | `docs/sources/overview.md`, `docs/research/*.md`, `kanban/tasks/*.md` | ~30 refs | **Do not update** — historical record |

**Total live edits needed: ~13 files.** Historical references (sources, research docs, archived tasks) should remain as-is — they document what was true at the time.

### 3c. Migration Strategy Comparison

| Approach | Pros | Cons | Confidence |
|----------|------|------|------------|
| **A. Copy then delete** — copy all to `skills/`, update refs, verify, then delete `.github/skills/` | Safe rollback, no broken period | Temporary duplication, VS Code loads skills from both | **.85** |
| **B. Move (atomic)** — `git mv .github/skills/* skills/` in a single commit | Git tracks renames, no duplication | If settings still point to `.github/skills/`, skills break until settings update | .70 |
| **C. Symlink bridge** — move to `skills/`, symlink `.github/skills/` → `skills/` | Zero broken-reference period | Windows symlinks need admin; git doesn't track symlinks well | .40 |

**Recommendation (.85): Approach A (copy-then-delete)**, split as two tasks:
1. **Copy + update refs + verify** — ends with both locations working
2. **Delete .github/skills/** — only after verification

### 3d. Settings Already Configured

`chat.agentSkillsLocations` already maps both `.github/skills/` and `skills/` (confirmed from `scripts/setup.py` and `.vscode/settings.json` grep). **No settings change needed** for VS Code to discover skills in `skills/`. The deletion of `.github/skills/` in the final step will need the settings reference removed.

### 3e. Test Impact

| Test file | Change needed |
|-----------|--------------|
| `test_validate_skills_ci.py` | Change `_SKILLS_DIR` from `.github/skills` to `skills`, update expected count from 21 to 22 (includes mcp-kanban) |
| `test_argument_hint_skills.py` | Update file paths from `.github/skills/` to `skills/` |
| `test_monorepo_skeleton.py` | Remove assertion for `.github/skills` in `agentSkillsLocations` after `.github/skills/` is deleted |
| `test_setup_script.py` | Remove `.github/skills` path expectation after `.github/skills/` is deleted |

### 3f. Risk: Duplicate Skill Loading

During the transition (both locations active), VS Code will discover each skill twice. The spec says `name` must be unique — VS Code deduplicates by name, preferring the first discovery path. Since `.github/skills/` is a native discovery path and `skills/` is a custom one, the `.github/skills/` version takes precedence. This means the `skills/` copy won't shadow until `.github/skills/` is removed. **Not a blocker** — just means verification must happen after deletion, not before.

### 3g. Post-Copy Content Drift (discovered 2026-03-29)

After the copy (#115), task #103 modified `.github/skills/` without updating `skills/`. Three skills now diverge:

| Skill | `.github/skills/` | `skills/` | Resolution |
|-------|-------------------|-----------|------------|
| code-review | Has `vscode_listCodeUsages` guidance (#103) | Missing that guidance | Sync `.github/` content to `skills/` |
| tdd-workflow | Has `vscode_listCodeUsages` guidance (#103) | Missing that guidance | Sync `.github/` content to `skills/` |
| kanban-md | 49 lines | 52 lines (3 extra pitfall entries) | `skills/` is authoritative — no action |
| research-workflow | Old `.github/` cross-ref | Updated cross-ref (#116) | `skills/` is authoritative — no action |

**Impact:** Task #117 (delete `.github/skills/`) will lose code-review and tdd-workflow updates unless synced first. Follow-up task #131 created to resolve this before #117 proceeds.

## 4. Recommendation (.85 confidence)

Split task #9 into **4 subtasks** executed sequentially (3 original + 1 sync):

1. **Copy skills** (#115, archived) — Copy all 21 skill directories from `.github/skills/` to `skills/`.
2. **Update references** (#116, todo) — Update ~13 files with path changes.
3. **Sync drifted content** (#131, ideation) — Reconcile 2 skills where `.github/skills/` received post-copy edits.
4. **Delete .github/skills/ and finalize** (#117, ideation) — Remove old location, update settings, update setup.py.

KISS principle: the skills are already agentskills.io compliant (per #3 research). The port is a mechanical file-copy + search-and-replace, not a restructuring.

## 5. Follow-up Tasks

| Task | Title | Status |
|------|-------|--------|
| #115 | Copy 21 skills from .github/skills/ to skills/ | archived |
| #116 | Update .github/skills/ references to skills/ after copy | todo |
| #131 | Sync drifted skill content before .github/skills/ deletion | ideation |
| #117 | Delete .github/skills/ and remove dual-path settings | ideation |
