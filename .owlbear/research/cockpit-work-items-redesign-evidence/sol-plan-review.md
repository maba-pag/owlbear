disposition: rethink
reviewed_claim: "A Change-grouped table and routed inspector, backed by ChangeGroupView/WorkItemCardView/WorkItemDetailView and Stage/Needs/Activity/Action, coherently represent the full Delivery lifecycle and can ship in independently coherent phases."
review_depth:
  actions: [critical-read, coherence-check, focused-contract-check, source-research, visual-inspection]
  evidence_limit: "Source and tests were inspected read-only. Live rendered text and API responses were inspected at 127.0.0.1:8420; browser automation, screenshots, viewport geometry, and independent Escape reproduction were unavailable. No tests were run. Confirmed: leakage, dropped semantics, request/block misprojection, raw diagnostics, task-inapplicable Integration progress, exception-first detail, and abstract identity overwrite. Falsified: production Change Design/Change Assembly/superseded rows, concurrent Assembly/Integration, `ready` as an attention disposition, and conflict paths requiring no new Git work. Uncertain: actual 1440px geometry, the reported Escape overlay, and intended operator authority over ready Integration."
dimensions:
  product_value:
    disposition: warning
    evidence: "Risk medium; confidence 0.95. Grouping and semantic-first detail directly address the live two-row confusion, but result evidence, completed-history continuity, and background freshness are absent."
  mental_model:
    disposition: error
    evidence: "Risk critical; confidence 0.99. [target_contract.py](serve/delivery/src/owlbear_delivery/target_contract.py) has active Outcomes only; production has no Change Assembly, pre-admission Change Design, or supersession projection. [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py) reconstructs richer authority lossily and even projects runtime Design as Planning."
  authority_and_control:
    disposition: error
    evidence: "Risk critical; confidence 0.99. `resume-design` has no Cockpit route; `Integrate now` expands current UI authority; Work Item projections are also an MCP contract in [target_server.py](serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py). Action authority is therefore unresolved."
  failure_and_reentry:
    disposition: error
    evidence: "Risk critical; confidence 0.98. `repair-authority` requires revision or backward movement, contradicting the proposed blanket prohibition. [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py) neither clears Integration attention nor rejects an active repair claim during administrative movement."
  information_hierarchy:
    disposition: warning
    evidence: "Risk medium; confidence 0.93. The table and conditional inspector are directionally sound, but Activity-or-Action hides valid simultaneous states, and acceptance plus task counts do not provide the promised completion evidence or technical trace."
  proportionality:
    disposition: warning
    evidence: "Risk high; confidence 0.96. Unsupported scope rows, duplicated view contracts, roving-table behavior, and always-complete Integration progress add ceremony. Final >=98% answer: no; a revised artifact could reach that threshold only after fresh source and browser review."
findings:
  - severity: blocker
    target: "Canonical lifecycle and scope model"
    consequence: "The implementation would manufacture unsupported rows, misreport Design reentry as Planning, and design identities for concurrency that production forbids."
    evidence: "Source: [target_contract.py](serve/delivery/src/owlbear_delivery/target_contract.py), `_project_runtime_authority`/`_project_runtime_evidence` in [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py), and `_project_items` in [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py). Change Assembly and supersession exist only in the richer projector path; Integration requires every runtime Outcome completed."
    revision_direction: "Base one canonical DeliveryPortfolioSnapshot on one `DeliveryContract + DeliveryFrontier` read and project binding stages directly. Remove Change Design, Change Assembly, and superseded rows unless separate production authorities are explicitly added; represent current Assembly as Outcome Assembly."
  - severity: blocker
    target: "Integration correction and backward movement"
    consequence: "Repair-authority can become a dead end, while direct API use can leave stale Integration attention or an active repair claim attached to an active-delivery Change."
    evidence: "Source: `integration_repair_authority_replacement` and `administrative_move` in [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py). The former instructs movement earlier; the latter preserves Integration state and lacks a repair-claim guard."
    revision_direction: "Define a code-specific corrective-action matrix. Reject movement during active repair; transactionally retire/archive attention when movement exits Integration; expose version-bound backward previews with exact invalidated Outcomes. Treat ready as absence of attention, not an attention disposition."
  - severity: major
    target: "Needs, Activity, and Action axes"
    consequence: "`Agent working` remains false for unclaimed work, totals misstate motion, and an active claim with recovery attention cannot show both Activity and Action."
    evidence: "Source: [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py) assigns AGENT without a claim; claims live separately in [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py). The proposed table explicitly makes Activity and Action mutually exclusive."
    revision_direction: "Use Needs only for intervention/blocking conditions (`you`, `dependency`, `repair`, `none`); derive Activity as `idle|ready|working|repairing` from claimability and claims. Keep request and requestless-block action kinds distinct, and render Activity and Action independently."
  - severity: major
    target: "Snapshot consistency and background progress"
    consequence: "Groups, cards, detail, totals, and mutation previews can describe different frontier versions; without polling, Supervise cannot reveal agent progress."
    evidence: "Source: [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py) performs separate runtime reads; [useWorkItems.ts](serve/cockpit/web/src/hooks/useWorkItems.ts) fetches only on mount and local mutations despite an existing polling primitive."
    revision_direction: "Return a per-Change snapshot digest/version, compose semantic and operator detail from the same frontier bytes, use expected-version mutation/preflight contracts, and poll current portfolio plus selected detail with race-safe reconciliation."
  - severity: major
    target: "Inspection evidence, completion, and history"
    consequence: "J3 promises evidence but the detail model contains only promise, acceptance, and counts. When Integration completes, the current group disappears without a defined route transition to completed history."
    evidence: "Source: task results carry commits and proof boundaries, while [completed_history.py](serve/delivery/src/owlbear_delivery/completed_history.py) validates retained result history. Neither appears in the proposed detail. Current list logic omits completed Changes."
    revision_direction: "Add bounded result/evidence summaries and technical references. Define current-item completion reentry and a distinct history deep-link route; treat historical recall/audit as an explicit Inspect subjob."
  - severity: major
    target: "HTTP/MCP contract and implementation sequence"
    consequence: "Replacing WorkItemProjection breaks Delivery MCP, while phases 3 and 4 cannot ship independently because the current frontend requires the old flat card contract."
    evidence: "Source: shared calls in [target_server.py](serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py), HTTP wrapping in [target_models.py](serve/cockpit/src/owlbear_cockpit/target_models.py), and frontend consumption in [workItems.ts](serve/cockpit/web/src/api/workItems.ts)."
    revision_direction: "Sequence: domain invariants and canonical snapshot; semantic/evidence projection; then one atomic Cockpit HTTP+frontend cutover while preserving or explicitly migrating MCP; routed inspector/history; polling and responsive/accessibility proof. Do not maintain duplicate long-lived view models."
  - severity: major
    target: "Table navigation, routing, responsive mode, and focus"
    consequence: "A semantic table with roving tabindex is not native table navigation; detail URLs do not currently match route families; split/flyout transitions lack close and focus-restoration semantics."
    evidence: "Source: exact-path selection in [CockpitShell.tsx](serve/cockpit/web/src/CockpitShell.tsx); current local selection in [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx); PDS confirms Escape emits `onDismiss`. Design judgment: viewport-only 1440px is weaker than available workspace width."
    revision_direction: "Use native anchor tab order and remove roving behavior unless adopting a complete grid pattern. Route with an opaque scope-qualified item key, update shell route-family matching, restore focus on close, unmount the flyout after dismissal, and choose split mode from measured workspace width."
  - severity: major
    target: "Acceptance proof"
    consequence: "The plan could pass existing tests while preserving the principal scope, reentry, staleness, and accessibility defects."
    evidence: "Current route tests use a fake application; Vitest mocks the API; assembled E2E covers one invalid mixed state and dismisses by button, not Escape. It lacks requestless block, Design return, all Integration dispositions, active repair, stale mutation, completion handoff, deep-link reload, and long/empty/error fixtures."
    revision_direction: "Add production-boundary observations for every named lifecycle scenario, snapshot races, exact pre-move invalidation, current-to-history handoff, native link behavior, focus restoration, Escape unmount, 1100/1440 geometry, long content, empty/loading/error, and serious/critical axe results."
user_questions:
  - "Should current Delivery include pre-admission Design and revision/supersession history, or begin only at admitted Outcomes as production does today?"
  - "May a user initiate ready Integration from Cockpit, or may Cockpit only retry failed Integration while orchestration owns initial execution?"
memory_candidate:
  source_agent: conceptual-design-reviewer
  title: "Project from production authority"
  content: "Cockpit Work Items currently adapt schema-v2 DeliveryContract/DeliveryFrontier into richer TargetAuthority projections in [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py); conceptual reviews must verify that proposed Design, Assembly, reentry, and supersession states survive that production adapter before treating projector capabilities as live behavior."
  categories: [domain-knowledge, pitfall]
  confidence: 0.9