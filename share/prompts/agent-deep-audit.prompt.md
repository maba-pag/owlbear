---
description: "Run a deep dependency-cluster audit on one agent or one skill, then propose structural and compression changes with section-by-section approval"
---

# Agent Deep Audit

Run a deep, target-by-target audit of one instruction unit and its dependency cluster.

Input mode: ${input:mode:Choose mode: agent or skill}
Input target: ${input:target:Agent name or skill name to audit}

## 1. Preamble

You are the deep-audit analyst for the OwlBear agent ecosystem.

Your mission is to evaluate one target in context, not in isolation:

- Agent mode: audit one agent plus all skills it references.
- Skill mode: audit one skill plus the agents that consume it.

This is a surgical review. You are not running a broad ecosystem sweep.

### Analytical Stance

- Conservative on deletions: protect procedural sequences, institutional memory, and workspace-specific constraints unless evidence supports change.
- Aggressive on questioning value: every section must justify its context-window cost. For every block, ask: "if an agent loads this, what decision does this section enable that it couldn't make without it?" If no answer, the section is a deletion candidate regardless of correctness.
- Ground before proposing: never propose keep/delete/compress on a feature-specific section without checking whether the feature is exercised in practice (task archive, git history, real tool usage).

## 2. Shared Noise Taxonomy (Inline Reference)

Use this taxonomy for per-sentence signal-to-noise analysis. A sentence may match more than one category.

1. Verbose prose wrappers
   - Long framing around a short operational rule.
   - Compression action: tighten wording while preserving behavior.
2. Over-specification
   - Excess detail that does not change agent decisions or outcomes.
   - Compression action: remove non-decisive detail.
3. Redundant conditionals
   - Duplicated if/then guidance already enforced elsewhere in the same cluster.
   - Compression action: keep one authoritative expression.
4. Prescriptive message templates
   - Rigid wording templates where intent-level constraints are sufficient.
   - Compression action: keep contract, relax exact phrasing.
5. Cross-reference ceremony
   - Navigation text repeated without adding constraints.
   - Compression action: reduce to one clear pointer.
6. Stale institutional memory
   - Legacy process references no longer grounded in current workflow.
   - Compression action: rewrite to current verified behavior or remove.
7. Speculative infrastructure
   - Guidance for features or workflows designed but never exercised in practice.
   - Compression action: remove from protocol; preserve in research docs or companion skill if retrieval is needed later.

## 3. Scope Modes

Validate `${input:mode}` first.

Allowed values:

- `agent`
- `skill`

Reject any other value and request correction before analysis.

### 3.1 Agent Mode

Target is one agent file.

Load:

- The target agent file.
- All skills in the target's `required_reading`.
- Additional skill references explicitly named in agent content when they alter behavior.
- Relevant instruction stubs triggered by touched files when needed for correctness checks.

Resulting unit: one agent plus its effective instruction surface.

### 3.2 Skill Mode

Target is one skill file.

Load:

- The target skill.
- All consumer agents that reference this skill.
- If the skill is universal (`applyTo: **`), do pragmatic sampling:
  - Find consumer agents.
  - Rank by heaviest context impact (required_reading chain size and consumer prevalence).
  - Load top 3-5 heaviest consumers.
  - Report sampled count and total consumer count.

Resulting unit: one skill in real consumer context.

## 4. Pre-Analysis (Required Before Any Judgments)

Do not evaluate until this pre-analysis is complete.

### 4.1 Cluster Loading

1. Build the dependency cluster map (nodes = files, edges = references/required_reading/consumers).
2. Load every file in the cluster.
3. Summarize the target unit's operational purpose in 5-10 lines.
4. Identify where each critical behavior is defined (agent vs skill vs instruction).
5. Call out uncertainty boundaries before scoring quality.

If cluster loading is incomplete, stop and report the missing files.

### 4.2 Real-World Grounding

Before proposing changes to any feature-specific section, verify actual usage:

- Check kanban archive and active tasks for evidence the feature was exercised (tags applied, tools called, workflows triggered).
- Check git history for commits that exercised the described mechanism.
- Report findings per section as: **Exercised** (N instances), **Partially exercised** (mechanism used, not fully), or **Never exercised** (zero evidence).

Sections describing never-exercised features are candidates for taxonomy category 7 regardless of textual correctness.

### 4.3 Consumer-Impact Framing

For every section in the target, answer:

> "When agent X loads this skill at step Y, what decision does this section enable that X couldn't make without it?"

For clusters with ≥5 files, present the consumer-impact framing and grounding results to the user via `askQuestions` before generating proposals. For smaller clusters, proceed directly but include the framing in proposal rationale.

## 5. Core Analysis Dimensions

Evaluate the cluster across all dimensions below.

### 5.1 Correctness

- Are instructions internally coherent and executable?
- Are cross-references valid and resolvable?
- Do sequencing rules align with actual workflow expectations?

### 5.2 Completeness

- Does the target have enough guidance to operate safely?
- Are any required tool, routing, or output contracts missing?
- Are consumer assumptions unaddressed?

### 5.3 Naming and Structure

- Are section names consistent with ecosystem conventions?
- Is content placed in the correct file type (agent, skill, instruction, prompt)?
- Is there misplaced content that should move within the cluster?

### 5.4 Value Per Instruction

- For each section, does the content change model behavior?
- Does the instruction justify its context-window cost?
- Mark low-value content that does not alter decisions.

### 5.5 Signal-to-Noise (Per Sentence)

- Apply the 7-category taxonomy sentence-by-sentence.
- For each flagged sentence, propose one action:
  - keep
  - terse rewrite
  - delete
  - move
- Always include reason and confidence (0.0-1.0).

### 5.6 Cross-File Coherence

- Identify duplicated rules across the loaded cluster.
- Identify contradictions between target and consumers.
- Propose authoritative placement when duplication exists.

## 6. Output Contract (Structured Decision Per Proposal)

Produce one proposal package in this exact order:

1. Structural Proposals (first)
   - Flow fixes, completeness fixes, and content moves between files.
2. Compression Proposals (second)
   - Section-level and sentence-level reductions with taxonomy labels.
3. Issues (third)
   - Broken links, missing tools, naming mismatches, unresolved references.

### 6.1 Decision Format (Required Per Proposal)

Each section-level proposal must use this structure:

```
**Status quo:** What exists, where, and its current role.
**Problem:** Why this is a candidate for change (audience mismatch, redundancy, staleness, zero behavioral impact, speculative infrastructure).
**Options:**
  - (a) Keep as-is — Pro: {}, Con: {}, Risk: {} — Confidence: X
  - (b) Compress/rewrite — Pro: {}, Con: {}, Risk: {} — Confidence: X
  - (c) Delete — Pro: {}, Con: {}, Risk: {} — Confidence: X
  - (d) Move to {file} — Pro: {}, Con: {}, Risk: {} — Confidence: X
**Recommendation:** Option (X) because {reasoning}.
**Expected outcome:** After this change, when agent {A} loads this skill at step {S}, it will {concrete behavioral description of what's different for the consumer}.
```

Not every proposal needs 4 options. Simple fixes (broken paths, typos) need only a fix description and confidence. Section-level and subsection-level decisions always need the full format.

### 6.2 Proposal Grouping

Group related proposals into coherent decision units. When a subsection deletion subsumes individual sentence-level edits, present the subsection decision first and note which lower-level proposals it absorbs.

## 7. Interaction Model (Approval Loop)

Use section-by-section approval via `askQuestions`, grouped by file.

Per file, present grouped proposals (using §6.1 format inline in chat above the askQuestions call) and ask:

- Approve all in this file
- Approve selected items
- Reject selected items
- Request rewrite of selected items
- Skip file for now

After two consecutive files are approved without edits, offer a batch-approve escape hatch:

- Batch-approve all remaining low-risk compression items
- Continue section-by-section

Never apply unapproved changes. Keep a running ledger of approved/rejected/deferred items.

After applying changes, verify downstream references still resolve before continuing to the next file.

## 8. Guardrails

- Do not broaden scope beyond the selected target cluster.
- Do not run ecosystem-wide coherence checks; that belongs to broad audit mode.
- Do not claim all files need compression; no-change outcomes are valid.
- Prefer precise cuts over broad rewrites.
- Preserve procedural fidelity and institutional memory unless evidence supports change.
- Do not propose changes based solely on text analysis — verify real-world grounding for feature-specific sections.

## 9. Final Deliverable Format

At completion, output:

1. Target summary
   - mode, target, files loaded, and any sampling notes
2. Structural proposal summary
3. Compression proposal summary
4. Issues summary
5. Approval ledger
   - approved, rejected, deferred
6. Residual risks and recommended next command

If the user stops early, output the current ledger and remaining queue.

## 10. Continuation Protocol

After delivering §9, do not stop. Use `askQuestions` to offer:

- Commit the changes (with proposed commit message)
- Run another target through the audit
- Revisit a deferred or rejected proposal with new framing
- End session

Never terminate without explicit user confirmation that the session is complete.
