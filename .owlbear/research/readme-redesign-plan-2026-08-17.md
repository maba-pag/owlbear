# README and Documentation UX Plan

> **Status:** Complete — structural redesign and review-driven corrections validated
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

## Review finding and resolution

R0-R8 improved factual trust and verified the existing paths. That is not the same as a complete
reader-first redesign. R9-R14 rebuilt the front doors around evaluator, consumer, contributor, and
package-integrator journeys. An independent Opus 5 review then found two executable-path blockers
and several routing and duplication defects. The review-driven corrections are included in the R14
closeout: the consumer path uses a real OwlBear clone URL and one sibling layout, developer-only
browser tests live in the Cockpit guide, package links work after the consumer README is renamed on
`main`, and the development README explains the contributor checkout boundary.

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
| R8 | Complete narrow verification | All maintained documentation | R7 | Focused link, lint, and executable checks establish a factual baseline; this verification does not by itself close the structural redesign |

The original R0-R8 sequence established factual trust and verified the existing paths. The
following units are the reopened structural redesign and must be completed in order:

| ID | Work unit | Maintained surfaces | Depends on | Completion proof |
| --- | --- | --- | --- | --- |
| R9 | Design reader routes | All newcomer and contributor entry docs | R8 | Each audience starts with a goal or role route, receives the minimum vocabulary before internal detail, and has one named next action |
| R10 | Rebuild development front door | `README.md` | R9 | An evaluator or contributor can choose a path, understand the product boundary, and reach setup, package orientation, or contribution guidance without architecture-first navigation |
| R11 | Rebuild consumer front door | `README-consumer.md` | R9 | A consumer can identify the rolling `main` product surface, complete the shortest setup route, verify it, and find troubleshooting without package archaeology |
| R12 | Reorder setup authority | `setup/setup-guide.md` | R10, R11 | The first setup path has four bounded actions with expected results; verification and first workflow precede optional reference detail; exact commands remain in this authority |
| R13 | Add package and ecosystem routing | `serve/README.md`, `serve/*/README.md`, `share/README.md`, `.github/sync-manifest.json` | R12 | Package and shared-ecosystem readers choose by job, every package guide links to the package map, and the map reaches the current package set on `main` |
| R14 | Verify redesigned journeys | All maintained documentation and `.owlbear/doc-index.md` | R10, R11, R12, R13 | Evaluator, consumer, contributor, and package-integrator dry runs each reach a useful next action; links, Markdownlint, index generation, and focused tests pass |

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
| R8 | Complete as narrow verification | Second-developer dry run passed: 84 focused setup, seed, sync, and Cockpit tests; 34 local links resolved; workflow YAML and seeded JSON parsed; five stdio servers, four shared customization roots, and the `/ideate` -> `/design` -> `/orchestrate` prompts were verified. This is retained as factual baseline evidence, not final structural acceptance |
| R9 | Complete | Reader routes are explicit in the development, consumer, setup, package-map, package, and shared-ecosystem entry surfaces |
| R10 | Complete | Development README rebuilt around role-first paths, plain-language definitions, current surfaces, and contribution/package next steps |
| R11 | Complete | Consumer README rebuilt around setup, verification, first workflow, current rolling-main policy, and troubleshooting |
| R12 | Complete | Setup authority reordered around prerequisites, four expected-result actions, verification, and first successful workflow; duplicate verification authority removed and existing-project versus clone-project wording clarified |
| R13 | Complete | Goal-based `serve/README.md` package map, synchronized consumer inclusion, shared-ecosystem routing, and package-guide navigation are in place |
| R14 | Complete | Review-driven evaluator, consumer, contributor, and package-integrator checks passed; source and virtual-`main` local-link walks found no broken links; `uv run doc-index`, Markdownlint, and `git diff --check` passed; 101 focused documentation, setup, sync, and Cockpit tests passed |

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
- [x] Historical narrow verification supplies factual baseline evidence.
- [x] Each front door routes by reader role or goal before architecture and internal vocabulary.
- [x] The consumer front door sends first-time users to the shortest setup and verification path before optional detail.
- [x] The setup authority presents one first-success path with expected results and no duplicate verification authority.
- [x] The package map lets a reader choose by job, and every package guide links back to it with concise use context.
- [x] Evaluator, consumer, contributor, and package-integrator dry runs each reach a useful next action.
- [x] The reopened structural redesign is committed in scoped units without changing versions, tags, releases, or unrelated worktree changes.

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
- **2026-08-17:** Reopened the plan for structural redesign after review found that R0-R8 improved
  factual trust but did not sufficiently change the reader journey. Added R9-R14 for reader routes,
  role-first front doors, setup ordering, package/ecosystem routing, and four-role verification.
- **2026-08-17:** Rebased generated documentation-index links from their source documents so the
  index remains navigable from `.owlbear/`, including same-file anchors, and added a regression test
  for nested package links.
- **2026-08-17:** Committed the structural redesign and index repair in scoped commit `7ca1aa2`;
  unrelated workflow, research, and lint-policy changes remained outside the commit.
- **2026-08-17:** An independent Opus 5 review found that the consumer clone example was not
  executable, browser-backed tests were misplaced in consumer setup, package links were not safe
  after the generated `main` rename, and several front doors duplicated procedural authority.
  Corrected those paths, added the contributor checkout route, normalized sharing placeholders, and
  revalidated source and virtual-`main` links plus the focused documentation and setup test suite.
