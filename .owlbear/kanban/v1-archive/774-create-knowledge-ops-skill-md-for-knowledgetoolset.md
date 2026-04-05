---
id: 774
title: Create knowledge-ops SKILL.md for KnowledgeToolset guidance
status: archived
priority: nice-to-have
created: 2026-03-13T10:41:51.3943036+01:00
updated: 2026-03-22T19:17:50.9938242+01:00
started: 2026-03-13T14:26:31.6341028+01:00
completed: 2026-03-22T19:17:50.9938242+01:00
tags:
    - tooling
    - docs
    - scope:core
blocked: true
block_reason: 'Superseded by #781 and existing .github/skills/knowledge-ops/SKILL.md; needs duplicate cleanup and replanning.'
class: standard
---

Superseded by #781 and not approval-ready in its current form.

If this work is re-opened after duplicate cleanup, the implementation contract must be:

- Update .github/skills/knowledge-ops/SKILL.md in place; do not create a second file and do not modify Python or test files.
- Keep YAML frontmatter parseable by SkillRegistry._parse_frontmatter() with name: knowledge-ops and a description that covers querying, ingestion, and source management.
- Include a decision tree with separate rows for: query_knowledge, ingest_document (text), ingest_document (file), ingest_document (url), list_knowledge_sources, add_source, list_sources, refresh_source, bookmark_source, and list_bookmarks.
- Document the actual parameters and valid values for the 8 exposed tools in src/owlbear/tools/knowledge.py, src/owlbear/tools/knowledge_source.py, and src/owlbear/memory/knowledge/bookmark_toolset.py.
- Scope guidance must match current implementation exactly:
  - query_knowledge auto-filters to [global, project:{id}] only when the toolset is constructed with project_scope
  - ingest_document exposes no scope parameter and currently ingests text, file, and url inputs with scope=global
  - add_source accepts scope and defaults to global
  - list_sources accepts an optional scope filter
- Domain reference must list the current enum values from src/owlbear/memory/knowledge/models.py:
  - EntityType: file, function, class_, decision, pattern, concept
  - RelationType: defines, imports, depends_on, related_to, implements, documents, governed_by
  - SourceType: url_list, crawl, file_glob
- Ingest workflow must cover text, file, and url modes, workspace-relative sandboxing for file ingest, and duplicate-content no-op behavior.
- Keep the skill concise and aligned with the existing kanban-md SKILL.md structure; do not describe parameters or behaviors that do not exist in code.

[[2026-03-21]] Sat 03:17
## Architecture Review
**Verdict:** Block

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Create .github/skills/knowledge-ops/SKILL.md | Stale: the file already exists and active task #781 targets the same deliverable. | Return to ideation for duplicate cleanup; if kept, update the existing file in place. |
| query patterns | Vague; it does not specify which tool intents must be covered. | Rewrite as a decision tree with one row per supported intent/tool. |
| ingest workflow (text/file/url) | Partially specific but omits sandboxing, duplicate-content behavior, and current scope behavior. | Rewrite to include file sandboxing, delta checking, and the actual interface limits. |
| scope conventions | Ambiguous and contradicted by the current code if read as caller-settable for all tools. | Rewrite to mirror knowledge.py and knowledge_source.py exactly. |
| format guidance | Vague; no required sections or correctness boundary. | Rewrite to require frontmatter, tool reference, domain reference, and no undocumented behavior. |

### Architecture Notes
- #774's own research output in docs/research/knowledge-ops-skill.md already created follow-up implementation task #781. Advancing #774 to todo would duplicate the pipeline.
- The target file already exists at .github/skills/knowledge-ops/SKILL.md, so the original imperative to create the file no longer matches repository state.
- The current skill content is close to the research recommendation, but it misstates scope behavior. In src/owlbear/tools/knowledge.py, query_knowledge adds scopes only when the toolset is constructed with project_scope, while ingest_document currently ingests all doc types with scope=global and exposes no scope parameter. Caller-visible scope handling lives on add_source and list_sources in src/owlbear/tools/knowledge_source.py.
- Valid enum values must come from src/owlbear/memory/knowledge/models.py; the skill must not invent extra EntityType, RelationType, or SourceType values.
- TDD: N/A. This is a docs-only skill-content task and does not request a Python behavior change.

### Changes Made
- Claimed #774 as holly-dusk
- Rewrote the task body with explicit, verifiable acceptance criteria and stale-task guidance
- Appended architecture review evidence
- Prepared task for backlog cleanup by returning it to ideation with a block reason

### Dependencies
- Verified duplicate/superseding task: #781 (in-progress)
- Verified referenced interfaces: src/owlbear/tools/knowledge.py, src/owlbear/tools/knowledge_source.py, src/owlbear/memory/knowledge/bookmark_toolset.py, src/owlbear/memory/knowledge/models.py, src/owlbear/skills/registry.py
