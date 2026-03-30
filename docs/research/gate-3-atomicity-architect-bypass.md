# Gate 3 Atomicity Heuristic — Architect Bypass

> **Owning task:** #214 — Fix Gate 3 atomicity heuristic to respect architect approval
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Gate 3 (Atomicity) in `dispatch-planning/SKILL.md` tells the planner to scan task
titles for "and" joining unrelated concerns — a crude heuristic meant to catch
non-atomic tasks. The architect evaluates exactly the same concern in `arch-review`
Step 3.1 ("Single responsibility — one thing only?") and records the verdict in
`## Architecture Review`. Gate 3 re-litigates that decision, permanently blocking
tasks the architect already approved.

**Question:** How should Gate 3 be modified so that architect-approved tasks are
exempt while preserving the safety net for tasks that bypassed architecture review?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `skills/dispatch-planning/SKILL.md` — Gate 3 definition (L213-216) | Current heuristic text |
| S2 | `skills/arch-review/SKILL.md` — Step 3.1 single-responsibility check | Architect's atomicity gate |
| S3 | Board data: 9 tasks with "and" + `## Architecture Review` | False-positive population |
| S4 | Tasks #151, #153 — manual triage required to unblock | Concrete failure evidence |
| S5 | Board Scan Recipe 1 — existing marker pattern (TW:MISSING, AC:MISSING) | Implementation precedent |

## 3. Analysis

### 3.1 Problem quantification

| Metric | Value |
|--------|-------|
| Tasks with "and" in title + architect review | 9 |
| Tasks with "and" in title, no architect review | 9 |
| Tasks manually unblocked due to this conflict | 2 (#151, #153) |
| Estimated future false positives if unfixed | ~50% of "and"-titled tasks |

### 3.2 Root cause

Gate 3 has no awareness of upstream decisions. The `## Architecture Review` section
is proof that the architect evaluated atomicity — the section always contains a
single-responsibility assessment per Step 3.1. Gate 3 ignores this evidence.

### 3.3 Fix options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Marker in Board Scan | Add `ARCH:REVIEWED` marker in Recipe 1 PS; Gate 3 skips when present | Consistent with existing TW:MISSING/AC:MISSING pattern; no new tooling | Marker logic in PS grows by 1 line |
| B: Remove Gate 3 entirely | Trust architect always | Simpler | Loses safety net for tasks that bypass architect (e.g., manual creates) |
| C: Change Gate 3 to body-only check | Gate 3 reads body instead of title | Richer signal | Requires LLM to read full body per task — expensive, slow |

### 3.4 Recommendation (.90 confidence)

**Option A** — add `ARCH:REVIEWED` marker to Board Scan, exempt marked tasks from
Gate 3 heuristic. This follows KISS (1 line of PS, 1 paragraph of gate text) and
preserves the safety net for edge cases.

**Risk:** Minimal. Only the architect agent writes `## Architecture Review` sections
per the pipeline definition. Spoofing requires manual task editing, which is an
accepted trust boundary.

## 4. Implementation Spec

### 4.1 Board Scan Recipe 1 change

Add after the `DECOMP` check in the ForEach-Object block:

```powershell
if ($_.body -match '## Architecture Review') {$w+='ARCH:REVIEWED'}
```

Update the "What the PowerShell layer adds" documentation to describe the new marker.

### 4.2 Gate 3 text change

Replace current Gate 3 text with:

> **Gate 3 — Atomicity gate:**
> Title describes a single responsibility. Red flag: the word "and" joining unrelated
> concerns (e.g., "Implement parser and update config"). Related concerns joined by
> "and" are fine (e.g., "Read board and build DAG" — both are planning sub-steps).
> **Exemption:** Tasks marked `[!ARCH:REVIEWED]` in the Board Scan output have
> already passed the architect's single-responsibility evaluation (arch-review
> Step 3.1). Skip the "and" heuristic for these tasks.

### 4.3 Board Scan comment update

Add to the "What the PowerShell layer adds" section:

> - `ARCH:REVIEWED` marker: task body contains `## Architecture Review` section
>   (architect already evaluated atomicity). **= Gate 3 exemption signal.**

### 4.4 LLM reasoning section update

Change the Gate 3 line under "What remains for LLM reasoning":

> - Gate 3 (atomicity): scan titles for "and" joining unrelated concerns.
>   **Skip for tasks with `[!ARCH:REVIEWED]` marker** — architect already evaluated.

## 5. Follow-up Tasks

Single implementation task — the change is a SKILL.md edit (type:config):

```
kanban\kanban-md.exe create "Implement Gate 3 architect-bypass in dispatch-planning SKILL.md" --priority needed --status ideation --tags "scope:agents,quality,type:config" --body "## Objective\nModify dispatch-planning SKILL.md to exempt architect-reviewed tasks from Gate 3 atomicity heuristic.\n\n## Acceptance Criteria\n- [ ] Board Scan Recipe 1 PS adds ARCH:REVIEWED marker when body contains ## Architecture Review\n- [ ] Gate 3 text updated: tasks with ARCH:REVIEWED marker skip the and heuristic\n- [ ] What the PowerShell layer adds section documents the new marker\n- [ ] What remains for LLM reasoning section updated for Gate 3 exemption\n- [ ] No other gates affected\n- [ ] The and heuristic remains active for tasks WITHOUT ## Architecture Review\n\n## Context\nSee docs/research/gate-3-atomicity-architect-bypass.md for full analysis.\nOwning research: #214"
```
