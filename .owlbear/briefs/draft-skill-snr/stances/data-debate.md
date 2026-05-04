# Data Stance — Critic Debate Log

## Cycle 1

### Initial Position (summarized)

1. Signal density is ordinal not cardinal — use High/Medium/Low tiers with structural proxies
2. Classification is binary with asymmetric error costs — bias conservative
3. Taxonomy needs 3 additional categories (institutional memory, anchor repetition, model drift insurance) — fixed-core + emergent
4. Cross-file signal requires consumer-context resolution for all classifications
5. "Trivial knowledge" = appears in pretraining data AND doesn't require project context
6. Broad audit scores must not propagate as ground truth into deep-dive

### Critic Challenges (severity: critical unless noted)

1. **Proxies reintroduce cardinality** — "imperative-to-prose ratio" is numeric; converting to H/M/L just hides calibration. The stance rejects cardinal measurement while smuggling it back in.
2. **Proxies don't track quality** — higher imperative ratio can mean brittle command spam; deeper reading chains can mean bureaucracy.
3. **"False negatives only waste tokens" is too weak** — retained noise dilutes salience and competes with anchors. Position 3's defense of deliberate repetition implicitly concedes attention is scarce.
4. **Binary classification is wrong** — a passage can be institutional memory, anchor repetition, AND consumer-specific signal simultaneously. Not a stable binary label.
5. **Taxonomy is level-inconsistent** — institutional memory (provenance), anchor repetition (rhetorical function), model drift insurance (temporal hedge) are not peer categories.
6. **"Model drift insurance" is unfalsifiable** — any low-value instruction can justify itself by appealing to speculative future regression.
7. **Consumer-context claim contradicts factual-knowledge claim** (moderate) — Position 2 says judgments are reliable for factual knowledge; Position 4 says no ground truth without consumer context. Cannot both be universally true.
8. **"Trivial knowledge" definition is unoperational** — "appears in pretraining data" is not observable to agent or user.
9. **Time horizon conflict** (moderate) — Position 5 evaluates against current model; Position 3 preserves for future drift. Same text can flip status.
10. **Position 6 reintroduces scoring** (minor) — calling output a "score" and failure mode "NaN propagation" suggests numeric design despite anti-cardinality argument.
11. **Interactive loop volume problem** (moderate) — 80 files × per-classification confidence creates unmanageable review surface.

### Blind Spots Identified

- Cross-file contradiction risk (instructions loaded together that conflict)
- Unit of analysis undefined (sentence? section? paragraph?)
- Inter-rater reliability unaddressed
- File heterogeneity (agents vs skills vs instructions vs prompts) makes single tiering logic suspect
- Nominal consumers ≠ actual runtime loading frequency

### Critic Confidence in Position: 0.41

### Revisions Made

- Dropped "model drift insurance" as a category (unfalsifiable)
- Changed from binary to two-axis classification (content function × signal adequacy)
- Acknowledged proxies are numeric but output is comparative ranking, not score
- Added asymmetric-but-both-costly error model (false negatives = silent degradation)
- Bounded "trivial knowledge" by behavioral testability, not pretraining archaeology
- Added unit-of-analysis specification (section for structure, paragraph for adequacy)
- Added inter-rater reliability framing (dropped specific % targets — unmeasurable in practice)
- Narrowed aggressive-cut bias: factual anchors get cautious treatment, not aggressive

---

## Cycle 2

### Revised Position (summarized)

1. Broad audit = comparative triage ranking optimizing expected compression yield
2. Two-axis classification: content function (6 types) × signal adequacy (4 levels)
3. Asymmetric error model with conservative bias on procedures/institutional memory, aggressive on ceremony
4. Fixed-core taxonomy (8 categories) + emergent extension with 3-file promotion threshold
5. Consumer-context resolution mandatory for procedural content, optional for factual
6. "Trivial knowledge" = removing it wouldn't change behavior on representative tasks
7. Unit of analysis: section (structural) / paragraph (adequacy)
8. Inter-rater agreement targets: >80% on function labels, ~60% on adequacy

### Critic Challenges

1. **Taxonomy still level-inconsistent** (critical) — mixes semantic roles (behavioral constraint, procedural sequence) with structural devices (emphasis anchor, cross-reference pointer). Position 4 references "structural content" not in the taxonomy. Taxonomy "grows through use" while claiming stable agreement targets.
2. **Safety argument self-contradicts** (critical) — "NO feedback signal" for false negatives, but interactive loop "catches disagreements." Silent retention is exactly what the loop won't catch. Inter-rater check ≠ single auditor's output reviewed by user.
3. **"Advisory" is rhetorical** (critical) — with finite attention, the ranking IS the gate. Calling it advisory doesn't prevent lockout.
4. **Aggressive cut on factual + optional context = high false-positive path** (critical) — factual anchors are often operational (paths, tool names, routing cues). Optional consumer context on the aggressively-cut class creates direct risk.
5. **No coherent optimization target for ranking** (moderate) — volume, prose density, and repetition measure different things. No resolution when they conflict.
6. **Unit of analysis assumes trustworthy structure** (moderate) — files grew organically and are badly structured. Using section boundaries bakes in current decomposition errors.
7. **Missing signal detection absent** (moderate) — stance is all about compression. Doesn't address how absent-but-necessary instruction is found.

### Blind Spots Identified

- Peer-group definition for "repetition across peers" undefined
- Agreement targets unmeasurable (no sample design, no adjudication rule)
- Model drift makes audit outcomes temporally unstable
- Non-paragraph artifacts (code blocks, tables, frontmatter, bullet imperatives) absent from unit-of-analysis

### Critic Confidence in Position: 0.46

### Revisions Made for Final Stance

- Acknowledged ranking IS the gate — dropped "advisory" framing, added re-runnability as mitigation
- Narrowed factual-anchor treatment to cautious (not aggressive) — only cut when fact provably available in loaded chain
- Added volume-of-loaded-chain as tiebreaker when heuristics conflict
- Dropped specific inter-rater % targets (unmeasurable without experiment)
- Added that deep-dive may propose structural reorganization (not confined to existing boundaries)
- Added explicit scope boundary: broad audit finds missing signal (negative-space), deep-dive does compression only
- Acknowledged behavioral-testability is judgment, not experiment
- Added "stale institutional memory" as 6th compression pattern (institutional memory whose failure is now architecturally prevented)
