# Test-Writer Non-Impl Fallback Heuristic

> **Owning task:** #498 — Add test-writer fallback for unrecognized non-impl tasks
> **Date:** 2026-03-31 (updated 2026-04-01) **Status:** Complete — DR resolved, Option A approved

## 1. Context and Question

The test-writer uses tag-based detection (Step 1, item 3 of tdd-red SKILL.md) to
identify non-implementation tasks and pass through without writing tests. The current
tag list is: `research`, `docs`, `type:config`, `type:docs`, `test`, `type:test`,
`agent`, `quality`. When a task produces no testable Python but lacks one of these
tags, the test-writer falls through to Step 2 (search codebase), finds nothing, and
fails silently — no notes appended, Gate 4 blocks the task indefinitely.

**Root cause:** Task #467 (create challenger.agent.md) was tagged `scope:agents` but
not `agent`. The test-writer didn't recognize it and got stuck. Tasks #470 and #34
were also cited as stuck, though those were Python implementation tasks — the real
pattern is #467-style pure-config tasks with missing pass-through tags.

**Question:** What heuristic should be added as a safety net between Step 2 and
Step 3, and how to prevent false positives on legitimate Python tasks?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `skills/tdd-red/SKILL.md` Step 1–3 | Internal | Current pass-through flow and search step |
| S2 | `agents/test-writer.agent.md` boundaries | Internal | Current boundary rules and examples |
| S3 | `docs/research/gate4-tw-missing-tag-exemptions.md` | Internal | Prior analysis of tag list gaps (#215) |
| S4 | `skills/dispatch-planning/SKILL.md` Gate 4 + Recipe 1 | Internal | Gate 4 TW:MISSING exemption mechanism |
| S5 | `skills/arch-review/SKILL.md` Step 4 tagging guidance | Internal | Architect's responsibility to tag non-impl tasks |
| S6 | GitHub Actions `paths`/`paths-ignore` pattern | External | Content-based routing: skip test jobs for non-code changes |
| S7 | GitLab CI `rules:changes` pattern | External | Same: route pipelines by file-type heuristic |
| S8 | Task #467 (challenger.agent.md — archived) | Internal | Root cause exemplar: pure .agent.md task mistagged |

## 3. Analysis

### 3.1 Current defense layers

| Layer | Mechanism | Catches |
|-------|-----------|---------|
| L1: Architect tagging | arch-review Step 4 guidance (S5) | Correctly tagged tasks |
| L2: Tag-based pass-through | tdd-red Step 1, item 3 (S1) | Tasks with correct tags |
| L3: Gate 4 exemption | dispatch-planning Recipe 1 (S4) | Blocks TW:MISSING, but task is already stuck |

**Gap:** No L2.5 — when L1 fails (mistagged) and L2 misses (wrong tag), nothing
catches the task before it reaches Step 2 and stalls.

### 3.2 Heuristic design options

| Option | Trigger point | Signal | False-positive risk | Complexity |
|--------|---------------|--------|---------------------|------------|
| A: AC content scan after Step 2 (rec:) ✅ | Between Step 2 and 3 | AC references only non-Python deliverables AND Step 2 found no testable code | Low — checks both content and codebase | Medium |
| B: Mandatory BLOCK on empty Step 2 | After Step 2 | Step 2 found nothing testable | None — always hands off | Low |
| C: Combined heuristic + BLOCK (bp:) | After Step 2 | Strong non-impl signals: pass-through; ambiguous: BLOCK | Lowest — escalates uncertainty | Medium-high |

### 3.3 False positive prevention

The critical constraint (AC item 4): the heuristic must NOT trigger for tasks where
a Python module simply doesn't exist yet (normal RED phase — tests fail with ImportError).

**Distinguishing signals:**

| Signal | Non-impl task | New-module Python task |
|--------|---------------|----------------------|
| AC mentions `.agent.md`, `SKILL.md`, `.yml`, `.instructions.md` | Yes | No |
| AC mentions `implement`, `add function/method/class`, `src/`, `packages/*/src/` | No | Yes |
| AC mentions Python imports, modules, or packages | No | Yes |
| Step 2 codebase search found related Python interfaces | No | Possibly (related code) |
| AC deliverables are exclusively non-Python file types | Yes | No |

A combined check (AC content + Step 2 result) provides the best discrimination:
proceed with RED phase if AC contains any Python implementation intent, even when
Step 2 finds no existing code.

### 3.4 Recommended heuristic (Option A with BLOCK escalation)

Insert between existing Step 2 and Step 3 as "Step 2a — Non-impl fallback check":

1. **If Step 2 found testable interfaces** → proceed to Step 3 (normal RED phase)
2. **Scan AC for Python implementation intent** — keywords: `implement`, `function`,
   `method`, `class`, `module`, `src/`, `packages/`, `.py`, `import`, `endpoint`, `API`
3. **If implementation intent found** → proceed to Step 3 (new module — ImportError
   tests are expected)
4. **If NO implementation intent AND AC deliverables reference only non-Python files**
   (`.agent.md`, `SKILL.md`, `.instructions.md`, `.yml`, `.yaml`, `.json`, `.md`,
   `.prompt.md`) → heuristic pass-through with warning
5. **If ambiguous** (neither clear impl intent nor clear non-impl) → create a
   decision request asking the architect to re-tag the task, or pass through with
   a strong warning. The escalation must always designate a clear next actor.
   Never use bare BLOCK without an assigned action.

### 3.5 Warning note format

```
## Test-Writer Notes
- Non-impl detected by heuristic — task may be missing a pass-through tag.
- AC deliverables: {list of non-Python files referenced}
- No Python implementation intent found in AC.
- Passing through to builder with warning.
```

This is distinguishable from proper tag-based pass-through (which says
"Non-implementation task (tagged {tag})").

### 3.6 Boundary rule for test-writer.agent.md

Add to the boundaries section:

> If the AC describes non-code deliverables only (agent files, skill files,
> config YAML, instruction files) and Step 2 found no testable Python interfaces,
> treat as heuristic non-impl pass-through. Append a warning note and advance.
> Do NOT trigger this for AC that mentions Python implementation — even if the
> module doesn't exist yet, that's normal RED phase.

### 3.7 Scope of changes

| File | Change | Lines affected |
|------|--------|----------------|
| `skills/tdd-red/SKILL.md` | Add Step 2a between Step 2 and Step 3 | ~20 new lines |
| `agents/test-writer.agent.md` | Add boundary rule in `<boundaries>` | ~5 new lines |

No Python code changes. No other agents/skills affected. The builder and reviewer
both read test-writer notes for text patterns — the new warning format is compatible
with existing `Non-implementation task` / `non-impl` text matching in tdd-workflow.

## 4. Recommendation (.85 confidence)

**Option A with decision-request escalation** — add a content-based heuristic after
Step 2 that scans AC for Python implementation intent vs. non-Python deliverables.
Clear non-impl cases pass through with a warning; ambiguous cases create a decision
request targeting the architect for re-tagging (or pass through with strong warning).
Per DR resolution: bare BLOCK without a designated next actor is never acceptable.

This follows the CI/CD pattern of content-based routing (S6, S7) and adds a safety
net without removing the existing tag-based mechanism. The architect remains the
primary defense (L1) — this heuristic is L2.5, not a replacement.

**Risk:** Heuristic is keyword-based and could miss edge cases. Mitigation: the BLOCK
escalation for ambiguous cases ensures no task silently stalls. Over time, missed
cases inform additions to the pass-through tag list.

## 5. Follow-up Tasks

T3 outcome — modifies agent skill (`tdd-red/SKILL.md`) and agent file
(`test-writer.agent.md`). DR resolved (Option A approved) at
`docs/decisions/resolved/498-test-writer-fallback-heuristic.md`.

No additional follow-up tasks needed — #498 itself captures the full implementation
scope (tdd-red SKILL.md Step 2a + test-writer.agent.md boundary rule). Task advanced
to backlog for architect review.
