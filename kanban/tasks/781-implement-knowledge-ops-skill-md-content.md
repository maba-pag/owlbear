---
id: 781
title: Implement knowledge-ops SKILL.md content
status: in-progress
priority: nice-to-have
created: 2026-03-13T14:31:20.9656179+01:00
updated: 2026-03-13T20:46:12.6329485+01:00
tags:
    - tooling
    - docs
    - scope:core
class: standard
---

Write .github/skills/knowledge-ops/SKILL.md covering: decision tree (10-12 rows), tool reference (8 tools across 3 toolsets), scope conventions (global vs project:{id}), domain reference (EntityType/RelationType/SourceType), ingest workflow (text/file/url + delta checking). Follow kanban-md SKILL.md structure. Max ~150 lines. See docs/research/knowledge-ops-skill.md S4.

[[2026-03-13]] Fri 20:02
## Research Validation

**Checklist:**
- [x] Theoretical validity: SKILL.md for 8 tools across 3 toolsets is sound (LlamaIndex confirms description quality matters)
- [x] Prior art: kanban-md SKILL.md (17 skills use same pattern), LlamaIndex + PydanticAI docs
- [x] Technical feasibility: .md file in .github/skills/knowledge-ops/  no blockers
- [x] Architecture fit: matches existing skill directory pattern exactly
- [x] Implementation approach: mirror kanban-md SKILL.md structure

**Depends on:** #780 (SkillRegistry glob fix) for runtime discovery. VS Code reads it now.

**AC (from research doc):**
- [ ] YAML frontmatter with name: knowledge-ops and descriptive description
- [ ] Decision tree table mapping agent intent to tool name (10-12 rows)
- [ ] All 8 tools documented with parameters and valid values
- [ ] Scope conventions section (global vs project:{id})
- [ ] Domain reference with EntityType, RelationType, SourceType valid values
- [ ] Ingest workflow section (text/file/url + delta checking)
- [ ] SkillRegistry._parse_frontmatter() succeeds on the file
- [ ] Max ~150 lines

[[2026-03-13]] Fri 20:45
## Test-Writer Notes
- Non-implementation task (tagged docs, tooling)  deliverable is a .md file, no new Python code.
- AC #7 (SkillRegistry._parse_frontmatter succeeds) tests existing code against new content  content validation, not code feature.
- Passing through to builder.

[[2026-03-13]] Fri 20:45
## Test-Writer Notes

[[2026-03-13]] Fri 20:45
- Non-implementation task (tagged docs, tooling) -- deliverable is a .md file, no new Python code.
- AC #7 (SkillRegistry._parse_frontmatter succeeds) tests existing code against new content -- content validation, not code feature.
- Passing through to builder.

[[2026-03-13]] Fri 20:45
- Non-implementation task (tagged docs, tooling) -- deliverable is a .md file, no new Python code.
- AC #7 (SkillRegistry._parse_frontmatter succeeds) tests existing code against new content -- content validation, not code feature.
- Passing through to builder.
