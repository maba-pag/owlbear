import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import {
  abandonedRecord,
  card,
  detail,
  fixtureState,
  group,
  inputValue,
  installWorkPortfolioHarness,
  namedPdsHost,
  portfolio,
  publicationCardForChecks,
  publicationForChecks,
  renderPage,
  requirePresent,
} from "./workPortfolioHarness";

installWorkPortfolioHarness();

it("shows Change attention diagnostics and resolves the selected disposition", async () => {
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
    next_step: "Resolve acceptance attention",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Resolve acceptance attention",
      done: null,
      total: null,
    },
    action: {
      kind: "resolve-attention",
      label: "Resolve acceptance attention",
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
      attention: {
        disposition_id: attentionId,
        kind: "acceptance-attention",
        change_id: "change-alpha",
        entered_from: "awaiting-merge",
        recorded_at: "2026-08-11T16:00:00Z",
        diagnostics: ["Pull request was closed without a merge commit."],
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
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "acceptance",
      outcome_completed: 0,
      items: [publicationCard],
    }),
  ]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent("Change attention");
  expect(inspector).toHaveTextContent("Pull request was closed without a merge commit.");
  expect(inspector).toHaveTextContent(`Disposition: ${attentionId}`);
  expect(within(inspector).queryByTestId("publication-supersede")).toBeNull();
  fireEvent.click(requirePresent(within(inspector).getAllByText("Resolve acceptance attention").at(-1)));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/attention/resolve",
      method: "POST",
      body: {
        expected_disposition_id: attentionId,
        expected_frontier_digest: "a".repeat(64),
      },
    }),
  );
  expect(await screen.findByText("Change attention resolved.")).toBeInTheDocument();
});

it("posts reasoned Change dispositions and resumes a deferred Change", async () => {
  const activeCard = card({
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
    card: activeCard,
    promise: "Publish the reviewed Change.",
    acceptance: [],
    commitments: [],
    tasks: [],
    pause_available: true,
    pause_unavailable_reason: null,
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
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "finalization",
      outcome_completed: 2,
      items: [activeCard],
    }),
  ]);
  const initialRender = renderPage("/delivery/change-alpha/publication");
  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).queryByText("Defer Change")).not.toBeInTheDocument();
  fireEvent.click(within(inspector).getByText("Pause"));
  const pauseReason = await waitFor(() => {
    const element = namedPdsHost(inspector, "p-input-text", "change-pause-reason");
    expect(element).not.toBeNull();
    return requirePresent(element);
  });
  inputValue(pauseReason, "Wait for user review");
  const pause = within(inspector).getByText("Confirm pause") as HTMLElement & {
    disabled: boolean;
  };
  await waitFor(() => expect(pause.disabled).toBe(false));
  fireEvent.click(pause);
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/defer",
      method: "POST",
      body: {
        reason: "Wait for user review",
        expected_frontier_digest: "a".repeat(64),
      },
    }),
  );
  const reason = await waitFor(() => {
    const element = namedPdsHost(inspector, "p-input-text", "change-disposition-reason");
    expect(element).not.toBeNull();
    return requirePresent(element);
  });

  inputValue(reason, "User stopped the Change");
  fireEvent.change(
    reason,
    new CustomEvent("change", {
      detail: { value: "User stopped the Change" },
      bubbles: true,
    }),
  );
  fireEvent.click(within(inspector).getByText("Abandon Change"));
  fireEvent.click(await screen.findByText("Confirm abandon Change"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/abandon",
      method: "POST",
      body: {
        confirmed_abandonment: true,
        reason: "User stopped the Change",
        expected_frontier_digest: "a".repeat(64),
      },
    }),
  );

  initialRender.unmount();
  const deferredCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "you",
    needs_headline: "Change is paused",
    next_actor: "you",
    next_step: "Resume the paused Change",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Change paused",
      done: null,
      total: null,
    },
    action: { kind: "resume-change", label: "Resume Change", command: null },
  });
  fixtureState.currentDetail = detail({
    card: deferredCard,
    publication: {
      phase: "deferred",
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
    },
  });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "deferred", items: [deferredCard] })]);
  renderPage("/delivery/change-alpha/publication");
  const deferredInspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(deferredInspector).getByText("Resume Change"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/resume",
      method: "POST",
      body: { expected_frontier_digest: "a".repeat(64) },
    }),
  );
});

it("keeps the successful Change abandonment notice until it is dismissed", async () => {
  const publicationCard = publicationCardForChecks({
    next_step: "Finalize the reviewed Change",
    progress: {
      kind: "publication",
      label: "Ready for finalization",
      done: null,
      total: null,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks("ready-for-finalization"),
  });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "finalization", items: [publicationCard] })]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  const reason = await waitFor(() => {
    const element = namedPdsHost(inspector, "p-input-text", "change-disposition-reason");
    expect(element).not.toBeNull();
    return requirePresent(element);
  });
  inputValue(reason, "User stopped the Change");
  fireEvent.change(
    reason,
    new CustomEvent("change", {
      detail: { value: "User stopped the Change" },
      bubbles: true,
    }),
  );
  fireEvent.click(within(inspector).getByText("Abandon Change"));

  fixtureState.currentPortfolio = portfolio([]);
  fireEvent.click(await screen.findByText("Confirm abandon Change"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/abandon",
      method: "POST",
      body: {
        confirmed_abandonment: true,
        reason: "User stopped the Change",
        expected_frontier_digest: "a".repeat(64),
      },
    }),
  );

  await waitFor(() => expect(screen.getByRole("button", { name: "Change history", exact: true })).toHaveFocus());
  const noticeText = "Portfolio redesign was abandoned and is now in Change history.";
  const noticeCopy = await screen.findByText(noticeText);
  const notice = requirePresent(noticeCopy.closest('[role="status"]'));
  expect(screen.queryByTestId("work-item-detail")).not.toBeInTheDocument();

  const getCountBeforeCurrentView = fixtureState.requests.filter((request) => request.method === "GET").length;
  fireEvent.click(screen.getByRole("button", { name: "Current delivery", exact: true }));
  await waitFor(() =>
    expect(fixtureState.requests.filter((request) => request.method === "GET").length).toBeGreaterThan(
      getCountBeforeCurrentView,
    ),
  );
  expect(screen.getByText(noticeText)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Change history", exact: true }));
  expect(screen.getByText(noticeText)).toBeInTheDocument();

  const dismissLabel = within(notice).getByText("Dismiss");
  const dismissHost = requirePresent(dismissLabel.closest("p-button"));
  const dismissButton = await waitFor(() => {
    const button = dismissHost.shadowRoot?.querySelector("button");
    expect(button).not.toBeNull();
    return requirePresent(button);
  });
  expect(dismissButton.getAttribute("aria-label") ?? dismissButton.textContent).toMatch(
    /dismiss abandonment confirmation/i,
  );
  dismissButton.focus();
  expect(dismissHost.shadowRoot?.activeElement).toBe(dismissButton);
  expect(document.activeElement).toBe(dismissHost);
  dismissButton.click();
  await waitFor(() => expect(screen.queryByText(noticeText)).not.toBeInTheDocument());
});

it("keeps Change abandonment confirmation open when abandonment fails", async () => {
  const publicationCard = publicationCardForChecks({
    next_step: "Finalize the reviewed Change",
    progress: {
      kind: "publication",
      label: "Ready for finalization",
      done: null,
      total: null,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks("ready-for-finalization"),
  });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "finalization", items: [publicationCard] })]);
  fixtureState.mutationFailurePath = "/abandon";
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  const reason = await waitFor(() => {
    const element = namedPdsHost(inspector, "p-input-text", "change-disposition-reason");
    expect(element).not.toBeNull();
    return requirePresent(element);
  });
  inputValue(reason, "User stopped the Change");
  fireEvent.change(
    reason,
    new CustomEvent("change", {
      detail: { value: "User stopped the Change" },
      bubbles: true,
    }),
  );
  fireEvent.click(within(inspector).getByText("Abandon Change"));
  fireEvent.click(await screen.findByText("Confirm abandon Change"));

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/abandon",
      method: "POST",
      body: {
        confirmed_abandonment: true,
        reason: "User stopped the Change",
        expected_frontier_digest: "a".repeat(64),
      },
    }),
  );
  const dialog = screen.getByRole("alertdialog");
  expect(within(dialog).getByRole("alert")).toHaveTextContent(
    "The Delivery operation was rejected while the confirmation was open.",
  );
  expect(within(dialog).getByText("Confirm Change abandonment")).toBeInTheDocument();
  expect(screen.queryByText(/is now in Change history/)).not.toBeInTheDocument();
});

it("does not show Change disposition controls on an Outcome detail", async () => {
  fixtureState.currentDetail = detail();
  fixtureState.currentPortfolio = portfolio();
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).queryByText("Defer Change")).not.toBeInTheDocument();
  expect(within(inspector).queryByText("Abandon Change")).not.toBeInTheDocument();
});

it("does not show Change disposition controls for an abandoned Change", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    needs_headline: null,
    next_actor: "none",
    next_step: "Change abandoned",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Change abandoned",
      done: null,
      total: null,
    },
    action: { kind: "none", label: null, command: null },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: "abandoned",
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
    },
  });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "abandoned", items: [publicationCard] })]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).queryByText("Defer Change")).not.toBeInTheDocument();
  expect(within(inspector).queryByText("Abandon Change")).not.toBeInTheDocument();
});

it("confirms discard and cleanup for an abandoned target-sync conflict from Change detail", async () => {
  const targetHead = "e".repeat(40);
  const operationId = "cockpit-target-sync-detail-test";
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    needs_headline: null,
    next_actor: "none",
    next_step: "Change abandoned",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Change abandoned",
      done: null,
      total: null,
    },
    action: { kind: "none", label: null, command: null },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: "abandoned",
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
      target_sync_conflict: {
        conflict_id: "f".repeat(64),
        operation_id: operationId,
        target_head: targetHead,
        change_head_before: "d".repeat(40),
        conflict_paths: ["src/app.py"],
      },
      worktree_cleanup: {
        eligible: true,
        blocked_reason: null,
        completion_id: null,
      },
    },
  });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "abandoned", items: [publicationCard] })]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(inspector).getByText("Discard merge and clean worktree"));
  fireEvent.click(await screen.findByText("Confirm discard and cleanup"));

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/worktree/cleanup/abandoned/target-sync-discard",
      method: "POST",
      body: {
        confirmed_discard: true,
        expected_target_head: targetHead,
        expected_operation_id: operationId,
      },
    }),
  );
  expect(
    await screen.findByText("Target merge discarded and abandoned Change worktree cleaned up."),
  ).toBeInTheDocument();
});

it("confirms and cleans an eligible abandoned Change from Change history", async () => {
  const abandoned = abandonedRecord();
  fixtureState.completedRecords = [abandoned];
  renderPage();

  fireEvent.click(screen.getByText("Change history"));
  const record = await screen.findByTestId("completed-change-record");
  fireEvent.click(within(record).getByRole("button", { name: `Inspect ${abandoned.title}` }));
  const detailView = await screen.findByTestId("completed-change-detail");
  fireEvent.click(within(detailView).getByText("Clean abandoned worktree"));
  fireEvent.click(await screen.findByText("Confirm cleanup"));

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/worktree/cleanup/abandoned",
      method: "POST",
      body: null,
    }),
  );
  expect(await screen.findByText("Abandoned Change worktree cleaned up.")).toBeInTheDocument();
});

it("keeps abandoned history cleanup confirmation open when cleanup fails", async () => {
  const abandoned = abandonedRecord();
  fixtureState.completedRecords = [abandoned];
  fixtureState.mutationFailurePath = "/worktree/cleanup/abandoned";
  renderPage();

  fireEvent.click(screen.getByText("Change history"));
  const record = await screen.findByTestId("completed-change-record");
  fireEvent.click(within(record).getByRole("button", { name: `Inspect ${abandoned.title}` }));
  const detailView = await screen.findByTestId("completed-change-detail");
  fireEvent.click(within(detailView).getByText("Clean abandoned worktree"));
  fireEvent.click(await screen.findByText("Confirm cleanup"));

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/worktree/cleanup/abandoned",
      method: "POST",
      body: null,
    }),
  );
  const dialog = screen.getByRole("alertdialog");
  expect(within(dialog).getByRole("alert")).toHaveTextContent(
    "The Delivery operation was rejected while the confirmation was open.",
  );
  expect(within(dialog).getByText("Clean abandoned worktree")).toBeInTheDocument();
});

it("confirms discard and cleanup for an abandoned target-sync conflict from Change history", async () => {
  const abandoned = abandonedRecord({
    target_sync_conflict: true,
    target_sync_conflict_target_head: "e".repeat(40),
    target_sync_conflict_operation_id: "cockpit-target-sync-test",
    cleanup_available: true,
  });
  fixtureState.completedRecords = [abandoned];
  renderPage();

  fireEvent.click(screen.getByText("Change history"));
  const record = await screen.findByTestId("completed-change-record");
  fireEvent.click(within(record).getByRole("button", { name: `Inspect ${abandoned.title}` }));
  const detailView = await screen.findByTestId("completed-change-detail");
  fireEvent.click(within(detailView).getByText("Discard conflict and clean worktree"));
  fireEvent.click(await screen.findByText("Confirm cleanup"));

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/worktree/cleanup/abandoned/target-sync-discard",
      method: "POST",
      body: {
        confirmed_discard: true,
        expected_target_head: "e".repeat(40),
        expected_operation_id: "cockpit-target-sync-test",
      },
    }),
  );
  expect(
    await screen.findByText("Target merge discarded and abandoned Change worktree cleaned up."),
  ).toBeInTheDocument();
});

it("cleans an eligible completed Change worktree with its exact completion identity", async () => {
  const completionId = "e".repeat(64);
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    needs_headline: null,
    next_actor: "none",
    next_step: "Acceptance observed",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Acceptance observed",
      done: null,
      total: null,
    },
    action: { kind: "none", label: null, command: null },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: "acceptance-observed",
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
      accepted_merge_commit: "2".repeat(40),
      merged_at: "2026-08-11T13:00:00Z",
      worktree_cleanup: {
        eligible: true,
        blocked_reason: null,
        completion_id: completionId,
      },
    },
  });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "acceptance", items: [publicationCard] })]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(inspector).getByText("Clean completed worktree"));
  fireEvent.click(await screen.findByText("Confirm clean completed worktree"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/worktree/cleanup/completed",
      method: "POST",
      body: { completion_id: completionId },
    }),
  );
  expect(await screen.findByText("Completed Change worktree cleaned up.")).toBeInTheDocument();
});

it("confirms and recovers a missing Change worktree from its exact reviewed head", async () => {
  const reviewedHead = "9".repeat(40);
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    needs_headline: null,
    next_actor: "none",
    next_step: "Change abandoned",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Change abandoned",
      done: null,
      total: null,
    },
    action: { kind: "none", label: null, command: null },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: "abandoned",
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
      worktree_recovery: {
        eligible: true,
        blocked_reason: null,
        recovery_reviewed_head: reviewedHead,
      },
    },
  });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "abandoned", items: [publicationCard] })]);
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByText(`Reviewed head: ${reviewedHead}`)).toBeInTheDocument();
  fireEvent.click(within(inspector).getByText("Recover missing worktree"));
  fireEvent.click(await screen.findByText("Confirm worktree recovery"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/worktree/recover",
      method: "POST",
      body: { confirmed_recovery: true, recovery_reviewed_head: reviewedHead },
    }),
  );
  expect(await screen.findByText("Missing Change worktree recovered.")).toBeInTheDocument();
});

it("keeps missing worktree recovery confirmation open when recovery fails", async () => {
  const reviewedHead = "1".repeat(40);
  const publicationCard = publicationCardForChecks({
    next_step: "Change abandoned",
    progress: {
      kind: "publication",
      label: "Change abandoned",
      done: null,
      total: null,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: {
      phase: "abandoned",
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
      worktree_recovery: {
        eligible: true,
        blocked_reason: null,
        recovery_reviewed_head: reviewedHead,
      },
    },
  });
  fixtureState.currentPortfolio = portfolio([group({ lifecycle: "abandoned", items: [publicationCard] })]);
  fixtureState.mutationFailurePath = "/worktree/recover";
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(inspector).getByText("Recover missing worktree"));
  fireEvent.click(await screen.findByText("Confirm worktree recovery"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/worktree/recover",
      method: "POST",
      body: { confirmed_recovery: true, recovery_reviewed_head: reviewedHead },
    }),
  );
  const dialog = screen.getByRole("alertdialog");
  expect(within(dialog).getByRole("alert")).toHaveTextContent(
    "The Delivery operation was rejected while the confirmation was open.",
  );
  expect(within(dialog).getByText("Recover missing worktree")).toBeInTheDocument();
});

it("uses the Complete status tag without leaking the internal Stage field", async () => {
  fixtureState.currentDetail = detail({
    card: card({
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
        label: "1 of 1 Delivery tasks reviewed",
        done: 1,
        total: 1,
      },
    }),
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent("Complete");
  expect(inspector).not.toHaveTextContent("Completed");
  expect(inspector).not.toHaveTextContent("Stage");
  expect(inspector).toHaveTextContent("Progress1 of 1 Delivery tasks reviewed");
  expect(inspector).not.toHaveTextContent("Complete — no action needed");
});

it("presents a draft pull request as publication work", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    next_actor: "agent",
    next_step: "Mark the pull request ready through Delivery",
    activity: {
      state: "ready",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    publication_phase: "pull-request-draft",
    progress: {
      kind: "publication",
      label: "Delivery ready state not recorded",
      done: null,
      total: null,
    },
    action: {
      kind: "mark-ready",
      label: "Make PR ready for review",
      command: null,
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "publication",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  renderPage();

  const table = await screen.findByTestId("work-portfolio-table");
  expect(table).toHaveTextContent("Change: Portfolio redesign");
  expect(table).toHaveTextContent("Delivery ready state not recorded");
  expect(table).toHaveTextContent("Make PR ready for review");
  const publicationRow = screen.getByLabelText("Change publication for Portfolio redesign");
  expect(publicationRow.querySelector("[data-status-tone]")).toHaveTextContent("Delivery ready state not recorded");
  const readyLink = within(table).getByText("Make PR ready for review").closest("p-link-pure") as HTMLElement & {
    href: string;
  };
  expect(readyLink.href).toBe("/delivery/change-alpha/publication");
  expect(screen.getByLabelText("Delivery portfolio status")).not.toHaveTextContent("need you");
});

it("warns before making a conflicted pull request ready and offers the resolution prompt", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "you",
    needs_headline: "Pull request has merge conflicts",
    next_actor: "you",
    next_step: "Resolve pull-request conflicts before making it ready",
    activity: {
      state: "idle",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    publication_phase: "pull-request-draft",
    progress: {
      kind: "publication",
      label: "Pull request conflicts detected",
      done: null,
      total: null,
    },
    action: {
      kind: "mark-ready",
      label: "Make PR ready for review",
      command: "/resolve-target-conflict change-alpha",
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: {
      ...publicationForChecks("pull-request-draft"),
      mergeable: false,
      merge_state_status: "dirty",
      mergeability_observed_at: "2026-09-04T10:00:00Z",
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
  expect(within(inspector).getByLabelText("Copy command /resolve-target-conflict change-alpha")).toBeInTheDocument();
  fireEvent.click(within(inspector).getByText("Make PR ready for review"));

  const dialog = await screen.findByRole("alertdialog");
  expect(dialog).toHaveTextContent("GitHub reports conflicts with the integration target.");
  expect(dialog).toHaveTextContent("Making the pull request ready will not resolve them");
  expect(dialog).toHaveTextContent("/resolve-target-conflict change-alpha");
  expect(fixtureState.requests.some(({ url, method }) => url.endsWith("/publication/ready") && method === "POST")).toBe(
    false,
  );

  fireEvent.click(within(dialog).getByText("Keep PR in draft"));
  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();

  fireEvent.click(within(inspector).getByText("Make PR ready for review"));
  fireEvent.click(await screen.findByText("Make PR ready anyway"));
  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/publication/ready",
      method: "POST",
      body: null,
    }),
  );
});

it("keeps check observation discoverable but unavailable for a draft", async () => {
  const publicationCard = publicationCardForChecks();
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks("pull-request-draft"),
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
  const observe = within(inspector).getByTestId("publication-checks-observe") as HTMLElement & { disabled: boolean };
  expect(observe).toBeInTheDocument();
  expect(observe.disabled).toBe(true);
  expect(within(inspector).getByTestId("publication-checks-draft-guidance")).toHaveTextContent(
    "You can observe check results here once this pull request is ready for review.",
  );
  expect(within(inspector).queryByTestId("publication-checks-status")).not.toBeInTheDocument();

  fireEvent.click(observe);
  expect(
    fixtureState.requests.filter(
      ({ url, method }) => url === "/api/changes/change-alpha/publication/checks/observe" && method === "POST",
    ),
  ).toHaveLength(0);
});

it("does not offer publication-check observation outside draft and awaiting-merge phases", async () => {
  const publicationCard = publicationCardForChecks({
    progress: {
      kind: "publication",
      label: "Ready for finalization",
      done: null,
      total: null,
    },
  });
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks("ready-for-finalization"),
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
  expect(within(inspector).queryByTestId("publication-checks-observe")).not.toBeInTheDocument();
});

it("clears publication-check results when the polled published head changes", async () => {
  vi.useFakeTimers();
  try {
    const publicationCard = publicationCardForChecks();
    fixtureState.currentDetail = detail({
      card: publicationCard,
      publication: publicationForChecks("awaiting-merge"),
    });
    fixtureState.currentPortfolio = portfolio([
      group({
        lifecycle: "awaiting-merge",
        outcome_completed: 2,
        items: [publicationCard],
      }),
    ]);
    renderPage("/delivery/change-alpha/publication");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    const inspector = screen.getByTestId("work-item-detail");
    fireEvent.click(within(inspector).getByTestId("publication-checks-observe"));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(within(inspector).getByText("Unit tests")).toBeInTheDocument();

    fixtureState.currentDetail = detail({
      card: publicationCard,
      publication: publicationForChecks("awaiting-merge", "2".repeat(40)),
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    expect(within(inspector).getByTestId("publication-checks-status")).toHaveTextContent(
      "Previous check results were cleared",
    );
    expect(within(inspector).queryByText("Unit tests")).not.toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
});

it("keeps observed publication checks visible across a phase change with the same head", async () => {
  vi.useFakeTimers();
  try {
    const publicationCard = publicationCardForChecks();
    fixtureState.currentDetail = detail({
      card: publicationCard,
      publication: publicationForChecks("awaiting-merge"),
    });
    fixtureState.currentPortfolio = portfolio([
      group({
        lifecycle: "awaiting-merge",
        outcome_completed: 2,
        items: [publicationCard],
      }),
    ]);
    renderPage("/delivery/change-alpha/publication");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    const inspector = screen.getByTestId("work-item-detail");
    fireEvent.click(within(inspector).getByTestId("publication-checks-observe"));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(within(inspector).getByText("Unit tests")).toBeInTheDocument();

    fixtureState.currentDetail = detail({
      card: publicationCard,
      publication: {
        ...publicationForChecks("awaiting-merge"),
        phase: "checkpoint-pending",
        pending_checkpoint_head: "1".repeat(40),
        pending_checkpoint_triggers: ["finalization"],
      },
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    expect(within(inspector).getByText("Checkpoint pending")).toBeInTheDocument();
    expect(within(inspector).queryByTestId("publication-checks-observe")).not.toBeInTheDocument();
    expect(within(inspector).getByText("Unit tests")).toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
});

it("disables publication-check observation while another publication action is pending", async () => {
  const publicationCard = publicationCardForChecks();
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks("awaiting-merge"),
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "awaiting-merge",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  fixtureState.pendingMutationPath = "/target/sync";
  renderPage("/delivery/change-alpha/publication");
  const inspector = await screen.findByTestId("work-item-detail");

  try {
    fireEvent.click(within(inspector).getByText("Merge latest target into Change"));
    fireEvent.click(screen.getByText("Confirm target update"));
    const observe = within(inspector).getByTestId("publication-checks-observe") as HTMLElement & { disabled: boolean };
    await waitFor(() => expect(observe.disabled).toBe(true));
  } finally {
    fixtureState.pendingMutationRelease?.();
    fixtureState.pendingMutationPath = null;
    fixtureState.pendingMutationRelease = null;
  }
});

it("disables publication actions while publication-check observation is pending", async () => {
  const publicationCard = publicationCardForChecks();
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks("awaiting-merge"),
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "awaiting-merge",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  fixtureState.pendingPublicationChecksObservation = true;
  renderPage("/delivery/change-alpha/publication");
  const inspector = await screen.findByTestId("work-item-detail");

  try {
    fireEvent.click(within(inspector).getByTestId("publication-checks-observe"));
    const sync = within(inspector).getByText("Merge latest target into Change") as HTMLElement & { disabled: boolean };
    await waitFor(() => expect(sync.disabled).toBe(true));
    expect(
      fixtureState.requests.filter(({ url, method }) => method === "POST" && url.endsWith("/target/sync")),
    ).toHaveLength(0);
  } finally {
    fixtureState.pendingPublicationChecksRelease?.();
    fixtureState.pendingPublicationChecksObservation = false;
    fixtureState.pendingPublicationChecksRelease = null;
  }
});
