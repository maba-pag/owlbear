---
id: 638
title: Add editFiles to deny-code-writes.ps1 write-tool gate after schema verification
status: backlog
priority: nice-to-have
created: 2026-04-06T02:18:41.0051204+02:00
updated: 2026-04-06T03:00:27.6597292+02:00
tags:
    - scope:agents
    - hooks
    - type:build
depends_on:
    - 591
class: standard
---

## Context
During architecture review of #591, `edit/editFiles` was removed from doc-writer's tools list because the PreToolUse hook cannot extract paths from an unverified tool_input schema. VS Code docs show `{ "tool_name": "editFiles", "tool_input": { "files": ["src/main.ts"] } }` but this has no empirical confirmation in the codebase.

## Acceptance Criteria
1. Empirically verify editFiles tool_input schema by testing with a real PreToolUse hook (log stdin to a temp file, trigger editFiles via doc-writer, inspect payload)
2. If confirmed: add `editFiles` to deny-code-writes.ps1 write-tools array, add `tool_input.files[*]` path extraction (array of strings or array of objects with filePath)
3. If schema differs from VS Code docs: document actual schema, adapt extraction accordingly
4. Re-add `edit/editFiles` to doc-writer.agent.md tools list
5. Tests cover editFiles path extraction for both allow and deny cases

## Depends on
- #591 (deny-code-writes.ps1 must exist first)

[[2026-04-06]] Mon 03:00
## Research
- Research doc: .owlbear/research/editfiles-schema-verification-638.md
- Sources: 9 studied, 3 high-relevance (VS Code hooks docs, deny-src-writes.ps1, #637 research)
- Recommendation: empirical-first build — verify schema via logging hook before implementing extraction (confidence: .70)
- Follow-up tasks created: none — #638 itself is the implementation task
- Decision requests: none — T1 (config/build, no arch change)

### Key Findings
1. VS Code docs show: `{ "tool_name": "editFiles", "tool_input": { "files": ["src/main.ts"] } }` — array of strings
2. `tool_name` is `editFiles` (camelCase) — NOT snake_case like other write tools
3. Schema confidence .70 (docs-only, Preview API, zero empirical data)
4. Silent-bypass risk: wrong property name → extraction returns empty → guard passes through
5. Empirical verification via logging hook ~15 min after #591 completes

## Challenge Results
- Challenger: reconsider (confidence: .65)
- Confidence in original: .65 → revised to .70
- Key challenges: C1 confidence inflation, C2 empirical verification is task's purpose, C3 defensive extraction mitigates wrong risk
- Researcher response: accepted C1-C3 — reinstated empirical-first approach
