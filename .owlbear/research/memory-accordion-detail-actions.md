# Memory Accordion Detail and State-Dependent Actions

> **Owning task:** #1672 — P3-02: Memory accordion detail and state-dependent actions
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

Task #1672 extends the read-only MemoryTab (built in #1671) with interactive accordion detail panels and CRUD mutation actions. Key questions: (1) How to integrate PAccordion per entry without DOM bloat, (2) what sanitization schema to use for markdown rendering, (3) how to handle the three mutation patterns (approve/edit/delete) with different response shapes, (4) how to surface the pending count badge at shell level.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| PDS v4 Accordion API docs (designsystem.porsche.com) | External | 0.9 — props, events, slots |
| rehype-sanitize README (github.com/rehypejs) | External | 0.9 — custom schema pattern |
| `serve/cockpit/web/src/components/DetailTab.tsx` | Codebase | 0.8 — PAccordion usage pattern |
| `serve/cockpit/web/src/components/ResolveModal.tsx` | Codebase | 0.9 — ReactMarkdown + rehypeSanitize |
| `serve/cockpit/web/src/components/ConfirmDialog.tsx` | Codebase | 0.9 — PModal with focus trap |
| `serve/cockpit/web/src/api/tasks.ts` | Codebase | 0.8 — fetch POST + ApiError pattern |
| `serve/cockpit/web/src/hooks/CockpitProvider.tsx` | Codebase | 0.9 — shell-level state lifting |
| `serve/cockpit/web/src/api/errorMessage.ts` | Codebase | 0.8 — current 422 handling gap |
| Git commit a507483d (NavBadge #1646) | Codebase | 0.9 — badge rendering pattern |
| `serve/cockpit/src/owlbear_cockpit/routes/memory.py` | Codebase | 1.0 — API response shapes |

## 3. Analysis

### 3.1 Accordion Strategy

| Approach | Pros | Cons | Score |
|----------|------|------|-------|
| A: PAccordion per entry, lazy detail | Matches AC; PDS native; `update` event fires only on summary click (form fields safe) | DOM weight if many entries; must conditionally render content | **0.82** |
| B: Custom disclosure (`<details>`) | Lighter DOM; native HTML | No PDS styling; accessibility gap; diverges from codebase convention | 0.55 |
| C: Modal for detail | Clean separation | AC explicitly says "inline"; poor UX for browse flow | 0.30 |

**Recommendation: A** — Conditional detail rendering (only render ReactMarkdown and form when `open=true`) eliminates the DOM cost concern. PAccordion API: `compact` prop, `open` controlled, `update` event for toggle.

### 3.2 Markdown Sanitization Schema

AC requires: strong, em, code, a (href validated). No img, no `dangerouslySetInnerHTML`.

```typescript
const MEMORY_SANITIZE_SCHEMA = {
  tagNames: ['strong', 'em', 'code', 'a', 'p', 'br', 'ul', 'ol', 'li'],
  attributes: { a: ['href'] },
  protocols: { href: ['http', 'https', 'mailto'] },
  strip: ['script', 'style', 'img', 'iframe'],
}
```

Use `[rehypeSanitize, MEMORY_SANITIZE_SCHEMA]` tuple in `rehypePlugins`. This is stricter than `defaultSchema` (which allows img, h1-h6, etc.). Pattern confirmed from rehype-sanitize docs — custom schemas fully replace defaultSchema.

### 3.3 Mutation Response Asymmetry

| Endpoint | Response | Local Update Strategy |
|----------|----------|---------------------|
| POST approve | `{ entry: {...} }` | Replace entry in array |
| POST edit | `{ entry: {...} }` | Replace entry in array |
| POST delete | `{ success: true }` | Remove entry from array (pending) or set state='deleted' locally (others) |

AC3+AC5 reconciliation: "update local state immediately from response payload" then trigger silent background `refetch()` for consistency. Delete doesn't return an entry — client must infer the result (removal or state change) based on original entry state.

### 3.4 Field-Level 422 Handling

Current `getResponseErrorMessage()` only reads `detail` as a string. FastAPI returns structured 422:
```json
{ "detail": [{ "loc": ["body", "confidence"], "msg": "...", "type": "..." }] }
```

Need: a `parseValidationErrors(response)` helper that returns `Record<string, string>` mapping field names to error messages. Applies only to the edit form; approve/delete won't generate field-level 422s.

### 3.5 Nav-Rail Badge

Commit `a507483d` implemented decisions badge in Shell.tsx (pattern: conditional `<span>` inside nav button, dynamic `aria-label`). That code was regressed in the working tree by a path-normalization refactor. For memory:

1. Restore decisions badge (regression fix)
2. Add `usePendingMemoryCount()` hook — lightweight fetch to `/api/memories` counting `state=pending` entries
3. Lift to CockpitProvider (same as `usePendingDRs`)
4. Render badge on memory nav button when count > 0

### 3.6 Edit Form UX

PAccordion fires `update` only on summary-area click. Content area clicks (form fields) do NOT trigger collapse — confirmed by PDS docs ("Clicking [summary slot] toggles the accordion"). Safe to embed inline edit form.

### 3.7 State Promotion (AC6)

Backend engine auto-promotes pending → curated when `scope_agents` provided in edit. The edit response returns the promoted entry with `state: 'curated'`. Frontend reads new state from response, shows inline PInlineNotification: "Promoted to curated — scope agents assigned".

## 4. Recommendation

**Proceed with implementation** using PAccordion + conditional content rendering + custom sanitize schema + structured mutation handlers.

Challenge: proceed — confidence in original: 0.78 (upgraded from 0.64 after addressing: lazy detail rendering for DOM weight, structured 422 parsing, and explicit nav badge state-lifting plan).

Key adjustments from challenger feedback:
- Conditional rendering of accordion detail content (not always-in-DOM)
- Separate 422 parser for field-level messages (not reuse getResponseErrorMessage)
- Explicit shell-level state source for pending memory count
- Delete mutation handled differently from approve/edit (no entry in response)

## 5. Follow-up Tasks

Implementation decomposes naturally into the AC structure — no additional research tasks needed. Task #1672 is ready for architecture review and TDD.
