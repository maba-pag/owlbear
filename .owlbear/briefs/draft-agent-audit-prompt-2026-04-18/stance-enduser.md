# End User Stance — Agent-Audit Prompt Rewrite

**Panelist:** End User (UX practitioner)
**Confidence:** 0.82
**Critic cycles:** 5 (max)

---

## User Experience Stance

The current prompt has a working skeleton but fails the human who must sit through dozens of findings without fatigue safeguards, progress visibility, or graceful exit. The executing agent also faces ambiguous instructions (two conflicting output formats, vague "verify," unspecified tool use). This stance defines the UX contract for both audiences.

---

## 1. Finding Presentation — The Card

Every finding is presented as a **card** with four sections. The entire card is shown inline in the chat message — the user must never open a file or external tool to evaluate a finding.

### Header

```
[Category] Finding N of ~M — Severity: HIGH/MED/LOW
```

Category = one of the existing audit categories (Structural, Duplication, Placement, Quality, Pipeline, SNR, Memory). Progress is approximate (`~`) because the queue shifts as fixes propagate.

### Evidence (proof only — no interpretation)

Adapts by finding type:

| Finding Type | Evidence Shape |
|---|---|
| **Text defect** | Blockquote of offending text with file path + line number |
| **Missing content** | Governing rule (quoted) + specific files searched (listed) + "not found" |
| **Cross-file mismatch** | Quotes from both files, side by side |
| **Memory entry** | Entry quote (with MCP entry ID if canonical) + conflicting source quote; follows owlbear-system.instructions.md governance tiers |

Evidence contains zero interpretation. Any analysis of *why* the evidence matters or *where* content should go belongs in Recommendation.

### Options (conditional)

Included whenever multiple valid approaches exist, regardless of severity. Omitted only when there is a single clear fix. Each option: one-line description, pros, risks. Cap at 2–3 including "do nothing."

### Recommendation

- Governing rule citation from the most specific applicable source (skill > instructions > copilot-instructions).
- Diff preview (before/after code block) for text changes; change plan for structural or multi-file changes.
- One-sentence impact statement: what breaks or degrades if unfixed.
- Confidence score (0.0–1.0) — informational, not used to branch UX.

### Approval (via askQuestions)

Minimum options for every finding: **Approve / Skip / Pause.**

For MED or HIGH severity, or when the Options section is present (genuine ambiguity): add **Approve with modification (free-text).**

---

## 2. Loop Fatigue Mitigation

The one-finding-at-a-time loop is a confirmed constraint. Fatigue is managed within that loop, not by breaking it.

### Severity-first ordering

HIGH → MED → LOW. If the user bails early, the most impactful fixes are already done.

### Severity rubric

| Severity | Criteria |
|---|---|
| **HIGH** | Pipeline breaks, missing audit dimensions, wrong routing, structural violations that cascade |
| **MED** | Rule violations, duplication (Rule of Two), content misplacement (80% rule) |
| **LOW** | SNR issues, naming conventions, minor phrasing, style |

### Ceremony scales with ambiguity

The Options section appears only when there's genuine choice. LOW-severity findings with a single clear fix get the 3-option approval. This reduces per-finding cognitive overhead without hiding real trade-offs.

### Progress indicator

Every card shows "Finding 3 of ~15 remaining." The `~` signals the count is approximate and dynamic.

### Conditional phase breaks

After completing all findings in a severity tier, show a brief summary and natural pause point IF the next tier has ≥ 3 findings: "High-severity complete (5/5 fixed). 10 medium-severity findings next. Continue / Pause?"

### Queue re-evaluation after structural fixes

After a structural or cross-file fix, the agent re-evaluates ALL remaining queued findings for continued relevance. Findings resolved by a prior fix are removed. The agent notes: "Re-evaluated queue: 2 findings resolved by prior fix, removed." Progress indicator updates.

---

## 3. Bail / Pause UX

### Pause is always available

Every askQuestions includes "Pause" as an option.

### On pause or bail

The agent shows a session summary: findings addressed, findings skipped, remaining queue size, categories covered. State is written to session memory for within-session resumption.

### Acknowledged deviations

When the user rejects a finding because the deviation is intentional (not because the agent is wrong), they can mark it as an **acknowledged deviation** with reasoning. Stored persistently in `.owlbear/audit/deviations.md`.

On each future run, the agent checks acknowledged deviations for staleness: if the governing rule changed OR the specific file location referenced in the finding changed, the deviation is re-presented. Staleness is scoped to the governing rule and the finding's target location — not the entire searched corpus (to avoid overfiring from unrelated churn).

Acknowledged deviations are mentioned in the run preamble ("3 acknowledged deviations from prior runs") but not re-presented unless stale.

### Disposition model (simplified)

| State | Persistence | Behavior on next run |
|---|---|---|
| **Fixed** | In the code | Won't appear (issue no longer exists) |
| **Skipped** | Ephemeral | Resurfaces if still present |
| **Rejected** | Ephemeral | Resurfaces if still present |
| **Acknowledged deviation** | `.owlbear/audit/deviations.md` | Suppressed unless staleness triggers |
| **Deferred** (from verification) | Ephemeral | Resurfaces if still present |

Only two durable states exist: the code itself (for fixes) and the deviations file (for acknowledged deviations). Everything else is ephemeral and reconsidered fresh.

### Drift tolerance

If saved state is > 7 days old, default to "start fresh."

---

## 4. "Run from the Top Again" UX

### End-of-run verification (mandatory)

When the finding queue is exhausted, before the "run again?" prompt, the agent runs holistic verification:

1. Trace an implementation task through the full pipeline.
2. Trace a non-implementation task (research, config).
3. Verify rejection routing is cause-based and consistent.
4. Spot-check 3 files for SNR.
5. Check memory governance compliance across audited stores.

Results are shown to the user. If verification surfaces new issues, each is presented with askQuestions: "Address now (extends session) / Defer to next run?"

### Summary and status

The summary distinguishes completion states:

| Status | Meaning |
|---|---|
| **Audit complete** | All findings addressed, verification passed |
| **Audit complete — N items deferred** | Verification found issues, user chose to defer |
| **Partial audit — [gap]** | Coverage gap (e.g., canonical memory unavailable) |

askQuestions: "Run again from the top? / Done for today."

On re-run: fully fresh evaluation. No suppression of previously rejected or skipped findings. Audit integrity demands fresh eyes.

---

## 5. Trust Signals

For the user to confidently approve or reject a finding:

1. **All evidence inline.** The user evaluates entirely from the chat message. No file-opening required.
2. **Rule citation.** Every finding traces to a specific governing rule from the most specific applicable source.
3. **Visual confirmation.** Diff preview for text changes; change plan for structural changes. The user sees exactly what will change before approving.
4. **Impact statement.** One sentence: what breaks or degrades if unfixed.
5. **Post-implementation verification.** After each fix: agent re-reads the modified section, confirms the edit landed, and spot-checks related files for breakage. Result shown inline.
6. **End-of-run holistic verification.** Pipeline traces, rejection routing, SNR spot-checks, memory governance. Coverage artifact.
7. **Rejection is safe.** Agent acknowledges rejection, optionally captures reasoning ("Why?" free-text), moves on. No arguing, no re-asking.

---

## 6. Ambiguity Surface for the Executing Agent

The current prompt has seams where an LLM will misinterpret:

| Ambiguity | Fix |
|---|---|
| **Two output formats** — the big markdown template (Findings/Checklist/Remediation Plan/Verification) and the one-at-a-time card protocol contradict each other. Agent will try to produce both. | Remove the big template. Replace with: (a) the per-finding card structure, (b) the end-of-run summary and verification format. |
| **"Save plan to session memory"** — vague. What's in the plan? | Specify: "After reading all files, write a prioritized finding queue (category, file, severity, one-line description) to session memory. This is the working queue." |
| **"Implement"** — never specifies how. | Specify: "Apply the approved edit using file editing tools (replace_string_in_file, create_file, etc.)." |
| **"Verify"** — "confirm the edit took effect" is too vague. Agent will just say "done." | Define two levels: (a) per-finding: re-read the modified file section, confirm expected text is present, spot-check related files; (b) end-of-run: holistic pipeline verification. |
| **Reading vs. presenting** — "Read ALL files first" but nothing says "form the complete queue before presenting." | Specify: "Do not present any finding until all files are read and the full queue is formed." |
| **Queue management** — agent has no instruction on what to do when fixes invalidate subsequent findings. | Specify: "After structural or cross-file fixes, re-evaluate all remaining queued findings. Remove resolved items. Update progress." |
| **Memory governance** — new dimension with no agent instructions. | Specify: "Follow the memory governance tiers in owlbear-system.instructions.md. If owlbearMemory MCP is unavailable, audit file-based memory only and report partial coverage." |

---

## Key Trade-offs

| Trade-off | Position | Rationale |
|---|---|---|
| Batching vs. one-at-a-time | One-at-a-time (confirmed constraint) | Fatigue managed via severity ordering, ceremony scaling, and phase breaks instead |
| Full Options on every finding vs. conditional | Conditional (present only when genuine ambiguity exists) | Reduces ceremony for clear fixes without hiding real trade-offs |
| Cross-session resume vs. fresh evaluation | Fresh evaluation (with acknowledged deviations) | Queue is too volatile for reliable resume; fresh eyes maintain audit integrity |
| Confidence as UX branch vs. informational | Informational only | Confidence scoring is not standardized; severity is more predictable for branching |
| Big aggregate report vs. incremental | Incremental with end-of-run summary | Interactive loop makes a pre-generated report stale after the first fix |

---

## Warnings

1. **askQuestions tension.** The confirmed constraints require askQuestions for all user-facing interaction. Research files in the repo (askquestions-cleanup-scope.md, vs-code-new-tools-evaluation.md) suggest the project is moving toward tool-agnostic structured options and away from askQuestions. This stance follows the confirmed constraint. If the project direction changes, the prompt's interaction model will need rework. The prompt should use behavioral language ("present structured options for the user to choose") with askQuestions as the current implementation mechanism, not hardcode askQuestions into the interaction design.
2. **Acknowledged deviations governance.** `.owlbear/audit/deviations.md` is a new persistent artifact with no existing precedent. The prompt writer should define the minimum fields (finding description, governing rule, referenced files, date, user reasoning) to make staleness checks computable.
3. **End-of-run verification extends sessions.** The mandatory holistic verification phase can surface new issues, each of which gets an "Address now / Defer" prompt. If many issues surface, this extends the session significantly. The user's "Done for today" escape valve mitigates this, but the prompt should warn the agent to keep verification presentation concise.
