---
id: 1789
title: Improve task tag and dependency editors
status: research
priority: important
created: 2026-05-24T01:57:03.668567+02:00
updated: 2026-05-24T03:09:50.702199+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - forms
  - discussion
parent: 1773
depends_on: []
ac:
  - Tag editing has a clear, compact, aligned add flow.
  - Dependency editing makes multi-dependency input explicit and does not rely 
    on guessed separators.
  - Structured collection fields behave consistently where practical.
  - No implementation begins until the user approves this task.
  - Parent uses the same task-reference interaction vocabulary as dependencies, 
    adapted for a single value.
  - Tag input avoids misleading natural-language spellcheck behavior unless 
    later evidence says otherwise.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User feedback on task detail edit fields:
- The tags editor flow is not logical: current tags first, then an add-new-tags field with label, then Add button.
- The Add button is not vertically aligned with the tag input field.
- The tag input is vertically large and may want compact treatment; user suggested compact and asked whether spellcheck for tags is good or bad.
- The Depends On field should behave more like tags: a list where the user can add items. Currently it is just a text field, and it is unclear whether multiple dependencies should use commas, spaces, or another syntax.

## Current Interpretation
Observed form UX issue. Tag/dependency editing is too text-field-like for structured data and does not make valid input syntax obvious.

## Value
Task metadata editing should be safe and self-explanatory. Tags and dependencies are structured collections, so users should not need to guess separators or hidden parsing rules.

## Discussion Questions
- Should tag input use spellcheck=false because tags are identifiers, or spellcheck=true because many tags are natural-language labels?
- Should dependency input search existing tasks by ID/title, accept pasted IDs, or both?
- Should Add buttons be inline compact icon/buttons aligned with each input?

[[2026-05-24T03:09:50+02:00]]
## Decision
User chose `Compact chip adders`. Tags, dependencies, and parent should use a consistent compact structured-input vocabulary. Tags/dependencies use compact input + aligned Add + chips/list; Parent should feel like the same task-reference control even though it accepts at most one task.

## Discussion Note
Tags are token-like, so spellcheck should likely be disabled for tag input. Dependencies and parent are task references and should not require users to guess comma/space syntax.
