---
id: 524
title: Expand validator role policy denied tools
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:32.0256337+01:00
updated: 2026-03-04T07:38:32.0256337+01:00
tags:
    - audit
    - security
    - scope:core
class: standard
---

ARC-20: VALIDATOR_POLICY only denies write_file and create_file. Doesnt restrict run_command, git_commit, git_push, browser_click, browser_type. Validator agent could still execute arbitrary shell commands. Expand denied set or switch to allow-list. AC: validators cant execute destructive ops. See docs/architecture-audit.md.
