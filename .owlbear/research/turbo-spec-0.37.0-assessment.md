# Turbo Spec 0.37.0 Assessment

> **Owning request:** User-requested repository assessment; no matching Kanban task exists
> **Date:** 2026-07-23
> **Question:** Which Turbo Spec capabilities are valuable to OwlBear, where is it stronger, and should it complement or replace OwlBear?

## 1. Context and Question

Turbo Spec 0.37.0 was supplied as `.owlbear/scratch/turbo-spec-0.37.0.zip` and extracted to
`.owlbear/scratch/turbo-spec-0.37.0/`. This review did not execute its code, install dependencies,
or contact external services. It inspected implementation, tests, workflows, actions, schemas, and
documentation. The archive contains 240 Python source files, 290 test modules, 13 built-in workflow
files, 50 `SKILL.md` files, and 17 evaluator packages.

The key product distinction is:

- **Turbo Spec** is a GitHub-native, issue-to-PR workflow runtime. A typed YAML blueprint selects
  agents, models, tools, stage dependencies, output schemas, quality gates, retry routes, reporters,
  triggers, sandbox policy, and network access.
- **OwlBear** is a local-first development operating system. A durable task board coordinates
  human shaping and Copilot agents across build, independent verification, collection, knowledge,
  memory, browser acquisition, and workspace governance.

These overlap in agentic software delivery, but they optimize different control planes. Turbo Spec
controls one autonomous run; OwlBear governs a continuing portfolio of work and human decisions.

## 2. Sources Studied

| Source | Relevant fact | Evidence limit |
|---|---|---|
| Turbo `README.md`, `pyproject.toml`, `config.yml` | Product contract, dependencies, CLI, defaults | Product claims were accepted only when source/tests supported them |
| Turbo `src/workflow_skeleton/` | Blueprint, runtime, agents, evaluators, MCP, relay, tracing | Static inspection; no live LLM, GitHub, container, or MCP run |
| Turbo `tests/`, tool-local tests | Breadth and intended behavior | Passing status was not independently established |
| Turbo `.github/`, `agent-sandbox/`, `customer_bootstrap/` | CI distribution, triggers, token and container boundaries | Hosted platform behavior was not exercised |
| Turbo `skills/`, `_builtin/`, `examples/`, `onboarding/`, `knowledge-mcp/` | Resource catalog and ancillary integrations | Some integrations depend on unavailable services or credentials |
| OwlBear `share/`, `serve/`, `openspec/`, tests, workspace instructions | Current pipeline, agents, board, MCP, Cockpit, governance | Current source is authoritative; no full regression run was needed |

**Licensing constraint:** the archive contains no `LICENSE` or equivalent grant. Concepts may be
reimplemented, but no Turbo Spec code, prompts, skills, schemas, or workflow content should be copied
until the upstream license and provenance are confirmed.

**Documentation drift:** parts of `docs/architecture.md` still describe session resume as future work.
Current source is stronger evidence: `MainOrchestrator.run()` loads saved state and restores context,
blueprint and worktree state; `WorkflowRunner` skips completed stages; and
`tests/integration/test_session_resume.py` asserts crash-then-resume behavior. Similar polished claims
elsewhere should be checked against current call sites and tests before adoption.

## 3. Turbo Spec Functional Analysis

### 3.1 Implemented Core

| Capability | How it works | Value to OwlBear |
|---|---|---|
| Typed workflow blueprints | Pydantic models validate stages, dependencies, conditions, agents, gates, MCP refs, output contracts, hooks, triggers, and network policy before execution | High as a run contract; low as a replacement for task storage |
| DAG planning | Kahn topological sort creates dependency-correct waves and rejects cycles/dangling dependencies | Useful validation, but the runner flattens waves and executes stages sequentially; it does not realize parallel stage execution |
| Deterministic continuation | `WorkflowRunner` owns execution pointer, per-gate retry budgets, loop-back targets, partial-agent reruns, conditions, terminal reporting, and escalation | Stronger than OwlBear's prompt-defined retry semantics inside one run |
| Typed agent output | Schema and artifact type are co-required; expected JSON schema is injected into the prompt and validated before handoff | Excellent fit for machine-verifiable builder/verifier handoffs |
| Pluggable gates | Deterministic build/test/script/outcome/human gates coexist with LLM evaluators; gates have thresholds, hooks, retry and routing policy | Stronger executable enforcement than OwlBear's largely agent-owned proof protocol |
| Resume snapshots | Session state checkpoints completed stages, context, attempts, metrics, outputs, blueprint snapshot, and worktree state; resume skips completed stages and supports feedback routing | High value for interrupted OwlBear orchestration and approval pauses |
| MCP lifecycle | MCP config is prevalidated; clients enter once through an `ExitStack`, remain open over retries, and expose namespaced tools per agent | A robust pattern if OwlBear gains a standalone runtime |
| Resource resolution | Built-in, project, user, and explicit-path resources resolve through one owner; blueprint refs are preflighted before model work | Useful for detecting broken OwlBear agent/skill wiring earlier |
| Model abstraction | Copilot, Anthropic, Bedrock, and BYOK selection are hidden behind provider construction and per-agent overrides | Valuable only if OwlBear moves beyond VS Code-managed model invocation |
| Structured tracing | Pipeline, wave, stage, agent, tool, gate, retry, routing, token, and duration events feed CLI, PR, JSON, and OTLP reporters with redaction | Material observability improvement over task notes and activity logs alone |
| Traceability tooling | REQ-ID validation, test-trace checking, and matrix generation connect requirements to evidence | Potentially valuable for high-rigor work, but too heavy as OwlBear's default |

### 3.2 Security and Operations

| Capability | Assessment |
|---|---|
| Agent credential boundary | Strong concept: scrub GitHub/model/cloud credentials, neutralize git/`gh` credential stores, and mediate privileged calls outside the worker |
| Container sandbox | Substantial implementation: non-root worker, guarded worktree mount, egress proxy/firewall, allowlist construction, fresh sandbox for executable gates, and live integration-test definitions |
| Model relay | Implemented, wired, and tested. A run-secret-gated relay permits only canonical `POST /chat/completions`, fixes the upstream host, strips client auth identity, injects the real token host-side, and supports token refresh |
| GitHub distribution | Mature reusable workflows/composite actions, GitHub App token minting, thin consumer shims, issue/comment routing, image release gates, Dependabot, and release automation |
| Failure watcher | CI failure artifacts and log excerpts can be classified into bounded auto-resume versus human escalation |
| Telemetry | OpenTelemetry/New Relic metrics and dashboards cover tokens, duration, stages, agents, and estimated cost; useful but vendor-specific and opt-in |
| Main residual risks | Broad GitHub workflow permissions, third-party action/image supply chain, arbitrary evaluator and hook code, secret/operator complexity, DNS egress, CI/LLM cost, and real-service paths that mocks cannot prove |

### 3.3 Agents, Skills, Workflows, and Integrations

Turbo Spec's resources are runtime-loadable rather than merely advisory. The catalog includes feature,
bug-fix, SDD/OpenSpec, AI-readiness, evaluator demonstration, Figma, and Graph2Code workflows; planning,
implementation, TDD, review/fix, test, visual-regression, diagnosis, outcome, OpenSpec, and Figma skills;
and GitHub, file, shell, Jira, Figma, Porsche Design System, Copilot review, AOP, and MCP tools.

Notable ideas:

- **Per-agent gates** let an implementation agent and reviewer form a bounded inner correction loop.
- **Sighted retries** attach visual gate evidence to the correction turn.
- **Blueprint inheritance** permits a consumer overlay without forking built-ins.
- **Deterministic stage outcome documents** reconcile agent narrative with actual check truth.
- **Terminal report stages** still run after upstream failure, preserving a useful final artifact.
- **Human approval** is a resumable state rather than a blocking process waiting indefinitely.
- **Figma handoff checks** validate component naming, variables, development resources, and render context.

Maturity is uneven outside the core. Slack/webhook declarations, some evaluator manifests, Graph2Code,
and external-service integrations are less proven than the local engine. The Neo4j/OpenAI knowledge
service is operationally heavier and less aligned with OwlBear's laptop-resident knowledge store.
The onboarding web application and dashboards are polished distribution surfaces, but they duplicate
Cockpit and introduce another deployed frontend rather than improving OwlBear's core control model.

## 4. Comparative Assessment

| Dimension | Better choice | Reason |
|---|---|---|
| Unattended issue-to-PR automation | Turbo Spec | End-to-end GitHub trigger, runner, sandbox, gates, reports, resume, and PR lifecycle |
| Deterministic per-run contracts | Turbo Spec | Typed blueprints, output schemas, executable evaluators, bounded retries, structured traces |
| Security for autonomous workers | Turbo Spec | Explicit credential, process, filesystem, and network boundaries |
| Multi-provider/model execution | Turbo Spec | Runtime provider abstraction and per-agent overrides |
| Human product shaping | OwlBear | Staged user review, OpenSpec authority, decision requests, and challenger review before build |
| Long-lived portfolio/task governance | OwlBear | Claims, dependencies, OCC, priorities, blocked requests, history, archival reasons, and fresh-board replanning |
| Independent verification and closure | OwlBear | Distinct builder/verifier/collector ownership and repair-cycle routing reduce self-certification |
| Local interactive development | OwlBear | VS Code tools, local filesystem integration, browser sessions, Cockpit, and no CI round trip |
| Institutional learning | OwlBear | Curated agent-scoped memory plus knowledge ingestion/enrichment; Turbo mainly preserves run state |
| Extensible agent guidance | OwlBear | Rich workflow/rules/handbook taxonomy, `applyTo` instructions, project-local customizations |
| Actual task concurrency | OwlBear today | OwlBear dispatches independent agents in waves; Turbo labels DAG waves but executes their stages sequentially |
| Operational simplicity and privacy | OwlBear | Laptop-resident by default, no required GitHub Actions, container registry, telemetry vendor, or cloud graph DB |

### Replacement Scenarios

| Scenario | Verdict |
|---|---|
| Replace OwlBear completely | **Reject.** It would discard the board, shaping conversation, requests, memory, browser acquisition, Cockpit, role separation, and local-first workflow to gain a different product: autonomous CI delivery |
| Replace OwlBear's orchestrator only | **Defer.** Turbo's runner cannot directly invoke VS Code custom agents and its sequential stage runtime does not match OwlBear's board-driven multi-task loop |
| Run Turbo Spec beside OwlBear | **Viable.** OwlBear shapes/approves work; Turbo executes selected CI-ready leaf work; results return as PR/check evidence. Identity, state ownership, and failure routing need one explicit bridge |
| Reimplement selected mechanisms in OwlBear | **Recommended.** Preserve OwlBear's control model while importing the strongest enforceable contracts |

## 5. Recommendation, Confidence, and Limits

### Recommended Sequence

1. **Adopt typed outcome contracts.** Define compact Pydantic/JSON-schema results for builder,
   verifier, collector, and challenger returns. Keep task notes human-readable, but derive routing and
   proof summaries from validated fields rather than prose. This is the highest-value, lowest-coupling idea.
2. **Add first-class executable proof gates.** Represent focused commands, expected exit/result format,
   timeout, and evidence artifacts in task metadata. Execute them through existing quality tooling;
   do not import Turbo's evaluator registry wholesale or make LLM judges the default.
3. **Add orchestration checkpoints.** Persist cycle, dispatched wave, completed task-agent pairs,
   failures, and user feedback so interrupted orchestration can resume without relying on chat history.
4. **Prototype a sandboxed builder path.** Start with credential scrubbing and a restricted subprocess;
   evaluate containers and egress controls only for unattended or untrusted work. Preserve normal local
   VS Code operation for interactive tasks.
5. **Add structured run events to Cockpit.** Extend current activity/SSE data with agent, proof, retry,
   duration, and token events. Keep telemetry local by default; OTLP can remain an optional reporter.
6. **Pilot, do not merge control planes.** Choose one low-risk leaf task and compare OwlBear-local build
   with an OwlBear-shaped/Turbo-executed CI run. Measure setup burden, completion quality, correction
   cycles, elapsed time, token/CI cost, and human intervention before considering a maintained adapter.

### Defer or Reject

- Do not replace Kanban Markdown with workflow YAML; tasks and run definitions are different entities.
- Do not copy Turbo resources until licensing is established.
- Do not adopt New Relic, Neo4j/OpenAI knowledge, Porsche-specific gates, Jira/Figma, Graph2Code, or a
  second onboarding UI without a concrete OwlBear use case.
- Do not advertise parallel stage execution from the DAG planner; v0.37.0 executes stages sequentially.
- Do not make arbitrary shell hooks or dynamically loaded evaluators privileged by default.

**Recommendation:** preserve OwlBear as the system of record and interactive control plane. Treat Turbo
Spec as strong prior art for a future **OwlBear execution plane**, and optionally as an external CI
executor behind an explicit adapter. Wholesale replacement becomes rational only if OwlBear's primary
goal changes to centrally operated, unattended GitHub issue-to-PR delivery.

**Confidence:** High for architecture and static behavior; medium for operational reliability and
integration maturity because no code, live service, container, or CI workflow was executed. The absent
license and unknown production usage are unresolved decision inputs.