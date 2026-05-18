---
id: 1663
title: 'P2-02: IdeasPage — markdown preview toggle'
status: backlog
priority: important
created: 2026-05-18T17:42:08.354112+02:00
updated: 2026-05-18T18:13:22.024037+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1658
depends_on:
  - 1638
  - 1662
ac:
  - Toggle button switches IdeasPage between edit (textarea visible) and preview
    (rendered markdown visible); only one mode active at a time
  - Preview mode renders content with GitHub Flavored Markdown syntax support 
    (tables, strikethrough, task lists) and sanitizes HTML output
  - Switching from preview back to edit preserves textarea content without data 
    loss
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

Brief: see parent #1658 (`.owlbear/briefs/draft-cockpit-ideas/brief.md`)

Uses `ReactMarkdown` + `remark-gfm` + `rehype-sanitize` for rendering. These are npm dependencies to add.

## In Scope

- Toggle button in IdeasPage (edit ↔ preview)
- Markdown preview rendering with GFM
- HTML sanitization of rendered output
- npm dependency additions (react-markdown, remark-gfm, rehype-sanitize)

## Out of Scope

- Edit mode textarea behavior (owned by P2-01)
- Custom markdown extensions beyond GFM
- Syntax highlighting for code blocks