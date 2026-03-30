# Arch-Review Premise Challenge Step

> **Owning task:** #195 — Add premise challenge step to arch-review skill
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

The pipeline quality audit (#192) found that six agents approved adding a
redundant GitHub MCP server (#121) because no agent questioned whether the
feature was needed — every check validated implementation quality, not premise
validity. Recommendation R2 proposes adding a "premise challenge" step to the
architect's review workflow so the architect questions *why* before evaluating *how*.

**Research question:** Is a premise challenge step theoretically sound, what
prior art supports it, and where should it be placed in the arch-review skill?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | Klein 2007 — "Performing a Project Premortem" (HBR 85(9):18–19) | External | 0.9 |
| S2 | Chesterton 1929 — "The Drift from Domesticity" (The Thing, ch.) | External | 0.8 |
| S3 | Du et al. 2023 — Multi-agent Debate (arXiv:2305.14325) | External | 0.7 |
| S4 | OwlBear pipeline quality audit (docs/research/pipeline-quality-audit.md) | Internal | 1.0 |
| S5 | Current arch-review skill (skills/arch-review/SKILL.md, Step 3) | Internal | 1.0 |

## 3. Analysis

### 3.1 Theoretical Grounding

The premise challenge draws on two established principles:

**Pre-mortem analysis** (S1): Klein's technique assumes the project has already
failed, then works backward to identify causes. The premise challenge inverts
this for additions: "Assume this feature already exists. Where is it?" If the
answer is "in the IDE/runtime/tooling", the task is unnecessary.

**Chesterton's fence** (S2): "If you don't see the use of it, I certainly won't
let you clear it away." The inverse applies to additions: don't add a new fence
until you verify one doesn't already stand. The architect must verify the
*absence* of a capability before approving its *addition*.

**Anchoring cascade** (S3): Du et al. show multi-agent debate reduces errors
only when agents reason independently. OwlBear's sequential pipeline inherits
upstream assumptions — each agent anchors on the previous. A premise challenge
breaks this by requiring the architect to re-derive necessity from scratch.

### 3.2 Placement Analysis

| Position | Pros | Cons |
|----------|------|------|
| First (before item 1) | Fails fast — no wasted evaluation if premise invalid | Disrupts familiar 1–10 numbering |
| After item 6 (KISS/YAGNI) | Natural extension of KISS/YAGNI checks | Late — architect may already anchor on AC quality |
| Last (item 11) | Non-disruptive to existing flow | Buried — easily skipped; fails late |

**Recommendation (.90 confidence):** Insert as a new item between current items
6 and 7 (after KISS/YAGNI, before Pattern consistency). Rationale: premise
challenge is a form of YAGNI validation ("does this already exist?") and groups
naturally with it. This avoids renumbering the entire list while placing the
check early enough to prevent anchoring.

### 3.3 Scope of "Environment"

The AC says "existing IDE feature, runtime capability, or installed tool." This
needs concrete examples in the step text to be actionable:

| Category | Examples |
|----------|----------|
| IDE features | VS Code built-in MCP, IntelliSense, Git integration, terminal |
| Runtime | Python stdlib, installed pip packages, OS utilities |
| Existing tooling | Scripts in `scripts/`, existing MCP servers, kanban-md features |
| Extensions | Copilot built-in server, installed VS Code extensions |

### 3.4 Red Flag Placement

The AC requires updating the red-flags list. The arch-review skill has a
self-critique checklist (Step 5 equivalent) but no explicit "red flags" list.
The closest analog is the self-critique checklist items. Add the red flag as a
new checklist item there.

## 4. Recommendation (.90 confidence)

**Approve #195 as-is**, with one refinement to the AC:

1. Insert premise challenge as Step 3 item 7 (renumbering current 7–10 to 8–11)
   rather than "3.10", to place it adjacent to KISS/YAGNI.
2. Add concrete environment categories (IDE, runtime, tooling, extensions) to
   the step text so architects know *what* to check.
3. Add checklist item to self-critique: "You are approving a feature addition
   without checking if the environment already provides it."
4. Trivial tasks still get the check — one-liner format: "Premise: validated —
   no duplicate capability" (matches existing trivial-task convention).

No new risks. No architectural concerns. This is a documentation-only change to
a single skill file.

## 5. Follow-up Tasks

No new tasks needed — #195 already captures the full scope. The sibling tasks
(#194 R1, #196 R3, #197 R4) cover the other audit recommendations. The
architect should consider the placement refinement in §4.1 when reviewing AC.
