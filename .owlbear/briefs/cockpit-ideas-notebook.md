# Cockpit Ideas Notebook

## Problem

There's no place for pre-task ideas. The kanban board is for structured, SMART tasks — but ideas start vague ("that repo looks interesting", "X feels broken", "we should refactor Y eventually"). Currently these thoughts either get lost or are forced prematurely into task format.

The cockpit is read+modify only — no creation, no freeform input. The user has to context-switch to an agent conversation to capture anything.

## Proposed Feature

A single markdown file (`.owlbear/ideas.md`) with a dedicated cockpit tab to read and edit it.

### Workflow

1. User has a vague idea
2. Opens the "Ideas" tab in cockpit, jots it down in markdown
3. Idea sits there until the user is ready to act on it
4. When ready: user starts an ideation prompt referencing the ideas file
5. Ideation agent picks up the notes, structures them into tasks/briefs

### What it is NOT

- Not a second kanban board
- Not structured data with fields/status/priority
- Not an agent-consumed format — it's a **human scratch pad**
- Not multiple files — one file, one view

### Backend

- `GET /api/ideas` — return `{content: str, mtime: str}`
- `PUT /api/ideas` — accept `{content: str}`, write to file, return updated mtime
- File location: `.owlbear/ideas.md`
- Write via `atomic_write` for crash safety
- File is git-tracked, visible to agents via filesystem
- No OCC required (single user) — mtime returned for potential future use

### Frontend

- New route/tab: "Ideas" in the cockpit navigation
- Split or toggle view: edit (textarea) and preview (rendered markdown)
- "Save" button that calls `PUT /api/ideas`
- Minimal chrome — no toolbar, no formatting buttons, just text and rendered output
- Consider auto-save on blur or after idle timeout (v2)

### File format

Plain markdown. No frontmatter, no structure imposed. The user writes whatever they want.

```markdown
# Ideas

## Frontend
- The task detail panel feels cramped on mobile
- Maybe add keyboard shortcuts for common actions?

## Backend  
- Look into that caching library someone mentioned
- The activity log compaction could be smarter

## Research
- Check if Anthropic's new tool-use format changes anything for MCP
```

### Scope

- One new API route pair (~20 lines backend)
- One new cockpit page component
- One new navigation entry
- File creation: `.owlbear/ideas.md` (empty or with a header)

### Extensions (not initial scope)

- Auto-save on idle timeout
- Multiple notebook files (`.owlbear/ideas/*.md`) with file picker
- Search within notes
- Link ideas to tasks (after ideation produces tasks from an idea, cross-reference)
- Collaborative editing (if multi-user ever happens)
