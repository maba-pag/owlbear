# README and Documentation UX Plan

> **Status:** Complete implementation plan
> **Decision date:** 2026-08-17
> **Scope:** Newcomer-facing documentation and package orientation

## Product identity decision

OwlBear has no numbered product release. The `main` branch is the rolling, supported
consumer branch generated from `dev` by the sync workflow.

Package `version` fields are internal packaging metadata and are not a product version,
release label, or maturity signal. They remain untouched by this documentation work.
There will be no version alignment, version bump, release tag, date-based version, or
changelog work as part of this plan. A documentation review date may be shown when useful,
but it is freshness metadata only.

Use these signals instead:

| Signal | Meaning |
| --- | --- |
| `main` | Current rolling consumer branch |
| Core / active | A maintained surface used by the primary workflow |
| Alpha | A capability that still needs real-world validation |
| Documentation reviewed | The date a documentation surface was last checked |

Browser and Knowledge remain explicitly alpha until field use provides stronger evidence.

## Goal

A newcomer evaluating or using OwlBear should be able to answer three questions without
reading the whole repository:

1. What is OwlBear and which branch represents the current consumer state?
2. What is the shortest path to a working project and a first successful verification?
3. Where should a developer go next for the specific package or workflow they need?

The documentation should provide one coherent path while preserving the necessary distinction
between the contributor/development front door and the consumer front door. The setup guide
remains the procedural authority; README files orient readers and route them there.

## Documentation boundaries

| Surface | Audience | Responsibility |
| --- | --- | --- |
| `README.md` | Evaluators and contributors | Explain the project, development checkout, and where to continue |
| `README-consumer.md` | People installing OwlBear into another project | Explain the rolling `main` product surface and first successful setup |
| `setup/setup-guide.md` | First-time installers | Own exact setup commands, expected outcomes, and troubleshooting |
| `setup/sharing-guide.md` | Teams sharing OwlBear and projects | Own multi-project and teammate workflows |
| `serve/*/README.md` | Developers integrating a package | Explain purpose, entry points, configuration, dependencies, and parent links |
| `share/README.md` | Contributors and pipeline agents | Explain the shared agent ecosystem categories and loading model |
| `SECURITY.md` | Users and security researchers | Own security support and private reporting information |
| `.owlbear/research/readme-redesign-plan-2026-08-17.md` | Maintainers | Preserve this plan and its execution order; it is not product documentation |

Do not merge `README.md` and `README-consumer.md`: the sync workflow renames the consumer file
to `README.md` on `main`, and the two branches serve different entry points.

## Sequential implementation units

Each unit has a bounded surface, a concrete proof target, and an explicit commit boundary.
The next unit starts only after the previous unit's focused validation passes.

| ID | Work unit | Maintained surfaces | Depends on | Completion proof |
| --- | --- | --- | --- | --- |
| R0 | Record policy and execution map | This plan | None | Plan is lint-clean and committed |
| R1 | Establish trust baseline | Root factual claims, `SECURITY.md`, license claim, sync-sensitive paths | R0 | Branch, license, path, and support-language claims match source/config |
| R2 | Rewrite development front door | `README.md` | R1 | Required root sections remain in order; links and commands route to canonical docs |
| R3 | Rewrite consumer front door | `README-consumer.md` | R1 | A new evaluator can find prerequisites, first success, status, and troubleshooting without package archaeology |
| R4 | Make first success procedural | `setup/setup-guide.md`, `setup/sharing-guide.md` | R2, R3 | Every setup step has an expected outcome and likely recovery path; no duplicated authority appears in root READMEs |
| R5a | Orient Delivery core | `serve/delivery/README.md` | R4 | Purpose, entry points, configuration/dependencies, current Change terminology, and parent link are accurate |
| R5b | Orient Delivery MCP | `serve/delivery-mcp/README.md` | R5a | MCP launch/configuration and user-visible boundary are accurate |
| R5c | Orient GitHub publication adapter | `serve/delivery-github/README.md` | R5b | Publication role and configuration are accurate |
| R5d | Orient Cockpit | `serve/cockpit/README.md` | R5c | Launch, frontend/backend split, configuration, and consumer `main` packaging are accurate |
| R5e | Orient Memory core | `serve/memory/README.md` | R5d | Memory purpose, configuration, and supported lifecycle are explicit |
| R5f | Orient Memory MCP | `serve/memory-mcp/README.md` | R5e | MCP tools, configuration, and user-controlled operations are accurately described |
| R5g | Orient Knowledge core | `serve/knowledge/README.md` | R5f | Alpha status, `ruamel.yaml`, optional integrations, and library boundary are accurate |
| R5h | Orient Knowledge MCP | `serve/knowledge-mcp/README.md` | R5g | Alpha status, source/search/enrichment boundary, and configuration are accurate |
| R5i | Orient Browser core | `serve/browser/README.md` | R5h | Alpha status, authenticated acquisition boundary, and actual output semantics are accurate |
| R5j | Orient Browser MCP | `serve/browser-mcp/README.md` | R5i | Alpha status, tools, Edge/CDP prerequisites, and snapshot semantics are accurate |
| R5k | Orient utility tools | `serve/tools/README.md` | R5j | Tool package purpose and the commands relevant to documentation maintenance are discoverable |
| R6 | Reconcile shared ecosystem orientation | `share/README.md` and package cross-links | R5k | Shared categories, loading model, and next links match the live tree without enumerating volatile files |
| R7 | Add only useful diagrams | `share/diagrams/` and references from active docs | R6 | Stale memory-layers material is archived or replaced; MCP topology and first-success flow reflect current code and are linked from a user journey |
| R8 | Run newcomer verification | All maintained documentation | R7 | A second developer can complete setup and identify the next workflow; broken links and factual gaps are recorded and repaired |

The package units are intentionally sequential even where some could be edited in parallel:
that keeps each package's vocabulary and cross-links reviewable, and makes a partial handoff
safe.

## Implementation status

| Unit | State | Evidence |
| --- | --- | --- |
| R0 | Complete | Plan committed in `2b9da3c` |
| R1 | Complete | Rolling-branch wording is corrected and the unsupported MIT claim was removed in `8bd78f4`; no root license is declared |
| R2 | Complete | Development front door committed in `2264598` |
| R3 | Complete | Consumer front door committed in `b4690c1` |
| R4 | Complete | Setup and sharing guides committed in `a52ac9d` and `e62b998` |
| R5a | Validated no-op | Delivery README already matched current Change authority |
| R5b | Complete | Delivery MCP terminology committed in `b4042c4` |
| R5c | Validated no-op | GitHub publication adapter README already matched its provider boundary |
| R5d | Validated no-op | Cockpit README already matched launch and `main` packaging |
| R5e | Complete | Memory configuration committed in `0b80cba` |
| R5f | Validated no-op | Memory MCP already documented human approval and lifecycle boundaries |
| R5g | Complete | Knowledge alpha status and dependency correction committed in `b7c68ac` |
| R5h | Complete | Knowledge MCP alpha status committed in `75444d3` |
| R5i | Complete | Browser alpha status committed in `dd668dd` |
| R5j | Complete | Browser MCP snapshot semantics committed in `1007cb3` |
| R5k | Validated no-op | Tools README already documented index maintenance and configuration |
| Index refresh | Complete | `.owlbear/doc-index.md` regenerated and committed in `72d9d84` |
| R6 | Complete | Shared ecosystem README validated against `.vscode/settings.json`, `WIRING.md`, and `h-agent-structure`; Markdownlint passed with no edit required |
| R7 | Complete | Archived stale memory-layer diagrams under `.owlbear/legacy/diagrams/`; corrected the five-server MCP topology, added an SVG preview, and linked the topology and first-success flow from active docs; `jq`, binding-reference, `xmllint`, link-target, Markdownlint, and whitespace checks passed |
| R8 | Complete | Second-developer dry run passed: 84 focused setup, seed, sync, and Cockpit tests; 34 local links resolved; workflow YAML and seeded JSON parsed; five stdio servers, four shared customization roots, and the `/ideate` -> `/design` -> `/orchestrate` prompts were verified |

## Editorial contract

- Describe `main` as the rolling supported consumer branch. Do not call OwlBear `0.1.0`,
  `0.2.0`, `26.08.17`, or any other product version.
- Keep package metadata out of newcomer-facing status claims. A package's metadata number is
  not evidence that it is stable, alpha, or validated.
- State maturity and validation separately from implementation existence. Browser and Knowledge
  are alpha, even though their code and MCP servers exist.
- Put exact commands and recovery instructions in the setup guides. Root READMEs link there.
- Prefer short orientation sections, tables, and next-step links over duplicated reference prose.
- Use current terminology: Design, Planning, Build, Change, publication, acceptance, and recovery.
  Do not revive retired Target Delivery or Kanban terminology where it no longer names the live
  surface.
- Verify claims against manifests, setup code, workflow configuration, and executable behavior
  before writing them.
- Every local link introduced or changed must resolve. Regenerate `.owlbear/doc-index.md` after
  live documentation changes when the index-maintenance workflow is available.
- Do not add diagrams as decoration. Each diagram must support a named reader question and be
  linked from an active document.

## Acceptance checklist

- [x] Root documentation says `main` is the rolling consumer branch and contains no product version.
- [x] No package version fields, tags, or release metadata were changed for this work.
- [x] The unsupported MIT claim was removed because no root license file or declaration exists.
- [x] `README.md` and `README-consumer.md` remain separate and route to the setup authority.
- [x] Both root audiences can reach a first successful setup and verification path.
- [x] All 11 package READMEs use the required package shape and link to the correct parent.
- [x] Browser and Knowledge are visibly marked alpha with honest validation limits.
- [x] Known factual issues are corrected, including paths, dependencies, output semantics, and
  current Delivery terminology.
- [x] Local links resolve and the generated documentation index is refreshed after the sweep.
- [x] Diagrams are retained only when they answer a documented user or maintainer question.
- [x] A second-developer dry run supplies the final usability evidence.

## Change log for this plan

- **2026-08-17:** Replaced numbered-release language with the rolling-`main` policy. Removed
  version alignment, release tags, date-based versions, and changelog work from scope. Added
  sequential package work units and explicit acceptance checks.
- **2026-08-17:** Completed R7 by archiving stale memory-layer diagrams, correcting the seeded
  five-server MCP topology, adding a rendered SVG preview, and linking diagrams from the newcomer
  journey and shared ecosystem orientation.
- **2026-08-17:** Completed R8 with a second-developer dry run, focused setup and Cockpit tests,
  local-link validation, seed/workflow parsing, and final Python, Delivery terminology, and
  rolling-main documentation repairs.
