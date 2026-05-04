# Synthesis — Agent & Skill SNR Tool Pair

## Summary

Three panelists evaluated the two-tool SNR design (broad audit + deep-dive). Strong convergence on architecture, taxonomy, routing, and error model. Primary tension is presentation strategy — whether the deep-dive exposes its adaptive analysis as multiple modes to the user or presents a single unified proposal regardless of file type. All panelists share conservative instincts on cutting and agree on user-bridged (not automated) tool coupling.

## Convergences

### C1 — Two-tool architecture is correct (architect, data, enduser)

No panelist challenges the fundamental split. Each builds upon it as given. The broad audit handles ecosystem-level coherence and triage; the deep-dive handles per-passage classification and compression. Merging them would collapse quality (architect), produce unreliable classifications (data), or create unacceptable cognitive load (enduser).

### C2 — Fixed-core noise taxonomy (architect, data)

Both agree on a small, stable taxonomy inlined in both prompts. Architect names 5 categories; data names 6 (adds "stale institutional memory"). Both reject fully-emergent taxonomies for consistency reasons. Data adds emergent extension (propose new labels, promote after 3+ occurrences) — architect is silent on extension but compatible.

### C3 — Consumer-context resolution before classification (architect, data, enduser)

Architect: deep-dive loads agent + required_reading to judge cross-file dependencies; compression proposals are file-local but safety evaluation is contract-wide. Data: resolving `applyTo` and `required_reading` is mandatory for procedural content; skipping it is a "data integrity violation." Enduser: deep-dive forms its own independent assessment (implicitly requires loading context to do so).

### C4 — Category-grouped ranking, not global (architect, data)

Architect: scoring is peer-relative; a 200-line agent and a 540-line skill aren't comparable. Data: "prose density relative to category peers." Enduser does not contradict.

### C5 — Universal files as highest-leverage class (architect, data)

Architect: `applyTo: **` files flagged separately regardless of category rank — 5% noise reduction in universal saves more than 30% in single-consumer. Data: "volume-of-loaded-chain dominates" as tiebreaker, which naturally elevates universals.

### C6 — User-bridged routing, no automated pipeline (architect, enduser)

Architect: user reads ranking, chooses file, invokes deep-dive. Enduser: deep-dive does NOT receive broad-audit findings automatically — prevents anchoring bias. Both reject injecting audit scores into deep-dive context.

### C7 — Ranking is end-of-run (architect, enduser)

Enduser: ranking requires full cohort; partial ranking at file 5/80 is noise. Architect: durable snapshot artifact with date stamp (implies complete pass). Running "attention flags" (unranked) are acceptable during the audit but the formal ranked deliverable waits.

### C8 — Conservative bias on cuts (architect, data, enduser)

Data: asymmetric error model — false positives (cutting signal) break fast, false negatives (keeping noise) degrade silently. Lean conservative on procedural sequences and institutional memory. Architect: warns against cuts that "look safe in isolation but break distributed behavioral intent." Enduser: structural proposals are the hardest decision; user is freshest reviewing them first.

### C9 — Interactive per-section approval (architect, data, enduser)

All three describe an interactive approval model. Architect: askQuestions per chunk. Data: interactive loop is the validation boundary. Enduser: section-based granularity with escape hatches (batch-approve after trust established).

## Disagreements

### T1 — Presentation strategy: adaptive modes vs. unified proposal

**Architect:** Four chunking strategies by file type (section-batch for workflow skills, full-file proposal for agents, single-pass for short files, step-group batches for procedural prompts). The tool adapts its presentation per file.

**Enduser:** One proposal document per file with two regions (structural changes first, compression edits second), reviewed top-to-bottom. For short files, offer full-file before/after as an alternative. The user's mental model is file-sections, not tool-modes.

**Data:** Silent on presentation format; operates at classification level.

**Tension level:** Moderate. These may be compatible if "adaptive chunking" is internal analysis strategy while "single proposal" is the user-facing output format. But architect explicitly describes presentation to the user varying by type; enduser explicitly argues against mode-switching.

### T2 — Taxonomy size: 5 vs. 6 categories

**Architect:** 5 noise categories (verbose wrappers, over-specification, redundant conditionals, prescriptive templates, cross-reference ceremony).

**Data:** 6 categories — same 5 plus "stale institutional memory." Argues it's a distinct pattern (encodes a failure that's been architecturally prevented).

**Tension level:** Low. Easily resolved by adopting 6.

### T3 — Whether deep-dive proposes structural reorganization

**Data (§7 scope table):** Deep-dive is "compression only" — does not find missing signal.

**Data (same file, below table):** "The deep-dive may propose structural reorganization (splitting sections, moving content to a different file)."

**Enduser:** Structural proposals are front-loaded in the deep-dive's output.

**Architect:** Implicitly supports — full-file proposal for agents implies structural-level reasoning.

**Tension level:** Low-to-none once clarified. "Compression" here means "reduce noise" not "only delete words." Structural reorg is a form of noise reduction. Data's "does not find missing signal" is about negative-space probing (detecting what's absent), not about whether reorganization is in-scope.

### T4 — Power of the ranking as a gate

**Data:** "The ranking IS the de facto gate on deep-dive attention. Acknowledge this honestly rather than hiding behind 'advisory.'"

**Enduser:** Acknowledges funneling (80 → 15-25 → 3-5 per session) but designs escape hatches. Deep-dive works on ANY file including unaudited ones.

**Architect:** Deep-dive "should work on ANY file, including ones not yet audited."

**Tension level:** Low. All agree ranking guides attention; architect and enduser both insist the deep-dive is independently invocable. Data's point is about honesty in framing, not about restricting access.

## Recommendation

Proceed with implementation using these design choices:

1. **Adopt data's 6-category taxonomy** (adds stale institutional memory to architect's 5).
2. **Single proposal format per file** (enduser's model) as the user-facing output, with the tool internally adapting its analysis depth by file type (architect's insight). The user sees one document; the tool reasons adaptively behind the scenes.
3. **Structural proposals are in-scope** for deep-dive (enduser and architect converge; data's "compression only" label is about finding-missing-signal being excluded, not structural reorg).
4. **Consumer-context resolution is mandatory** — deep-dive loads the file's consumer chain before classifying.
5. **Ranking is end-of-run** with unranked "attention flags" during the audit as progressive signal.
6. **User bridges between tools** — no automated context passing.
7. **Section-based approval** with informed batch-approve escape hatch after trust is established.

**Confidence: 0.78** — Strong convergence on fundamentals. Residual risk on whether the single-proposal format scales cleanly to 540-line workflow skills without overwhelming the user (enduser's escape hatches may need tuning in practice).

## Open Questions

1. **Adaptive chunking in prompt expression** — Can the deep-dive's internal 4-strategy approach be described clearly in a `.prompt.md` without making the prompt itself bloated? (architect residual)
2. **End-of-run delay tolerance** — Will the user find end-of-run-only ranking acceptable for an 80-file audit that spans multiple sessions? Unranked attention flags may not provide enough early signal. (enduser residual)
3. **Context budget actionability** — Is "maximum potential context budget" a useful enough metric when some load paths are session-contingent? (architect residual)
4. **Behavioral testability as prompt instruction** — Can "would the model already produce this behavior without the instruction?" be made operational enough for the deep-dive agent to classify reliably? (data residual)
5. **Multi-file analysis limits** — Deep-dive loading agent + all required_reading for the heaviest agents (reviewer, builder) may stress context windows. Fallback strategy undefined. (architect trade-off)
6. **Funnel aggressiveness** — If the broad audit flags 60/80 files, the UX collapses. What's the target false-positive rate for the ranking? (enduser warning)
