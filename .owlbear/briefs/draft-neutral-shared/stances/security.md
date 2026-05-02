# Security Stance — Neutral Shared Layer

## Position

This refactoring is **security-neutral with minor improvements**. It does not introduce new attack surface, does not escalate privileges, and reduces unnecessary information exposure. The trust model (single user controls both repo and consumers) is unchanged.

Two areas warrant care during implementation:

1. **Always-loaded blast radius.** Content extracted from conditional skills into `.github/copilot-instructions.md` gains broader influence — that file is loaded on every agent turn for every mode. Path-specific content placed there can shape AI behavior more strongly than the same content in a skill file that triggers only on `applyTo` match. This is not a vulnerability but it is an integrity-relevant surface change.

2. **Path-sensitive routing logic.** At least one shared skill (`h-quality-runner`) uses path prefixes as behavioral switches (e.g., detecting `serve/cockpit/web/` to select Vitest vs pytest). Genericizing path examples in such files is not merely cosmetic — it must be accompanied by logic changes or the consumer's AI will route incorrectly. Incorrect routing is a correctness bug, not a security vulnerability, but in a defense context (guard hooks, deny-writes), incorrect path detection could degrade enforcement.

## Risk Assessment

| Risk | Severity | Likelihood | Notes |
|------|----------|------------|-------|
| Trust boundary weakened | None | N/A | Unchanged — same principal controls both sides |
| Path injection via placeholders | Negligible | Very low | No runtime resolution mechanism exists in VS Code skill files; prose placeholders are not machine-evaluated |
| Privilege escalation via crafted copilot-instructions.md | None | N/A | That file is project-local, under project owner's source control |
| Guard hook integrity degraded | None | N/A | Refactoring doesn't touch hooks; all 6 are path-generic already |
| Information exposure | Improved | N/A | OwlBear-dev internal layout (directory table, namespace table) will no longer ship in shared consumer content |
| MCP tool argument misbehavior | Low | Low | Genericized path examples could produce wrong-path errors if consumer follows stale examples literally; no privilege escalation possible |
| Path-sensitive routing misbehavior | Low | Medium | `h-quality-runner` (and possibly others) use path prefixes for tool selection — genericization must update this logic |
| Init-time template injection | Negligible | Very low | `setup/init.py` does template substitution at setup time, but inputs (`owlbear_rel_path`) come from user-controlled `owlbear-project.json`, not from shared content |

## Recommendations

1. **When extracting to `copilot-instructions.md`:** Keep extracted content factual and declarative (directory tables, path mappings). Avoid placing behavioral directives there that override shared skill logic — that creates a split-brain instruction conflict the AI must resolve heuristically.

2. **When genericizing path-sensitive skills:** Audit each file for conditional logic that branches on specific path prefixes. Replace both the example AND the routing logic with a project-configurable mechanism (e.g., "detect from pyproject.toml" or "check for package.json in subdirectory").

3. **Hook independence (no action needed):** The 6 guard hooks use workspace-relative patterns and don't reference `serve/` paths. No changes required. Note: deployed consumer hooks may drift from seed versions — this is a pre-existing concern unrelated to this refactoring.

4. **Placeholder notation:** Use prose descriptions ("your frontend package root") not template syntax (`{frontend_root}`). Prose cannot be mistaken for a resolution mechanism. This is already the preferred approach per research notes.

5. **Future consideration — team scenarios:** The current threat model assumes single-user control of both sides. If the sharing model expands to teammates or organization-level distribution (as `setup/sharing-guide.md` supports), the integrity properties of `.github/copilot-instructions.md` as a mutable override layer would need re-evaluation. Not blocking for this work.

## Confidence

0.88

The high confidence reflects: no secrets at risk, no privilege boundaries crossed, both consumers user-controlled, and the refactoring's primary effect is removing content rather than adding attack surface. Deducted for: the path-sensitive routing nuance (could cause behavioral regression if not handled), and the theoretical future-team integrity question.
