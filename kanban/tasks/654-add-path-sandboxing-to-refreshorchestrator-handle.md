---
id: 654
title: Add path sandboxing to RefreshOrchestrator._handle_file_glob
status: archived
priority: needed
created: 2026-03-07T23:11:33.1151799+01:00
updated: 2026-03-09T00:13:49.5501585+01:00
started: 2026-03-08T00:33:46.1508076+01:00
completed: 2026-03-09T00:13:49.5501585+01:00
tags:
    - security
    - knowledge
depends_on:
    - 651
class: standard
---

SEC-11 related: `_handle_file_glob` accepts `base_dir` from source config without validation. An attacker-controlled source config could glob arbitrary directories.

## Acceptance Criteria

- [ ] `_handle_file_glob` validates `base_dir` with `sandbox_path(self._workspace_root, base_dir_str)` before globbing
- [ ] When `base_dir` is None, defaults to `self._workspace_root` (existing behavior, no check needed)
- [ ] When `base_dir` resolves outside workspace, raises `PermissionError`
- [ ] Each resolved glob path is validated with `sandbox_path` before ingestion (guard against symlink escapes)
- [ ] `_ingest_items` receives only sandboxed paths
- [ ] Tests: base_dir outside workspace raises, glob result with symlink escape skipped/rejected, valid base_dir + pattern works
- [ ] ruff clean

See docs/knowledge-intake-path-sandboxing-research.md section 3.5.

[[2026-03-08]] Sun 23:50
Wave 1, agent: auditor

[[2026-03-08]] Sun 23:57
Wave 2, agent: auditor

[[2026-03-09]] Mon 00:13
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| sandbox_path on base_dir | refresh.py L171: sandbox_path(self._workspace_root, base_dir_str) | .98 |
| None base_dir defaults to workspace_root | refresh.py L173: base = self._workspace_root | .98 |
| base_dir outside workspace raises PermissionError | test_base_dir_outside_workspace_raises + test_base_dir_traversal_raises pass | .98 |
| Each glob path validated with sandbox_path | refresh.py L180-184: loop with sandbox_path per item | .98 |
| _ingest_items receives only sandboxed paths | items list built from sandboxed strs only | .97 |
| Tests cover all scenarios | 6 tests in TestFileGlobSandboxing: outside raises, traversal raises, symlink skip, valid works, None default, mixed filter | .98 |
| ruff clean | All checks passed | 1.0 |

### Verdict
Confidence: .98  all 7 AC items verified with code evidence and passing tests.
