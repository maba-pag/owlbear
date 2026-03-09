---
id: 652
title: Add workspace_root sandboxing to intake.read_file
status: archived
priority: needed
created: 2026-03-07T23:11:16.9563246+01:00
updated: 2026-03-09T00:01:53.4318576+01:00
started: 2026-03-08T01:12:33.7029106+01:00
completed: 2026-03-09T00:01:53.4318576+01:00
tags:
    - security
    - knowledge
depends_on:
    - 651
class: standard
---

SEC-11 fix: Add `workspace_root` keyword arg to `intake.read_file()` so the deepest file-reading layer rejects paths outside the workspace.

## Signature Change

Before: `async def read_file(path: str | Path) -> IntakeResult`
After:  `async def read_file(path: str | Path, *, workspace_root: Path) -> IntakeResult`

`workspace_root` is required (no default). Per project principles: no backwards compatibility.

## Acceptance Criteria

- [ ] `intake.read_file(path, workspace_root=root)` calls `sandbox_path(root, path)` from `owlbear.paths`
- [ ] Raises `PermissionError` for paths outside workspace (traversal, absolute, null byte)
- [ ] Returns `IntakeResult` for valid paths inside workspace (existing behavior preserved)
- [ ] `IngestPipeline.__init__` accepts new `workspace_root: Path` parameter
- [ ] `IngestPipeline._read_source` passes `workspace_root` to `intake.read_file`
- [ ] All callers of `IngestPipeline()` in bootstrap.py updated to pass `workspace_root`
- [ ] All callers of `intake.read_file()` updated (only `IngestPipeline._read_source`)
- [ ] Existing tests in test_knowledge_intake.py::TestReadFile updated for new kwarg
- [ ] New tests: traversal rejected, absolute outside rejected, null byte rejected, valid path accepted
- [ ] ruff clean

See docs/knowledge-intake-path-sandboxing-research.md section 3.4.

[[2026-03-08]] Sun 23:50
Wave 1, agent: auditor

[[2026-03-08]] Sun 23:57
Wave 1, agent: auditor

[[2026-03-09]] Mon 00:01
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| sandbox_path call | intake.py L47: sandbox_path(workspace_root, path) | 1.0 |
| PermissionError | paths.py L28-35: raises for null byte, traversal, abs | 1.0 |
| Returns IntakeResult | intake.py L48-53: returns IntakeResult post-sandbox | 1.0 |
| IngestPipeline workspace_root | ingest.py L88: workspace_root: Path in ctor | 1.0 |
| _read_source passes kwarg | ingest.py L401-407: workspace_root=self._workspace_root | 1.0 |
| bootstrap.py callers | knowledge.py L156,235,279 all pass workspace_root=workspace | 1.0 |
| All read_file callers | Only caller is _read_source - verified | 1.0 |
| Existing tests updated | All TestReadFile pass workspace_root, TypeError test present | 1.0 |
| New sandbox tests | traversal, absolute, null_byte, valid_path - all present | 1.0 |
| ruff clean | All checks passed | 1.0 |

Overall: 1.0
25 tests passed, ruff clean.

### Commit Log
N/A - audit only, no code changes.

### Push: N/A
