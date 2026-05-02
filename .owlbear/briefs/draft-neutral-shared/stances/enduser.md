# End-User Stance — Neutral Shared Layer

## Position

**Prose-first genericization with explicit scope-limit signaling.** No template syntax (`{variable, e.g. example}`). Shared files use conceptual nouns ("your source packages", "your frontend package root") and acknowledge their own ambiguity boundaries. Project-local path mapping in `copilot-instructions.md` is recommended for non-trivial projects but not mandatory — the system degrades gracefully without it.

The most dangerous failure mode is not "file not found" — it's **false-green**: an agent runs a command against a plausible-but-incomplete scope and reports success. Template syntax makes this worse by providing a concrete-looking path the model treats as authoritative. Prose at least forces the model into exploration mode.

## Usability Reasoning

### Why no template syntax

`{frontend_root, e.g. serve/cockpit/web/}` has three failure paths for LLM consumers:
1. Model copies the example literally (most common — the "e.g." becomes the default)
2. Model preserves the curly-brace string in generated commands
3. Model recognizes it as a template but has no resolution mechanism

All three are worse than prose. Prose ("your frontend package root") triggers instruction-following behavior rather than template-filling behavior. The model looks for a package.json or vite.config in the project tree. This isn't perfect — but it's the least-bad option given VS Code's lack of variable resolution.

### Why self-sufficiency still holds (with caveats)

D3 mandates skills work without overlay. For standard-layout projects (single Python package, one frontend, obvious test directory), prose instructions ARE actionable through filesystem exploration. D3 is satisfied.

For complex projects (monorepos, multiple package managers per subtree, shared test discovery across multiple roots), prose alone creates false-green risk. The agent finds ONE valid path but misses others. This is where project-local config moves from "nice-to-have" to "quality-critical."

The shared layer should explicitly acknowledge this boundary rather than pretending prose is universally sufficient.

### Why the onboarding moment matters most

The highest-leverage UX intervention is `setup/init.py` scaffolding a path-mapping section in the consumer's `copilot-instructions.md`. Even a commented-out template:

```markdown
## Project Layout
<!-- Uncomment and fill for monorepos or non-standard layouts -->
<!-- Source packages: src/ -->
<!-- Frontend root: web/ -->
<!-- Test directories: tests/ -->
```

This costs nothing for simple projects (they ignore it) and prevents false-greens for complex ones. Without this scaffolding, there's no signal that project-local context EXISTS as an option.

## UX Risks

| Risk | Severity | Trigger |
|------|----------|---------|
| False-green from partial scope | High | Agent runs ruff/pytest on one of N source roots, reports clean |
| Synonym drift across files | Medium | "source packages" in one file, "Python modules" in another, "your packages" in a third |
| Abstract nouns become placeholders-by-another-name | Medium | Model treats "your frontend package root" as a string to pattern-match rather than a concept to resolve |
| Complex-project onboarding gap | Medium | No signal in bootstrap flow that path-mapping exists or is needed |
| Convention vs structure confusion | Low | Prose can't encode "this subtree uses npm, that one uses uv" — that's semantic, not spatial |

## Recommendations

1. **Ban template syntax in shared files.** No curly braces, no `e.g.` examples with OwlBear paths. Prose conceptual nouns only.

2. **Standardize a canonical vocabulary.** Define 3-5 conceptual nouns used consistently across all 10 affected files. Document them once (in the shared README or a vocabulary section of system instructions). Prevent synonym drift.

3. **Add scope-limit notes to command-heavy skills.** Where a skill's commands depend on project layout (pytest testpaths, ruff src list, vitest working directory), include a one-line acknowledgment: "For multi-root or monorepo projects, verify paths against your project instructions."

4. **Scaffold path-mapping in setup/init.py.** Generate a commented path-mapping section in `copilot-instructions.md` during consumer onboarding. This is the single highest-leverage intervention for preventing false-greens.

5. **Add a disambiguation rule to shared skills.** When a conceptual noun resolves to multiple candidates, instruct the model to check project instructions first, then report ambiguity rather than guessing. "If multiple directories match, consult project instructions or ask."

6. **Accept that detection heuristics need real configuration.** The quality-runner's "paths under X use vitest" logic is not a prose problem — it's a behavioral coupling that needs project-level config. Flag it as a structural issue for the architect.

## Confidence

**0.68**

Prose-over-templates is well-grounded (no mechanism for resolution, multiple failure modes for literal copying). The false-green risk identification is the most actionable insight. The "self-sufficient with graceful degradation" framing honestly represents what this approach delivers without overpromising. Gaps: no empirical evidence for LLM behavior across models; no proof that canonical vocabulary prevents drift in practice.
