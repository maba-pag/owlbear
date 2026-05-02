# Simplifier Stance

## Key Challenges

1. **"Make everything generic" is a false uniform.** Skills split into procedure skills (already generic) and system-awareness skills (the actual offenders). Treating both equally inflates scope ~5x.

2. **The #1 offender is one file.** `owlbear-system.instructions.md` fires on every file operation (`applyTo: "**"`). Contains OwlBear's pipeline diagram, `serve/` directory table, MCP bootstrap table. This single file causes the majority of consumer confusion.

3. **The product IS opinionation.** Abstracting "use uv" into "use your package manager" destroys value. The problem correctly identifies defaults to keep, but "make everything generic" framing creates pressure to weaken them.

## Suggested Decomposition

| Priority | Files | Value |
|----------|-------|-------|
| P1 | Split `owlbear-system.instructions.md` — extract §2-§4 to `copilot-instructions.md` | ~60% of pain |
| P2 | Parameterize 3 path-heavy skills: `r-project-standards`, `h-quality-runner`, `h-agent-structure` | ~25% more |
| P3 (defer) | Full 35-skill audit — mostly cosmetic "OwlBear" mentions in frontmatter | ~15%, low urgency |

## Risks

- Over-abstraction: removing examples strips concreteness that makes skills usable
- Scope creep into agent files: the 26 agents ARE the product, not generic shells
- Premature full-sweep: 2 controlled consumers, fix surgically first

## Strongest Recommendation

P1 alone is a 30-minute edit. P2 is 3 more files. Defer P3 indefinitely until friction reports.

**Confidence: 0.85**
