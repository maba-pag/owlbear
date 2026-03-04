---
id: 461
title: Add run_command to default approval policy
status: ideation
priority: critical
created: 2026-03-04T07:37:41.925532+01:00
updated: 2026-03-04T07:37:41.925532+01:00
tags:
    - audit
    - security
    - config
class: standard
---

SEC-05: Default approval_policy gates git_push, create_pr, deploy but NOT run_command. Shell execution is currently ungated. Single highest-impact security fix. AC: run_command in default policy, tests verify approval trigger. See docs/security-audit.md.
