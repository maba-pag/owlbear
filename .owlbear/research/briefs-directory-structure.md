# Briefs Directory Structure — Blackboard for Ideator Agents

> **Owning task:** #642 — P4-02: Create .owlbear/briefs/ directory structure
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

The Phase 4 Thinking Companion Framework introduces an Ideator agent system using a **Blackboard pattern** where multiple voice agents communicate through shared filesystem artifacts. Task #642 asks: _Is the proposed `.owlbear/briefs/` directory structure sound, and what implementation approach should follow?_

The spec (`.owlbear/research/thinking-companion-framework.md`, §12) defines the structure. This research validates the design against prior art, existing OwlBear conventions, and technical constraints.

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| S1 | Framework spec §12 | `.owlbear/research/thinking-companion-framework.md` L376–420 | 1.0 |
| S2 | Blackboard pattern | Wikipedia: Blackboard_(design_pattern); Lalanda 1997 | .85 |
| S3 | OwlBear `.owlbear/scratch/` conventions | `.owlbear/scratch/.instructions.md` + `.gitignore` L55–58 | .90 |
| S4 | OwlBear `.owlbear/decisions/` conventions | `.owlbear/decisions/README.md` | .90 |
| S5 | CrewAI framework | github.com/crewAIInc/crewAI — Flows use in-memory Pydantic state | .60 |
| S6 | AutoGen framework | github.com/microsoft/autogen — message-passing, no filesystem blackboard | .55 |

## 3. Analysis

### 3A. Research Gate Checklist

| Gate | Verdict | Rationale |
|------|---------|-----------|
| Theoretical validity | **Pass** | Blackboard is established (S2). Filesystem-as-medium fits VS Code agents that share workspace but have isolated context windows. |
| Environment audit | **Pass — no existing capability** | `.owlbear/scratch/` is ad-hoc temp files, not structured inter-agent state. `.owlbear/decisions/` handles only DRs. No overlap. |
| Prior art | **Pass** | OwlBear already uses directory-based conventions (S3, S4). Other frameworks (S5, S6) use in-memory state — filesystem approach is unique to OwlBear's Copilot CLI architecture. |
| Technical feasibility | **Pass** | Pure filesystem. VS Code agents natively read/write files. No runtime deps. |
| Architecture fit | **Pass** | Follows `.owlbear/{purpose}/` convention. Parallels `decisions/`, `research/`, `scratch/`. |
| Implementation approach | **See §3C** | Directory + README + .gitignore update. |

### 3B. Trade-off Matrix: Git Versioning Strategy

| Strategy | Audit Trail | Repo Noise | Conflict Risk | Recommendation |
|----------|-------------|------------|---------------|----------------|
| A: Track all briefs | Full history | High — voice debates are verbose | Low (separate files per voice) | — |
| B: Gitignore all briefs | None | Zero | N/A | — |
| **C: Track completed, ignore WIP** | Completed briefs archived | Moderate — only final artifacts | Low | **(rec:) .80** |

**Recommendation C:** Track `draft-{name}/` directories (audit trail per spec S1 §lifecycle item 7), gitignore `draft-new/` (transient template, renamed at M1). Confidence: **.80**.

### 3C. Implementation Approach

The spec fully defines the directory tree (S1 L378–397). Implementation is:

1. Create `.owlbear/briefs/` with `.gitkeep`
2. Create `.owlbear/briefs/README.md` documenting structure, lifecycle, and agent read/write matrix
3. Add `!.owlbear/briefs/.gitkeep` and `!.owlbear/briefs/README.md` to `.gitignore` if needed
4. Gitignore `draft-new/` (template directory created at invocation, renamed at M1)
5. Completed `draft-{name}/` directories tracked for audit

### 3D. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| File proliferation | Medium | Low | Lifecycle cleanup: auditor removes when parent task archived (spec S1 §lifecycle item 7) |
| Write conflicts during voice deliberation | Low | Low | Each voice writes to `voices/{name}.md` — no shared files during parallel phase |
| `draft-new/` collision (two concurrent invocations) | Very Low | Medium | VS Code = single user; ideator is user-invocable interactive agent |
| Stale briefs accumulate | Medium | Low | Same cleanup rule as scratch — auditor or curation job |

## 4. Recommendation

**Proceed with implementation as specified.** The directory structure from the framework spec is sound, aligns with OwlBear conventions, and has no technical blockers. The only design addition is the git versioning strategy (§3B option C).

**Tier: T1 — Autonomous.** This is directory creation + documentation. No new capability, no architecture change, no security impact. The structure is already fully designed in the framework spec.

**Challenge: FALLBACK — no challenger invocation needed for T1 directory-creation task with pre-approved spec.**

Confidence in recommendation: **.85**

## 5. Follow-up Tasks

| Task | Status | Description |
|------|--------|-------------|
| Create briefs directory + README | ideation | Create `.owlbear/briefs/`, `.gitkeep`, `README.md` with conventions |
| Update .gitignore for briefs | ideation | Add `draft-new/` ignore pattern, preserve `.gitkeep` and `README.md` |
