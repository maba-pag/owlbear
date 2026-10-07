import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import {
  card,
  detail,
  fixtureState,
  group,
  inputValue,
  installWorkPortfolioHarness,
  namedPdsHost,
  portfolio,
  publicationForChecks,
  readiness,
  renderPage,
  requirePresent,
  selectValue,
  situation,
} from "./workPortfolioHarness";

installWorkPortfolioHarness();

it("expires a backward preview when polling detects a newer snapshot", async () => {
  vi.useFakeTimers();
  try {
    fixtureState.currentDetail = detail({ card: card({ stage: "implementation" }) });
    renderPage("/delivery/change-alpha/outcome%3AOUT-001");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    fireEvent.click(screen.getByText("Administrative actions"));
    const stage = namedPdsHost(document.body, "p-select", "backward-stage");
    const reason = namedPdsHost(document.body, "p-input-text", "backward-reason");
    expect(stage).not.toBeNull();
    expect(reason).not.toBeNull();
    selectValue(requirePresent(stage), "planning");
    inputValue(requirePresent(reason), "Authority changed");
    fireEvent.click(screen.getByText("Review backward move"));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText("The following Outcomes will be reset:")).toBeInTheDocument();

    fixtureState.currentDetail = detail({
      ...fixtureState.currentDetail.item,
      snapshot_version: "b".repeat(64),
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });

    expect(screen.queryByText("The following Outcomes will be reset:")).not.toBeInTheDocument();
    expect(
      screen.getByText("The backward-move preview expired because Delivery changed. Review the move again."),
    ).toBeInTheDocument();
    expect(fixtureState.requests.some(({ url, method }) => method === "POST" && url.endsWith("/move-backward"))).toBe(
      false,
    );
  } finally {
    vi.useRealTimers();
  }
});

it("keeps backward confirmation open when the move fails", async () => {
  fixtureState.currentDetail = detail({ card: card({ stage: "implementation" }) });
  fixtureState.moveBackwardFailure = true;
  const { container } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByTestId("work-item-detail");

  fireEvent.click(screen.getByText("Administrative actions"));
  const [stage, reason] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, "p-select", "backward-stage"),
      namedPdsHost(container, "p-input-text", "backward-reason"),
    ];
    expect(elements.every(Boolean)).toBe(true);
    return elements as [Element, Element];
  });
  selectValue(stage, "planning");
  inputValue(reason, "Authority changed");
  fireEvent.click(screen.getByText("Review backward move"));
  await screen.findByText("The following Outcomes will be reset:");
  fireEvent.click(screen.getByText("Confirm backward move"));

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/outcomes/OUT-001/move-backward",
      method: "POST",
      body: {
        target: "planning",
        reason: "Authority changed",
        snapshot_version: "a".repeat(64),
      },
    }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "The Delivery frontier changed before the move was applied.",
  );
  expect(screen.getByText("The following Outcomes will be reset:")).toBeInTheDocument();
  expect(screen.getByRole("alertdialog")).toBeInTheDocument();
});

it("closes confirmation modals with Escape without performing the action", async () => {
  const { container } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByTestId("work-item-detail");

  fireEvent.click(screen.getByText("Administrative actions"));
  const [stage, reason] = await waitFor(() => {
    const elements = [
      namedPdsHost(container, "p-select", "backward-stage"),
      namedPdsHost(container, "p-input-text", "backward-reason"),
    ];
    expect(elements.every(Boolean)).toBe(true);
    return elements as [Element, Element];
  });
  selectValue(stage, "planning");
  inputValue(reason, "Authority changed");
  fireEvent.click(screen.getByText("Review backward move"));
  await screen.findByText("The following Outcomes will be reset:");

  fireEvent.keyDown(screen.getByText("Confirm backward move"), {
    key: "Escape",
  });

  await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
  expect(fixtureState.requests.some(({ url, method }) => method === "POST" && url.endsWith("/move-backward"))).toBe(
    false,
  );
});

it("closes the primary work-item flyout with Escape", async () => {
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  const detailView = await screen.findByTestId("work-item-detail");

  fireEvent.keyDown(detailView, { key: "Escape" });

  await waitFor(() => expect(screen.queryByTestId("work-item-detail")).not.toBeInTheDocument());
});

it("reconciles a pending publication checkpoint from the Change publication view", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    needs_headline: null,
    next_actor: "agent",
    next_step: "Reconcile the final checkpoint",
    activity: {
      state: "ready",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    publication_phase: "checkpoint-pending",
    progress: {
      kind: "publication",
      label: "Checkpoint pending",
      done: null,
      total: null,
    },
    action: {
      kind: "reconcile-checkpoint",
      label: "Publish checkpoint",
      command: null,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    promise: "Publish the reviewed Change.",
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: "checkpoint-pending",
      finalization_id: "f".repeat(64),
      finalized_head: "1".repeat(40),
      published_head: null,
      pending_checkpoint_head: "1".repeat(40),
      pending_checkpoint_triggers: ["finalization"],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "publication",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  const publicationRow = screen.getByLabelText("Change publication for Portfolio redesign");
  expect(
    within(publicationRow)
      .getAllByRole("term")
      .map((term) => term.textContent),
  ).toEqual(["Work", "State"]);
  expect(within(publicationRow).getAllByRole("definition")).toHaveLength(2);
  expect(inspector).toHaveTextContent("Checkpoint pending");
  expect(inspector).toHaveTextContent("Finalized head");
  expect(inspector).toHaveTextContent("1".repeat(40));
  expect(inspector).toHaveTextContent("Pending head:");
  expect(inspector).toHaveTextContent("Triggered by: finalization");
  expect(screen.getByLabelText("Delivery portfolio status")).toHaveTextContent("1Ready");
  expect(publicationRow).toHaveTextContent("Checkpoint pending");
  expect(
    within(publicationRow).getByText("Checkpoint pending", {
      selector: "[data-status-tone]",
    }),
  ).toHaveAttribute("data-status-tone", "active");
  fireEvent.click(within(inspector).getByText("Publish checkpoint"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/publication/reconcile",
      method: "POST",
      body: null,
    }),
  );
  expect(await screen.findByText("Publication checkpoint reconciled.")).toBeInTheDocument();
});

it("shows persisted checkpoint retry diagnostics and structured reconciliation errors", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    next_actor: "agent",
    next_step: "Reconcile the final checkpoint",
    activity: {
      state: "ready",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Checkpoint pending",
      done: null,
      total: null,
    },
    action: {
      kind: "reconcile-checkpoint",
      label: "Publish checkpoint",
      command: null,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: "checkpoint-pending",
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: ["verified-outcome"],
      pending_checkpoint_attempt_count: 2,
      pending_checkpoint_last_attempted_at: "2026-08-11T17:00:00+00:00",
      pending_checkpoint_error_code: "ERR_DELIVERY_CHECKPOINT_HEAD_MISSING",
      pending_checkpoint_error_detail: "Checkpoint publication is waiting for a reviewed Change head.",
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "publication",
      outcome_completed: 1,
      items: [publicationCard],
    }),
  ]);
  fixtureState.publicationReconciliationResult = {
    change_id: "change-alpha",
    attempted_head: null,
    reconciled: false,
    error_code: "ERR_DELIVERY_CHECKPOINT_HEAD_MISSING",
    error_detail: "Checkpoint publication is waiting for a reviewed Change head.",
    pending_checkpoint_attempt_count: 2,
    pending_checkpoint_last_attempted_at: "2026-08-11T17:00:00+00:00",
    pending_checkpoint_error_code: "ERR_DELIVERY_CHECKPOINT_HEAD_MISSING",
    pending_checkpoint_error_detail: "Checkpoint publication is waiting for a reviewed Change head.",
  };
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  const diagnostics = within(inspector).getByTestId("checkpoint-diagnostics");
  expect(diagnostics).toHaveTextContent("2 attempts recorded");
  expect(diagnostics).toHaveTextContent("Triggered by: verified-outcome");
  expect(diagnostics).toHaveTextContent("Last attempt: 2026-08-11T17:00:00+00:00");
  expect(diagnostics).toHaveTextContent("ERR_DELIVERY_CHECKPOINT_HEAD_MISSING");
  fireEvent.click(within(inspector).getByText("Publish checkpoint"));

  await waitFor(() =>
    expect(
      screen.getByText(
        "ERR_DELIVERY_CHECKPOINT_HEAD_MISSING: Checkpoint publication is waiting for a reviewed Change head.",
      ),
    ).toBeInTheDocument(),
  );
});

it("does not claim publication success when reconciliation remains incomplete", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    needs_headline: null,
    next_actor: "agent",
    next_step: "Reconcile the final checkpoint",
    activity: {
      state: "ready",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Checkpoint pending",
      done: null,
      total: null,
    },
    action: {
      kind: "reconcile-checkpoint",
      label: "Publish checkpoint",
      command: null,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    promise: "Publish the reviewed Change.",
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: "checkpoint-pending",
      finalization_id: "f".repeat(64),
      finalized_head: "1".repeat(40),
      published_head: null,
      pending_checkpoint_head: "1".repeat(40),
      pending_checkpoint_triggers: ["finalization"],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "publication",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  fixtureState.publicationReconciliationResult = {
    change_id: "change-alpha",
    attempted_head: null,
    reconciled: false,
    error_code: null,
    error_detail: null,
    pending_checkpoint_attempt_count: 0,
    pending_checkpoint_last_attempted_at: null,
    pending_checkpoint_error_code: null,
    pending_checkpoint_error_detail: null,
  };
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(inspector).getByText("Publish checkpoint"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/publication/reconcile",
      method: "POST",
      body: null,
    }),
  );
  await waitFor(() => expect(screen.queryByText("Publication checkpoint reconciled.")).not.toBeInTheDocument());
});

it("syncs the Change with the target and shows the latest sync receipt", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    needs_headline: null,
    next_actor: "agent",
    next_step: "Finalize the reviewed Change",
    activity: {
      state: "ready",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Ready for finalization",
      done: null,
      total: null,
    },
    action: {
      kind: "finalize",
      label: "Finalize Change",
      command: "/finalize-change change-alpha",
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    readiness: readiness({ progress: situation("ready-for-next-step", { target_sync: "required" }) }),
    promise: "Publish the reviewed Change.",
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: "ready-for-finalization",
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
      target_sync: {
        receipt_id: "a".repeat(64),
        operation_id: "sync-portfolio-change",
        target_branch: "main",
        expected_target: "1".repeat(40),
        target_head: "1".repeat(40),
        change_head_before: "2".repeat(40),
        merged_head: "3".repeat(40),
        merge_commit: true,
        review_required: false,
      },
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "finalization",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent(`Target head${"1".repeat(40)}`);
  expect(inspector).toHaveTextContent(`Target-sync merge result${"3".repeat(40)}`);
  expect(inspector).toHaveTextContent("Last target sync: main (merge commit)");
  fireEvent.click(within(inspector).getByText("Merge latest target into Change"));
  fireEvent.click(screen.getByText("Confirm target update"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/target/sync",
      method: "POST",
      body: { operation_id: expect.stringMatching(/^cockpit-target-sync-/) },
    }),
  );
  expect(await screen.findByText("Target synchronized with the integration target.")).toBeInTheDocument();
});

it("shows publication history and keeps ordinary attention remedies available", async () => {
  const attentionId = "a".repeat(64);
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "you",
    needs_headline: "Change attention requires resolution",
    next_actor: "you",
    next_step: "Resolve publication attention",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Resolve publication attention",
      done: null,
      total: null,
    },
    action: {
      kind: "resolve-attention",
      label: "Resolve publication attention",
      command: null,
      attention_id: attentionId,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    promise: "Resolve the provider evidence before continuing.",
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: "awaiting-merge",
      finalization_id: "b".repeat(64),
      finalized_head: "1".repeat(40),
      published_head: "1".repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: "owlbear/example",
      pull_request_number: 42,
      pull_request_head: "1".repeat(40),
      accepted_merge_commit: null,
      merged_at: null,
      attention: {
        disposition_id: attentionId,
        kind: "publication-attention",
        change_id: "change-alpha",
        entered_from: "awaiting-merge",
        recorded_at: "2026-08-11T16:00:00Z",
        diagnostics: ["Provider publication needs reconciliation."],
      },
      publication_generations: [
        {
          repository: "owlbear/example",
          number: 41,
          node_id: "PR_example_41",
          head_sha: "2".repeat(40),
        },
        {
          repository: "owlbear/example",
          number: 42,
          node_id: "PR_example_42",
          head_sha: "1".repeat(40),
        },
      ],
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "publication",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent("Publication history");
  expect(inspector).toHaveTextContent(`Generation 1: owlbear/example #41 / ${"2".repeat(40)}`);
  expect(inspector).toHaveTextContent(`Generation 2: owlbear/example #42 / ${"1".repeat(40)}`);
  expect(within(inspector).getAllByText("Resolve publication attention")).not.toHaveLength(0);
  expect(within(inspector).getByTestId("publication-supersede")).toBeInTheDocument();
  const evidence = within(inspector).getByText("Publication evidence", { selector: "summary" }).closest("details");
  expect(evidence).not.toHaveAttribute("open");
  expect(within(inspector).getByTestId("publication-supersede")).toBeVisible();

  fireEvent.click(within(inspector).getByTestId("publication-supersede"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/publication/supersede",
      method: "POST",
      body: {
        operation_id: expect.stringMatching(/^cockpit-publication-supersede-/),
      },
    }),
  );
  expect(await screen.findByText("Publication superseded.")).toBeInTheDocument();
});

it("reuses a supersession operation identity after a retry-safe failure", async () => {
  const attentionId = "a".repeat(64);
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "you",
    needs_headline: "Change attention requires resolution",
    next_actor: "you",
    next_step: "Resolve publication attention",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Resolve publication attention",
      done: null,
      total: null,
    },
    action: {
      kind: "resolve-attention",
      label: "Resolve publication attention",
      command: null,
      attention_id: attentionId,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: "awaiting-merge",
      finalization_id: "b".repeat(64),
      finalized_head: "1".repeat(40),
      published_head: "1".repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: "owlbear/example",
      pull_request_number: 42,
      pull_request_head: "1".repeat(40),
      accepted_merge_commit: null,
      merged_at: null,
      attention: {
        disposition_id: attentionId,
        kind: "publication-attention",
        change_id: "change-alpha",
        entered_from: "awaiting-merge",
        recorded_at: "2026-08-11T16:00:00Z",
        diagnostics: ["Provider publication needs reconciliation."],
      },
      publication_generations: [
        {
          repository: "owlbear/example",
          number: 42,
          node_id: "PR_example_42",
          head_sha: "1".repeat(40),
        },
      ],
    },
  });
  fixtureState.supersedeFailuresRemaining = 1;
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "publication",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  renderPage("/delivery/change-alpha/publication");

  const supersede = await screen.findByTestId("publication-supersede");
  fireEvent.click(supersede);
  await waitFor(() => expect(screen.getByText("ERR_PROVIDER_UNAVAILABLE")).toBeInTheDocument());
  fireEvent.click(supersede);
  await waitFor(() =>
    expect(
      fixtureState.requests.filter(({ url, method }) => method === "POST" && url.endsWith("/publication/supersede")),
    ).toHaveLength(2),
  );

  const supersessionRequests = fixtureState.requests.filter(
    ({ url, method }) => method === "POST" && url.endsWith("/publication/supersede"),
  );
  expect(supersessionRequests[0].body).toEqual({
    operation_id: expect.stringMatching(/^cockpit-publication-supersede-/),
  });
  expect(supersessionRequests[1].body).toEqual(supersessionRequests[0].body);
});

it("offers explicit exits for a preserved target-sync conflict", async () => {
  const dispositionId = "d".repeat(64);
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "you",
    needs_headline: "Target sync conflict",
    next_actor: "you",
    next_step: "Choose an explicit target-sync conflict exit",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Finalization invalidated",
      done: null,
      total: null,
    },
    action: {
      kind: "resolve-attention",
      label: "Resolve attention",
      command: "/resolve-target-conflict change-alpha",
      attention_id: dispositionId,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    promise: "Publish the reviewed Change.",
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: "finalization-invalidated",
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: "5".repeat(40),
      invalidated_observed_head: "4".repeat(40),
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
      attention: {
        disposition_id: dispositionId,
        kind: "publication-attention",
        change_id: "change-alpha",
        entered_from: "finalization",
        recorded_at: "2026-08-12T12:00:00Z",
        diagnostics: ["target-sync-operation:cockpit-target-sync-conflict"],
      },
      target_sync_conflict: {
        conflict_id: "e".repeat(64),
        operation_id: "cockpit-target-sync-conflict",
        target_head: "4".repeat(40),
        change_head_before: "5".repeat(40),
        conflict_paths: ["src/app.py", "tests/test_app.py"],
      },
      publication_generations: [
        {
          repository: "owlbear/example",
          number: 42,
          node_id: "PR_example_42",
          head_sha: "1".repeat(40),
        },
      ],
    },
  });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "publication", items: [publicationCard] })]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent("Target sync conflict");
  expect(inspector).toHaveTextContent("src/app.py");
  expect(within(inspector).getByLabelText("Copy command /resolve-target-conflict change-alpha")).toBeInTheDocument();
  expect(within(inspector).queryByText("Resolve attention")).toBeNull();
  expect(within(inspector).queryByTestId("publication-supersede")).toBeNull();

  fireEvent.click(screen.getByTestId("target-sync-conflict-abort"));
  fireEvent.click(screen.getByText("Confirm abort"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/target/conflict/abort",
      method: "POST",
      body: {
        expected_disposition_id: dispositionId,
        target_head: "4".repeat(40),
        operation_id: "cockpit-target-sync-conflict",
      },
    }),
  );
  expect(await screen.findByText("Target sync conflict aborted.")).toBeInTheDocument();

  fireEvent.click(screen.getByTestId("target-sync-conflict-resolve"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/target/conflict/resolve",
      method: "POST",
      body: {
        expected_disposition_id: dispositionId,
        target_head: "4".repeat(40),
        operation_id: "cockpit-target-sync-conflict",
      },
    }),
  );
});

it("keeps invalidated finalization heads distinct and offers re-finalization", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    needs_headline: "Finalization invalidated",
    next_actor: "agent",
    next_step: "Re-finalize the current Change head",
    activity: {
      state: "ready",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Head drift observed",
      done: null,
      total: null,
    },
    action: {
      kind: "finalize",
      label: "Re-finalize Change",
      command: null,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    promise: "Publish the reviewed Change.",
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: "finalization-invalidated",
      finalization_id: null,
      finalized_head: null,
      published_head: null,
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: "1".repeat(40),
      invalidated_observed_head: "2".repeat(40),
      repository: null,
      pull_request_number: null,
      pull_request_head: null,
      accepted_merge_commit: null,
      merged_at: null,
    },
  });
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByRole("region", { name: "Finalization invalidated" })).toBeInTheDocument();
  expect(inspector).toHaveTextContent(`Expected head${"1".repeat(40)}`);
  expect(inspector).toHaveTextContent(`Observed head${"2".repeat(40)}`);
  expect(inspector).toHaveTextContent("Next: Re-finalize the current Change head");
  expect(inspector.querySelector("[data-section-tone]")).toHaveAttribute("data-section-tone", "warning");
});

it("shows GitHub merge as user-owned work with observation as the only Cockpit control", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "you",
    needs_headline: "Merge pull request in GitHub",
    next_actor: "you",
    next_step: "Merge pull request in GitHub",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Awaiting merge in GitHub",
      done: null,
      total: null,
    },
    action: {
      kind: "observe-acceptance",
      label: "Check merge status",
      command: null,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    promise: "Publish the reviewed Change.",
    acceptance: [],
    commitments: [],
    tasks: [],
    publication: {
      phase: "awaiting-merge",
      finalization_id: "f".repeat(64),
      finalized_head: "1".repeat(40),
      published_head: "1".repeat(40),
      pending_checkpoint_head: null,
      pending_checkpoint_triggers: [],
      invalidated_expected_head: null,
      invalidated_observed_head: null,
      repository: "owlbear/example",
      pull_request_number: 42,
      pull_request_head: "1".repeat(40),
      accepted_merge_commit: null,
      merged_at: null,
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "awaiting-merge",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByRole("region", { name: "Awaiting merge in GitHub" })).toBeInTheDocument();
  expect(inspector).toHaveTextContent("owlbear/example");
  expect(inspector).toHaveTextContent("42");
  expect(within(inspector).queryByText(/merge now/i)).not.toBeInTheDocument();
  fireEvent.click(within(inspector).getByText("Check merge status"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/acceptance/observe",
      method: "POST",
      body: null,
    }),
  );

  fixtureState.acceptanceObservationFailure = true;
  fireEvent.click(within(inspector).getByText("Check merge status"));
  const waiting = await within(inspector).findByRole("status");
  expect(waiting).toHaveTextContent("ERR_DELIVERY_ACCEPTANCE_WAITING");
  expect(within(inspector).queryByRole("alert")).not.toBeInTheDocument();
});

it("keeps conflict guidance and merge-status control for a ready conflicted pull request", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "you",
    needs_headline: "Pull request has merge conflicts",
    next_actor: "you",
    next_step: "Resolve pull-request conflicts before continuing",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Pull request conflicts detected",
      done: null,
      total: null,
    },
    action: {
      kind: "observe-acceptance",
      label: "Check merge status",
      command: "/resolve-target-conflict change-alpha",
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: {
      ...publicationForChecks("awaiting-merge"),
      mergeable: false,
      merge_state_status: "dirty",
      mergeability_observed_at: "2026-09-04T10:00:00Z",
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "awaiting-merge",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByLabelText("Copy command /resolve-target-conflict change-alpha")).toBeInTheDocument();
  fireEvent.click(within(inspector).getByText("Check merge status"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/acceptance/observe",
      method: "POST",
      body: null,
    }),
  );
});
