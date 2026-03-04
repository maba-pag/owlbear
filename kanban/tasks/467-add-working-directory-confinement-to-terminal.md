---
id: 467
title: Add working directory confinement to terminal toolset
status: ideation
priority: needed
created: 2026-03-04T07:37:47.0146661+01:00
updated: 2026-03-04T07:37:47.0146661+01:00
tags:
    - audit
    - security
    - tools
class: standard
---

SEC-02: working_dir parameter accepts any absolute path. Filesystem tools are sandboxed to workspace_root but terminal can operate anywhere. Apply same _safe_path pattern. AC: PermissionError for paths outside workspace, test covers traversal attempt. See docs/security-audit.md.
