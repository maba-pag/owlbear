---
id: 936
title: 'P2-07: GREEN — Sidecar (Detail + Activity tabs) + polling + optimistic UI'
status: todo
priority: important
created: 2026-04-17T19:59:03.599720+00:00
updated: 2026-04-18T21:29:28.888418+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
parent: 920
depends_on:
- 935
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Implement sidecar tabs, polling infrastructure, and optimistic UI to pass RED tests from #935.

## Acceptance Criteria

- [ ] Detail tab: allowlisted YAML fields as structured controls (PDS or Radix inputs, dropdowns, tag chips); markdown body rendered with react-markdown + remark-gfm + rehypeSanitize; toggle edit mode for body
- [ ] Save-time `updated` comparison (D9): on 409, show refresh-or-overwrite modal with current vs. server values
- [ ] History subtab: per-session breakdown from `GET /api/sessions?task_id={id}` (agent, duration, outcome)
- [ ] Activity tab: sessions from `GET /api/sessions?filter=`; default filter = active; switchable filters (all / failed-or-rejected / released)
- [ ] Click session row selects task in Detail tab + activates History subtab
- [ ] Polling: mtime-aware ~3s interval (TanStack Query refetchInterval or custom hook); skip 1 cycle after local mutation
- [ ] Connection health traffic light in status bar: green (poll within threshold) / yellow (lagging) / red (disconnected)
- [ ] Optimistic UI: snapshot state before mutation; immediate local update; rollback on API error
- [ ] Confirmation dialogs: backward moves, unclaim, unblock (surfaces block_reason before clearing)
- [ ] XSS hardening: strict CSP meta tag; no `dangerouslySetInnerHTML`; rehypeSanitize on all task-derived markdown
- [ ] Designed empty, loading, and error states for both tabs (no white-screen paths)
- [ ] All RED tests from #935 pass

## Files

- `serve/cockpit/web/src/components/DetailTab.tsx`
- `serve/cockpit/web/src/components/ActivityTab.tsx`
- `serve/cockpit/web/src/components/HistorySubtab.tsx`
- `serve/cockpit/web/src/components/ConfirmDialog.tsx`
- `serve/cockpit/web/src/hooks/usePolling.ts`
- `serve/cockpit/web/src/hooks/useOptimistic.ts`
- `serve/cockpit/web/src/hooks/useConnectionHealth.ts`
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/936-sidecar-green-gaps.md
- Sources: 7 studied, 5 high-relevance (S1–S2 external, S3–S7 codebase)
- Recommendation: close 5 AC gaps in order: G5 snapshot bug → G4 file extraction → G1 remark-gfm/rehype-sanitize → G2 CSP (production-only) → G3 PDS spike (confidence: 0.75)
- Follow-up tasks created: none — #936 itself covers all gaps
- Decision requests: none (all T1 autonomous)

## Challenge Results
- Challenger: reconsider (confidence in original: 0.45)
- Key challenges: C1 rehype-sanitize no-op without rehypeRaw, C2 CSP breaks Vite dev mode, C3 PDS shadow DOM may break test queries, C5 useOptimistic snapshot never updates before mutation
- Researcher response: accepted all — revised G2 to production-only CSP, revised G3 to spike-first approach, added G5 as new finding, dropped defense-in-depth framing for G1

## Key Findings Summary
1. **G5 (bug):** useOptimistic snapshot.current set at mount, never before mutation — rollback reverts to stale initial
2. **G4 (normative):** HistorySubtab, ConfirmDialog, useConnectionHealth listed as AC deliverables but inline
3. **G1 (compliance):** remark-gfm adds real GFM value; rehype-sanitize is AC compliance without rehypeRaw
4. **G2 (conflict):** Static CSP meta tag breaks Vite HMR; recommend production-only via transformIndexHtml
5. **G3 (risk):** PDS wrapper migration needs jsdom spike before committing — shadow DOM query breakage
[[2026-04-18]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | GREEN gap-closing task — all items serve one goal: close AC gaps identified by research. Splitting would orphan existing RED tests. |
| Interface clarity | PASS (after refinement) | 3 AC items refined below for precision. Research doc provides full implementation guidance. |
| Dependency correctness | PASS | depends_on #935 (done). No missing deps. |
| Module layering | PASS | Frontend-only. Shell → components → hooks layering is clean. |
| TDD compliance | PASS | 66 RED tests from #935 exist (DetailTab.test.tsx, ActivityTab.test.tsx, usePolling.test.ts, optimistic.test.ts). Test-writer should add gap-specific tests for G1/G5. |
| KISS/YAGNI | PASS | Research narrowed scope to 5 concrete gaps. No speculative work. |
| Premise challenge | PASS | Gaps are real: snapshot bug causes incorrect rollback, CSP absent, remark-gfm not wired, files mislocated. |
| Pattern consistency | PASS | Follows existing custom-hook + functional-component pattern. File reorg aligns with hooks/useBoard.ts convention. |
| Security surface | PASS | XSS: react-markdown is safe by default (no dSIH). rehypeSanitize is compliance without rehypeRaw. CSP is defense-in-depth. |
| Single domain | PASS | Frontend only. |

### AC Refinements (binding for builder)

**AC1 — PDS form controls:** RED tests from #935 use plain HTML selectors (`input[data-field="title"]`, `select[data-field="priority"]`). PDS wrapper migration MUST NOT break existing test selectors. Approach: plain HTML controls are the baseline. PDS wrappers are best-effort — spike one wrapper in a test first (per research G3 Option D). If jsdom `querySelector` still finds the slotted `<input>`, proceed. If not, defer PDS migration to follow-up task and use plain HTML.

**AC10 — CSP:** Rewrite to: "Production-only CSP meta tag via Vite `transformIndexHtml` hook. Policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'`. `'unsafe-inline'` for styles is required due to PDS inline style injection. Dev mode unaffected (no meta tag injected)."

**AC (implicit) — Dependency installation:** `npm install remark-gfm rehype-sanitize` required. Wire both into `<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>` — Option A from research (no rehypeRaw).

### File Reorganization Guidance

Current files at `src/` root must move to match AC `Files` section:
- `src/DetailTab.tsx` → `src/components/DetailTab.tsx`
- `src/ActivityTab.tsx` → `src/components/ActivityTab.tsx`
- `src/optimistic.ts` → `src/hooks/useOptimistic.ts` (rename)
- `src/usePolling.ts` → `src/hooks/usePolling.ts`
- Extract: `src/components/HistorySubtab.tsx` (from DetailTab)
- Extract: `src/components/ConfirmDialog.tsx` (from DetailTab)
- Extract: `src/hooks/useConnectionHealth.ts` (from usePolling)

All imports must be updated in: Shell.tsx, KanbanBoard.tsx (if applicable), and all test files under `src/__tests__/`. Test imports currently use `'../DetailTab'` etc. — these become `'../components/DetailTab'`.

### G5 Snapshot Fix Pattern

`useOptimistic.mutate()` must capture `prev` inside the `setState` callback before applying the updater:
```typescript
function mutate(updater: (s: T) => T): void {
  setState((prev) => {
    snapshot.current = prev
    return updater(prev)
  })
}
```
Test-writer should add a test confirming rollback returns to pre-mutation state when state has changed since mount.

### Challenge Results

Challenge: FALLBACK — challenger agent not available as subagent. Prior research challenge results (reconsider, confidence 0.45) were accepted by researcher with all revisions incorporated (G2 → production-only CSP, G3 → spike-first, G5 added, G1 framing corrected). No further challenge needed — research challenge cycle was thorough.

### Verdict: APPROVE (with refinements above)
### Action: Advanced to todo. Builder must follow AC refinements and research doc (.owlbear/research/936-sidecar-green-gaps.md) for implementation order: G5 → G4 → G1 → G2 → G3.