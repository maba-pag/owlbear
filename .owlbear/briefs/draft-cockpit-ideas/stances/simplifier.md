# Simplifier Stance — Cockpit Ideas Notebook

## Confidence: 0.85

## Cut 1 — Challenge the premise: does this need to be in the cockpit at all?

The problem statement says ideas "get lost or require context-switching to the filesystem." But the user is already in VS Code — the cockpit is a supplementary browser tab, not the primary workspace. Opening `.owlbear/ideas.md` in VS Code is `Cmd+P → ideas → Enter`. That's less friction than switching to a browser tab, clicking a nav-rail entry, waiting for a page load, typing, and hitting Save.

VS Code is a best-in-class markdown editor. The cockpit's textarea will always be worse: no syntax highlighting, no keybindings, no multi-cursor, no search-and-replace, no spell check, no split panes. Building a markdown editor inside a browser dashboard to avoid "context-switching" to an IDE that is already open is solving a problem that doesn't exist for this user profile (single laptop-resident developer).

**Pressure:** Before building anything, validate that the real friction is "I have to leave the cockpit" and not "I don't have a designated file for ideas." If the answer is the latter, create `.owlbear/ideas.md` with a heading, add it to the doc-index, and you're done — zero code.

## Cut 2 — Drop the preview toggle

The proposed component reuses TaskFieldsEditor's edit/preview pattern. For task bodies this makes sense — you're reviewing structured content with formatting, links, and checklists before committing changes to a task record. For a personal scratchpad, preview adds nothing. Nobody previews their own scratch notes. The user types a bullet point and moves on.

Dropping preview removes: ReactMarkdown rendering, remarkGfm plugin, rehypeSanitize dependency, the toggle button, and the associated state management. If you do build this (despite Cut 1), make it a textarea with a save button. That's it.

## Cut 3 — Strip mtime from the API response

The API spec returns `mtime` alongside `content`. Decision D3 explicitly says "no OCC required (single user)" and mtime is included "for potential future use." That's textbook YAGNI. Return `{content: str}`, nothing else. If OCC is ever needed, add mtime then.

## Cut 4 — Tab system coupling is a sequencing risk, not a simplification

This feature is scoped as "add a route config entry + component" once the tab system (#1638) lands. But #1638 has 10+ subtasks still in flight. This feature can't ship until that infrastructure is done, and if the tab system's shape changes during implementation, the ideas tab takes collateral damage.

**Decomposition pressure:** If the cockpit ideas feature has real value (see Cut 1), it should not be blocked by the tab system. A standalone `/ideas` route that works without the nav-rail would decouple delivery. But this further highlights that the feature may not need the cockpit at all — if you have to work around the tab system to ship it, the cockpit isn't the right home.

## Summary

| # | Cut | Impact |
|---|-----|--------|
| 1 | Validate that the problem is "cockpit capture" not "no designated file" | Potentially eliminates the entire feature |
| 2 | Drop markdown preview toggle | Removes ~40% of frontend component complexity |
| 3 | Strip mtime from API | Minor, but enforces YAGNI discipline |
| 4 | Decouple from tab system or accept sequencing dependency | Clarifies delivery boundary |

The strongest signal here is Cut 1. This is a single-user laptop tool where the IDE is always open. The proposed solution builds an inferior markdown editor inside a browser to avoid switching to a superior markdown editor that's already running. If the user validates that cockpit-resident capture genuinely matters (e.g., "I use the cockpit on a tablet away from VS Code"), then Cuts 2–4 apply to the surviving scope.
