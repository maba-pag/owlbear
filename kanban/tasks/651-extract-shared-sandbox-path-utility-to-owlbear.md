---
id: 651
title: Extract shared sandbox_path utility to owlbear.paths
status: archived
priority: needed
created: 2026-03-07T23:11:04.0957583+01:00
updated: 2026-03-09T00:02:10.6326811+01:00
started: 2026-03-07T23:49:00.2956642+01:00
completed: 2026-03-09T00:02:10.6326811+01:00
tags:
    - security
    - refactor
class: standard
---

DRY: Extract the null-byte + resolve + is_relative_to pattern into a standalone `sandbox_path(root: Path, user_path: str | Path) -> Path` function in `owlbear/paths.py` (leaf module — importable by all layers including memory/).

Replace the 3 existing copy-pasted _safe_path implementations:

- FileToolset._safe_path (tools/filesystem.py)
- KnowledgeToolset._safe_path (tools/knowledge.py)
- TerminalToolset inline check (tools/terminal.py)

## Acceptance Criteria

- [ ] `owlbear/paths.py` exists with `sandbox_path(root: Path, user_path: str | Path) -> Path`
- [ ] Rejects null bytes in user_path with `PermissionError('Path outside workspace: ...')`
- [ ] Resolves `(root / user_path).resolve()` and checks `is_relative_to(root)`
- [ ] Raises `PermissionError('Path outside workspace: ...')` for paths outside root
- [ ] Returns the resolved absolute `Path` for valid paths
- [ ] `FileToolset._safe_path` delegates to `sandbox_path(self._root, user_path)`
- [ ] `KnowledgeToolset._safe_path` delegates to `sandbox_path(self._root, user_path)`
- [ ] `TerminalToolset.run_command` cwd validation delegates to `sandbox_path(self._workspace_root, working_dir)`
- [ ] All existing tests in test_filesystem_tools.py::TestSafePath, test_knowledge_toolset.py, test_terminal_tools.py still pass
- [ ] New unit tests in tests/test_paths.py: traversal (../escape), absolute outside (/etc/passwd), null byte, valid relative, dot path
- [ ] Module is a leaf — no imports from owlbear.core, owlbear.tools, owlbear.memory, owlbear.agents
- [ ] ruff clean

See docs/knowledge-intake-path-sandboxing-research.md section 3.3.

[[2026-03-08]] Sun 23:50
Wave 1, agent: auditor

[[2026-03-08]] Sun 23:57
Wave 1, agent: auditor

[[2026-03-09]] Mon 00:02
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| paths.py exists with sandbox_path | paths.py L14, correct signature | 1.0 |
| Rejects null bytes with PermissionError | paths.py L26-28 | 1.0 |
| Resolves via root/user_path + is_relative_to | paths.py L30-31 | 1.0 |
| PermissionError for outside root | paths.py L33-34 | 1.0 |
| Returns resolved absolute Path | paths.py L36 | 1.0 |
| FileToolset._safe_path delegates | filesystem.py L71 | 1.0 |
| KnowledgeToolset._safe_path delegates | knowledge.py L98 | 1.0 |
| TerminalToolset delegates | terminal.py L176 | 1.0 |
| Existing tests pass | 48 scoped, 258 full suite | 1.0 |
| New test_paths.py with required cases | 8 test methods | 1.0 |
| Leaf module no heavy imports | Only pathlib + __future__; test enforced | 1.0 |
| Ruff clean | All checks passed | 1.0 |

### Verdict: ARCHIVE (confidence 1.0)
