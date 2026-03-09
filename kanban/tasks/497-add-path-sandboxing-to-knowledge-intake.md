---
id: 497
title: Add path sandboxing to knowledge intake
status: done
priority: important
created: 2026-03-04T07:38:11.4324226+01:00
updated: 2026-03-07T23:11:42.094359+01:00
started: 2026-03-06T23:31:39.0730282+01:00
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
