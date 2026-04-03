---
id: 546
title: 'Add apply_patch to #210 lint guard tool_name filter'
status: backlog
priority: needed
created: 2026-04-02T14:51:56.2992239+02:00
updated: 2026-04-02T15:51:06.4369459+02:00
tags:
    - scope:agents
    - hooks
    - type:build
depends_on:
    - 210
class: standard
---

## Context
Empirical verification (#532, docs/research/posttooluse-subagent-output-routing.md s3.6) discovered that the builder uses tool_name 'apply_patch' for file edits. Task #210's AC currently filters on create_file|replace_string_in_file|multi_replace_string_in_file only, missing apply_patch.

## Acceptance Criteria
- [ ] #210 lint guard script matches apply_patch in addition to existing tool_names
- [ ] Verified via hook log that apply_patch triggers lint check

[[2026-04-02]] Thu 15:50
## Research
See docs/research/apply-patch-lint-guard-filter.md for full findings.

Key findings:
- apply_patch confirmed as builder edit tool_name (#532 empirical, VS Code hooks docs)
- tool_input format unknown: likely tool_input.filePath or tool_input.patch with diff headers
- T1 classification: filter extension, no new capability or arch change
- depends_on #210 added: script must exist before modification

Refined AC guidance:
- Add apply_patch to tool_name regex in lint-changed.ps1
- For path extraction: try tool_input.filePath first, fall back to diff header parsing
- Add test cases parallel to existing AC3a-AC3f for apply_patch tool_name
- Builder should log actual apply_patch tool_input JSON to confirm format

[[2026-04-02]] Thu 15:50
## Research
See docs/research/apply-patch-lint-guard-filter.md for full findings.

Key findings:
- apply_patch confirmed as builder edit tool_name (#532 empirical, VS Code hooks docs)
- tool_input format unknown: likely tool_input.filePath or tool_input.patch with diff headers
- T1 classification: filter extension, no new capability or arch change
- depends_on #210 added: script must exist before modification

Refined AC guidance:
- Add apply_patch to tool_name regex in lint-changed.ps1
- For path extraction: try tool_input.filePath first, fall back to diff header parsing
- Add test cases parallel to existing AC3a-AC3f for apply_patch tool_name
- Builder should log actual apply_patch tool_input JSON to confirm format
