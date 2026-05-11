# Security Proposal — Proof Bundle Taxonomy Reform

## Design Summary

**Recommended: Approach 1 — 2+2 Model** with a mandatory security-escalation guardrail.

Two primary axes (`test`, `proof`) control test creation and proof execution. Two derived-with-override signals (`challenge`, `code-reader`) control adversarial review. The override mechanism is the critical security feature: it decouples adversarial review from test depth so that security-relevant checks cannot be silently bypassed by setting a low proof level.

The extended single-axis model (Approach 2) is rejected because fixed dispatch per depth value creates a rigid coupling between "how much testing" and "how much adversarial scrutiny." That coupling is the root cause of the current security gap — td:0 silences everything, including challenger and code-reader, with no override.

### Task-Level Annotation Format

```yaml
# In task frontmatter or architecture review output:
test: skip | smoke | full
proof: none | existing | scoped | full
challenge: derived | required | skip    # default: derived
```

`code-reader` dispatch is not an explicit field — it is derived deterministically from `proof` (see dispatch rules below). Only `challenge` gets an explicit override because challenger dispatch involves a judgment call about risk that the architect is positioned to make.

## Key Structural Choices

### 1. Derivation Defaults — Least Privilege by Default

| test | proof | Derived challenge | Derived code-reader |
|------|-------|-------------------|---------------------|
| skip | none | skip | no |
| skip | existing | skip | no |
| smoke | scoped | required | no |
| smoke | full | required | no |
| full | scoped | required | no |
| full | full | required | yes |

**Security rationale:** Challenger is ON by default for any task that writes new tests (`test != skip`). Code-reader is ON only for `proof:full`. These defaults mean the only way to get zero adversarial review is `test:skip` without an override — and even then, the escalation guardrail (below) can intervene.

### 2. Override Mechanism — Architect Can Force, Not Suppress

The `challenge` field has three values:

- **`derived`** (default, omitted): Follow the derivation table above. No action needed from the architect.
- **`required`**: Force challenger dispatch regardless of test/proof axes. The architect sets this when a task touches security-sensitive code, trust boundaries, or access control logic — even if `test:skip proof:existing`.
- **`skip`**: Suppress challenger even when derivation would dispatch it. **This value triggers a mandatory reviewer flag** — the reviewer must acknowledge the skip in their verdict with an explicit rationale. The skip is not silent.

There is no `code-reader: skip` override. Code-reader dispatch is mechanical (proof:full → yes, else no). If an architect wants code-reader on a lower proof level, they escalate `proof` to `full`. This prevents an override surface that could suppress the most thorough adversarial check.

**Security rationale:** The override is asymmetric by design. Escalating security scrutiny is frictionless (`challenge:required`). Suppressing it requires a justification trail (`challenge:skip` + reviewer acknowledgment). This is defense-in-depth — the path of least resistance is the secure path.

### 3. Security-Escalation Guardrail — File-Path Trigger

A file-path–based escalation rule in `r-pipeline-protocol` auto-sets `challenge:required` when the changed-file list touches designated security-sensitive paths. The architect can still set `test:skip proof:existing` for speed, but challenger fires regardless.

**Trigger paths** (configurable, initial set):

```
share/skills/r-pipeline-protocol/    # The routing convention itself
share/skills/w-code-review/          # Review dispatch rules
share/skills/w-task-verification/    # Exit gate
share/instructions/pipeline-agents.instructions.md
serve/mcp-*/                         # MCP server code (trust boundary)
setup/                               # Workspace initializer (supply chain)
SECURITY.md
```

**Mechanism:** The architect skill (`w-arch-review`) checks the task's changed-file list against the trigger-path set during Step 2 (test-depth assignment). If any path matches, `challenge:required` is auto-applied and the architect documents the trigger. The architect cannot downgrade this to `derived` or `skip` — the guardrail is not overridable by the same role that assigns proof depth.

**Security rationale:** This is a trust-boundary enforcement. The architect is trusted to assess routine risk, but for code that controls the pipeline's own security posture, a second pair of eyes (challenger) is mandatory. The guardrail prevents a single point of failure where one agent's misconfiguration silences all adversarial review on security-critical changes.

### 4. No Named Bundles

Bundles are rejected from the security perspective. They add an indirection layer between what the architect writes and what agents read. Each indirection is an opportunity for misinterpretation — the bundle name maps to axis values, and if the mapping table drifts from the dispatch table, the system silently misroutes. Two explicit axis values (`test:X proof:Y`) are auditable; a bundle name (`smoke`) requires looking up a mapping to verify what dispatch behavior it produces.

### 5. Legacy Compatibility — Degradation Direction

In-progress tasks retain `(td:N)` annotations. The mapping is:

| Legacy | New equivalent |
|--------|----------------|
| td:0 | test:skip proof:none |
| td:0 + "Existing proof required" | test:skip proof:existing challenge:required |
| td:1 | test:smoke proof:scoped |
| td:2 | test:full proof:full |

**Security note on td:0 legacy mapping:** The current td:0 with existing-proof prose is mapped to `challenge:required` (not `derived`). This is a deliberate escalation — the current system silently skips challenger for these tasks, which is the exact security gap this reform fixes. Legacy td:0-with-proof tasks get MORE scrutiny under the new model, not equal.

## Trade-offs

| Trade-off | Accepted cost | Security benefit |
|-----------|--------------|-----------------|
| Two fields instead of one integer | Slightly more annotation work for the architect | Each field maps to exactly one downstream decision — no conflation, no silent coupling |
| Override field adds a third field in edge cases | Three fields when the architect forces or suppresses challenge | Explicit paper trail for security-relevant routing decisions |
| File-path guardrail requires path-set maintenance | Someone must update the trigger-path list when security-sensitive code moves | Prevents the single highest-impact failure mode: pipeline changes that skip their own quality checks |
| No bundle shorthand | Architects write `test:X proof:Y` explicitly every time | No mapping-table drift; what you read is what agents dispatch |
| Asymmetric override (easy to escalate, hard to suppress) | Architects who genuinely want to skip challenger must accept reviewer scrutiny | The secure path is the easy path — defense-in-depth without friction for legitimate low-risk tasks |

## Domain Rationale

### Why Not Extended Single-Axis (Approach 2)

The extended single-axis model (e.g., `skip / existing / smoke / behavioral / critical`) maps each value to a fixed dispatch row. This means:

1. **No override mechanism.** A task at `existing` depth has fixed challenger behavior. If that behavior is "skip," there is no way to force adversarial review without promoting the entire task to a higher depth — which triggers unnecessary test writing and proof execution just to get a challenger pass.

2. **Blast radius of misconfiguration is total.** Setting the wrong single value silences or activates ALL downstream checks simultaneously. With 2+2, setting `test:skip` when you meant `test:smoke` only affects test creation — proof execution, code-reader, and (with the guardrail) challenger are unaffected.

3. **The "security review" concern is always orthogonal to "how many tests."** A documentation-only task (`test:skip`) that changes `SECURITY.md` needs challenger review. A single-axis model either invents a dedicated "security" depth level (conflating security with test creation) or can't express this case at all.

### Why the Override Is Asymmetric

Symmetric overrides (architect can both force and suppress any signal) create an authorization problem: the architect is both the risk assessor and the person choosing whether to accept the risk. In access-control terms, this is role conflation — the same principal evaluates and approves.

The asymmetric design splits the authority:
- **Architect** can escalate (force challenger) — this is always safe, it adds scrutiny.
- **Architect** can request suppression (`challenge:skip`) — but the **reviewer** must validate the rationale. Two roles must agree to reduce scrutiny.

This is the separation-of-duties principle applied to pipeline routing.

### Why the File-Path Guardrail Is Not Overridable

The guardrail exists because the pipeline's own security posture depends on the routing convention. If the routing convention can be changed without adversarial review, the entire system's quality guarantee is circular — the thing that ensures quality can be modified without the quality checks it ensures.

Making the guardrail non-overridable by the architect breaks this circularity. The only way to change the trigger-path set is to modify `r-pipeline-protocol`, which is itself in the trigger-path set, which forces challenger dispatch on that change. The system is self-protecting.

## Failure Mode Analysis

| Failure mode | Blast radius | Detection | Mitigation |
|-------------|-------------|-----------|------------|
| Architect sets wrong `test` value | Test-writer creates wrong test type; proof/challenge unaffected | Reviewer sees test-code mismatch during review | Bounded — only test creation is affected, not review depth |
| Architect sets wrong `proof` value | Quality-runner runs wrong scope; code-reader may or may not fire | Reviewer sees proof gap if results don't match AC | Bounded — test creation is unaffected |
| Architect omits `challenge` field | Falls to `derived` default, which is the secure default | No detection needed — default is correct | By design |
| Architect sets `challenge:skip` on security-sensitive task | Challenger does not fire | Reviewer must acknowledge skip; file-path guardrail overrides for known-sensitive paths | Dual control — reviewer + guardrail |
| File-path guardrail has stale path set | New security-sensitive code escapes auto-escalation | Periodic audit of trigger paths (quarterly or on security review tasks) | Residual risk — accepted, mitigated by manual `challenge:required` |
| Consumer skill reads wrong axis | One downstream agent misroutes | Other agents are unaffected (axes are independent); test suite for skill files catches parse errors | Bounded — no single parse failure cascades |
| Legacy td:0 task misinterpreted | Mapped to `test:skip proof:none` (most conservative) | If existing-proof prose is present, mapping escalates to `challenge:required` | Legacy mapping errs toward more scrutiny |

## Escalation Path

When a task touches security-sensitive code with low proof depth:

1. **Automatic:** File-path guardrail detects the match in `w-arch-review` Step 2. Architect documents the trigger. `challenge:required` is applied regardless of `test`/`proof` values. No agent action needed.

2. **Manual (guardrail miss):** Architect recognizes security relevance during risk assessment and sets `challenge:required` explicitly. This is the current-state equivalent of the architect's judgment call, but now it's a structured field instead of prose.

3. **Reviewer backstop:** If both automatic and manual escalation fail, the reviewer sees the changed-file list and can flag the absence of challenger output as a review finding. This is the third line of defense — it catches the case where the guardrail path set is stale AND the architect missed the risk.

4. **Auditor final check:** `w-task-verification` (the exit gate) does not currently check for challenger output, but a simple "challenger-ran-if-security-tagged" assertion could be added as a fourth-line defense. This is not in the current proposal scope but is architecturally trivial to add.

## Confidence

**0.88** — High confidence that the 2+2 model with asymmetric override and file-path guardrail addresses the core security gap (silent skipping of adversarial review). The design is minimal — it adds one optional field and one mechanical guardrail to the existing 2-axis model. The main residual risk is guardrail staleness, which is mitigatable by self-referential path inclusion.
