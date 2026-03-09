---
id: 497
title: Add path sandboxing to knowledge intake
status: archived
priority: important
created: 2026-03-04T07:38:11.4324226+01:00
updated: 2026-03-09T20:44:07.3768002+01:00
started: 2026-03-06T23:31:39.0730282+01:00
completed: 2026-03-09T20:44:07.3768002+01:00
tags:
    - audit
    - security
    - knowledge
class: standard
---

SEC-11: intake.py read_file() reads any path without sandboxing.

**SPLIT** by architect into 3 atomic tasks:
- #651  Extract shared sandbox_path utility to owlbear.paths
- #652  Add workspace_root sandboxing to intake.read_file
- #654  Add path sandboxing to RefreshOrchestrator._handle_file_glob

See docs/knowledge-intake-path-sandboxing-research.md for full analysis.

[[2026-03-09]] Mon 20:44
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SEC-11: intake.py read_file without sandboxing | intake.py L47: sandbox_path(workspace_root, path) guards all reads | PASS |
| Split into #651 #652 #654 | All 3 subtasks archived (confidence 1.0, 1.0, .98) | PASS |
| sandbox_path utility created | paths.py L14-36: null byte + resolve + is_relative_to | PASS |
| _handle_file_glob sandboxed | refresh.py L171: sandbox_path on base_dir + L180 per-item | PASS |
| Delegations wired | filesystem.py L71, knowledge.py L98, terminal.py L176 | PASS |

### Test Results
- pytest (scoped): 75 passed, 0 failed
- ruff: All checks passed

### Confidence: .98
### Action: archive
