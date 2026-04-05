# Environment Audit Step for Research-Workflow Skill

> **Owning task:** #194 — Add environment audit step to research-workflow skill
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

The pipeline quality audit (#192, `docs/research/pipeline-quality-audit.md`) found
that no agent in the full pipeline asks "does the IDE/runtime already provide this?"
before recommending additions. This led to a redundant GitHub MCP server entry (#121)
passing through 6 agents unchallenged. Recommendation R1 proposes an "environment
audit" checklist item in the research-workflow skill.

**Question:** What's the right wording, placement, and implementation for this item?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | Pipeline quality audit (docs/research/pipeline-quality-audit.md) | Internal | 1.0 |
| S2 | research-workflow skill (skills/research-workflow/SKILL.md) | Internal | 1.0 |
| S3 | Google Eng-Practices: What to Look For in a Code Review | External | 0.8 |
| S4 | Du et al. 2023 — Multi-agent Debate (arXiv:2305.14325) | External | 0.7 |
| S5 | VS Code MCP Server Guide | External | 0.8 |

**S3** asks in its Design section: "Does this change belong in your codebase, or in a
library?" — directly analogous to "does the IDE already provide this?" Both check
whether the proposed addition is necessary before evaluating how to build it.

**S4** shows multi-agent debate improves factuality only when agents reason
independently. OwlBear's sequential pipeline inherits upstream assumptions — the
environment audit breaks this by requiring the researcher to validate the premise
against the runtime environment before passing assumptions downstream.

## 3. Analysis

### 3.1 Placement Options

| Option | Placement | Pros | Cons |
|--------|-----------|------|------|
| A | Between item 1 and 2 (new item 2) | Check environment before searching prior art — saves wasted effort | Renumbers items 2-7 |
| B | After prior art (new item 3) | Prior art search may reveal the duplication naturally | Delays catching the problem; prior art search is wasted if capability already exists |
| C | Separate pre-checklist gating question | Maximum visibility | Creates a two-tier structure; adds complexity |

**Recommendation (.90 confidence): Option A.** Checking the environment before prior art
search is the earliest intervention point. If the capability already exists, no prior art
search is needed. This matches Google's practice (S3) of asking "does this belong?" as
the first design question, not the last. KISS-aligned — one flat checklist, no structural
changes.

### 3.2 Wording Assessment

The AC proposes:
> "Environment audit: Is this capability already provided by the IDE, runtime, installed
> extensions, or existing tooling? Check VS Code built-in features, extension-provided
> servers, and installed packages before recommending additions."

This is comprehensive. The enumeration (IDE, runtime, extensions, tooling) covers the
specific blind spot from #121 (the Copilot extension's built-in GitHub MCP server).

### 3.3 Implementation Details

| Change | Location | Notes |
|--------|----------|-------|
| Insert new item 2 | Research checklist (lines 22-30) | Renumber old 2-5 to 3-6, old 6-7 to 7-8 |
| Mark as mandatory | Same section | "Items 1–6 are **mandatory**" (was 1-5) |
| Update trivial exemption | Paragraph after checklist | "items 1–4" (was "items 1–3") — new item gets same N/A treatment for trivial tasks |
| Add self-critique item | Self-critique checklist (line ~120) | "[ ] Verified no environment duplication" |

### 3.4 Risk: Trivial-Task Exemption

The current exemption says "items 1–3 get a one-liner N/A." After inserting the new
item 2, this range must update to "items 1–4" to cover: Theoretical validity,
Environment audit, Prior art, Technical feasibility. For a trivial rename task, the
environment audit is genuinely N/A ("no capability being added"), so the exemption is
correct. **The builder must update this range.**

## 4. Recommendation (.90 confidence)

Implement Option A: insert environment audit as new item 2, renumber, update mandatory
range to 1–6, update trivial exemption to 1–4, add self-critique item. No structural
changes to the skill — just a checklist item insertion.

Risk: minimal. The change is additive and backward-compatible.

## 5. Follow-up Tasks

No additional tasks needed — #194 already captures the full implementation scope.
The AC is specific and actionable. Builder implements the skill file edits.
