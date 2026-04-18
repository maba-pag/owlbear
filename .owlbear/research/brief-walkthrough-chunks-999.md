# Brief Walkthrough: Chunk by Topic + Mediator Commentary

> **Owning task:** #999 — Brief Walkthrough: chunk by topic + Mediator commentary
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

The current Brief Walkthrough Protocol (w-ideation Step 5) walks each Brief section one-at-a-time with 7-8 sequential askQuestions calls. User feedback: this feels like form-filling. Two improvements requested:

1. **Chunk by topic** — group tightly coupled sections (4-5 chunks instead of 7-8 sections).
2. **Add Mediator commentary** — opinion, decision trail, trade-offs, honest negatives per chunk.

**Question:** How should Brief sections map to topic chunks, and what should the Mediator commentary template contain?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `share/skills/w-ideation/SKILL.md` — Brief Walkthrough Protocol (L270-310) | Codebase | 1.0 |
| `share/skills/w-ideation/SKILL.md` — Brief Artifact structure (L220-250) | Codebase | 1.0 |
| Task #999 body — user feedback verbatim from #973 ideation session | Task | 1.0 |
| `share/skills/w-ideation/SKILL.md` — Walkthrough Metrics (L296-310) | Codebase | 0.9 |

## 3. Analysis

### 3.1 Section-to-Chunk Mapping

Current Brief sections → proposed topic chunks:

| Chunk | Name | Brief Sections Covered | Rationale |
|-------|------|----------------------|-----------|
| 1 | **The Why** | Problem + Outcomes | Why this exists, what success looks like |
| 2 | **The How** | Approach + Alternatives Considered + Context | Solution choice, what was rejected, ecosystem evidence |
| 3 | **The Boundary** | Scope (In/Out) + Key Decisions | What's included, what's excluded, major choices that shaped scope |
| 4 | **The Honesty** | Risks & Mitigations | Known risks, trade-offs accepted, mitigations planned |
| 5 | **The Next Step** | Decomposition preview | How this breaks into tasks — new addition, not currently in Brief |

### 3.2 Mapping Gaps

| Gap | Resolution |
|-----|-----------|
| Task says "Acceptance criteria" in chunk 4, but Brief has no AC section | Outcomes (chunk 1) serve as AC. Chunk 4 can cross-reference outcomes as verifiability anchors without repeating them. |
| Task says "Architecture" in chunk 2, but Brief has no Architecture section | Approach section already covers architecture decisions. Context section provides codebase/ecosystem evidence. Combined in chunk 2. |
| "Decomposition preview" (chunk 5) doesn't exist in current Brief | New walkthrough-only content. Mediator previews how the Brief will decompose into tasks before M6 handoff. Not a Brief section — a walkthrough addition. |
| Key Decisions section placement | Grouped with Scope (chunk 3). Decisions explain why the boundary is what it is. |

### 3.3 Mediator Commentary Template

Current walkthrough gives each section: (1) present text, (2) management summary, (3) brief opinion, (4) metrics, (5) askQuestions.

Proposed commentary replaces steps 2-3 with a richer structure per chunk:

| Slot | Purpose | Example signal |
|------|---------|----------------|
| **Summary** | Mediator's restatement in own words (no quoting) | "This chunk says we're solving X by doing Y" |
| **Opinion** | Honest assessment: strengths + weaknesses | "The approach is solid but the fallback is underspecified" |
| **Decision trail** | Which user/panelist decisions shaped this | "You chose option A in M4 because [panelist] flagged..." |
| **Trade-offs** | What was accepted, given up, or dropped | "We dropped option B (simpler) because it couldn't handle..." |
| **Why this shape** | Why optimal vs. alternatives | "This is the right shape because it aligns with existing..." |
| **Honest negatives** | Risks, gaps, things that could bite | "The 50-LOC wrapper risk is real but contained" |

### 3.4 Interaction Design

| Aspect | Current | Proposed |
|--------|---------|----------|
| Number of askQuestions calls | 7-8 (one per section) | 5 (one per chunk) |
| Mediator voice | Neutral presenter | Opinionated reviewer |
| Content per call | Section text + 1-2 line summary | Chunk text + commentary (6 slots) |
| Message length per turn | Short (section + metrics) | Medium (chunk + commentary + metrics) |
| User cognitive load per turn | Low (one section) | Moderate (two sections + commentary) |

**Risk:** Longer messages per turn could overwhelm. **Mitigation:** Commentary slots are 1-2 sentences each, not paragraphs. Total per chunk ≈ 8-12 sentences.

## 4. Recommendation

**Implement the 5-chunk walkthrough with 6-slot commentary template** as described above.

Confidence: **0.90** — The user explicitly directed this change with specific requirements. The mapping is clean. The only design judgment is the commentary template structure, which directly maps to user's listed requirements.

Challenge: Skipped — user-directed change with no competing alternatives. No recommendation ambiguity to challenge.

**Implementation notes:**
- Edit the `## Brief Walkthrough Protocol` section in `w-ideation/SKILL.md`
- Replace the Walkthrough Loop with topic-chunk loop
- Add commentary template (6 slots per chunk)
- Add a worked example showing one chunk walkthrough
- Keep existing Walkthrough Metrics (Fidelity, Readiness, Risk) — they still apply per-chunk
- Keep the Post-Walkthrough Summary table — update to show chunk names instead of section names

## 5. Extension: Walkthrough Offer as Top-Level Rule

### Problem

The walkthrough offer lives at w-ideation Step 5 sub-step 5 — buried deep. During the #984 ideation session the Mediator dumped the full Brief and asked "approve?" without offering a walkthrough. The user had to call it out.

### Analysis: Where to Place the Rule

| Location | Visibility | Risk of being missed |
|----------|-----------|---------------------|
| `ideator.agent.md` critical_rules | Loaded on every invocation — first thing the agent reads | Low |
| w-ideation Step 5 sub-step 1 (moved from sub-step 5) | Read when executing M5 | Medium — agent may skim sub-steps |
| Both locations | Redundant but reinforced | Lowest |

**Recommendation: Both locations.** The critical_rule catches the behavior at the agent's top-of-mind level; the Step 5 sub-step ordering makes it procedurally first. Cost of redundancy is ~2 lines. Confidence: **0.92**.

### Proposed critical_rule text

> **Never present a Brief without first offering a walkthrough.** Before showing any Brief content (even partial), use askQuestions to offer "Walk me through it" / "I'll read it myself". Presenting Brief content before this offer is a protocol violation.

### Proposed askQuestions call shape (worked example)

```
askQuestions:
  question: "The Brief is ready. How would you like to review it?"
  options:
    - label: "Walk me through it"
      description: "I'll present each topic chunk with my commentary, trade-offs, and honest assessment"
    - label: "I'll read it myself"
      description: "I'll share the Brief and you review at your own pace"
  allowFreeformInput: false
```

## 6. Follow-up Tasks

1. **Implementation task** — Edit w-ideation SKILL.md: replace section-by-section walkthrough with topic-chunk walkthrough + Mediator commentary template + worked example. Add walkthrough offer as Step 5 sub-step 1. Add critical_rule to ideator.agent.md.
