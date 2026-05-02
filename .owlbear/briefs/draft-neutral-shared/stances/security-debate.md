# Security Debate Log — Neutral Shared Layer

## Cycle 1

### Initial Position (pre-Critic)

Assessed the refactoring as security-neutral to mildly positive across six dimensions:

1. Trust boundary unchanged (same user controls both sides)
2. Path injection via placeholders non-escalating (no runtime resolution mechanism)
3. Guard hooks unaffected (confirmed clean by audit)
4. Information exposure improved (OwlBear-dev layout removed from shared)
5. MCP tool arguments not affected (wrong path = error, not escalation)
6. Overall: no new attack surface

### Critic Challenges (7 moderate, 1 minor)

**On trust boundary (Claim 1):**
- `.github/copilot-instructions.md` is always-loaded and functions as a priority override, not a normal skill — broader blast radius than shared content
- Moving from read-only shared layer to project-local mutable override is a different integrity assumption
- Sharing docs explicitly support team use, making "single owner" assumption brittle

**On path injection (Claim 2):**
- `setup/init.py` has template substitution (`owlbear_rel_path`, `owlbear_abs_path`) at init time — "no resolution mechanism" is overstated as a global claim
- Consumer VS Code settings grant read access to specific paths, not arbitrary filesystem — "full workspace access" is imprecise

**On hooks (Claim 3):**
- Audited seed hooks ≠ deployed consumer hooks; sharing-guide documents that local hooks may drift

**On MCP/path arguments (Claim 5):**
- `h-quality-runner` uses path prefixes as behavioral switches (Vitest vs pytest detection) — genericization changes behavior, not just prose
- Knowledge ops has path-bearing parameters that are operational inputs, not merely illustrative

**Blind spots identified:**
- Position used privilege-escalation lens exclusively, ignoring integrity dimension
- Conflated "not auto-exposed in context" with "not accessible"
- Path strings treated as passive documentation when some are routing inputs

**Critic confidence in original position: 0.56 (medium pressure)**

### Refinements Applied

1. **Acknowledged blast radius distinction.** `.github/copilot-instructions.md` always-loaded nature noted as integrity-relevant surface change. Added recommendation to keep extracted content factual/declarative.

2. **Clarified template resolution boundary.** Init-time templating (`setup/init.py`) exists but inputs come from user-controlled `owlbear-project.json`, not from shared content. Runtime skill resolution still doesn't exist. Narrowed the claim appropriately.

3. **Narrowed hook claim.** From "hooks are clean" to "refactoring doesn't introduce hook vulnerability; drift is pre-existing and unrelated."

4. **Elevated path-sensitive routing.** From dismissal to a named risk with specific recommendation. `h-quality-runner`'s branching logic must be updated alongside its path examples.

5. **Added future-team consideration.** Noted that if sharing model expands beyond single-user, integrity properties of the mutable override layer need re-evaluation. Not blocking for current scope.

6. **Did not concede on core position.** The fundamental assessment (security-neutral, no privilege escalation, same trust principal) holds. The Critic's challenges refined precision and surfaced implementation care-abouts, but did not reveal a vulnerability.

### Final Assessment

Position hardened from "security-neutral to mildly positive" to "security-neutral with minor improvements and two implementation care-abouts." Confidence rose from implicit ~0.80 to explicit 0.88 after addressing the valid nuances.
