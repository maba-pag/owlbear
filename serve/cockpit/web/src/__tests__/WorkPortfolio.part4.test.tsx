import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type { CompletedChangeRecord } from "../api/workItems";
import {
  card,
  completed,
  detail,
  fixtureState,
  group,
  inputValue,
  installWorkPortfolioHarness,
  portfolio,
  publicationCardForChecks,
  publicationForChecks,
  readiness,
  receiptCompleted,
  renderPage,
  requirePresent,
} from "./workPortfolioHarness";

installWorkPortfolioHarness();

it("rejects an observation returned for a different exact head", async () => {
  fixtureState.publicationChecksResponse = {
    ...fixtureState.publicationChecksResponse,
    exact_commit: "2".repeat(40),
  };
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

  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(inspector).getByTestId("publication-checks-observe"));

  const error = await within(inspector).findByRole("alert");
  expect(error).toHaveTextContent("ERR_WORK_ITEM_PUBLICATION_CHECKS_OBSERVE");
  expect(error).toHaveTextContent("do not match the current Change published head");
  expect(within(inspector).queryByText("Unit tests")).not.toBeInTheDocument();
});

it("discloses provider checks omitted by the bounded response", async () => {
  fixtureState.publicationChecksResponse = {
    ...fixtureState.publicationChecksResponse,
    truncated_count: 1,
  };
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

  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(inspector).getByTestId("publication-checks-observe"));

  expect(await within(inspector).findByText("1 additional check not shown.")).toBeInTheDocument();
});

it("shows typed provider failure for publication-check observation", async () => {
  fixtureState.publicationChecksFailure = true;
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

  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(inspector).getByTestId("publication-checks-observe"));
  const error = await within(inspector).findByRole("alert");
  expect(error).toHaveTextContent("ERR_DELIVERY_PROVIDER_UNAVAILABLE");
  expect(error).toHaveTextContent("GitHub is unavailable");
});

it("keeps cached routed detail visible when a background refresh fails", async () => {
  vi.useFakeTimers();
  try {
    renderPage("/delivery/change-alpha/outcome%3AOUT-001");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    const detailView = screen.getByTestId("work-item-detail");
    fixtureState.portfolioFailure = true;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Showing the last successful refresh — live updates paused.");
    expect(alert).toHaveTextContent("Temporary polling failure");
    expect(alert).not.toHaveTextContent("Work portfolio is unavailable");
    expect(detailView).toBeInTheDocument();
    expect(screen.getByTestId("work-item-detail")).toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
}, 6_000);

it("shows stale Work Item detail state and retries the refresh in place", async () => {
  vi.useFakeTimers();
  try {
    renderPage("/delivery/change-alpha/outcome%3AOUT-001");
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByTestId("work-item-detail")).toBeInTheDocument();
    fixtureState.detailFailure = true;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Showing the last successful Work Item detail; live updates paused.");
    expect(alert).toHaveTextContent("Delivery runtime is absent: change-alpha");
    expect(screen.getByTestId("work-item-detail")).toBeInTheDocument();

    fixtureState.detailFailure = false;
    fireEvent.click(within(alert).getByText("Retry Work Item", { exact: true }));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(
      screen.queryByText("Showing the last successful Work Item detail; live updates paused."),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("work-item-detail")).toBeInTheDocument();
  } finally {
    vi.useRealTimers();
  }
}, 6_000);

it("keeps backend detail collapsed when a selected Work Item is unavailable", async () => {
  fixtureState.detailFailure = true;
  renderPage("/delivery/change-alpha/outcome%3AOUT-999");

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("This Work Item is unavailable.");
  expect(alert).toHaveTextContent("Technical evidence");
  const evidence = screen.getByText("Technical evidence").closest("details");
  expect(evidence).not.toHaveAttribute("open");
});

it("explains returned Design progress and labels evidence without raw enum text", async () => {
  fixtureState.currentDetail = detail({
    card: card({
      stage: "design",
      activity: {
        state: "idle",
        worker_role: null,
        started_at: null,
        task_id: null,
      },
      progress: {
        kind: "design-return",
        label: "Returned to Design",
        done: null,
        total: null,
      },
    }),
    return_context: {
      target: "design",
      reason: "The admitted authority changed.",
      locators: ["request:REQ-001"],
      source_boundary: "commit:abc123",
      preserved_commit: null,
    },
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent("Returned to Design");
  expect(inspector).toHaveTextContent("Next: Resume /design change-alpha.");
  expect(inspector).toHaveTextContent("Evidence: request:REQ-001");
  expect(inspector).toHaveTextContent("Source boundary: commit:abc123");
  expect(inspector).not.toHaveTextContent("Next: request:REQ-001");
});

it("does not prescribe Design for a return to Planning", async () => {
  fixtureState.currentDetail = detail({
    card: card({ stage: "planning" }),
    return_context: {
      target: "planning",
      reason: "The implementation plan needs revision.",
      locators: ["finding:F-001"],
      source_boundary: null,
      preserved_commit: null,
    },
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const inspector = await screen.findByTestId("work-item-detail");
  expect(inspector).toHaveTextContent("Returned to Planning");
  expect(inspector).toHaveTextContent("The implementation plan needs revision.");
  expect(inspector).not.toHaveTextContent("/design");
});

it("shows finalized and accepted merge heads as distinct identities", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    needs: "none",
    needs_headline: null,
    next_actor: "agent",
    next_step: "Record accepted completion",
    activity: {
      state: "ready",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Merge observed",
      done: null,
      total: null,
    },
    action: {
      kind: "observe-acceptance",
      label: "Complete accepted Change",
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
      merged_at: "2026-08-11T12:00:00Z",
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "acceptance",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  renderPage("/delivery/change-alpha/publication");

  const detailView = await screen.findByTestId("work-item-detail");
  expect(detailView).toHaveTextContent(`Finalized head${"1".repeat(40)}`);
  expect(detailView).toHaveTextContent(`Accepted merge commit${"2".repeat(40)}`);
  expect(detailView).not.toHaveTextContent(/ancestor|descendant|merge method/i);
  expect(detailView.querySelector("[data-section-tone]")).toHaveAttribute("data-section-tone", "success");
});

it("moves a completed selected Change into completed history instead of leaving a dead route", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    activity: {
      state: "ready",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Merge observed",
      done: null,
      total: null,
    },
    action: {
      kind: "observe-acceptance",
      label: "Complete accepted Change",
      command: null,
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "acceptance",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  fixtureState.currentDetail = detail({
    card: publicationCard,
    promise: "Publish the reviewed Change.",
    acceptance: [],
    commitments: [],
    tasks: [],
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
      merged_at: "2026-08-11T12:00:00Z",
    },
  });
  fixtureState.portfolioAfterPublication = portfolio([]);
  renderPage("/delivery/change-alpha/publication");
  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(inspector).getByText("Complete accepted Change"));

  expect(await screen.findByTestId("completed-history-workspace")).toHaveTextContent("Change history");
  await waitFor(() => expect(screen.getByTestId("test-location")).toHaveTextContent("/delivery/history"));
  expect(await screen.findByText("Portfolio redesign")).toBeInTheDocument();
});

it("closes live detail before entering completed history", async () => {
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByTestId("work-item-detail");

  fireEvent.click(screen.getByRole("button", { name: "Change history", exact: true }));

  await screen.findByTestId("completed-history-workspace");
  expect(screen.queryByTestId("work-item-detail")).not.toBeInTheDocument();
  await waitFor(() => {
    const openFlyout = Array.from(document.querySelectorAll("p-flyout")).find(
      (element) => (element as HTMLElement & { open: boolean }).open,
    );
    expect(openFlyout).toBeUndefined();
  });
  await waitFor(() => expect(screen.getByRole("button", { name: "Change history", exact: true })).toHaveFocus());
});

it("presents receipt-backed completion evidence explicitly", async () => {
  renderPage();
  fireEvent.click(screen.getByText("Change history"));
  const record = await screen.findByTestId("completed-change-record");
  fireEvent.click(within(record).getByRole("button", { name: "Inspect Portfolio redesign" }));

  const detailView = await screen.findByTestId("completed-change-detail");
  const openFlyout = Array.from(document.querySelectorAll("p-flyout")).find(
    (element) => (element as HTMLElement & { open: boolean }).open,
  );
  expect(openFlyout).toBeInTheDocument();
  expect(detailView).toHaveTextContent("Purpose");
  expect(detailView).toHaveTextContent("Give operators a clear view of grouped Delivery work.");
  expect(detailView).toHaveTextContent("Delivered outcomes");
  expect(detailView).toHaveTextContent("Ship the grouped Delivery workspace");
  expect(detailView).toHaveTextContent("Accepted delivery");
  expect(detailView).toHaveTextContent("Completion receipt");
  expect(detailView).toHaveTextContent("owlbear/example");
});

it("refreshes current delivery immediately after returning from completed history", async () => {
  fixtureState.currentPortfolio = portfolio([group({ title: "Initial delivery" })]);
  renderPage();
  await screen.findByRole("heading", { name: "Initial delivery", exact: true });

  fireEvent.click(screen.getByRole("button", { name: "Change history", exact: true }));
  await screen.findByTestId("completed-history-workspace");
  fixtureState.currentPortfolio = portfolio([group({ title: "Refreshed delivery" })]);
  const requestsBeforeReturn = fixtureState.requests.filter(
    ({ method, url }) => method === "GET" && url === "/api/work-items",
  ).length;

  fireEvent.click(screen.getByRole("button", { name: "Current delivery", exact: true }));
  await screen.findByRole("heading", {
    name: "Refreshed delivery",
    exact: true,
  });

  const requestsAfterReturn = fixtureState.requests.filter(
    ({ method, url }) => method === "GET" && url === "/api/work-items",
  ).length;
  expect(requestsAfterReturn).toBeGreaterThan(requestsBeforeReturn);
});

it("explains when completed history is empty", async () => {
  fixtureState.completedRecords = [];
  renderPage();
  fireEvent.click(screen.getByText("Change history"));

  const emptyState = await screen.findByTestId("completed-history-empty-state");
  expect(emptyState).toHaveTextContent("No changes in history yet");
  expect(emptyState).toHaveTextContent(
    "Completed and abandoned Changes will appear here with their retained evidence.",
  );
});

it("distinguishes no matching completed history and clears the search", async () => {
  fixtureState.completedRecords = [completed];
  const { container } = renderPage();
  fireEvent.click(screen.getByText("Change history"));
  await screen.findByTestId("completed-change-record");

  const search = container.querySelector("p-input-search");
  expect(search).not.toBeNull();
  inputValue(search as Element, "unmatched history");

  const emptyState = await screen.findByTestId("completed-history-empty-state");
  expect(emptyState).toHaveTextContent('No changes match "unmatched history"');
  expect(emptyState).toHaveTextContent("Try a different search or clear the current search.");
  fireEvent.click(within(emptyState).getByText("Clear search", { exact: true }));

  await waitFor(() => expect(screen.getByTestId("completed-change-record")).toBeInTheDocument());
});

it("marks previous completed history results while a search is pending", async () => {
  fixtureState.completedRecords = [completed, receiptCompleted];
  fixtureState.completedHistorySearchPending = true;
  const { container } = renderPage();
  fireEvent.click(screen.getByText("Change history"));
  await waitFor(() => expect(screen.getAllByTestId("completed-change-record")).toHaveLength(2));

  try {
    const search = container.querySelector("p-input-search");
    expect(search).not.toBeNull();
    inputValue(search as Element, "unmatched history");

    const staleStatus = await screen.findByTestId("completed-history-stale-status");
    expect(staleStatus).toHaveTextContent("Previous results are shown until the search finishes.");
    expect(screen.getByTestId("completed-history-results")).toHaveAttribute("aria-busy", "true");
    expect(screen.getAllByTestId("completed-change-record")).toHaveLength(2);
    expect(screen.getAllByTestId("completed-change-record")[0]).toHaveAttribute("data-stale", "true");
  } finally {
    fixtureState.completedHistorySearchRelease?.();
    fixtureState.completedHistorySearchPending = false;
    fixtureState.completedHistorySearchRelease = null;
  }

  await screen.findByTestId("completed-history-empty-state");
});

it("retains previous completed history when a search fails", async () => {
  fixtureState.completedRecords = [completed, receiptCompleted];
  fixtureState.completedHistoryNextCursor = "page-2";
  fixtureState.completedHistorySearchFailuresRemaining = 1;
  fixtureState.completedHistorySearchRecords = [receiptCompleted];
  const { container } = renderPage();
  fireEvent.click(screen.getByText("Change history"));
  await waitFor(() => expect(screen.getAllByTestId("completed-change-record")).toHaveLength(2));

  const search = container.querySelector("p-input-search");
  expect(search).not.toBeNull();
  inputValue(search as Element, "Beta");

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Change history is unavailable.");
  expect(screen.getAllByTestId("completed-change-record")).toHaveLength(2);
  expect(screen.getByTestId("completed-history-stale-status")).toHaveTextContent(
    "Previous results are shown while this search is retried.",
  );
  const loadMore = screen.getByText("Load more", { exact: true }).closest("p-button") as HTMLElement & {
    disabled?: boolean;
  };
  expect(loadMore.disabled).toBe(true);

  fireEvent.click(within(alert).getByText("Retry history", { exact: true }));
  await screen.findByText("Receipt-backed delivery", { exact: true });
  expect(screen.getAllByTestId("completed-change-record")).toHaveLength(1);
  expect(screen.queryByTestId("completed-history-stale-status")).not.toBeInTheDocument();
});

it("disables load more while a completed history search is pending", async () => {
  fixtureState.completedRecords = [completed, receiptCompleted];
  fixtureState.completedHistoryNextCursor = "page-2";
  fixtureState.completedHistorySearchPending = true;
  const { container } = renderPage();
  fireEvent.click(screen.getByText("Change history"));
  await waitFor(() => expect(screen.getAllByTestId("completed-change-record")).toHaveLength(2));

  try {
    const search = container.querySelector("p-input-search");
    expect(search).not.toBeNull();
    inputValue(search as Element, "Beta");
    await screen.findByTestId("completed-history-stale-status");

    const loadMore = screen.getByTestId("completed-history-load-more").closest("p-button") as HTMLElement & {
      disabled?: boolean;
    };
    expect(loadMore.disabled).toBe(true);
  } finally {
    fixtureState.completedHistorySearchRelease?.();
    fixtureState.completedHistorySearchPending = false;
    fixtureState.completedHistorySearchRelease = null;
  }
});

it("appends paginated results for a completed history search", async () => {
  fixtureState.completedHistorySearchRecords = [completed];
  fixtureState.completedHistorySearchNextCursor = "search-page-2";
  fixtureState.completedHistorySearchPageRecords = [receiptCompleted];
  const { container } = renderPage();
  fireEvent.click(screen.getByText("Change history"));
  await waitFor(() => expect(screen.getAllByTestId("completed-change-record")).toHaveLength(1));

  const search = container.querySelector("p-input-search");
  expect(search).not.toBeNull();
  inputValue(search as Element, "Beta");
  await screen.findByTestId("completed-history-load-more");

  fireEvent.click(screen.getByTestId("completed-history-load-more"));
  await screen.findByText("Receipt-backed delivery", { exact: true });
  expect(screen.getAllByTestId("completed-change-record")).toHaveLength(2);
  expect(
    fixtureState.requests.filter(
      ({ url, method }) =>
        method === "GET" && url === "/api/work-items/completed/search?query=Beta&cursor=search-page-2",
    ),
  ).toHaveLength(1);
  await waitFor(() => expect(screen.getByTestId("completed-history-workspace")).toHaveFocus());
});

it("closes completed history detail when a settled search removes the selected record", async () => {
  fixtureState.completedRecords = [completed, receiptCompleted];
  fixtureState.completedHistorySearchPending = true;
  const { container } = renderPage();
  fireEvent.click(screen.getByText("Change history"));
  await waitFor(() => expect(screen.getAllByTestId("completed-change-record")).toHaveLength(2));

  try {
    const search = container.querySelector("p-input-search");
    expect(search).not.toBeNull();
    inputValue(search as Element, "unmatched history");
    await screen.findByTestId("completed-history-stale-status");

    const record = screen
      .getAllByTestId("completed-change-record")
      .find((candidate) => candidate.textContent?.includes("Portfolio redesign"));
    expect(record).toBeDefined();
    fireEvent.click(
      within(requirePresent(record)).getByRole("button", {
        name: "Inspect Portfolio redesign",
      }),
    );
    await screen.findByTestId("completed-change-detail");

    fixtureState.completedHistorySearchRelease?.();
    fixtureState.completedHistorySearchPending = false;
    await screen.findByTestId("completed-history-empty-state");
    await waitFor(() => {
      const openFlyout = Array.from(document.querySelectorAll("p-flyout")).find(
        (element) => (element as HTMLElement & { open: boolean }).open,
      );
      expect(openFlyout).toBeUndefined();
    });
  } finally {
    fixtureState.completedHistorySearchRelease?.();
    fixtureState.completedHistorySearchPending = false;
    fixtureState.completedHistorySearchRelease = null;
  }
});

it("debounces completed history search requests while typing", async () => {
  fixtureState.completedRecords = [completed, receiptCompleted];
  const { container } = renderPage();
  fireEvent.click(screen.getByText("Change history"));
  await waitFor(() => expect(screen.getAllByTestId("completed-change-record")).toHaveLength(2));

  const search = container.querySelector("p-input-search");
  expect(search).not.toBeNull();
  for (const value of ["a", "al", "alp", "alph", "alpha"]) inputValue(search as Element, value);

  const searchRequests = () =>
    fixtureState.requests.filter(
      ({ url, method }) => method === "GET" && url.startsWith("/api/work-items/completed/search?"),
    );
  await waitFor(() => expect(searchRequests()).toHaveLength(1), {
    timeout: 2_000,
  });
  expect(searchRequests()[0].url).toContain("query=alpha");
});

it("retries failed completed history detail in place", async () => {
  fixtureState.completedRecords = [completed];
  fixtureState.completedDetailFailuresRemaining = 1;
  renderPage();
  fireEvent.click(screen.getByText("Change history"));
  const record = await screen.findByTestId("completed-change-record");
  fireEvent.click(within(record).getByRole("button", { name: "Inspect Portfolio redesign" }));

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Completion detail is unavailable.");
  fireEvent.click(within(alert).getByText("Retry completion detail", { exact: true }));

  await screen.findByTestId("completed-change-detail");
  expect(screen.getByTestId("completed-change-detail")).toHaveTextContent("Accepted delivery");
  expect(
    fixtureState.requests.filter(
      ({ url, method }) => method === "GET" && url.includes("/api/work-items/completed/change-alpha?"),
    ).length,
  ).toBe(2);
});

it("closes a listed completion when its detail is confirmed missing", async () => {
  fixtureState.completedRecords = [completed];
  renderPage();
  fireEvent.click(screen.getByText("Change history"));
  const record = await screen.findByTestId("completed-change-record");
  const trigger = within(record).getByRole("button", {
    name: "Inspect Portfolio redesign",
  });
  fixtureState.completedDetailNotFound = true;
  fireEvent.click(trigger);

  await waitFor(() => {
    const openFlyout = Array.from(document.querySelectorAll("p-flyout")).find(
      (element) => (element as HTMLElement & { open: boolean }).open,
    );
    expect(openFlyout).toBeUndefined();
  });
  await waitFor(() => expect(trigger).toHaveFocus());
});

it("closes a missing completion despite a failed history page load", async () => {
  fixtureState.completedRecords = [completed];
  fixtureState.completedHistoryNextCursor = "page-2";
  fixtureState.completedHistoryPageFailuresRemaining = 1;
  renderPage();
  fireEvent.click(screen.getByText("Change history"));
  const record = await screen.findByTestId("completed-change-record");
  const trigger = within(record).getByRole("button", {
    name: "Inspect Portfolio redesign",
  });

  fireEvent.click(screen.getByText("Load more", { exact: true }));
  await screen.findByText("Retry loading more", { exact: true });
  fixtureState.completedDetailNotFound = true;
  fireEvent.click(trigger);

  await waitFor(() => {
    const openFlyout = Array.from(document.querySelectorAll("p-flyout")).find(
      (element) => (element as HTMLElement & { open: boolean }).open,
    );
    expect(openFlyout).toBeUndefined();
  });
  await waitFor(() => expect(trigger).toHaveFocus());
});

it("returns focus to history after appending the final page", async () => {
  const nextRecord: CompletedChangeRecord = {
    ...completed,
    change_id: "change-beta",
    completion_id: "f".repeat(64),
    title: "Second historical change",
  };
  fixtureState.completedRecords = [completed];
  fixtureState.completedHistoryNextCursor = "page-2";
  fixtureState.completedHistoryPageRecords = [nextRecord];
  renderPage();
  fireEvent.click(screen.getByText("Change history"));
  await screen.findByTestId("completed-history-load-more");

  fireEvent.click(screen.getByTestId("completed-history-load-more"));
  await screen.findByText("Second historical change", { exact: true });
  await waitFor(() => expect(screen.getByTestId("completed-history-workspace")).toHaveFocus());
});

it("keeps a valid later-page completion deep link open", async () => {
  fixtureState.completedRecords = [completed];
  fixtureState.completedDetailRecord = receiptCompleted;
  fixtureState.completedHistoryNextCursor = "page-2";
  renderPage(`/delivery/history/${receiptCompleted.change_id}/${receiptCompleted.completion_id}`);

  const detailView = await screen.findByTestId("completed-change-detail");
  expect(detailView).toHaveTextContent("Receipt-backed delivery");
  expect(screen.getByTestId("completed-history-workspace")).toBeInTheDocument();
});

it("keeps a deep-linked completion open while the initial history list fails", async () => {
  fixtureState.completedHistoryFailuresRemaining = 1;
  renderPage(`/delivery/history/${completed.change_id}/${completed.completion_id}`);

  const detailView = await screen.findByTestId("completed-change-detail");
  expect(detailView).toHaveTextContent("Accepted delivery");
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Change history is unavailable.");

  fireEvent.click(within(alert).getByText("Retry history", { exact: true }));
  await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  expect(screen.getByTestId("completed-change-detail")).toBe(detailView);

  fireEvent.click(within(detailView).getByText("Close", { exact: true }));
  await waitFor(() => expect(screen.getByTestId("completed-history-workspace")).toHaveFocus());
});

it("rejects a completion detail response with the wrong identity", async () => {
  fixtureState.completedDetailMismatch = receiptCompleted;
  renderPage(`/delivery/history/${completed.change_id}/${completed.completion_id}`);

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Completion detail is unavailable.");
  expect(alert).toHaveTextContent("did not match the requested identity");
  expect(screen.queryByText("Receipt-backed delivery")).not.toBeInTheDocument();

  fixtureState.completedDetailMismatch = null;
  fireEvent.click(within(alert).getByText("Retry completion detail", { exact: true }));
  const detailView = await screen.findByTestId("completed-change-detail");
  expect(detailView).toHaveTextContent("Accepted delivery");
});

it("retries a failed completed history page without resetting loaded records", async () => {
  const nextRecord: CompletedChangeRecord = {
    ...completed,
    change_id: "change-beta",
    completion_id: "f".repeat(64),
    title: "Second historical change",
  };
  fixtureState.completedRecords = [completed];
  fixtureState.completedHistoryNextCursor = "page-2";
  fixtureState.completedHistoryPageRecords = [nextRecord];
  fixtureState.completedHistoryPageFailuresRemaining = 1;
  renderPage();
  fireEvent.click(screen.getByText("Change history"));
  await screen.findByTestId("completed-change-record");
  expect(screen.getByTestId("completed-history-count")).toHaveTextContent("2");

  fireEvent.click(screen.getByText("Load more", { exact: true }));
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Could not load more Change history.");
  expect(within(alert).getByText("Retry loading more", { exact: true })).toBeInTheDocument();
  expect(screen.getAllByTestId("completed-change-record")).toHaveLength(1);

  fireEvent.click(within(alert).getByText("Retry loading more", { exact: true }));
  await screen.findByText("Second historical change", { exact: true });
  expect(screen.getAllByTestId("completed-change-record")).toHaveLength(2);
  expect(
    fixtureState.requests.filter(
      ({ url, method }) => method === "GET" && url === "/api/work-items/completed?cursor=page-2",
    ),
  ).toHaveLength(2);
});

it("presents receipt completion identities without graph claims", async () => {
  fixtureState.completedRecords = [receiptCompleted];
  renderPage();
  fireEvent.click(screen.getByText("Change history"));
  const record = await screen.findByTestId("completed-change-record");
  const pullRequest = within(record).getByRole("link", { name: "PR #42" });
  expect(pullRequest).toHaveAttribute("href", "https://github.com/owlbear/example/pull/42");
  expect(within(record).getByText(/Aug 11, 2026/)).toBeInTheDocument();
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
  fireEvent.click(within(record).getByRole("button", { name: "Copy accepted merge commit" }));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith("4".repeat(40)));
  fireEvent.click(
    within(record).getByRole("button", {
      name: "Inspect Receipt-backed delivery",
    }),
  );

  const detailView = await screen.findByTestId("completed-change-detail");
  expect(detailView).toHaveTextContent("Purpose");
  expect(detailView).toHaveTextContent("Record the accepted change with durable evidence.");
  expect(detailView).toHaveTextContent("Delivered outcomes");
  expect(detailView).toHaveTextContent("Accept the merged Delivery change");
  expect(detailView).toHaveTextContent("Accepted delivery");
  expect(detailView).toHaveTextContent("Completion receipt");
  expect(detailView).toHaveTextContent("owlbear/example");
  expect(detailView).toHaveTextContent("#42");
  expect(detailView).toHaveTextContent("main");
  expect(detailView).toHaveTextContent("Finalized Change head");
  expect(detailView).toHaveTextContent("3".repeat(40));
  expect(detailView).toHaveTextContent("Accepted merge commit");
  expect(detailView).toHaveTextContent("4".repeat(40));
  expect(within(detailView).getByRole("button", { name: "Copy completion ID" })).toBeInTheDocument();
  expect(
    within(detailView).getByRole("button", {
      name: "Copy finalized Change head",
    }),
  ).toBeInTheDocument();
  expect(detailView).not.toHaveTextContent(/ancestor|descendant|merged into|merge method/i);
});

it("keeps current delivery open when only the selected publication card disappears", async () => {
  const publicationCard = card({
    item_key: "publication",
    work_item_id: "change-alpha",
    scope: "change-publication",
    title: "Change publication",
    stage: null,
    activity: {
      state: "ready",
      worker_role: null,
      started_at: null,
      task_id: null,
    },
    progress: {
      kind: "publication",
      label: "Merge observed",
      done: null,
      total: null,
    },
    action: {
      kind: "observe-acceptance",
      label: "Complete accepted Change",
      command: null,
    },
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "acceptance",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  fixtureState.currentDetail = detail({
    card: publicationCard,
    promise: "Publish the reviewed Change.",
    acceptance: [],
    commitments: [],
    tasks: [],
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
      merged_at: "2026-08-11T12:00:00Z",
    },
  });
  fixtureState.portfolioAfterPublication = portfolio([group({ items: [card({ title: "Returned outcome" })] })]);
  renderPage("/delivery/change-alpha/publication");
  const inspector = await screen.findByTestId("work-item-detail");
  fireEvent.click(within(inspector).getByText("Complete accepted Change"));

  expect(await screen.findByTestId("work-portfolio-table")).toHaveTextContent("Returned outcome");
  expect(screen.queryByTestId("completed-history-workspace")).not.toBeInTheDocument();
});

it("renders engine readiness without recomputing eligibility", async () => {
  fixtureState.currentDetail = detail({
    readiness: readiness({
      status: "blocked",
      reason_code: "workspace-dirty",
      next_actor: "you",
      checks_state: "not-run",
    }),
  });
  renderPage();
  const table = await screen.findByTestId("work-portfolio-table");
  fireEvent.click(within(table).getAllByRole("link", { name: /Delivery foundation/ })[0]);

  const inspector = await screen.findByTestId("work-item-detail");
  const readinessPanel = within(inspector).getByTestId("delivery-readiness");
  expect(within(readinessPanel).getByTestId("readiness-status")).toHaveTextContent("Blocked");
  expect(within(readinessPanel).getByTestId("readiness-checks-state")).toHaveTextContent("Checks: Not run");
  expect(readinessPanel).toHaveTextContent("Managed workspace preflight is blocked by local changes.");
  expect(within(readinessPanel).getByTestId("readiness-not-executable")).toBeInTheDocument();
  expect(readinessPanel).toHaveTextContent("1".repeat(40));
});

it("reports checks that have not run without implying a pass", async () => {
  fixtureState.currentDetail = detail({
    readiness: readiness({
      status: "ready",
      reason_code: "ready",
      checks_state: "not-run",
    }),
  });
  renderPage();
  const table = await screen.findByTestId("work-portfolio-table");
  fireEvent.click(within(table).getAllByRole("link", { name: /Delivery foundation/ })[0]);

  const readinessPanel = within(await screen.findByTestId("work-item-detail")).getByTestId("delivery-readiness");
  expect(within(readinessPanel).getByTestId("readiness-checks-state")).toHaveTextContent("Not run");
  expect(readinessPanel).not.toHaveTextContent("Passed");
});

it("shows the applicable finalization attempt retained by readiness", async () => {
  fixtureState.currentDetail = detail({
    readiness: readiness({
      status: "blocked",
      reason_code: "workspace-preflight-failed",
      checks_state: "failed",
      last_attempt: {
        applicability: "current",
        report: {
          report_id: "e".repeat(64),
          sequence: 3,
          observed_at: "2026-08-12T09:00:00Z",
          summary: "Managed workspace preflight did not pass.",
          producer: "finalization-diagnostic",
          request: {
            change_id: "change-alpha",
            attempt_key: "attempt-3",
            category: "custody-preflight",
            code: "workspace-preflight-failed",
            checks_state: "not-run",
            check_id: null,
            exit_status: null,
            procedure_id: null,
            proof_fingerprint_before: null,
            proof_fingerprint_after: null,
            paths: [],
          },
        },
      },
    }),
  });
  renderPage();
  const table = await screen.findByTestId("work-portfolio-table");
  fireEvent.click(within(table).getAllByRole("link", { name: /Delivery foundation/ })[0]);

  const attempt = within(await screen.findByTestId("work-item-detail")).getByTestId("readiness-last-attempt");
  expect(within(attempt).getByTestId("readiness-attempt-applicability")).toHaveTextContent("Applies to this candidate");
  expect(attempt).toHaveTextContent("Managed workspace preflight did not pass.");
  expect(attempt).toHaveTextContent("workspace-preflight-failed");
  expect(attempt).toHaveTextContent("Not run");
});

it("reports the historical applicability of a finalization attempt from an earlier candidate", async () => {
  fixtureState.currentDetail = detail({
    readiness: readiness({
      status: "ready",
      reason_code: "ready",
      checks_state: "not-run",
      last_attempt: {
        applicability: "historical",
        report: {
          report_id: "a".repeat(64),
          sequence: 2,
          observed_at: "2026-08-10T09:00:00Z",
          summary: "Maintained checks failed on an earlier candidate.",
          producer: "finalization-diagnostic",
          request: {
            change_id: "change-alpha",
            attempt_key: "attempt-2",
            category: "maintained-check",
            code: "maintained-check-failed",
            checks_state: "failed",
            check_id: "uv run test",
            exit_status: 1,
            procedure_id: null,
            proof_fingerprint_before: null,
            proof_fingerprint_after: null,
            paths: ["serve/delivery"],
          },
        },
      },
    }),
  });
  renderPage();
  const table = await screen.findByTestId("work-portfolio-table");
  fireEvent.click(within(table).getAllByRole("link", { name: /Delivery foundation/ })[0]);

  const attempt = within(await screen.findByTestId("work-item-detail")).getByTestId("readiness-last-attempt");
  expect(within(attempt).getByTestId("readiness-attempt-applicability")).toHaveTextContent("Historical");
  expect(attempt).toHaveTextContent("Maintained checks failed on an earlier candidate.");
  expect(attempt).toHaveTextContent("Failed");
});

it("renders proof-mutation finalization evidence", async () => {
  fixtureState.currentDetail = detail({
    readiness: readiness({
      status: "blocked",
      reason_code: "finalization-failed",
      checks_state: "failed",
      last_attempt: {
        applicability: "current",
        report: {
          report_id: "b".repeat(64),
          sequence: 4,
          observed_at: "2026-08-13T09:00:00Z",
          summary: "The maintained proof procedure mutated the managed workspace.",
          producer: "finalization-diagnostic",
          request: {
            change_id: "change-alpha",
            attempt_key: "attempt-4",
            category: "proof-mutation",
            code: "proof-mutated-worktree",
            checks_state: "failed",
            check_id: null,
            exit_status: 0,
            procedure_id: "proof-procedure",
            proof_fingerprint_before: "c".repeat(64),
            proof_fingerprint_after: "d".repeat(64),
            paths: ["serve/delivery/src/owlbear_delivery"],
          },
        },
      },
    }),
  });
  renderPage();
  const table = await screen.findByTestId("work-portfolio-table");
  fireEvent.click(within(table).getAllByRole("link", { name: /Delivery foundation/ })[0]);

  const attempt = within(await screen.findByTestId("work-item-detail")).getByTestId("readiness-last-attempt");
  expect(attempt).toHaveTextContent("proof-mutation");
  expect(attempt).toHaveTextContent("proof-mutated-worktree");
  expect(attempt).toHaveTextContent("proof-procedure");
  expect(attempt).toHaveTextContent("c".repeat(64));
  expect(attempt).toHaveTextContent("d".repeat(64));
});

it("reports engine readiness rather than the publication phase for a dirty candidate", async () => {
  const publicationCard = publicationCardForChecks({
    publication_phase: "ready-for-finalization",
    next_step: "Finalize the reviewed Change",
    progress: {
      kind: "publication",
      label: "Reviewed Change awaiting finalization",
      done: null,
      total: null,
    },
    readiness: readiness({
      status: "blocked",
      reason_code: "workspace-dirty",
      next_actor: "you",
      checks_state: "not-run",
    }),
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "publication",
      outcome_completed: 2,
      items: [publicationCard],
    }),
  ]);
  fixtureState.currentDetail = detail({
    card: publicationCard,
    publication: publicationForChecks("ready-for-finalization"),
    readiness: readiness({
      status: "blocked",
      reason_code: "workspace-dirty",
      next_actor: "you",
      checks_state: "not-run",
    }),
  });
  renderPage();

  const row = await screen.findByLabelText("Change publication for Portfolio redesign");
  expect(row.querySelector("[data-status-tone]")).toHaveTextContent("Blocked");
  expect(row).toHaveTextContent("Ready for finalization");

  fireEvent.click(within(row).getByRole("link", { name: "Publication" }));
  const inspector = await screen.findByTestId("work-item-detail");
  expect(within(inspector).getByTestId("publication-readiness-status")).toHaveTextContent("Blocked");
  expect(inspector).toHaveTextContent("Ready for finalization");
  expect(within(inspector).getByTestId("readiness-status")).toHaveTextContent("Blocked");
  expect(within(inspector).getByTestId("readiness-not-executable")).toBeInTheDocument();
});

it("reports a clean finalization candidate as ready and a running one as running", async () => {
  const readyCard = publicationCardForChecks({
    publication_phase: "ready-for-finalization",
    readiness: readiness({
      status: "ready",
      operation: "finalize",
      executable: true,
      reason_code: "ready",
      next_actor: "agent",
      action: {
        kind: "finalize",
        label: "Finalize the reviewed Change",
        command: "/finalize-change change-alpha",
      },
    }),
  });
  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "publication",
      outcome_completed: 2,
      items: [readyCard],
    }),
  ]);
  const { unmount } = renderPage();
  const readyRow = await screen.findByLabelText("Change publication for Portfolio redesign");
  expect(readyRow.querySelector("[data-status-tone]")).toHaveTextContent("Ready");
  expect(readyRow).toHaveTextContent("Ready for finalization");
  unmount();

  fixtureState.currentPortfolio = portfolio([
    group({
      lifecycle: "publication",
      outcome_completed: 2,
      items: [
        publicationCardForChecks({
          publication_phase: "ready-for-finalization",
          readiness: readiness({
            status: "running",
            reason_code: "active-custody",
            next_actor: "agent",
          }),
        }),
      ],
    }),
  ]);
  renderPage();
  const runningRow = await screen.findByLabelText("Change publication for Portfolio redesign");
  expect(runningRow.querySelector("[data-status-tone]")).toHaveTextContent("Running");
  expect(runningRow).toHaveTextContent("Ready for finalization");
});
