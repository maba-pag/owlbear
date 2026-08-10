# Context — Quality-Runner Structural Config

## Project Type

existing-feature/refactor

## Problem

The quality-runner's toolchain routing is implicitly coupled to the OwlBear-dev project layout. When `share/` is consumed by a project with a different structure, agents have no reliable way to determine which test files need which toolchain and where to execute them. The skill's current prose assumes familiarity with the host project, which breaks the portability promise of `share/`.

## Key Tension

Agent inference (agents figure out toolchain from context clues like file extensions and package.json proximity) vs explicit project-level declaration (consumers state their layout once). User preference leans toward inference-from-context, treating declarations as a possible fallback rather than primary mechanism.

## Evidence of Breakage

**No post-implementation routing failures.** The #1276 incident (quality-runner picking pytest for .tsx files) was the *catalyst* for creating dual-toolchain routing, not a failure of it. The current routing works correctly for OwlBear-dev.

**The gap is consumer portability.** After #1287 genericized paths to "your frontend package root," external consumers who clone `share/` have:
- No mechanism to declare their frontend root
- h-quality-runner says "routing authority is copilot-instructions.md" but that file has no routing section template
- Agents on consumer projects would need to infer or discover the frontend root themselves

## Affected Users

- External consumers who clone `share/` into projects with different directory layouts
- Pipeline agents (quality-runner, reviewer) running on those consumer projects

## Scope (confirmed by user)

Broad: h-quality-runner + h-vitest-and-linting + copilot-instructions.md template + setup/init.py scaffold

## Status

M2 complete. Early challengers reduced scope to prose fix + possible utility script. Proceeding with critic + panel inspiration, then direct implementation.

## Outcomes (revised after early challenge)

**Core fix:** The quality-runner skill needs a general cwd-resolution rule instead of path-prefix examples. Agents need to know "walk up to nearest package manifest" or call a utility that does this for them.

**Emerging idea:** A lightweight Python utility script that agents invoke to discover test roots — avoids multi-step filesystem traversal in agent tool calls. Returns path + toolchain + relevant config.

**Scope (reduced):**
- IN: h-quality-runner prose (cwd-resolution rule), possibly a discovery utility script
- MAYBE: copilot-instructions.md template section
- OUT: N-context generalization, multi-root design, h-vitest-and-linting changes, init.py scaffold logic, formal kanban task
