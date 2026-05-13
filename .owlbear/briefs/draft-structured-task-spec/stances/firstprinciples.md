# First-Principles Stance — AC + Proof Bundle in Frontmatter

## Irreducible Core

Two claims survive reduction:

1. **Proof bundle is a single enum that agents and reviewers need to dispatch on.** This is genuinely load-bearing — it determines test-writer scope, challenger involvement, reviewer depth. Moving a single enum to frontmatter is trivially correct and low-cost.

2. **AC defines task completion criteria.** True. But the proposal's structural prescription (frontmatter YAML) does not follow from this claim alone.

## Assumptions Challenged

### A1 — "AC is stable specification" (partially unearned)

The framing treats AC as stable-once-written, like `priority` or `tags`. In practice, AC gets refined during architecture review and sometimes rewritten entirely when the architect challenges scope. AC is *more* stable than work logs but *less* stable than the fields already in frontmatter. Calling it "specification" overstates its rigidity and biases toward a container (YAML schema) optimized for things that don't change.

**Irreducible version:** AC is *more structured* than work logs. It is not necessarily *more stable*.

### A2 — "Not machine-queryable" is a problem (unearned)

The context states AC is "not machine-queryable" as if self-evidently bad, but names no consumer that needs programmatic AC queries today. Agents read `show_task` and parse the body — this works. `list_tasks` doesn't need per-task AC. `pick_tasks` dispatches on priority/status/tags, not AC content. The only consumer that would benefit from structured AC is the Cockpit UI checklist — and that's a presentation preference, not a structural necessity.

**Challenge:** Name the workflow that breaks or degrades because AC isn't in frontmatter. If the answer is "Cockpit wants a checklist," that's a UI feature request, not a data model problem.

### A3 — "Frontmatter is the right container for AC" (borrowed, not earned)

YAML frontmatter is optimized for flat key-value pairs and short scalar lists. AC items can be multi-line, contain technical language, reference code paths. Cramming them into YAML trades *human* ergonomics for *machine* ergonomics — in a system where the primary authors and readers are LLM agents working in markdown. Agents are *better* at parsing markdown sections than humans are at writing YAML lists with proper quoting and escaping.

Proof bundle (single enum) fits frontmatter naturally. AC (variable-length, potentially complex strings) does not. The "shared insight" framing hides this asymmetry.

### A4 — "The body is the problem" (misdiagnosed)

The actual complaint is that AC gets "buried as body grows with work logs." But if the real issue is findability in a noisy body, the fix could be body structure conventions (enforced `## Acceptance Criteria` section at top, clear `## Work Log` boundary) rather than migrating content to a different container. Agents already parse markdown headings reliably. A convention-based fix has zero model/API/migration cost.

**Irreducible version of the problem:** The body lacks enforced structure, so everything in it — including AC — is positionally unstable. Moving AC to frontmatter treats one symptom. Enforcing body section conventions treats the cause.

### A5 — "AC and proof bundle share the same insight" (false economy)

Proof bundle is a closed enum, single value, trivially fits frontmatter, trivially fits MCP tools. AC is an open-ended list of variable complexity. Their similarity begins and ends at "both are spec-ish." Bundling them forces the harder problem (AC in YAML) to ride the easier problem's timeline, when the easier problem could ship independently in hours.

## What Survives

| Claim | Status | Notes |
|-------|--------|-------|
| Proof bundle belongs in frontmatter | **Earned** | Single enum, clear dispatch value, zero ergonomic cost |
| AC should be more findable | **Earned** | But the solution space is wider than "frontmatter" |
| AC belongs in YAML frontmatter | **Unearned** | Container choice not justified; convention-based alternatives not eliminated |
| Machine-queryable AC is needed | **Unearned** | No concrete consumer named |
| Bundle AC + proof_bundle as one feature | **Unearned** | Asymmetric complexity hidden by shared framing |
| Forward-only migration is sufficient | **Conditionally earned** | Only if the chosen approach doesn't create two parallel AC locations indefinitely |

## Alternative Decompositions Worth Testing

1. **Proof bundle to frontmatter (standalone).** Ship in hours. No controversy. Unblocks reviewer/test-writer dispatch improvements independently.

2. **Body structure convention.** Enforce AC at fixed position (first body section), enforce work-log boundary. Zero schema cost. Agents already parse this. Cockpit can render it by parsing markdown rather than reading a YAML field.

3. **AC in frontmatter (if earned).** Only after naming the concrete consumer that needs programmatic AC access beyond "render a checklist." If that consumer exists, the YAML ergonomic cost is justified.

## Confidence

**0.75** — The proof-bundle half is clean and should ship. The AC half is solving a problem that hasn't been demonstrated to exist beyond aesthetic preference, using a container that's a worse fit than the current one for its content shape. The bundling hides this asymmetry.
