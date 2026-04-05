---
id: 519
title: Extract shared sandbox_path utility from duplicated _safe_path
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:28.7733322+01:00
updated: 2026-03-22T18:59:23.1235364+01:00
started: 2026-03-06T23:58:23.339179+01:00
completed: 2026-03-10T04:38:28.3792932+01:00
tags:
    - audit
    - dry
    - refactor
    - tools
    - duplicate
class: standard
---

ARC-11/DRY-03: Identical _safe_path logic in FileToolset and KnowledgeToolset. Same null-byte check, same resolve+boundary check, same error message. Extract to owlbear.core.paths.sandbox_path(). AC: single implementation, both toolsets use it. See docs/architecture-audit.md, docs/software-design-audit.md.

---

## Research Findings (2026-03-06)

**DUPLICATE OF #497 FOLLOW-UP.** Task #497 research (docs/research/knowledge-intake-path-sandboxing.md, section 3.3) already analyzed this extraction with .85 confidence and proposed the same shared utility.

### Overlap Summary

| Aspect | This task (#519) | #497 Research |
|---|---|---|
| Problem | 2x identical _safe_path | 3x copy-paste including TerminalToolset |
| Location | owlbear.tools._path_utils | owlbear.core.paths (better) |
| Scope | Toolsets only | Toolsets + intake + RefreshOrchestrator |
| Research | Not started | Complete: sources, matrix, .85 confidence |

### Verified Findings

1. FileToolset._safe_path (filesystem.py L59-76) and KnowledgeToolset._safe_path (knowledge.py L88-105) are character-for-character identical (minus one comment).
2. TerminalToolset (terminal.py L170-184) has same pattern inline with minor variant for absolute paths.
3. #497 recommends owlbear.core.paths (intake.py also needs it, not just toolsets).
4. #497 follow-up tasks proposed but never created as kanban entries.

### Recommendation

Merge into #497. Step 4 of #497 research recommendation covers #519 entirely. Close as duplicate or block on #497.

[[2026-03-10]] Tue 04:38
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Single sandbox_path implementation | paths.py L14: sandbox_path(root, user_path)  single function, leaf module | PASS |
| FileToolset uses it | filesystem.py L71: return sandbox_path(self._root, user_path) | PASS |
| KnowledgeToolset uses it | knowledge.py L98: return sandbox_path(self._root, user_path) | PASS |

### Context
Task is a duplicate of #651 (subtask of archived #497). Work was completed and archived under #651 at confidence 1.0. All three AC items satisfied by the same implementation.

### Test Results
- pytest (scoped: test_paths, test_filesystem_tools, test_knowledge_toolset): 65 passed, 0 failed
- pytest (full suite excl. daemon): 3825 passed, 29 failed (all pre-existing, none related to sandbox_path)
- ruff: All checks passed (paths.py, filesystem.py, knowledge.py)

### Confidence: .98
### Action: archive (duplicate resolved by #651)
