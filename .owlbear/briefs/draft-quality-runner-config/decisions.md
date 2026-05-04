# Decisions — Quality-Runner Structural Config

## Project Type

- **Chosen:** existing-feature/refactor
- **Rationale:** h-quality-runner already exists and ships; this is about improving its routing mechanism, not building from scratch.

## Investment Tier

- **Chosen:** Tool
- **Rationale:** Internal utility for agent pipeline; single author with known consumers (share/ clones). Standard M2, selective panel, full Brief. Not Shared because consumers are agent pipelines, not human teams.
- **Rejected:** Scratch (too lightweight for a durability concern), Shared (full panel overkill for agent tooling), Production (not external-facing)

## Scope Reduction (early challenge)

- **Chosen:** Accept scope reduction — this is primarily a prose fix, not a structural architecture task
- **Rationale:** Both simplifier and first-principles challengers identified that the irreducible problem is "agents need a cwd-resolution rule" (~40 words of prose), not a config schema or N-context routing table
- **Rejected:** Original 4-artifact scope (h-quality-runner + h-vitest-and-linting + copilot-instructions.md template + init.py scaffold) — over-engineered for the actual gap
- **Preserved option:** Utility script that agents invoke to discover test roots (reduces agent tool-call overhead)

## Disposition

- **Chosen:** Lightweight panel for inspiration → direct implementation without formal kanban task
- **Rationale:** Fix is small enough to execute directly; full Brief/decomposition pipeline would be heavier than the fix itself
