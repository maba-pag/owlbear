import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type {
  ChangeGroupView,
  DeliveryReadiness,
  DeliveryReadinessReasonCode,
  WorkItemAvailableDetailResponse,
  WorkItemCardView,
} from "../api/workItems";
import { MERGE_BLOCK_LABELS, READINESS_REASON_LABELS } from "../components/workItemPresentation";
import {
  CONTINUATION_PROMPT,
  card,
  changeStatus,
  continuationCard,
  detail,
  expectPauseOffered,
  expectPauseRefused,
  fixtureState,
  group,
  heldCard,
  inputValue,
  installWorkPortfolioHarness,
  namedPdsHost,
  PAUSE_AVAILABLE,
  PAUSE_REFUSALS,
  PAUSE_REQUESTED,
  type PublicationView,
  portfolio,
  publicationCardForChecks,
  publicationForChecks,
  quietCard,
  readiness,
  renderPage,
  requirePresent,
  selectValue,
  unavailableChange,
} from "./workPortfolioHarness";

installWorkPortfolioHarness();

it("maps every coherent engine readiness response to its portfolio state and controls", async () => {
  const finalizeAction = {
    kind: "finalize" as const,
    label: "Finalize Change",
    command: "/finalize-change change-alpha",
  };
  // Engine target-sync prerequisite: named operation with a label but no caller-runnable command.
  const syncTargetAction = {
    kind: "sync-target" as const,
    label: "Synchronize target",
    command: null,
  };
  interface ReadinessScenario {
    item: WorkItemCardView;
    state: DeliveryReadiness;
    lifecycle: ChangeGroupView["lifecycle"];
    publication: PublicationView | null;
    chip: string;
    reason: string;
    actor: string;
    command: string | null;
  }
  // Each case is one response the engine can actually compose: status, operation,
  // executable, action and card facts stay mutually consistent.
  const scenarios: ReadinessScenario[] = [
    {
      item: publicationCardForChecks({
        publication_phase: "ready-for-finalization",
        next_step: "Finalize the reviewed Change",
        progress: {
          kind: "publication",
          label: "Reviewed Change awaiting finalization",
          done: null,
          total: null,
        },
        action: finalizeAction,
      }),
      state: readiness({
        status: "ready",
        operation: "finalize",
        executable: true,
        next_actor: "agent",
        reason_code: "ready",
        action: finalizeAction,
      }),
      lifecycle: "publication",
      publication: {
        ...publicationForChecks("ready-for-finalization"),
        ready_for_finalization: true,
      },
      chip: "Ready",
      reason: "Delivery reports this operation is eligible now.",
      actor: "Agent",
      command: finalizeAction.command,
    },
    {
      item: card({
        next_step: "Builder is implementing TASK-001",
        activity: {
          state: "working",
          worker_role: "builder",
          started_at: "2026-08-08T10:00:00Z",
          task_id: "TASK-001",
        },
      }),
      state: readiness({
        status: "running",
        next_actor: "agent",
        reason_code: "active-custody",
      }),
      lifecycle: "in-delivery",
      publication: null,
      chip: "Running",
      reason: "An active operation retains Change custody.",
      actor: "Agent",
      command: null,
    },
    {
      item: card({
        item_key: "outcome:OUT-003",
        work_item_id: "OUT-003",
        title: "Dependent outcome",
        needs: "dependency",
        needs_headline: "Waiting on OUT-001",
        next_actor: "dependency",
        next_step: "Waiting on OUT-001",
        activity: {
          state: "idle",
          worker_role: null,
          started_at: null,
          task_id: null,
        },
        progress: {
          kind: "plan",
          label: "Task plan not published",
          done: null,
          total: null,
        },
      }),
      state: readiness({
        status: "waiting",
        next_actor: "dependency",
        reason_code: "dependency-wait",
      }),
      lifecycle: "in-delivery",
      publication: null,
      chip: "Waiting",
      reason: "A dependency has not completed yet.",
      actor: "Dependency",
      command: null,
    },
    {
      item: card({
        next_actor: "you",
        next_step: "Resume the deferred Change",
        activity: {
          state: "idle",
          worker_role: null,
          started_at: null,
          task_id: null,
        },
      }),
      state: readiness({
        status: "blocked",
        next_actor: "you",
        reason_code: "change-paused",
      }),
      lifecycle: "deferred",
      publication: null,
      chip: "Blocked",
      reason: "This Change is paused.",
      actor: "You",
      command: null,
    },
    {
      item: publicationCardForChecks({
        publication_phase: "ready-for-finalization",
        next_step: "Finalize the reviewed Change",
        progress: {
          kind: "publication",
          label: "Reviewed Change awaiting finalization",
          done: null,
          total: null,
        },
      }),
      state: readiness({
        status: "unavailable",
        operation: "finalize",
        next_actor: "agent",
        reason_code: "workspace-inspection-failed",
      }),
      lifecycle: "publication",
      publication: publicationForChecks("ready-for-finalization"),
      chip: "Unavailable",
      reason: "Managed workspace readiness could not be observed.",
      actor: "Agent",
      command: null,
    },
    {
      item: publicationCardForChecks({
        publication_phase: "ready-for-finalization",
        next_step: "Synchronize the Change with its integration target",
        progress: {
          kind: "publication",
          label: "Reviewed Change awaiting finalization",
          done: null,
          total: null,
        },
        action: syncTargetAction,
      }),
      state: readiness({
        status: "ready",
        operation: "sync-target",
        next_actor: "agent",
        reason_code: "target-sync-required",
        basis: {
          contract_digest: "c".repeat(64),
          frontier_digest: "d".repeat(64),
          source_head: "1".repeat(40),
          target_head: "e".repeat(40),
          continuation_id: `continue-${"c".repeat(64)}`,
          candidate_head: "1".repeat(40),
          reviewed_head: "2".repeat(40),
          workspace_fingerprint: null,
          diagnostic_sequence: 0,
        },
      }),
      lifecycle: "publication",
      publication: publicationForChecks("ready-for-finalization"),
      chip: "Ready",
      reason: "The Change must be synchronized with its integration target first.",
      actor: "Agent",
      command: null,
    },
    {
      item: card({
        stage: "completed",
        next_actor: "none",
        next_step: "Complete — no action needed",
        activity: {
          state: "idle",
          worker_role: null,
          started_at: null,
          task_id: null,
        },
        progress: {
          kind: "tasks",
          label: "2 of 2 Delivery tasks reviewed",
          done: 2,
          total: 2,
        },
      }),
      state: readiness({
        status: "complete",
        next_actor: "none",
        reason_code: "change-terminal",
      }),
      lifecycle: "in-delivery",
      publication: null,
      chip: "Complete",
      reason: "This Change reached a terminal state.",
      actor: "Nobody",
      command: null,
    },
  ];

  for (const scenario of scenarios) {
    const item: WorkItemCardView = {
      ...scenario.item,
      readiness: scenario.state,
    };
    fixtureState.currentPortfolio = portfolio([group({ lifecycle: scenario.lifecycle, items: [item] })]);
    fixtureState.currentDetail = detail({
      card: item,
      readiness: scenario.state,
      publication: scenario.publication,
    });
    const { unmount } = renderPage(`/delivery/change-alpha/${item.item_key}`);

    const table = await screen.findByTestId("work-portfolio-table");
    const row = table.querySelector(`[data-work-item="change-alpha:${item.item_key}"]`) as HTMLElement;
    expect(row.querySelector("[data-status-tone]")).toHaveTextContent(scenario.chip);

    const inspector = await screen.findByTestId("work-item-detail");
    expect(within(inspector).getByTestId("readiness-status")).toHaveTextContent(scenario.chip);
    expect(inspector.querySelector(`[data-readiness-reason="${scenario.state.reason_code}"]`)).toHaveTextContent(
      scenario.reason,
    );
    expect(inspector.querySelector(`[data-readiness-actor="${scenario.state.next_actor}"]`)).toHaveTextContent(
      `Next: ${scenario.actor}`,
    );
    if (scenario.command) {
      expect(within(inspector).queryByTestId("readiness-not-executable")).not.toBeInTheDocument();
      expect(
        within(inspector).getByRole("button", {
          name: `Copy command ${scenario.command}`,
        }),
      ).toBeInTheDocument();
    } else {
      expect(within(inspector).getByTestId("readiness-not-executable")).toHaveTextContent(
        "Delivery offers no runnable operation for this Work Item right now.",
      );
      expect(within(inspector).queryByRole("button", { name: /^Copy command/ })).not.toBeInTheDocument();
    }
    expect(fixtureState.requests.filter((request) => request.method !== "GET")).toEqual([]);
    unmount();
  }
});

it("offers the finalize command only while engine readiness is executable", async () => {
  const executableAction = {
    kind: "finalize" as const,
    label: "Finalize the reviewed Change",
    command: "/finalize-change change-alpha",
  };
  fixtureState.currentDetail = detail({
    card: publicationCardForChecks({
      publication_phase: "ready-for-finalization",
      action: executableAction,
    }),
    publication: {
      ...publicationForChecks("ready-for-finalization"),
      ready_for_finalization: true,
    },
    readiness: readiness({
      status: "ready",
      operation: "finalize",
      executable: true,
      reason_code: "ready",
      action: executableAction,
      prompt: "/continue-change change-alpha reread get_change and pass its readiness basis unchanged.",
    }),
  });
  renderPage("/delivery/change-alpha/publication");
  const executableInspector = await screen.findByTestId("work-item-detail");
  expect(
    within(executableInspector).getByRole("button", {
      name: `Copy command ${executableAction.command}`,
    }),
  ).toBeInTheDocument();
  expect(within(executableInspector).queryByTestId("readiness-not-executable")).not.toBeInTheDocument();
  const prompt = within(executableInspector).getByTestId("readiness-prompt");
  expect(prompt.tagName).toBe("PRE");
  expect(prompt).toHaveTextContent(
    "/continue-change change-alpha reread get_change and pass its readiness basis unchanged.",
  );
  expect(prompt.querySelector("a, button")).toBeNull();

  fixtureState.currentDetail = detail({
    card: publicationCardForChecks({
      publication_phase: "ready-for-finalization",
    }),
    publication: {
      ...publicationForChecks("ready-for-finalization"),
      ready_for_finalization: false,
    },
    readiness: readiness({
      status: "blocked",
      reason_code: "workspace-dirty",
      next_actor: "you",
    }),
  });
  await waitFor(
    () =>
      expect(
        screen.queryByRole("button", {
          name: `Copy command ${executableAction.command}`,
        }),
      ).not.toBeInTheDocument(),
    { timeout: 6000 },
  );
  const blockedInspector = screen.getByTestId("work-item-detail");
  expect(within(blockedInspector).getByTestId("finalization-readiness")).toHaveTextContent(
    "Delivery cannot finalize the current Change yet.",
  );
  expect(within(blockedInspector).getByTestId("readiness-not-executable")).toBeInTheDocument();
});

it("offers read-only inspection for an unavailable Change without controls", async () => {
  const unavailable = unavailableChange("change-alpha", "Portfolio redesign");
  fixtureState.currentUnavailableDetail = {
    ...unavailable,
    readiness: { ...unavailable.readiness, prompt: "/repair-delivery Diagnose Change change-alpha read-only." },
  };
  renderPage("/delivery/change-alpha/outcome:OUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent("Runtime unavailable");
  expect(inspector).toHaveTextContent(
    "This view is read-only inspection evidence; no Change operation is offered here.",
  );
  expect(within(inspector).getByTestId("unavailable-change-diagnostics")).toHaveTextContent("runtime-unavailable");
  expect(within(inspector).getByTestId("readiness-status")).toHaveTextContent("Unavailable");
  expect(within(inspector).getByTestId("readiness-checks-state")).toHaveTextContent("Unknown");
  const prompt = within(inspector).getByTestId("readiness-prompt");
  expect(prompt.tagName).toBe("PRE");
  expect(prompt).toHaveTextContent("/repair-delivery Diagnose Change change-alpha read-only.");
  expect(prompt.querySelector("a, button")).toBeNull();
  expect(within(inspector).queryByRole("button")).not.toBeInTheDocument();
});

it.each([
  ["continuation text", "/continue-change change-alpha reread readiness before continuing."],
  ["diagnostic text containing markup", '/repair-delivery Diagnose <a href="/mutate">this Change</a> read-only.'],
  ["absent prompt", undefined],
  ["null prompt", null],
] as const)("renders readiness prompts inertly or omits them: %s", async (_label, prompt) => {
  const promptState = prompt === undefined ? {} : { prompt };
  fixtureState.currentDetail = detail({
    readiness: readiness({
      status: "blocked",
      reason_code: "engine-action-blocked",
      ...promptState,
    }),
  });
  renderPage("/delivery/change-alpha/outcome:OUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  const renderedPrompt = within(inspector).queryByTestId("readiness-prompt");
  if (typeof prompt === "string") {
    const promptElement = requirePresent(renderedPrompt);
    expect(promptElement.tagName).toBe("PRE");
    expect(promptElement).toHaveTextContent(prompt);
    expect(promptElement.querySelector("a, button, img, script")).toBeNull();
  } else {
    expect(renderedPrompt).not.toBeInTheDocument();
  }
});

it("labels every continuation readiness reason without blanking a new engine state", async () => {
  const continuationReasons: DeliveryReadinessReasonCode[] = [
    "design-attention",
    "builder-transition-contained",
    "finalization-failed",
    "settled-attention-target-drift",
    "claim-activation-failed",
    "coordination-unavailable",
    "execution-occupancy-unavailable",
    "engine-action-pending",
    "engine-action-blocked",
    "engine-action-interrupted",
    "engine-action-failed",
    "engine-action-incomplete",
    "target-sync-required",
    "claim-custody-unreconciled",
    "retry-backoff",
    "retry-exhausted",
    "acceptance-wait",
    "retry-containment",
    "retry-ledger-unavailable",
    "worker-stall-wait",
  ];
  expect(new Set(continuationReasons.map((reason) => READINESS_REASON_LABELS[reason])).size).toBe(
    continuationReasons.length,
  );

  const retryCondition = "Wait until the retained attempt can be safely inspected.";
  const containedBuilderAttention: NonNullable<WorkItemAvailableDetailResponse["item"]["recovery_attention"]> = {
    attempt_id: "attempt-001",
    claim_id: "claim-001",
    reason: "The Builder block transition remains contained with custody retained.",
    custody_retained: true,
    retry_condition: retryCondition,
    diagnostic_transition: {
      action: "block",
      outcome_id: "OUT-001",
      claim_id: "claim-001",
      block_id: "block-001",
      reason: "A bounded user decision is required.",
      unblock_condition: "The decision is recorded.",
      expected_evidence: ["Recorded user decision"],
      locators: ["request:REQUEST-001"],
      request: {
        request_id: "REQUEST-001",
        kind: "decision",
        outcome_id: "OUT-001",
        summary: "Choose the next step.",
        options: [{ option_id: "continue", label: "Continue" }],
        resolution: null,
      },
      resume_commit: null,
    },
  };

  for (const reason of continuationReasons) {
    const designAttention = reason === "design-attention";
    const targetDrift = reason === "settled-attention-target-drift";
    const builderTransitionContained = reason === "builder-transition-contained";
    const state = readiness({
      status: designAttention || targetDrift || builderTransitionContained ? "blocked" : "waiting",
      executable: false,
      next_actor: designAttention ? "you" : "agent",
      reason_code: reason,
    });
    fixtureState.currentDetail = detail({
      readiness: state,
      ...(builderTransitionContained ? { recovery_attention: containedBuilderAttention } : {}),
    });
    const { unmount } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");

    const inspector = await screen.findByTestId("work-item-detail");
    const rendered = inspector.querySelector(`[data-readiness-reason="${reason}"]`);
    expect(rendered).toHaveTextContent(READINESS_REASON_LABELS[reason]);
    expect(rendered?.textContent?.trim()).not.toBe("");
    expect(rendered).not.toHaveTextContent(READINESS_REASON_LABELS.ready);
    if (designAttention) {
      expect(inspector.querySelector('[data-readiness-actor="you"]')).toHaveTextContent("Next: You");
    }
    if (targetDrift) {
      expect(within(inspector).getByTestId("readiness-status")).toHaveTextContent("Blocked");
      expect(within(inspector).getByTestId("readiness-not-executable")).toBeInTheDocument();
    }
    if (builderTransitionContained) {
      expect(within(inspector).getByText("Recovery attention")).toBeInTheDocument();
      expect(inspector).toHaveTextContent(containedBuilderAttention.reason);
      expect(inspector).toHaveTextContent(`Next: ${retryCondition}`);
      expect(within(inspector).getByTestId("readiness-status")).toHaveTextContent("Blocked");
      expect(within(inspector).getByTestId("readiness-not-executable")).toBeInTheDocument();
      expect(within(inspector).queryByRole("button", { name: /^Copy command/ })).not.toBeInTheDocument();
    }
    unmount();
  }
}, 60_000);

it("renders an awaiting-merge offer as read-only readiness", async () => {
  const offer: NonNullable<DeliveryReadiness["merge_offer"]> = {
    offer_id: "9".repeat(64),
    repository: "owlbear/example",
    number: 42,
    node_id: "PR_example_42",
    title: "Merge approval example",
    head_sha: "a".repeat(40),
    base_branch: "main",
    target_head: "b".repeat(40),
    finalization_id: "c".repeat(64),
    ready_receipt_id: "d".repeat(64),
    merge_method: "merge",
    stack_size: 1,
    required_checks: [{ name: "build", conclusion: "success" }],
    check_summary: {
      required_passed: 2,
      required_pending: 1,
      required_failed: 0,
      optional_failed: 1,
    },
    proof: {
      observation_count: 3,
      review_id: "e".repeat(64),
      proof_target: "f".repeat(40),
    },
  };
  const state = readiness({
    status: "waiting",
    next_actor: "you",
    reason_code: "merge-approval-required",
    merge_offer: offer,
  });
  const item = publicationCardForChecks({ publication_phase: "awaiting-merge", readiness: state });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "awaiting-merge", items: [item] })]);
  fixtureState.currentDetail = detail({
    card: item,
    readiness: state,
    publication: publicationForChecks("awaiting-merge"),
  });
  renderPage(`/delivery/change-alpha/${item.item_key}`);

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector.querySelector('[data-readiness-reason="merge-approval-required"]')).toHaveTextContent(
    READINESS_REASON_LABELS["merge-approval-required"],
  );
  const summary = within(inspector).getByTestId("merge-offer");
  expect(summary).toHaveTextContent("owlbear/example#42");
  expect(summary).toHaveTextContent("Merge approval example");
  expect(summary).toHaveTextContent("2 passed, 1 pending, 0 failed; 1 optional failed");
  expect(within(inspector).queryByRole("button", { name: /approve|merge/i })).not.toBeInTheDocument();
});

it("renders the GitHub next step for a blocked merge offer", async () => {
  const detailText = "GitHub reported an unresolved conflict.";
  const state = readiness({
    status: "blocked",
    next_actor: "you",
    reason_code: "merge-blocked",
    merge_block: { reason: "conflicts", detail: detailText },
  });
  const item = publicationCardForChecks({ publication_phase: "awaiting-merge", readiness: state });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "awaiting-merge", items: [item] })]);
  fixtureState.currentDetail = detail({
    card: item,
    readiness: state,
    publication: publicationForChecks("awaiting-merge"),
  });
  renderPage(`/delivery/change-alpha/${item.item_key}`);

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("merge-block")).toHaveTextContent(
    `${MERGE_BLOCK_LABELS.conflicts} (${detailText})`,
  );
});

it("renders an unknown merge as attention with the pull request link and no merge control", async () => {
  const prUrl = "https://github.com/owlbear/example/pull/42";
  const state = readiness({
    status: "blocked",
    next_actor: "you",
    reason_code: "merge-response-unknown",
    merge_attempt: { approval_id: "1".repeat(64), state: "released", approved_head: "a".repeat(40), pr_url: prUrl },
  });
  const item = publicationCardForChecks({ publication_phase: "awaiting-merge", readiness: state });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "awaiting-merge", items: [item] })]);
  fixtureState.currentDetail = detail({
    card: item,
    readiness: state,
    publication: publicationForChecks("awaiting-merge"),
  });
  renderPage(`/delivery/change-alpha/${item.item_key}`);

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector.querySelector('[data-readiness-reason="merge-response-unknown"]')).toHaveTextContent(
    READINESS_REASON_LABELS["merge-response-unknown"],
  );
  const attempt = within(inspector).getByTestId("merge-attempt");
  expect(within(attempt).getByRole("link", { name: /pull request/i })).toHaveAttribute("href", prUrl);
  expect(attempt).toHaveTextContent("a".repeat(12));
  expect(within(inspector).queryByRole("button", { name: /approve|merge/i })).not.toBeInTheDocument();
});

it("gives every new merge readiness reason a distinct non-empty label", () => {
  const reasons: DeliveryReadinessReasonCode[] = [
    "merge-approval-required",
    "merge-checking",
    "merge-blocked",
    "checks-running",
    "provider-unavailable",
    "merge-in-progress",
    "merge-response-unknown",
  ];
  const labels = reasons.map((reason) => READINESS_REASON_LABELS[reason]);

  expect(labels.every((label) => label.trim().length > 0)).toBe(true);
  expect(new Set(labels).size).toBe(reasons.length);
});

it("renders durable retry readiness metadata", async () => {
  fixtureState.currentDetail = detail({
    readiness: readiness({
      status: "waiting",
      reason_code: "retry-backoff",
      attempts: 2,
      next_eligible_at: "2026-08-04T00:00:02Z",
      stop_reason: null,
    }),
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent("Automatic attempts");
  expect(inspector).toHaveTextContent("2");
  expect(inspector).toHaveTextContent("Next eligible at");
  expect(inspector).toHaveTextContent("2026-08-04T00:00:02Z");
});

it.each([
  ["retry-exhausted", "Automatic retries are exhausted; Delivery offers no action to reset this budget."],
  [
    "retry-containment",
    "A prior attempt has no authoritative outcome. Preserve custody; no caller action can retry or release it.",
  ],
] as const)("shows no expected actor or prompt for %s", async (reason, explanation) => {
  fixtureState.currentDetail = detail({
    readiness: readiness({
      status: "blocked",
      reason_code: reason,
      next_actor: "none",
      prompt: null,
      stop_reason: reason,
    }),
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector.querySelector('[data-readiness-actor="none"]')).toHaveTextContent("Next: Nobody");
  expect(inspector.querySelector(`[data-readiness-reason="${reason}"]`)).toHaveTextContent(explanation);
  expect(screen.queryByTestId("readiness-prompt")).not.toBeInTheDocument();
});

it("renders the bounded attempt history of an exhausted retry episode", async () => {
  fixtureState.currentDetail = detail({
    readiness: readiness({
      status: "blocked",
      reason_code: "retry-exhausted",
      next_actor: "agent",
      attempts: 3,
      stop_reason: "retry-exhausted",
      retry_history: [
        {
          ordinal: 1,
          kind: "original",
          status: "failed",
          failure_code: "builder-failed",
          observed_at: "2026-08-04T00:00:00Z",
        },
        { ordinal: 2, kind: "repair", status: "failed", failure_code: "worker-timeout", observed_at: null },
        { ordinal: 3, kind: "repair", status: "failed", failure_code: null, observed_at: "2026-08-04T02:00:00Z" },
      ],
    }),
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const history = await screen.findByTestId("readiness-retry-history");
  expect(history).toHaveTextContent("Attempt history");
  const entries = within(history).getAllByRole("listitem");
  expect(entries).toHaveLength(3);
  expect(entries[0]).toHaveTextContent("1. original failed builder-failed at 2026-08-04T00:00:00Z");
  expect(entries[1]).toHaveTextContent("2. repair failed worker-timeout");
  expect(entries[2]).toHaveTextContent("3. repair failed at 2026-08-04T02:00:00Z");
});

it("offers release for a running continuation worker with its exact claim identity", async () => {
  fixtureState.currentDetail = detail({
    card: card({ stage: "implementation" }),
    active_claim: {
      attempt_id: "attempt-continuation",
      claim_id: "claim-continuation",
      owner_id: "cockpit-host",
      process_id: "cockpit-session",
      continuation: true,
      started_at: "2026-09-13T10:00:00Z",
      worker_role: "builder",
      task_id: null,
    },
    readiness: readiness({ status: "running", reason_code: "active-custody" }),
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("claim-continuation-custody")).toHaveTextContent(
    "Delivery holds this custody as an engine continuation.",
  );
  expect(inspector).toHaveTextContent("Engine continuation");
  expect(inspector).toHaveTextContent("cockpit-host");
  expect(inspector).toHaveTextContent("cockpit-session");
  expect(inspector).toHaveTextContent("not evidence that the worker is still running");
  fireEvent.click(within(inspector).getByText("Release stuck worker"));
  fireEvent.click(screen.getByText("Confirm release"));

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/workers/release-stuck",
      method: "POST",
      body: { outcome_id: "OUT-001", attempt_id: "attempt-continuation", claim_id: "claim-continuation" },
    }),
  );
});

it("does not offer stuck-worker release when a claim is missing its identifiers", async () => {
  fixtureState.currentDetail = detail({
    card: card({ stage: "implementation" }),
    active_claim: {
      attempt_id: "",
      claim_id: "",
      owner_id: "cockpit-host",
      process_id: "cockpit-session",
      continuation: true,
      started_at: "2026-09-13T10:00:00Z",
      worker_role: "builder",
      task_id: null,
    },
    readiness: readiness({ status: "running", reason_code: "active-custody" }),
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).queryByText("Release stuck worker")).not.toBeInTheDocument();
});

it("exposes the coordination status behind an unreadable Change record", async () => {
  fixtureState.currentUnavailableDetail = {
    ...unavailableChange("change-alpha", "Portfolio redesign"),
    diagnostics: ["runtime-unavailable", "coordination-unavailable"],
    coordination_status: "unreadable",
    readiness: readiness({
      status: "unavailable",
      next_actor: "none",
      reason_code: "coordination-unavailable",
      checks_state: "unknown",
    }),
  };
  renderPage("/delivery/change-alpha/outcome:OUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  const diagnostics = within(inspector).getByTestId("unavailable-change-diagnostics");
  expect(diagnostics).toHaveTextContent("runtime-unavailable");
  expect(diagnostics).toHaveTextContent("coordination-unavailable");
  expect(diagnostics).toHaveTextContent("Coordination record: unreadable");
  expect(inspector.querySelector('[data-readiness-reason="coordination-unavailable"]')).toHaveTextContent(
    "This Change has no readable coordination record.",
  );
  expect(within(inspector).queryByRole("button")).not.toBeInTheDocument();
});

it("lists engine-reported unavailable Changes that no operating status covers", async () => {
  fixtureState.currentPortfolio = {
    ...portfolio(),
    unavailable_changes: [unavailableChange("quarantined-change", "Quarantined work")],
  };
  renderPage();

  const issues = await screen.findByTestId("delivery-issues-section");
  expect(issues).toHaveTextContent("1 Change unavailable to Delivery.");
  const row = issues.querySelector('[data-delivery-unavailable="quarantined-change"]') as HTMLElement;
  expect(row).toHaveTextContent("Quarantined work");
  expect(row).toHaveTextContent("Delivery could not compose this Change runtime.");
  expect(row).toHaveTextContent("Read-only inspection only. Checks: Unknown.");
});

it("opens read-only inspection for a listed unavailable Change from the keyboard", async () => {
  fixtureState.currentPortfolio = {
    ...portfolio([]),
    unavailable_changes: [unavailableChange("change-alpha", "Quarantined work")],
  };
  fixtureState.currentUnavailableDetail = unavailableChange("change-alpha", "Quarantined work");
  renderPage();

  const issues = await screen.findByTestId("delivery-issues-section");
  const trigger = within(issues).getByRole("link", {
    name: "Quarantined work",
  });
  trigger.focus();
  expect(trigger).toHaveFocus();
  fireEvent.click(trigger);

  const inspector = await screen.findByTestId("work-item-detail");
  expect(screen.getByTestId("test-location")).toHaveTextContent("/delivery/change-alpha/publication");
  expect(inspector).toHaveTextContent(
    "This view is read-only inspection evidence; no Change operation is offered here.",
  );
  expect(within(inspector).queryByRole("button")).not.toBeInTheDocument();

  fireEvent.keyDown(inspector, { key: "Escape" });
  await waitFor(() => expect(trigger).toHaveFocus());
});

it("counts listed unavailable Changes in portfolio accounting and filters", async () => {
  fixtureState.currentPortfolio = {
    ...portfolio(),
    unavailable_changes: [unavailableChange("quarantined-change", "Quarantined work")],
  };
  const { container } = renderPage();

  await screen.findByTestId("work-portfolio-table");
  fireEvent.click(screen.getByTestId("work-filters-toggle"));
  const selects = container.querySelectorAll("p-select");
  selectValue(selects[0], "quarantined-change");

  await waitFor(() => expect(screen.getByTestId("work-shown-count")).toHaveTextContent("1 of 3"));
  expect(screen.getByTestId("delivery-issues-section")).toHaveTextContent("Quarantined work");
  expect(screen.queryByTestId("work-empty-state")).not.toBeInTheDocument();
});

it("keeps the inspector on a Change that becomes unavailable and restores it when available again", async () => {
  renderPage("/delivery/change-alpha/outcome:OUT-001");
  expect(await screen.findByTestId("work-item-detail")).toHaveTextContent("Delivery foundation");
  await screen.findByTestId("work-portfolio-table");

  fixtureState.currentPortfolio = {
    ...portfolio([]),
    unavailable_changes: [unavailableChange("change-alpha", "Portfolio redesign")],
  };
  fixtureState.currentUnavailableDetail = unavailableChange("change-alpha", "Portfolio redesign");

  await waitFor(() => expect(screen.getByTestId("work-item-detail")).toHaveTextContent("Runtime unavailable"), {
    timeout: 6000,
  });
  const unavailableInspector = screen.getByTestId("work-item-detail");
  expect(unavailableInspector).toHaveTextContent(
    "This view is read-only inspection evidence; no Change operation is offered here.",
  );
  expect(within(unavailableInspector).getByTestId("unavailable-change-diagnostics")).toHaveTextContent(
    "runtime-unavailable",
  );
  expect(within(unavailableInspector).getByTestId("readiness-status")).toHaveTextContent("Unavailable");
  expect(within(unavailableInspector).queryByRole("button")).not.toBeInTheDocument();
  expect(fixtureState.requests.filter((request) => request.method !== "GET")).toEqual([]);
  expect(screen.getByTestId("delivery-issues-section")).toHaveTextContent("Portfolio redesign");
  expect(screen.getByTestId("test-location")).toHaveTextContent("/delivery/change-alpha/outcome:OUT-001");
  expect(screen.queryByTestId("completed-history-workspace")).not.toBeInTheDocument();

  fixtureState.currentPortfolio = portfolio();
  fixtureState.currentUnavailableDetail = null;
  await waitFor(() => expect(screen.getByTestId("work-item-detail")).toHaveTextContent("Delivery foundation"), {
    timeout: 6000,
  });
  const restoredInspector = screen.getByTestId("work-item-detail");
  expect(restoredInspector).toHaveTextContent("Make Delivery supervision coherent.");
  expect(within(restoredInspector).queryByTestId("unavailable-change-diagnostics")).not.toBeInTheDocument();
  await waitFor(() => expect(screen.getByTestId("work-portfolio-table")).toHaveTextContent("Delivery foundation"), {
    timeout: 6000,
  });
  expect(screen.getByTestId("test-location")).toHaveTextContent("/delivery/change-alpha/outcome:OUT-001");
  expect(fixtureState.requests.filter((request) => request.method !== "GET")).toEqual([]);
});

it("does not duplicate an unavailable Change already carried by an operating status", async () => {
  const base = portfolio();
  fixtureState.currentPortfolio = {
    ...base,
    unavailable_changes: [unavailableChange("unavailable-change")],
    operating: {
      ...base.operating,
      statuses: [
        ...base.operating.statuses,
        changeStatus("unavailable-change", {
          actionable_runtime: false,
          diagnostic_code: "runtime_unavailable",
          diagnostic_detail: "Runtime composition is unavailable.",
        }),
      ],
    },
  };
  renderPage();

  const issues = await screen.findByTestId("delivery-issues-section");
  expect(issues.querySelectorAll('[data-delivery-unavailable="unavailable-change"]')).toHaveLength(0);
  expect(issues.querySelectorAll('[data-delivery-status="unavailable-change"]')).toHaveLength(1);
  expect(issues).toHaveTextContent("1 Change unavailable to Delivery.");
});

it("copies the engine continuation prompt from a row without navigating or starting an agent", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  fixtureState.currentPortfolio = portfolio([group({ progress: "waiting-for-chat", items: [continuationCard()] })]);
  renderPage();

  const table = await screen.findByTestId("work-portfolio-table");
  const row = within(table).getAllByText("Delivery foundation")[0].closest("[data-work-item]") as HTMLElement;
  expect(within(row).getByText("Waiting for chat to resume", { selector: "[data-status-tone]" })).toBeVisible();
  expect(within(table).getByTestId("change-progress-change-alpha")).toHaveTextContent("Waiting for chat to resume");
  const copy = within(row).getByRole("button", { name: "Copy continuation prompt" });
  expect(copy).toHaveAccessibleDescription("Run it in Copilot Chat. Copying does not start an agent.");
  expect(within(table).queryByRole("link", { name: "Copy continuation prompt" })).not.toBeInTheDocument();
  const toast = document.querySelector("p-toast") as HTMLElement & { addMessage: (message: unknown) => void };
  const addMessage = vi.spyOn(toast, "addMessage");

  fireEvent.click(copy);

  await waitFor(() => expect(writeText).toHaveBeenCalledWith(CONTINUATION_PROMPT));
  expect(addMessage).toHaveBeenCalledWith({ text: "Copied continuation prompt", state: "success" });
  expect(screen.getByTestId("test-location")).toHaveTextContent("/delivery");
  expect(document.body).not.toHaveTextContent(/\bStart\b/);
  expect(document.body).not.toHaveTextContent(/agent (started|launched)/i);
});

it.each([
  ["/repair-delivery Diagnose Change change-alpha read-only; preserve existing custody and journals."],
  ["/inspect-change change-alpha Diagnose the exhausted retry episode read-only."],
  ["/design change-alpha Resume the existing Design session."],
  ["/continue-change change-beta reread get_change and pass its readiness basis unchanged."],
  ["/continue-change change-alphabet reread get_change and pass its readiness basis unchanged."],
])("never labels %s as this Change's continuation prompt", async (prompt) => {
  const other = continuationCard({
    readiness: readiness({ status: "blocked", reason_code: "retry-exhausted", prompt, progress: "needs-decision" }),
  });
  fixtureState.currentPortfolio = portfolio([group({ items: [other] })]);
  fixtureState.currentDetail = detail({ card: other, readiness: other.readiness });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("readiness-prompt")).toHaveTextContent(prompt);
  expect(screen.queryByRole("button", { name: "Copy continuation prompt" })).not.toBeInTheDocument();
});

it("shows the continuation copy, progress and Change activity in detail", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  const ready = continuationCard();
  fixtureState.currentPortfolio = portfolio([group({ progress: "waiting-for-chat", items: [ready] })]);
  fixtureState.currentDetail = detail({ card: ready, readiness: ready.readiness, change_progress: "waiting-for-chat" });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("readiness-progress")).toHaveTextContent("Waiting for chat to resume");
  expect(within(inspector).getByTestId("change-progress")).toHaveTextContent("Waiting for chat to resume");
  fireEvent.click(within(inspector).getByRole("button", { name: "Copy continuation prompt" }));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith(CONTINUATION_PROMPT));
});

it("renders held custody neutrally and unknown issuer evidence as a decision", async () => {
  const completedFirst = card({
    item_key: "outcome:OUT-002",
    work_item_id: "OUT-002",
    title: "Completed outcome",
    stage: "completed",
    activity: { state: "idle", worker_role: null, started_at: null, task_id: null },
    readiness: readiness({ status: "complete", reason_code: "change-terminal", progress: "completed" }),
  });
  fixtureState.currentPortfolio = portfolio([group({ progress: null, items: [completedFirst, heldCard()] })]);
  const { unmount } = renderPage();

  let table = await screen.findByTestId("work-portfolio-table");
  const heldRow = within(table).getAllByText("Delivery foundation")[0].closest("[data-work-item]") as HTMLElement;
  expect(within(heldRow).getByText("Running", { selector: "[data-status-tone]" })).toBeInTheDocument();
  expect(heldRow).toHaveTextContent("Claimed by Builder");
  expect(table).not.toHaveTextContent(/Working|Checking|Repairing/);
  expect(within(table).queryByTestId("change-progress-change-alpha")).not.toBeInTheDocument();
  unmount();

  fixtureState.currentPortfolio = portfolio([
    group({ progress: "needs-decision", items: [completedFirst, heldCard("needs-decision")] }),
  ]);
  renderPage();
  table = await screen.findByTestId("work-portfolio-table");
  expect(within(table).getByTestId("change-progress-change-alpha")).toHaveTextContent("Needs your decision");
  expect(within(table).getByText("Needs your decision", { selector: "td [data-status-tone]" })).toBeInTheDocument();
});

it("offers Pause on every unfinished Change, including one whose step holds custody", async () => {
  fixtureState.currentPortfolio = portfolio([
    group({ items: [heldCard()], ...PAUSE_AVAILABLE }),
    group({
      change_id: "change-beta",
      title: "Quiescent change",
      progress: "waiting-for-chat",
      items: [continuationCard({ change_id: "change-beta" })],
      ...PAUSE_AVAILABLE,
    }),
  ]);
  renderPage();

  const held = await screen.findByTestId("change-pause-change-alpha");
  fireEvent.click(within(held).getByText("Pause"));
  const reason = await waitFor(() =>
    requirePresent(namedPdsHost(held, "p-input-text", "change-pause-reason-change-alpha")),
  );
  inputValue(reason, "Hold for review");
  const confirm = within(held).getByText("Confirm pause") as HTMLElement & { disabled: boolean };
  await waitFor(() => expect(confirm.disabled).toBe(false));
  fireEvent.click(confirm);
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/defer",
      method: "POST",
      body: { reason: "Hold for review", expected_frontier_digest: "a".repeat(64) },
    }),
  );
  expect(fixtureState.requests.some((request) => request.url === "/api/changes/change-beta/defer")).toBe(false);
  expect(within(screen.getByTestId("change-pause-change-beta")).getByText("Pause")).toBeInTheDocument();
});

it("shows a recorded Pause request with Resume while the started step drains", async () => {
  fixtureState.currentPortfolio = portfolio([group({ items: [heldCard()], ...PAUSE_REQUESTED })]);
  renderPage();

  const control = await screen.findByTestId("change-pause-change-alpha");
  expect(within(control).getByTestId("pause-requested-change-alpha")).toHaveTextContent("Pause requested");
  expect(within(control).queryByText("Pause")).not.toBeInTheDocument();
  fireEvent.click(within(control).getByText("Resume"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/resume",
      method: "POST",
      body: { expected_frontier_digest: "a".repeat(64) },
    }),
  );
  expect(fixtureState.requests.some((request) => request.url.endsWith("/defer"))).toBe(false);
});

it("resumes a paused Change from its group header", async () => {
  const paused = card({
    readiness: readiness({ status: "blocked", reason_code: "change-paused", progress: "paused" }),
    activity: { state: "idle", worker_role: null, started_at: null, task_id: null },
  });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "deferred", progress: "paused", items: [paused] })]);
  renderPage();

  const control = await screen.findByTestId("change-pause-change-alpha");
  expect(screen.getByTestId("change-progress-change-alpha")).toHaveTextContent("Paused");
  expect(within(control).queryByText("Pause")).not.toBeInTheDocument();
  fireEvent.click(within(control).getByText("Resume"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/resume",
      method: "POST",
      body: { expected_frontier_digest: "a".repeat(64) },
    }),
  );
});

it("shows a recorded Pause request on an outcome detail with Resume", async () => {
  const held = heldCard();
  fixtureState.currentPortfolio = portfolio([group({ items: [held], ...PAUSE_REQUESTED })]);
  fixtureState.currentDetail = detail({
    card: held,
    readiness: held.readiness,
    pause_available: false,
    pause_unavailable_reason: "pause-requested",
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("pause-requested-change-alpha")).toHaveTextContent("Pause requested");
  expect(within(inspector).queryByText("Pause")).not.toBeInTheDocument();
  expect(within(inspector).getByText("Resume")).toBeInTheDocument();
  expect(within(inspector).queryByText("Abandon Change")).not.toBeInTheDocument();
});

it.each(PAUSE_REFUSALS)("disables group Pause for Delivery reason %s", async (reason, message) => {
  fixtureState.currentPortfolio = portfolio([
    group({
      progress: null,
      items: [quietCard("ready", "ready")],
      pause_available: false,
      pause_unavailable_reason: reason,
    }),
  ]);
  renderPage();

  await expectPauseRefused(await screen.findByTestId("change-pause-change-alpha"), message);
});

it.each(PAUSE_REFUSALS)("disables detail Pause for Delivery reason %s", async (reason, message) => {
  const quiet = quietCard("ready", "ready");
  fixtureState.currentPortfolio = portfolio([group({ progress: null, items: [quiet], ...PAUSE_AVAILABLE })]);
  fixtureState.currentDetail = detail({
    card: quiet,
    readiness: quiet.readiness,
    pause_available: false,
    pause_unavailable_reason: reason,
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  await expectPauseRefused(within(inspector).getByTestId("change-pause-change-alpha"), message);
});

it("fails Pause closed when Delivery omits the availability field", async () => {
  fixtureState.currentPortfolio = portfolio([group({ progress: null, items: [quietCard("ready", "ready")] })]);
  renderPage();

  await expectPauseRefused(
    await screen.findByTestId("change-pause-change-alpha"),
    "Delivery cannot confirm this Change is idle, so Pause is unavailable.",
  );
});

it("renders Finalizer custody from Delivery when an unreadable retry ledger masks card readiness", async () => {
  const masked = quietCard("unavailable", "retry-ledger-unavailable");
  const finalizer = { pause_available: false, pause_unavailable_reason: "finalizer-custody" } as const;
  fixtureState.currentPortfolio = portfolio([group({ progress: null, items: [masked], ...finalizer })]);
  fixtureState.currentDetail = detail({ card: masked, readiness: masked.readiness, ...finalizer });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  await expectPauseRefused(
    within(inspector).getByTestId("change-pause-change-alpha"),
    "A Finalizer attempt holds this Change.",
  );
  const table = screen.getByTestId("work-portfolio-table");
  await expectPauseRefused(
    within(table).getByTestId("change-pause-change-alpha"),
    "A Finalizer attempt holds this Change.",
  );
});

it.each([
  ["blocked", "finalization-failed"],
  ["blocked", "retry-containment"],
  ["blocked", "retry-exhausted"],
] as const)("offers Pause for passive %s %s when Delivery accepts the defer intent", async (status, reason) => {
  const passive = quietCard(status, reason);
  fixtureState.currentPortfolio = portfolio([group({ progress: null, items: [passive], ...PAUSE_AVAILABLE })]);
  fixtureState.currentDetail = detail({ card: passive, readiness: passive.readiness, ...PAUSE_AVAILABLE });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expectPauseOffered(within(inspector).getByTestId("change-pause-change-alpha"));
  expectPauseOffered(within(screen.getByTestId("work-portfolio-table")).getByTestId("change-pause-change-alpha"));
});

it("keeps the Change-level Pause request when a filter hides the running item", async () => {
  const needsYou = group().items[1];
  fixtureState.currentPortfolio = portfolio([
    group({ progress: null, items: [heldCard(), needsYou], ...PAUSE_REQUESTED }),
  ]);
  renderPage();

  await screen.findByTestId("work-portfolio-table");
  const filter = screen.getByRole("button", { name: "Filter to 1 work item: Needs you" });
  fireEvent.click(filter);
  await waitFor(() => expect(filter).toHaveAttribute("aria-pressed", "true"));
  const table = screen.getByTestId("work-portfolio-table");
  expect(table).toHaveTextContent("User controls");
  expect(table).not.toHaveTextContent("Delivery foundation");

  const control = screen.getByTestId("change-pause-change-alpha");
  expect(within(control).getByTestId("pause-requested-change-alpha")).toHaveTextContent("Pause requested");
  expect(within(control).queryByText("Pause")).not.toBeInTheDocument();
});

it("keeps Change-level Pause available when a filter shows only a held-looking item", async () => {
  const needsYou = group().items[1];
  fixtureState.currentPortfolio = portfolio([
    group({ progress: null, items: [quietCard("blocked", "finalization-failed"), needsYou], ...PAUSE_AVAILABLE }),
  ]);
  renderPage();

  await screen.findByTestId("work-portfolio-table");
  const filter = screen.getByRole("button", { name: "Filter to 1 work item: Needs you" });
  fireEvent.click(filter);
  await waitFor(() => expect(filter).toHaveAttribute("aria-pressed", "true"));

  expectPauseOffered(screen.getByTestId("change-pause-change-alpha"));
});
