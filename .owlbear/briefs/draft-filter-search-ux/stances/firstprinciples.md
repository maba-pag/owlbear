# First-Principles Stance — Task 1232: Filter/Search UX

**Date:** 2026-05-01
**Confidence:** 0.82

---

## Irreducible Core

Users with ~35 active tasks cannot locate a specific task or isolate a
meaningful subset without manually scanning all columns.

The minimum addressable artifact is: **a text input that client-side filters
visible cards by title fragment.** One `<input>`, one filter pass, no panel,
no chips, no dropdowns. That solves the stated primary pain point.

---

## Challenges

**1. The board is the wrong surface for "see all blocked tasks."**
The kanban board encodes workflow state spatially — columns *are* the data.
Filtering to blocked tasks across 8 columns produces 8 mostly-empty columns
with "0 tasks" placeholders. That is not a useful view of blocked tasks; a
flat sorted list is. The board shape is inherited from "this is where tasks
live," not from "this is how search results should present." The empty-columns
requirement is a downstream symptom of this mismatch.

**2. AND semantics on tags is a borrowed database instinct.**
OR is the natural default for tag filtering (show me anything tagged
`frontend` or `P1`). AND produces surprising tiny result sets. No evidence
given that AND matches the user's mental model. Name this choice explicitly;
don't inherit it.

**3. "Blocked" is computed state, not a tag.**
The proposed blocked toggle implies the task payload exposes a filterable
`blocked` boolean at the API layer. If that field doesn't already exist in
the cockpit response, this toggle is an architecture assumption smuggled into
a UX proposal. Verify the wire shape before committing.

**4. No persistence is a real tradeoff, not a neutral default.**
If the user repeatedly applies the same filter session over session, no
persistence is an active cost. State it as a decision, not an omission.

---

## What Is and Isn't Load-Bearing

| Claim | Necessary? |
|-------|-----------|
| Client-side text search | Yes — this is the irreducible fix |
| Priority and tag filters | Useful, not irreducible |
| AND tag semantics | Borrowed — should be OR by default |
| Empty columns during filter | Questionable — flat list beats this |
| Active filter chips | Convenience, not necessary |
| No persistence | Decision, not neutral default |
| Blocked toggle | Requires wire-shape verification first |
