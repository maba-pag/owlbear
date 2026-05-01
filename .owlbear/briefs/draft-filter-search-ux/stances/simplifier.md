# Simplifier Stance — Task 1232: Filter/Search UX

**Date:** 2026-05-01
**Confidence:** 0.80

---

## Three Cuts

**Cut 1 — Tag multi-select AND → defer or simplify.**
AND semantics on a multi-valued field produce surprisingly small result sets.
~35 active tasks rarely need cross-tag intersection filtering. A single-tag
select (or no tag filter at all in v1) covers the real use case without the
UX trap of "why does my filter show nothing?"

**Cut 2 — Active filter chips → badge only.**
Chips are redundant while the panel is one click away. A `"Filter (2)"` label
on the toggle button gives the same signal for ~3 lines of code vs. a whole
component. If users find the badge insufficient, add chips in a follow-up.

**Cut 3 — Empty column placeholder → hide empty columns.**
With 35 tasks across 8 statuses, most columns have tasks. Showing "0 tasks"
placeholders during filtering is visual noise. Hide empty columns when a
filter is active; restore them when filter is cleared.

---

## Recommended P1 Scope

Text search input + priority single-select + blocked toggle + toggle-button
badge showing active count. **No** tag multi-select (defer). **No** chips
(badge only). Ship that. Measure whether anyone needs tags or chips before
building them.

**Result:** ~80 lines of TypeScript, 1 new sub-component, no new API calls.
