# Fix SkillRegistry Glob to Scan Subdirectory SKILL.md Files

> **Owning task:** #780 — Fix SkillRegistry glob to scan subdirectory SKILL.md files
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

`SkillRegistry._scan()` uses `self._skills_dir.glob("*.md")` — a flat glob
that matches only files directly in the skills directory. All 17 existing skills
use the VS Code convention: `{name}/SKILL.md` (one subdirectory per skill).
The registry discovers **zero skills at runtime**, though VS Code reads them fine.

**Question:** What glob pattern should replace `"*.md"`, and should the fix
support both flat files and subdirectory layouts?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python 3.12 `pathlib.Path.glob()` docs | <https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.glob> | `.90` — confirms `*/SKILL.md` matches one-level subdirs, `**/*.md` recurses |
| 2 | VS Code Agent Skills docs (2026-03-09) | <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | `.95` — canonical convention: each skill in own subdir with `SKILL.md` |
| 3 | Existing codebase `test_pipeline_e2e.py` L249-287 | (local) | `.85` — e2e test already creates `test-skill/SKILL.md` in subdir layout |
| 4 | Prior research `docs/research/knowledge-ops-skill.md` §3.3 | (local) | `.90` — identified this bug, called it "Critical" |

## 3. Analysis

### Glob pattern options

| Pattern | Matches flat `*.md` | Matches `*/SKILL.md` | Matches nested `a/b/SKILL.md` | Performance | KISS |
|---------|---------------------|----------------------|-------------------------------|-------------|------|
| `*.md` (current) | Yes | **No** | No | Fast | High |
| `*/SKILL.md` | No | **Yes** | No | Fast | High |
| `*/*.md` | No | Yes (any .md) | No | Fast | Medium |
| `**/SKILL.md` | Yes (if flat named SKILL.md) | Yes | Yes | Slower on large trees | Low |

### Decision factors

- **Convention is locked:** All 17 skills use `{name}/SKILL.md`. VS Code docs
  require this layout. There are zero flat `.md` files in the skills dir.
- **No backwards compat needed:** Project rules say "No legacy code, no backwards
  compatibility." Zero flat files exist to break.
- **KISS:** `*/SKILL.md` is the most precise pattern — one level, exact filename.
- **YAGNI:** Recursive `**` adds complexity for a nesting depth that doesn't exist.
- **Existing tests need update:** `test_skills.py` creates flat `alpha.md`/`beta.md`
  files. These must be restructured to `alpha/SKILL.md` layout.
- **e2e test already correct:** `test_pipeline_e2e.py` uses `test-skill/SKILL.md`.

### Docstring and class-level docs

The `_scan` docstring says "Walk *skills_dir* for `*.md` files" and the class
docstring says "Scans *skills_dir* for `*.md` files". Both need updating.

## 4. Recommendation (.95 confidence)

Change `glob("*.md")` to `glob("*/SKILL.md")`.

- Matches the VS Code convention exactly
- Precise (no accidental matches on README.md or other .md files in subdirs)
- No performance overhead vs current pattern
- One-line fix in `_scan()` + docstring updates + test fixture restructure

Risk: If someone later adds a flat skill file, it won't be found. Mitigation:
the convention is well-documented and enforced by VS Code — this is not a
realistic scenario.

## 5. Follow-up Tasks

The fix is atomic and small enough for a single task. The existing task #780
already covers it. No additional tasks needed — the AC is clear:

1. Change glob pattern from `"*.md"` to `"*/SKILL.md"`
2. Update `_scan` and class docstrings
3. Restructure `test_skills.py` fixtures from flat to subdir layout
4. Verify `test_pipeline_e2e.py` still passes (already uses correct layout)
5. Verify `list_skills` / `load_skill` discover all 17 real skills

```
kanban\kanban-md.exe edit 780 -b "## Acceptance Criteria\n- [ ] `_scan()` uses `glob('*/SKILL.md')` instead of `glob('*.md')`\n- [ ] Class docstring and `_scan` docstring updated\n- [ ] `test_skills.py` fixtures restructured to `{name}/SKILL.md` layout\n- [ ] All existing tests pass\n- [ ] `list_skills` discovers 17 skills when pointed at `.github/skills`" -t
```
