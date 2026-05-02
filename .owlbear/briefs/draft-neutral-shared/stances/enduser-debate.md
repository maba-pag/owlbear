# End-User Debate Log — Neutral Shared Layer

## Critic Cycle 1

### Draft Position (v1)

Prose-first genericization. No curly-brace templates. copilot-instructions.md carries concrete paths. setup/init.py scaffolds that file. Where examples are critical, keep OwlBear-dev paths with "adapt to your project" framing.

### Critic Challenges

1. **Self-sufficiency contradiction (critical).** D3 says skills must work without overlay. Position made overlay mandatory by requiring copilot-instructions.md to define conceptual nouns. Shared layer becomes non-self-sufficient.

2. **Claim 6 undercuts claims 1-3 (critical).** Argued models copy examples literally, then proposed keeping OwlBear examples with "adapt" labels. Same failure mode with softer framing. Research notes already push toward removing OwlBear paths entirely.

3. **Linguistic vs structural conflation (critical).** Some files need to MOVE or SPLIT, not just reword. Position framed everything as a wording problem. h-quality-runner detection logic needs behavioral change, not prose.

4. **copilot-instructions.md as scarce budget (moderate).** Repo treats that file as always-on context load. Adding path-mapping sections competes with existing content. Position didn't defend against loading-model concerns.

5. **Unsupported confidence (moderate).** No evidence for "6+ placeholders" threshold. No model-specific data. Research notes only say prose is "clearer" — not proven.

6. **Human debugging underserved (moderate).** Conceptual phrases harder to grep/diff than stable symbolic markers. No vocabulary governance plan.

7. **Bootstrap gap (moderate).** setup/init.py doesn't scaffold copilot-instructions.md today. Signal path doesn't exist in current bootstrap flow.

### Panelist Response

- **Accepted 1:** Dropped mandatory overlay. Revised to "self-sufficient through filesystem inference."
- **Accepted 2:** Dropped claim 6 entirely. No OwlBear examples in shared, period.
- **Accepted 3:** Scoped position to textual genericization only. Acknowledged structural issues separately.
- **Partially accepted 4:** Kept copilot-instructions.md as recommended (not mandatory) path. Minimized to a path-mapping section, not verbose content.
- **Accepted 5:** Removed unsupported thresholds. Stated claims directionally without false precision.
- **Accepted 6:** Added canonical vocabulary standardization recommendation.
- **Accepted 7:** Downgraded setup/init.py scaffolding from blocking to high-leverage recommendation.

---

## Critic Cycle 2

### Draft Position (v2)

"Filesystem-discoverable prose." Shared instructions teach WHAT without encoding WHERE. LLMs discover paths from the filesystem. Three tiers: command examples (prose), detection heuristics (config needed), enumeration lists (category descriptions). Canonical vocabulary. copilot-instructions.md optional.

### Critic Challenges

1. **Discovery is non-deterministic in multi-root repos (critical).** OwlBear-dev has package.json at root AND serve/cockpit/web/package.json. "Frontend package root" is an interpretation, not a filesystem fact. copilot-instructions.md already encodes this explicitly — evidence that filesystem alone was judged insufficient.

2. **Command/heuristic tier split doesn't hold (critical).** "Run tests" already embeds path coupling — uv for Python, npm for frontend. Package-manager choice is semantic, not spatial. The tiers are not cleanly separable.

3. **Canonical nouns too coarse (critical).** Pytest discovery scope ≠ ruff src scope ≠ "source packages" in general. One noun maps to multiple non-equivalent tool configurations.

4. **D3 satisfaction downgraded to "can be attempted" (critical).** "Works without overlay" silently became "can start exploring." OwlBear-dev itself ships explicit path mapping — direct evidence that prose-only was insufficient for this very project type.

5. **Missing failure mode: false-green from incomplete scope (critical).** Agent runs ruff on /tests but misses /serve. Result is green but incomplete. Not modeled in the error analysis.

6. **Filesystem can't encode conventions (moderate).** Package-manager choice, generated-output locations, exclusion boundaries are documented conventions, not directory-name facts.

7. **Category prose loses auditable boundaries (moderate).** Replacing explicit doc-scope lists with "package READMEs in your source tree" loses enforceable boundaries.

8. **Overcorrection from copying risk to under-specification (moderate).** Banning all examples without providing resolution mechanism means the noun IS a placeholder by another name.

### Panelist Response

- **Accepted 1, 4, 5:** Dropped "filesystem-discoverable" as a reliability claim. Acknowledged that non-trivial projects genuinely need project-local config. Identified false-green as the primary UX danger.
- **Accepted 2, 6:** Acknowledged that conventions are semantic, not spatial. Detection heuristics and package-manager choice are structural issues, not genericization-style questions.
- **Accepted 3:** Acknowledged noun coarseness risk. Added vocabulary governance recommendation but limited claims about what it solves.
- **Partially accepted 7:** Acknowledged boundary loss for enumeration cases. Positioned this as a trade-off (losing auditability, gaining generality) rather than pretending prose preserves everything.
- **Partially accepted 8:** Acknowledged the risk. Mitigated with disambiguation rule ("check project instructions or ask") rather than re-introducing examples.

### Final Position Adjustments

- Reframed from "filesystem-discoverable" to "prose-first with explicit scope-limit signaling"
- Made copilot-instructions.md path-mapping "recommended for non-trivial projects" rather than "optional nice-to-have"
- Identified false-green as the primary UX risk (not file-not-found, not template-literal-copy)
- setup/init.py scaffolding elevated to highest-leverage intervention
- Added disambiguation rule: "report ambiguity rather than guess"
- Confidence set at 0.68 — directionally strong, empirically unproven
