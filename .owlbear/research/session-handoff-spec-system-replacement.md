# Session Handoff: BiRRe Alert RCA and OwlBear Specification-System Replacement

> **Date:** 2026-07-12
> **Repositories:** `/Users/markus/Projects/birre`, `/Users/markus/Projects/owlbear-dev`
> **Purpose:** Restart this long chat without losing the technical history, decisions, implementations, reversals, and current open question.

## 1. Recommended Restart Prompt

Use this in the next chat:

```text
Continue from /Users/markus/Projects/owlbear-dev/.owlbear/research/session-handoff-spec-system-replacement.md.

Be direct and action-oriented. Do not repeat the history back to me. First inspect current files and git state because some files may have changed. The immediate decision is whether GitHub Spec Kit is fundamentally the wrong front end for rough-idea discovery because /speckit-specify drafts immediately without dialogue, or whether we should replace only its specify/clarify interaction. Reassess GSD's discuss/spec workflow and OpenSpec's explore flow specifically for interactive intent extraction before changing more code.

Also review the current generated BiRRe spec. It still appears to over-assume local historical-boundary calculations and rating-history fallback for /v1/companies/trends. The requested feature is structured extraction from that endpoint; do not invent comparison semantics before validating the real contract.
```

## 2. User Working Style and Explicit Preferences

- Be brutally direct. The user is German and does not want politeness or sugar coating.
- Do not spam the chat with internal checklists, long explanations, or repeated plan text.
- User-facing updates should say what is happening, what is blocked, and what input is needed.
- Put detailed analysis into project artifacts rather than large chat walls.
- Do not preserve OwlBear machinery because of sunk cost or perceived differentiation.
- Installing/configuring an existing comparable solution is strongly preferred over rebuilding it.
- The target is the best intended result with minimal human effort, model effort, and maintenance.
- Tests are evidence, not product specification.
- The user dislikes process metrics and process theater. Do not propose measuring token counts, human turns, or vague pilot scores.
- A valid evaluation is one real defined deliverable: work through it, inspect whether the result is usable, fix bounded integration issues, and decide.
- For a rough-idea test, do not pre-specify commands, APIs, architecture, task boundaries, or proof strategy.
- When interactive tools ask questions, the user may paste the whole chat back. The assistant should research and prepare answers. The user should only decide genuine product preferences.
- Do not spend effort on Markdown lint/style unless it blocks content or execution; user said they will handle lint later with an optimized model.

## 3. Original Request and Root-Cause Analysis

The initial task was to understand why a completed BiRRe implementation missed the product goal.

### Original implementation

The alert workflow implementation came from:

- Original Brief: `birre/.owlbear/briefs/draft-birre-alert-workflows/brief.md`
- Archived Kanban tasks: #1 through #13
- Main implementation commits supplied by user:
  - `c2751302ec3d8abbbe9854389b64e34811d46a00` (unrelated formatting commit)
  - `967e96a15c9cb580a2dbef6e964a5c15359a6112`
  - `b311bc499653a052f75dbb427a9ed4363ff61f64`
  - `ae4d8d07c54a295fc4b53f9dbabe2aadc78c1146`
  - `3f0b252622195b19986e75671c5007b682acf454`
  - `56ba6a5d701b9d107a2993ab7971dfb11a97db6b`
  - `ced4b4815ad99d18d1879bed8f269a2bb64f8ec5`
- Relevant test commits omitted from the initial list included `7130437`, `f2914bd`, and `cfd4fb0`.

### Corrective Brief chronology

The later corrective Brief is:

- `birre/.owlbear/briefs/draft-birre-real-alert-validation/brief.md`

It was approved after the implementation and is therefore a correction specification, not the source of tasks #1-#13.

Decision D17 explicitly said not to create tasks or dispatch the shaper.

### Proven implementation failures

A bounded real CLI invocation was run:

```text
uv run birre security-analyst-alerts --alert-date-gte 2026-07-11 --page-size 1 --max-pages 1 --max-companies 1
```

It failed with:

```text
FastMCP tool 'getAlerts' execution failed: Unknown tool: 'getAlerts'
```

Two separate integration defects exist:

1. `src/birre/domain/security_analyst/alerts.py` hardcoded `V2_ALERTS_ENDPOINT = "getAlerts"`.
2. The generated OpenAPI operation is `AlertsList`.
3. `src/birre/application/server.py` applied a v2 allowlist containing only company-request tools to both `risk_manager` and `security_analyst`, hiding `AlertsList`.
4. Changing only the operation name would still fail due to visibility.

Semantic defects:

- Production alert details use `start_rating`, `end_rating`, `start_grade`, and `end_grade`.
- Implementation expected `rating_before`, `rating_after`, `category_before`, and `category_after`.
- Workflow selected `alert_type` before the human `trigger`, causing transport enums such as `RISK_CATEGORY` to override the category needed for scoring.
- Company history could mask missing alert-derived movement.
- Candidate aggregation selected `max(priority_score)` even though lower mapped priority numbers are more urgent.
- Consolidation tests observed null before/after values and still passed.

Focused fixture tests passed despite production failure. This established that mocks certified the implementation's own assumptions, not the assembled product.

### Process causes

- Original Brief selected API/CLI-first but did not define command hierarchy, command name, or interface fit.
- Shaper converted unresolved external assumptions into mock-verifiable AC.
- No task owned the cross-boundary invariant: generated `AlertsList` is visible and callable through the assembled `security_analyst` context.
- Work was fragmented into twelve linear tasks.
- Task #4 explicitly certified the wrong `getAlerts` name with a mocked caller.
- Task #13 made live BitSight proof a non-goal and injected the CLI workflow runner.
- Verifiers optimized for literal AC, not normal product assembly.
- Archive commit `5046925` preceded final core code commit `ced4b48` by 13 seconds. This proves closure was not commit-pinned, though timing alone does not prove exactly which state each test used.

### CLI conclusion

`security-analyst-alerts` was a root-level role-named bolt-on. The recommended replacement in the corrective Brief became:

```text
uv run birre alerts prepare
```

The role `security_analyst` should remain an internal runtime context, not appear in command names.

## 4. Corrective BiRRe Brief Changes

The corrective Brief was expanded into a repair PRD:

- `birre/.owlbear/briefs/draft-birre-real-alert-validation/brief.md`
- `birre/.owlbear/briefs/draft-birre-real-alert-validation/decisions.md`

Material additions:

- Supersedes old internal contracts.
- Defines `alerts prepare` command hierarchy.
- Requires removal of `security-analyst-alerts`, `getAlerts`, invented movement fields, and stale tests.
- Defines user workflow, stdout/stderr/error behavior, help behavior.
- Defines five ownership boundaries: production collection, typed normalization, projection/priority, CLI integration, aggregate proof.
- Makes generated operation inventory and assembled tool visibility canonical authorities.
- Requires discriminated typed models, explicit completeness states, and source-labelled company-history fallback.
- Defines a proof ladder: unit, generated-server contract, real CLI integration with only lower transport replaced, bounded production comparison.
- Requires commit-SHA-linked aggregate proof.

`decisions.md` received D18 documenting the replacement command, supersession, proof rules, and continued no-task/no-shaper pause.

Current BiRRe worktree at handoff:

```text
 M .gitignore
 M .owlbear/briefs/draft-birre-real-alert-validation/brief.md
 M .owlbear/briefs/draft-birre-real-alert-validation/decisions.md
?? specs/
```

Latest committed BiRRe HEAD shown during handoff:

```text
820ebb0 Remove obsolete documentation and stance files related to alert workflows
```

Do not revert user changes or the Brief edits.

## 5. First OwlBear Process Changes Implemented

All OwlBear ecosystem changes were correctly made in `../owlbear-dev`, not consumed `../owlbear`.

The following temporary safeguards were implemented before the external-framework decision changed:

- Mediation ends at approved Brief and explicit `/shape` handoff; no automatic task creation or shaper dispatch.
- Mediator Kanban/shaper capabilities removed.
- `/shape` accepts approved Brief paths.
- Four-item Brief readiness gate:
  - product outcome/invocation;
  - existing-system fit/authority;
  - normal-path proof;
  - completion/change contract.
- External/generated contract authority guard with observed/documented/assumed states.
- Product Invariant Map: invariant -> owning task -> normal boundary -> proof/allowed replacement.
- Boundary-valid proof rule: mocks may replace only lower layers.
- Builder rejects canonical-source contradictions.
- Verifier checks named authorities and claimed normal boundary.
- Collector requires SHA-linked aggregate proof.
- Shared/Production post-shaping expectation fidelity moved into interactive shaping.
- Shaper challenger checks readiness, authority, invariant ownership, proof, fragmentation, and fidelity.

Files changed include:

- `share/skills/w-task-decomposition/SKILL.md`
- `share/skills/h-ac-quality/SKILL.md`
- `share/skills/r-pipeline-protocol/SKILL.md`
- `share/skills/w-ideation-mediation/SKILL.md`
- `share/skills/h-ideation/SKILL.md`
- `share/agents/ideation-mediator.agent.md`
- `share/agents/shaper.agent.md`
- `share/agents/shaper-challenger.agent.md`
- `share/agents/builder.agent.md`
- `share/agents/verifier.agent.md`
- `share/agents/collector.agent.md`
- `share/prompts/ideation-mediate.prompt.md`
- `share/prompts/shape.prompt.md`
- `share/WIRING.md`
- `tests/test_ideation_overhaul_static.py`

These changes passed focused semantic tests and validators. They should now be treated as temporary containment, not necessarily the final architecture.

## 6. External SDD Framework Research

Five repositories were cloned, inspected at pinned commits, analyzed, and then deleted from scratch:

- OpenSpec: `0a99f410457271aa773d8b106f03f637f7c6b3c0`
- GSD Core: `30feeaa8be86b71616dd7d47bbd157d4ee0d2736`
- GitHub Spec Kit: `1be42992e64b08ff0dce3d7a914eaabf04284ffb`
- Wallfacer: `fa6616e82d20901fc4e666a333da006113732bad`
- Comet: `a2b804d575bc99574b245fd52b45fa42016a130c`

All five are MIT licensed.

Research artifact:

- `owlbear-dev/.owlbear/research/sdd-framework-comparison.md`
- Sources indexed in `owlbear-dev/.owlbear/sources/overview.md`

Key findings:

### OpenSpec

- Strongest at delta-first brownfield requirements and declarative artifact graph.
- Minimal default spec is too thin for deep product discovery.
- `/opsx:explore` may be a stronger rough-idea dialogue candidate than Spec Kit's `/specify`.
- Partial adoption adds Node and authority synchronization concerns.

### GSD Core

- Strongest complete spec template: Current/Target/Acceptance, explicit boundaries, negative requirements, edge coverage, ambiguity report, interview log, stable requirement IDs, validation matrix.
- Has an explicit discuss/spec lifecycle and fresh-context agents.
- Heavy overall framework, but its interactive discuss/spec front end now deserves focused reassessment.

### Spec Kit

- Strong templates and artifact separation: constitution, specify, clarify, plan, tasks, analyze, implement, converge.
- Strong user stories, measurable outcomes, bounded clarify taxonomy, and cross-artifact analysis.
- Presets/extensions and native Copilot skill generation work.
- Default task template is file-oriented and too granular for OwlBear.
- Critical observed weakness: `/speckit-specify` drafts immediately and does not conduct serious dialogue. `/speckit-clarify` comes later.

### Wallfacer

- Strong lifecycle, stale/drift semantics, reality-grounded design records, spec/task graph.
- Full engineering control plane; too much overlap with OwlBear execution.

### Comet

- Strong typed phase guards, evidence records, checkpoints, recovery, and mandatory decision points.
- Combines OpenSpec + Superpowers + own runtime; too much coupling.

## 7. Decision Reversals: Important Context

The recommendation changed several times. Do not blindly follow the earlier sections of the research document without reading the later reassessment.

1. Initial conclusion: keep OwlBear and borrow patterns.
2. User correctly challenged preservation bias and custom-framework cost.
3. Revised conclusion: replace OwlBear ideation/shaping with customized Spec Kit and keep Kanban execution.
4. A pinned Spec Kit integration, preset, and deterministic importer were implemented.
5. First real `/speckit-specify` use showed immediate drafting without dialogue and substantial assumption-making.
6. Current conclusion: Spec Kit is not proven as the right rough-idea discovery front end. Reassess specifically:
   - GSD discuss/spec interaction;
   - OpenSpec explore interaction;
   - or a very small custom interactive specification agent using external artifact/planning tooling.

Current best judgment at handoff:

- Do not continue assuming Spec Kit should replace ideation.
- Spec Kit's artifact, plan, analysis, preset, and importer work may still be useful.
- The open issue is the initial rough-idea-to-understood-intent dialogue.
- Do not rebuild the old eleven-agent panel topology.

## 8. Spec Kit Integration Implemented in OwlBear-dev

Pinned version:

```text
GitHub Spec Kit v0.12.0
uv tool run --from git+https://github.com/github/spec-kit.git@v0.12.0 specify
```

Implemented files:

- `share/spec-kit/owlbear/preset.yml`
- `share/spec-kit/owlbear/templates/spec-template.md`
- `share/spec-kit/owlbear/templates/plan-template.md`
- `share/spec-kit/owlbear/templates/tasks-template.md`
- `share/spec-kit/owlbear/commands/speckit.specify.md`
- `share/spec-kit/owlbear/commands/speckit.tasks.md`
- `setup/spec-kit.py`
- `tests/test_spec_kit_setup.py`
- `serve/kanban/src/owlbear_kanban/spec_import.py`
- `serve/kanban/tests/test_spec_import.py`
- `serve/kanban/pyproject.toml` exposes `owlbear-spec-import`
- `setup/setup-guide.md` documents setup/use.

### Preset intent

Custom spec fields include:

- Problem and intended outcome.
- User journeys and independent proof.
- Current/Target/Acceptance requirement format.
- Technically done but wrong.
- Boundaries and preserved remainder.
- Assumptions/open decisions.
- Success criteria and accepted trade-offs.

Custom plan fields include:

- Brownfield current state.
- Existing conventions and owning surface.
- Contract authorities with evidence state/confidence.
- Architecture decisions and rejected alternatives.
- Interfaces/data contracts.
- Migration/removal.
- Product invariant -> assembled boundary -> proof -> allowed lower replacement.

Custom task format includes a strict YAML `owlbear` manifest in `tasks.md` frontmatter.

### Deterministic importer

Command:

```text
uv run --project ../owlbear-dev owlbear-spec-import specs/<feature>/tasks.md
uv run --project ../owlbear-dev owlbear-spec-import specs/<feature>/tasks.md --apply
```

Dry-run is default; apply is explicit.

Importer validates before writes:

- strict typed manifest;
- feature/spec/plan paths;
- requirement coverage against `REQ-*` in spec;
- unique task keys;
- dependency existence and acyclic graph;
- exactly one owner per invariant;
- supported priorities/proof bundles;
- no unresolved `[placeholder]` strings;
- duplicate feature import rejection.

Apply behavior:

- Creates leaves in topological order at `build`.
- Creates aggregate at `collect` depending on all leaves.
- Adds parent links from leaves to aggregate.
- Uses stable `spec-kit:<feature>` tags for idempotency.
- Attempts rollback of files created by the current invocation on failure.

### Tests and validation already run

- Importer unit tests: 7 passed after semantic validation expansion.
- Setup tests: 4 passed after idempotency/local-runtime changes.
- Larger focused suite: 163 passed.
- Ruff checks and format checks passed on new Python files.
- Agent validator: all 23 agent files conformed.
- Skill validator passed.
- Real disposable-project setup worked.
- Copilot skills generated.
- OwlBear preset resolved for spec, plan, tasks.
- Importer real smoke dry-run/apply/duplicate rejection passed.

## 9. Spec Kit Consumer Footprint Decision

Initial setup added 34 files / about 190 KB to BiRRe:

- `.specify/` runtime, templates, scripts, manifests, preset copies.
- `.github/skills/speckit-*` generated skills.
- Duplicate `.github/agents/speckit.*` and `.github/prompts/speckit.*` from preset command registration.

This was judged unacceptable as committed BiRRe source.

Final setup behavior:

- Generated Spec Kit runtime remains project-local because upstream Spec Kit assumes project-local `.specify/` scripts/templates/state.
- Generated runtime is ignored in consumer Git.
- Only actual `specs/<feature>/...` should be committed.
- Duplicate generated agent/prompt files are removed automatically.
- Setup is idempotent: existing OwlBear preset is removed, then reinstalled.

Managed `.gitignore` block added to BiRRe:

```text
# --- OwlBear Spec Kit generated runtime ---
.specify/
.github/skills/speckit-*/
.github/agents/speckit.*.agent.md
.github/prompts/speckit.*.prompt.md
```

BiRRe setup command:

```text
uv run --project ../owlbear-dev python ../owlbear-dev/setup/spec-kit.py
```

After the final rerun:

- `.github/skills/speckit-specify/SKILL.md` exists and is usable.
- `.specify/integration.json` exists.
- Duplicate agent/prompt files no longer exist.
- Generated runtime disappeared from Git status.
- `.gitignore` is intentionally modified.

## 10. BiRRe Uses OwlBear-dev Customizations

BiRRe `.vscode/settings.json` was changed so shared customizations load from `../owlbear-dev`:

- agents
- prompts
- instructions
- skills

MCP config was deliberately not changed; `.vscode/mcp.json` still points at consumed OwlBear where applicable.

Current settings observed at handoff:

- customization locations point to `../owlbear-dev/share/...`.
- `github.copilot.chat.additionalReadAccessPaths` currently contains both:
  - `/Users/markus/Projects/owlbear`
  - `/Users/markus/Projects/owlbear-dev`

This dual read path may have been edited by the user or setup. Do not remove without checking intent.

## 11. First Real Spec Kit Rough-Idea Test

User input:

```text
I need BiRRe to provide structured data for two related needs: reliable definitions of the malware or infection categories used by BitSight, and company rating changes over the last 7, 30, and 90 days. I found an undocumented but stable /v1/companies/trends endpoint used by the official BitSight web UI. I believe the documented API also has an endpoint for infection definitions, but I have not investigated the exact contract. I have not decided how BiRRe should expose or model this data.
```

Spec Kit behavior:

- It immediately searched repository/docs.
- Correctly distinguished `/companies/trends` from `/companies/trending`; did not hallucinate toward the documented unrelated endpoint.
- Found documented infection APIs.
- Drafted a full spec immediately without asking intent questions.
- User was unhappy with lack of dialogue and assumption-making.
- `/speckit-clarify` existing as a later command does not solve early intent extraction cleanly.
- Many other installed Spec Kit skills appear irrelevant to the desired focused specification experience.

Generated feature:

- `birre/specs/001-infection-definitions-rating-changes/spec.md`
- local ignored pointer: `birre/.specify/feature.json`

The first draft was corrected after review:

- Two independent capabilities, not combined investigation response.
- Global infection catalog/detail.
- Company-scoped rating-change capability in existing company-rating domain.
- `GET /infections` and `GET /knowledge-base/infections/{id}` explicitly named.
- `/defaults/infections` treated as an unsupported discrepancy.
- `/v1/companies/trends` made mandatory scope.
- User Story 3 removed.

## 12. Important Current Spec Defect

The revised generated spec still appears to over-specify calculations and fallback behavior that were not requested and cannot be selected before the real `/v1/companies/trends` contract is inspected.

Current problematic concepts in `spec.md` include:

- historical observations;
- exact 7/30/90-day boundary selection;
- comparison rule;
- locally computed rating differences;
- rating-history corroboration/fallback;
- unavailable period behavior based on missing history.

The user's rough request was for structured extraction from `/v1/companies/trends`, not local calculation.

Recommended response to the current remaining question:

```text
Do not define a historical-observation rule. This feature should first preserve and type the 7-, 30-, and 90-day values supplied by /v1/companies/trends. If the endpoint omits a period or returns an unusable value, mark that field unavailable. Do not derive or substitute a value from company rating history in this delivery.
```

Likely required spec corrections:

- Remove or rewrite User Story 2 scenarios 2/3 if they assume selecting local history boundaries.
- Rewrite FR-006/FR-007 around preserving typed source fields, not selecting historical observations.
- Remove FR-010 fallback unless explicitly requested later.
- Remove `Rating observation` and `Comparison rule` entities unless proven by actual response.
- Rewrite SC-002/SC-003 around source-field preservation and malformed/missing endpoint fields.
- Open Decision 1 should become: validate actual endpoint schema first; do not choose a boundary rule.

## 13. Current Strategic Open Question

The immediate strategic question is:

> Is Spec Kit fundamentally the wrong rough-idea discovery front end, or should only `/speckit-specify` and `/speckit-clarify` be replaced by a better interactive specification agent while retaining Spec Kit plan/tasks/analyze artifacts and the deterministic importer?

Evidence against Spec Kit front end:

- Drafted immediately after one rough paragraph.
- Asked no questions before generating many requirements.
- Assumed purpose and data semantics not established by the user.
- Clarification is temporally separated and feels late.
- User would need a separate non-agent conversation before specify, defeating replacement goal.
- Most shipped Spec Kit skills are unnecessary for the intended workflow.

Do not rubberstamp Spec Kit because integration code exists.

Next research should be narrowly focused on interactive intent extraction:

1. Re-clone/read GSD only as needed.
2. Examine exact `discuss-phase`, phase spec interview, question cadence, artifacts, and whether it can be used without GSD execution.
3. Examine OpenSpec `/opsx:explore` and proposal transition.
4. Compare both with one small custom interactive agent that writes a Spec Kit-compatible `spec.md` or another selected artifact.
5. Optimize for:
   - starts from one rough thought;
   - researches code before asking factual questions;
   - asks material questions one at a time;
   - does not draft until intent is sufficiently understood;
   - separates product intent from architecture/implementation planning;
   - minimal mandatory agents/artifacts;
   - no duplicated source of truth.

Do not evaluate whole frameworks again. Evaluate only the missing front-end behavior.

## 14. Current OwlBear-dev Worktree

At handoff, `git status --short` showed:

```text
 M .owlbear/sources/overview.md
 M serve/kanban/pyproject.toml
 M setup/setup-guide.md
 M share/WIRING.md
 M share/agents/builder.agent.md
 M share/agents/collector.agent.md
 M share/agents/ideation-mediator.agent.md
 M share/agents/shaper-challenger.agent.md
 M share/agents/shaper.agent.md
 M share/agents/verifier.agent.md
 M share/prompts/ideation-mediate.prompt.md
 M share/prompts/shape.prompt.md
 M share/skills/h-ac-quality/SKILL.md
 M share/skills/h-ideation/SKILL.md
 M share/skills/r-pipeline-protocol/SKILL.md
 M share/skills/w-ideation-mediation/SKILL.md
 M share/skills/w-task-decomposition/SKILL.md
 M tests/test_ideation_overhaul_static.py
?? .owlbear/research/sdd-framework-comparison.md
?? serve/kanban/src/owlbear_kanban/spec_import.py
?? serve/kanban/tests/test_spec_import.py
?? setup/spec-kit.py
?? share/spec-kit/
?? tests/test_spec_kit_setup.py
```

This handoff file itself is additionally untracked after creation.

No commits were created.

## 15. Known Baseline Test Debt

A focused suite including `tests/test_cross_references.py` produced four failures because current `HEAD` already lacks expected `agent-ecosystem.instructions` rows in `share/WIRING.md`.

Confirmed baseline with `git show HEAD:share/WIRING.md`.

Excluding that unrelated file, focused suites passed.

Do not attribute those four failures to the Spec Kit work.

## 16. Suggested Next Actions

1. Read this handoff and current files; do not repeat the history to the user.
2. Correct the current BiRRe generated spec's unsupported comparison/fallback semantics or prepare the exact response for the current Spec Kit chat.
3. Perform a narrow source-level comparison of:
   - GSD discuss/spec front end;
   - OpenSpec explore/propose front end;
   - tiny custom interactive agent writing a standard spec artifact.
4. Make a direct recommendation with:
   - what to keep from current Spec Kit integration;
   - what to delete;
   - exact next implementation step.
5. Keep chat concise. Detailed findings go into `owlbear-dev/.owlbear/research/`.

## 17. Things Not To Do

- Do not feed existing polished Briefs into a rough-idea evaluation.
- Do not claim the endpoint contract needs historical-boundary selection before seeing the real response.
- Do not preserve old OwlBear panel machinery by default.
- Do not recreate eleven-agent choreography inside Spec Kit.
- Do not add another permanent planning layer on top of Spec Kit.
- Do not evaluate success by token counts, human-turn counts, or arbitrary scores.
- Do not commit generated `.specify/` or `.github/skills/speckit-*` runtime files in consumer repos.
- Do not modify BiRRe `.vscode/mcp.json` unless a concrete MCP need appears.
- Do not revert unrelated user changes.
